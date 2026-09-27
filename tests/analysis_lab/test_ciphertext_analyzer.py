"""
Unit tests for CiphertextAnalyzer.
"""

import pytest

from src.analysis_lab.ciphertext_analyzer import CiphertextAnalyzer


class TestCiphertextAnalyzer:
    """Tests for CiphertextAnalyzer derivation utility."""

    def test_zero_byte_input(self):
        # 0 bytes plaintext produces 1 full block (16 bytes) of PKCS#7 padding
        plaintext = b""
        ciphertext = b"A" * 16
        metrics = CiphertextAnalyzer.analyze(plaintext, ciphertext)

        assert metrics.plaintext_size_bytes == 0
        assert metrics.ciphertext_size_bytes == 16
        assert metrics.padding_overhead_bytes == 16
        assert metrics.expansion_percentage is None

    def test_block_boundary_16_bytes(self):
        # 16 bytes plaintext produces 32 bytes ciphertext (1 full block of padding added)
        plaintext = b"B" * 16
        ciphertext = b"X" * 32
        metrics = CiphertextAnalyzer.analyze(plaintext, ciphertext)

        assert metrics.plaintext_size_bytes == 16
        assert metrics.ciphertext_size_bytes == 32
        assert metrics.padding_overhead_bytes == 16
        assert metrics.expansion_percentage == 100.0

    def test_near_boundary_sub_block_15_bytes(self):
        # 15 bytes plaintext produces 16 bytes ciphertext (1 byte padding added)
        plaintext = b"C" * 15
        ciphertext = b"Y" * 16
        metrics = CiphertextAnalyzer.analyze(plaintext, ciphertext)

        assert metrics.plaintext_size_bytes == 15
        assert metrics.ciphertext_size_bytes == 16
        assert metrics.padding_overhead_bytes == 1
        assert metrics.expansion_percentage is not None
        assert pytest.approx(metrics.expansion_percentage, rel=1e-3) == (1.0 / 15.0) * 100.0

    def test_near_boundary_over_block_17_bytes(self):
        # 17 bytes plaintext produces 32 bytes ciphertext (15 bytes padding added)
        plaintext = b"D" * 17
        ciphertext = b"Z" * 32
        metrics = CiphertextAnalyzer.analyze(plaintext, ciphertext)

        assert metrics.plaintext_size_bytes == 17
        assert metrics.ciphertext_size_bytes == 32
        assert metrics.padding_overhead_bytes == 15
        assert metrics.expansion_percentage is not None
        assert pytest.approx(metrics.expansion_percentage, rel=1e-3) == (15.0 / 17.0) * 100.0

    def test_larger_file_exact_multiple(self):
        # 1024 bytes plaintext -> 1040 bytes ciphertext (16 bytes padding added)
        plaintext = b"\x00" * 1024
        ciphertext = b"\x01" * 1040
        metrics = CiphertextAnalyzer.analyze(plaintext, ciphertext)

        assert metrics.plaintext_size_bytes == 1024
        assert metrics.ciphertext_size_bytes == 1040
        assert metrics.padding_overhead_bytes == 16
        assert pytest.approx(metrics.expansion_percentage, rel=1e-3) == (16.0 / 1024.0) * 100.0

    def test_bytearray_support(self):
        plaintext = bytearray(b"test data 12345")
        ciphertext = bytearray(b"0" * 32)
        metrics = CiphertextAnalyzer.analyze(plaintext, ciphertext)

        assert metrics.plaintext_size_bytes == 15
        assert metrics.ciphertext_size_bytes == 32
        assert metrics.padding_overhead_bytes == 17
        assert pytest.approx(metrics.expansion_percentage, rel=1e-3) == (17.0 / 15.0) * 100.0

    def test_type_error_on_invalid_input(self):
        with pytest.raises(TypeError, match="plaintext must be bytes or bytearray"):
            CiphertextAnalyzer.analyze("not bytes", b"1234567890123456")  # type: ignore[arg-type]

        with pytest.raises(TypeError, match="ciphertext must be bytes or bytearray"):
            CiphertextAnalyzer.analyze(b"valid", 12345)  # type: ignore[arg-type]
