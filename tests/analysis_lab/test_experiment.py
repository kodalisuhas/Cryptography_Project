"""
Unit tests for PerformanceExperiment.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.analysis_lab.experiment import (
    SUPPORTED_CONFIGURATIONS,
    PerformanceExperiment,
)
from src.engines.cipher_factory import CipherFactory


class TestPerformanceExperiment:
    """Tests for PerformanceExperiment microbenchmarking runner."""

    def test_configuration_matrix_count(self):
        assert len(SUPPORTED_CONFIGURATIONS) == 6
        expected = {
            ("AES", 128, "CBC"),
            ("AES", 192, "CBC"),
            ("AES", 256, "CBC"),
            ("AES", 128, "ECB"),
            ("AES", 192, "ECB"),
            ("AES", 256, "ECB"),
        }
        actual = {
            (c["algorithm"], c["key_size"], c["mode"])
            for c in SUPPORTED_CONFIGURATIONS
        }
        assert actual == expected

    def test_type_validation_on_payload(self):
        with pytest.raises(TypeError, match="payload must be bytes or bytearray"):
            PerformanceExperiment(payload="not bytes")  # type: ignore[arg-type]

    def test_full_run_with_encryption_and_decryption(self):
        payload = b"Sample test file payload for benchmarking AES configurations."
        exp = PerformanceExperiment(payload)
        results, enc_collector, dec_collector = exp.run()

        assert len(results) == 6
        assert dec_collector is not None

        # Check summary dataframe in both collectors
        enc_df = enc_collector.get_summary_dataframe()
        dec_df = dec_collector.get_summary_dataframe()
        assert len(enc_df) == 6
        assert len(dec_df) == 6

        # Check each configuration result
        for res in results:
            assert res.status == "SUCCESS"
            assert res.error_message is None
            assert res.encryption_metrics is not None
            assert res.decryption_metrics is not None
            assert res.ciphertext_metrics is not None

            # Verify 5 warmup + 30 measured contract
            assert res.encryption_metrics.sample_count == 30
            assert len(res.encryption_metrics.raw_times_ms) == 30
            assert res.decryption_metrics.sample_count == 30
            assert len(res.decryption_metrics.raw_times_ms) == 30

            # Verify positive throughput for non-empty file
            assert res.encryption_metrics.throughput_mb_s is not None
            assert res.encryption_metrics.throughput_mb_s > 0
            assert res.decryption_metrics.throughput_mb_s is not None
            assert res.decryption_metrics.throughput_mb_s > 0

    def test_skip_decryption_option(self):
        payload = b"Skip decryption test payload"
        exp = PerformanceExperiment(payload, skip_decryption=True)
        results, enc_collector, dec_collector = exp.run()

        assert len(results) == 6
        assert dec_collector is None
        assert len(enc_collector.get_summary_dataframe()) == 6

        for res in results:
            assert res.status == "SUCCESS"
            assert res.encryption_metrics is not None
            assert res.decryption_metrics is None

    def test_zero_byte_payload_contract(self):
        payload = b""
        exp = PerformanceExperiment(payload)
        results, enc_collector, dec_collector = exp.run()

        assert len(results) == 6
        for res in results:
            assert res.status == "SUCCESS"
            assert res.encryption_metrics is not None
            assert res.decryption_metrics is not None
            assert res.ciphertext_metrics is not None

            # 0-byte file produces 16-byte PKCS#7 block
            assert res.ciphertext_metrics.plaintext_size_bytes == 0
            assert res.ciphertext_metrics.ciphertext_size_bytes == 16
            assert res.ciphertext_metrics.padding_overhead_bytes == 16
            assert res.ciphertext_metrics.expansion_percentage is None

            # Latency is measurable, but throughput is reported as None (N/A)
            assert res.encryption_metrics.sample_count == 30
            assert res.encryption_metrics.mean_ms > 0
            assert res.encryption_metrics.throughput_mb_s is None
            assert res.decryption_metrics.throughput_mb_s is None

    def test_per_configuration_expected_failure_isolation(self):
        payload = b"Resilience test against single configuration failures."
        real_factory = CipherFactory()

        # Wrap factory to inject failure only on AES-256-CBC
        mock_factory = MagicMock(spec=CipherFactory)

        def side_effect(algo, key_size, mode):
            if key_size == 256 and mode == "CBC":
                raise ValueError("Simulated cryptographic failure on AES-256-CBC")
            return real_factory.create_cipher(algo, key_size, mode)

        mock_factory.create_cipher.side_effect = side_effect

        exp = PerformanceExperiment(payload, cipher_factory=mock_factory)
        results, enc_collector, _ = exp.run()

        assert len(results) == 6

        failed_configs = [r for r in results if r.status == "FAILED"]
        success_configs = [r for r in results if r.status == "SUCCESS"]

        assert len(failed_configs) == 1
        assert len(success_configs) == 5

        failed = failed_configs[0]
        assert failed.config_name == "AES-256-CBC"
        assert failed.error_message == "Simulated cryptographic failure on AES-256-CBC"
        assert failed.encryption_metrics is None

        # Verify remaining 5 configurations executed successfully
        assert len(enc_collector.get_summary_dataframe()) == 5

    def test_round_trip_failure_isolation(self):
        payload = b"Round-trip validation test payload."
        real_factory = CipherFactory()
        mock_factory = MagicMock(spec=CipherFactory)

        # Mock cipher for AES-192-ECB whose decrypt returns corrupted payload
        def side_effect(algo, key_size, mode):
            real_cipher = real_factory.create_cipher(algo, key_size, mode)
            if key_size == 192 and mode == "ECB":
                mock_cipher = MagicMock()
                mock_cipher.mode = "ECB"
                mock_cipher.key_size = 192
                mock_cipher.generate_key.return_value = real_cipher.generate_key()
                mock_cipher.generate_iv.return_value = None
                mock_cipher.encrypt.return_value = b"corrupted_cipher"
                mock_cipher.decrypt.return_value = b"mismatched_plaintext"
                return mock_cipher
            return real_cipher

        mock_factory.create_cipher.side_effect = side_effect

        exp = PerformanceExperiment(payload, cipher_factory=mock_factory)
        results, enc_collector, _ = exp.run()

        assert len(results) == 6
        failed_configs = [r for r in results if r.status == "FAILED"]
        assert len(failed_configs) == 1
        assert failed_configs[0].config_name == "AES-192-ECB"
        assert "Pre-benchmark round-trip check failed" in str(failed_configs[0].error_message)

    def test_programming_defect_in_collector_propagates(self):
        payload = b"Test defect propagation"
        exp = PerformanceExperiment(payload)

        # Force a programming defect inside add_metric (e.g. invalid type error)
        with patch.object(
            exp.encryption_collector,
            "add_metric",
            side_effect=ValueError("Internal schema programming defect"),
        ):
            # Must raise ValueError, NOT catch it as an isolated configuration failure!
            with pytest.raises(ValueError, match="Internal schema programming defect"):
                exp.run()
