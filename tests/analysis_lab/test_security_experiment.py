"""
Unit tests for SecurityExperiment and BMP structural pattern guard.
"""

import struct
from unittest.mock import MagicMock
import pytest

from src.analysis_lab.security_experiment import SecurityExperiment
from src.analyzers.security_evaluator import SecurityEvaluator


def _create_valid_bmp(
    width: int = 2,
    height: int = 2,
    bpp: int = 24,
    comp: int = 0,
    corrupt_size: bool = False,
    corrupt_sig: bool = False,
    planes: int = 1,
    dib_size: int = 40,
) -> bytes:
    """Helper to synthesize BMP byte sequences for behavioral testing."""
    row_bytes = (width * bpp + 7) // 8
    row_stride = ((row_bytes + 3) // 4) * 4
    pixel_len = row_stride * abs(height)
    file_size = 54 + pixel_len
    if corrupt_size:
        file_size += 999

    sig = b"XX" if corrupt_sig else b"BM"
    header = struct.pack(
        "<2sIHHI IiiHHIIiiII",
        sig,
        file_size,
        0,
        0,
        54,
        dib_size,
        width,
        height,
        planes,
        bpp,
        comp,
        pixel_len,
        0,
        0,
        0,
        0,
    )
    pixels = b"\x80" * pixel_len
    return header + pixels


class TestSecurityExperiment:
    """Tests for SecurityExperiment decoupled diffusion runner."""

    def test_type_validation_on_payload(self):
        with pytest.raises(TypeError, match="payload must be bytes or bytearray"):
            SecurityExperiment(payload="not bytes")  # type: ignore[arg-type]

    def test_zero_byte_skip_guard(self):
        exp = SecurityExperiment(payload=b"")
        results = exp.run()

        assert len(results) == 6
        for name, metrics in results.items():
            assert metrics.status == "SKIPPED"
            assert metrics.avalanche_effect_pct is None
            assert metrics.key_sensitivity_pct is None
            assert not metrics.ecb_weakness_analyzed
            assert "Diffusion metrics require non-empty payload" in str(metrics.notes)

    def test_non_bmp_text_payload_guarded(self):
        payload = b"Plain text file: diffusion evaluated but BMP structural test guarded."
        exp = SecurityExperiment(payload=payload)
        results = exp.run()

        assert len(results) == 6
        for name, metrics in results.items():
            assert metrics.status == "SUCCESS"
            assert metrics.avalanche_effect_pct is not None
            assert 0.0 <= metrics.avalanche_effect_pct <= 100.0
            assert metrics.key_sensitivity_pct is not None
            assert 0.0 <= metrics.key_sensitivity_pct <= 100.0
            assert not metrics.ecb_weakness_analyzed
            assert "Structural pattern test is specific to 24-bpp uncompressed BMP images" in str(
                metrics.notes
            )

    def test_valid_supported_bmp_invokes_ecb_weakness(self):
        bmp_payload = _create_valid_bmp(width=2, height=2, bpp=24, comp=0)
        mock_evaluator = MagicMock(spec=SecurityEvaluator)
        mock_evaluator.calculate_avalanche_effect.return_value = 52.5
        mock_evaluator.test_key_sensitivity.return_value = 49.0
        mock_evaluator.test_ecb_weakness.return_value = {
            "original_header": bmp_payload[:54],
            "original_pixel_data": bmp_payload[54:],
            "ecb_ciphertext": b"\xAA" * 16,
            "cbc_ciphertext": b"\xBB" * 16,
            "bmp_trailing_data": b"",
        }

        exp = SecurityExperiment(payload=bmp_payload, security_evaluator=mock_evaluator)
        metrics = exp.evaluate_configuration(
            {"algorithm": "AES", "key_size": 128, "mode": "CBC"}
        )

        assert metrics.status == "SUCCESS"
        assert metrics.ecb_weakness_analyzed
        assert "24-bpp uncompressed BMP analyzed" in str(metrics.notes)
        assert mock_evaluator.test_ecb_weakness.called

    def test_bmp_invalid_signature_guarded(self):
        # Starts with b"XX" instead of b"BM"
        corrupt_sig_bmp = _create_valid_bmp(corrupt_sig=True)
        mock_evaluator = MagicMock(spec=SecurityEvaluator)
        mock_evaluator.calculate_avalanche_effect.return_value = 50.0
        mock_evaluator.test_key_sensitivity.return_value = 50.0

        exp = SecurityExperiment(payload=corrupt_sig_bmp, security_evaluator=mock_evaluator)
        metrics = exp.evaluate_configuration(
            {"algorithm": "AES", "key_size": 128, "mode": "ECB"}
        )

        assert metrics.status == "SUCCESS"
        assert not metrics.ecb_weakness_analyzed
        assert not mock_evaluator.test_ecb_weakness.called
        assert "Structural pattern test is specific to 24-bpp uncompressed BMP images" in str(
            metrics.notes
        )

    def test_bmp_wrong_bpp_guarded(self):
        # 32 bpp instead of 24 bpp
        wrong_bpp_bmp = _create_valid_bmp(bpp=32)
        mock_evaluator = MagicMock(spec=SecurityEvaluator)
        mock_evaluator.calculate_avalanche_effect.return_value = 50.0
        mock_evaluator.test_key_sensitivity.return_value = 50.0

        exp = SecurityExperiment(payload=wrong_bpp_bmp, security_evaluator=mock_evaluator)
        metrics = exp.evaluate_configuration(
            {"algorithm": "AES", "key_size": 128, "mode": "ECB"}
        )

        assert metrics.status == "SUCCESS"
        assert not metrics.ecb_weakness_analyzed
        assert not mock_evaluator.test_ecb_weakness.called
        assert "Structural pattern test is specific to 24-bpp uncompressed BMP images" in str(
            metrics.notes
        )

    def test_bmp_compressed_guarded(self):
        # comp=1 (RLE-8) instead of comp=0
        comp_bmp = _create_valid_bmp(comp=1)
        mock_evaluator = MagicMock(spec=SecurityEvaluator)
        mock_evaluator.calculate_avalanche_effect.return_value = 50.0
        mock_evaluator.test_key_sensitivity.return_value = 50.0

        exp = SecurityExperiment(payload=comp_bmp, security_evaluator=mock_evaluator)
        metrics = exp.evaluate_configuration(
            {"algorithm": "AES", "key_size": 128, "mode": "ECB"}
        )

        assert metrics.status == "SUCCESS"
        assert not metrics.ecb_weakness_analyzed
        assert not mock_evaluator.test_ecb_weakness.called

    def test_bmp_truncated_header_guarded(self):
        # Truncated to 40 bytes (< 54 bytes)
        truncated_bmp = b"BM" + b"\x00" * 38
        mock_evaluator = MagicMock(spec=SecurityEvaluator)
        mock_evaluator.calculate_avalanche_effect.return_value = 50.0
        mock_evaluator.test_key_sensitivity.return_value = 50.0

        exp = SecurityExperiment(payload=truncated_bmp, security_evaluator=mock_evaluator)
        metrics = exp.evaluate_configuration(
            {"algorithm": "AES", "key_size": 128, "mode": "ECB"}
        )

        assert metrics.status == "SUCCESS"
        assert not metrics.ecb_weakness_analyzed
        assert not mock_evaluator.test_ecb_weakness.called

    def test_bmp_corrupt_file_size_field_guarded(self):
        corrupt_size_bmp = _create_valid_bmp(corrupt_size=True)
        mock_evaluator = MagicMock(spec=SecurityEvaluator)
        mock_evaluator.calculate_avalanche_effect.return_value = 50.0
        mock_evaluator.test_key_sensitivity.return_value = 50.0

        exp = SecurityExperiment(payload=corrupt_size_bmp, security_evaluator=mock_evaluator)
        metrics = exp.evaluate_configuration(
            {"algorithm": "AES", "key_size": 128, "mode": "CBC"}
        )

        assert metrics.status == "SUCCESS"
        assert not metrics.ecb_weakness_analyzed
        assert not mock_evaluator.test_ecb_weakness.called

    def test_exception_handling_records_failed(self):
        payload = b"Valid test payload"
        mock_evaluator = MagicMock(spec=SecurityEvaluator)
        mock_evaluator.calculate_avalanche_effect.side_effect = ValueError(
            "Simulated avalanche computation error"
        )

        exp = SecurityExperiment(payload=payload, security_evaluator=mock_evaluator)
        metrics = exp.evaluate_configuration(
            {"algorithm": "AES", "key_size": 128, "mode": "CBC"}
        )

        assert metrics.status == "FAILED"
        assert metrics.avalanche_effect_pct is None
        assert "Security evaluation failed: Simulated avalanche computation error" in str(
            metrics.notes
        )
