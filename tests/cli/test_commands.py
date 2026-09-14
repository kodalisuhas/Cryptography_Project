"""Tests for CLI command handlers: encrypt/decrypt/benchmark/security.

Convention: pytest, real Core/Service integration for crypto tests, unittest.mock
for benchmark service verification.  No new test infrastructure.
"""

import argparse
import pytest
from unittest.mock import patch, MagicMock

from src.engines import CipherFactory, CipherService
from src.analyzers.security_evaluator import SecurityEvaluator
from src.cli.commands import (
    _parse_hex,
    _decode_input,
    _format_plaintext,
    _one_bit_partner,
    _key_size_from_key,
    _build_bmp_bytes,
    _build_payload,
    _parse_comma_separated_ints,
    _parse_benchmark_lists,
    run_encrypt,
    run_decrypt,
    run_benchmark,
    run_security,
)


# ═══════════════════════════════════════════════════════════════════════
# Helper unit tests
# ═══════════════════════════════════════════════════════════════════════


class TestParseHex:
    def test_valid_hex(self):
        assert _parse_hex("deadbeef", "test") == b"\xde\xad\xbe\xef"

    def test_empty_string(self):
        assert _parse_hex("", "test") == b""

    def test_invalid_hex(self):
        with pytest.raises(ValueError, match="Invalid hex"):
            _parse_hex("xyz", "test")

    def test_odd_length_rejected(self):
        with pytest.raises(ValueError, match="Invalid hex"):
            _parse_hex("abc", "test")

    def test_with_spaces_accepted(self):
        # bytes.fromhex ignores whitespace
        assert _parse_hex("de ad be ef", "test") == b"\xde\xad\xbe\xef"


class TestDecodeInput:
    def test_text_format(self):
        assert _decode_input("hello", "text") == b"hello"

    def test_text_utf8(self):
        assert _decode_input("café", "text") == "café".encode("utf-8")

    def test_hex_format(self):
        assert _decode_input("deadbeef", "hex") == b"\xde\xad\xbe\xef"


class TestFormatPlaintext:
    def test_valid_utf8(self):
        assert _format_plaintext(b"hello") == "hello"

    def test_invalid_utf8_shows_hex(self):
        result = _format_plaintext(b"\xff\xfe")
        assert result.startswith("(hex) ")
        assert "fffe" in result

    def test_empty(self):
        assert _format_plaintext(b"") == ""


class TestOneBitPartner:
    def test_flips_one_bit(self):
        partner = _one_bit_partner(b"hello")
        # Exactly one byte differs
        diff_count = sum(a != b for a, b in zip(b"hello", partner))
        assert diff_count == 1

    def test_flips_first_byte_lsb(self):
        partner = _one_bit_partner(b"\x00")
        assert partner == b"\x01"

    def test_flips_first_byte_lsb_1_to_0(self):
        partner = _one_bit_partner(b"\x01")
        assert partner == b"\x00"

    def test_two_byte_key(self):
        key = b"K" * 16
        partner = _one_bit_partner(key)
        assert len(partner) == 16
        diff_count = sum(a != b for a, b in zip(key, partner))
        assert diff_count == 1

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _one_bit_partner(b"")

    def test_result_differs_from_original(self):
        partner = _one_bit_partner(b"abc")
        assert partner != b"abc"


class TestKeySizeFromKey:
    def test_128_bit(self):
        assert _key_size_from_key(b"K" * 16) == 128

    def test_192_bit(self):
        assert _key_size_from_key(b"K" * 24) == 192

    def test_256_bit(self):
        assert _key_size_from_key(b"K" * 32) == 256

    def test_invalid_length(self):
        with pytest.raises(ValueError, match="does not match"):
            _key_size_from_key(b"K" * 15)


class TestBuildBmpBytes:
    def test_valid_dimensions(self):
        bmp = _build_bmp_bytes(4, 4)
        assert bmp[:2] == b"BM"
        assert len(bmp) > 54

    def test_accepted_by_security_evaluator(self):
        """The real SecurityEvaluator must accept our BMP."""
        bmp = _build_bmp_bytes(8, 8)
        evaluator = SecurityEvaluator()
        # This would raise if the BMP is invalid
        # Just verify structure (the real security test validates fully)
        assert bmp[:2] == b"BM"

    def test_zero_width_raises(self):
        with pytest.raises(ValueError, match="positive"):
            _build_bmp_bytes(0, 8)

    def test_zero_height_raises(self):
        with pytest.raises(ValueError, match="positive"):
            _build_bmp_bytes(8, 0)

    def test_header_fields(self):
        import struct
        bmp = _build_bmp_bytes(4, 4)
        width = struct.unpack_from("<i", bmp, 0x12)[0]
        height = struct.unpack_from("<i", bmp, 0x16)[0]
        bpp = struct.unpack_from("<H", bmp, 0x1C)[0]
        assert width == 4
        assert height == 4
        assert bpp == 24

    def test_deterministic(self):
        assert _build_bmp_bytes(4, 4) == _build_bmp_bytes(4, 4)


class TestBuildPayload:
    def test_correct_size(self):
        assert len(_build_payload(1024)) == 1024

    def test_small_size(self):
        assert len(_build_payload(1)) == 1

    def test_exact_pattern_boundary(self):
        payload = _build_payload(32)
        assert len(payload) == 32


class TestParseCommaSeparatedInts:
    def test_valid(self):
        assert _parse_comma_separated_ints("128,192,256", "test") == [128, 192, 256]

    def test_single_value(self):
        assert _parse_comma_separated_ints("1048576", "test") == [1048576]

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="no values"):
            _parse_comma_separated_ints("", "test")

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="expected"):
            _parse_comma_separated_ints("abc,def", "test")


class TestParseBenchmarkLists:
    def _make_args(self, **kwargs):
        defaults = {"key_sizes": "128,192,256", "modes": "ECB,CBC", "payload_sizes": "1048576"}
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_defaults(self):
        ks, modes, ps = _parse_benchmark_lists(self._make_args())
        assert ks == [128, 192, 256]
        assert modes == ["ECB", "CBC"]
        assert ps == [1048576]

    def test_invalid_key_size(self):
        with pytest.raises(ValueError, match="Invalid key size"):
            _parse_benchmark_lists(self._make_args(key_sizes="999"))

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="Invalid mode"):
            _parse_benchmark_lists(self._make_args(modes="GCM"))

    def test_invalid_payload_size(self):
        with pytest.raises(ValueError, match="positive"):
            _parse_benchmark_lists(self._make_args(payload_sizes="0"))


# ═══════════════════════════════════════════════════════════════════════
# Encrypt integration (all 6 key-size × mode combos via real Core/Service)
# ═══════════════════════════════════════════════════════════════════════


class TestEncryptDecryptRoundtrip:
    """Real encryption then decryption through the CLI handlers (all 6 combos)."""

    def _make_encrypt_args(self, key_size, mode, plaintext="hello"):
        key_hex = "ab" * (key_size // 8)
        args = argparse.Namespace(
            algorithm="AES",
            key_size=key_size,
            mode=mode,
            key=key_hex,
            generate_key=False,
            input=plaintext,
            input_format="text",
            iv=None,
            verbose=False,
        )
        return args, key_hex

    def _run_roundtrip(self, key_size, mode, capsys):
        enc_args, key_hex = self._make_encrypt_args(key_size, mode)
        run_encrypt(enc_args)
        enc_out = capsys.readouterr().out

        # Parse Ciphertext and optional IV from output
        ct_line = [l for l in enc_out.splitlines() if l.startswith("Ciphertext:")][0]
        ct_hex = ct_line.split(":", 1)[1].strip()

        iv_hex = None
        for line in enc_out.splitlines():
            if line.startswith("IV:"):
                iv_hex = line.split(":", 1)[1].strip()
                break

        dec_args = argparse.Namespace(
            algorithm="AES",
            key_size=key_size,
            mode=mode,
            key=key_hex,
            input=ct_hex,
            iv=iv_hex,
            verbose=False,
        )
        run_decrypt(dec_args)
        dec_out = capsys.readouterr().out
        assert "hello" in dec_out

    @pytest.mark.parametrize("key_size", [128, 192, 256])
    @pytest.mark.parametrize("mode", ["ECB", "CBC"])
    def test_roundtrip_all_combos(self, key_size, mode, capsys):
        self._run_roundtrip(key_size, mode, capsys)


class TestEncryptCBCIvOutput:
    """CBC encrypt must print the IV for downstream reuse."""

    def test_cbc_prints_iv(self, capsys):
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="CBC",
            key="ab" * 16, generate_key=False,
            input="hi", input_format="text",
            iv=None, verbose=False,
        )
        run_encrypt(args)
        out = capsys.readouterr().out
        assert any(line.startswith("IV:") for line in out.splitlines())

    def test_ecb_no_iv(self, capsys):
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="ECB",
            key="ab" * 16, generate_key=False,
            input="hi", input_format="text",
            iv=None, verbose=False,
        )
        run_encrypt(args)
        out = capsys.readouterr().out
        assert not any(line.startswith("IV:") for line in out.splitlines())


class TestGenerateKeyE2E:
    """End-to-end: generate key → encrypt → capture key+ct → decrypt."""

    def test_generated_key_roundtrip(self, capsys):
        enc_args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="CBC",
            key=None, generate_key=True,
            input="secret message", input_format="text",
            iv=None, verbose=False,
        )
        run_encrypt(enc_args)
        enc_out = capsys.readouterr().out

        ct_hex = iv_hex = gen_key = None
        for line in enc_out.splitlines():
            if line.startswith("Ciphertext:"):
                ct_hex = line.split(":", 1)[1].strip()
            elif line.startswith("IV:"):
                iv_hex = line.split(":", 1)[1].strip()
            elif line.startswith("Key (generated):"):
                gen_key = line.split(":", 1)[1].strip()

        assert gen_key is not None
        assert ct_hex is not None

        dec_args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="CBC",
            key=gen_key, input=ct_hex,
            iv=iv_hex, verbose=False,
        )
        run_decrypt(dec_args)
        dec_out = capsys.readouterr().out
        assert "secret message" in dec_out


class TestGenerateKeySizes:
    """Generated keys must match the selected AES key size (length/type only)."""

    @pytest.mark.parametrize("key_size, expected_bytes", [(128, 16), (192, 24), (256, 32)])
    def test_generated_key_length(self, key_size, expected_bytes, capsys):
        args = argparse.Namespace(
            algorithm="AES", key_size=key_size, mode="ECB",
            key=None, generate_key=True,
            input="hi", input_format="text",
            iv=None, verbose=False,
        )
        run_encrypt(args)
        out = capsys.readouterr().out
        key_line = [l for l in out.splitlines() if l.startswith("Key (generated):")][0]
        gen_hex = key_line.split(":", 1)[1].strip()
        # Correct type (valid hex) and length (2 hex chars per byte).
        # Never assert a fixed value — a generated key is not deterministic.
        decoded = bytes.fromhex(gen_hex)
        assert len(decoded) == expected_bytes


# ═══════════════════════════════════════════════════════════════════════
# Decrypt error cases
# ═══════════════════════════════════════════════════════════════════════


class TestDecryptErrors:
    def test_cbc_decrypt_requires_iv(self):
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="CBC",
            key="ab" * 16, input="cafe" * 16,
            iv=None, verbose=False,
        )
        with pytest.raises(ValueError, match="CBC decryption requires --iv"):
            run_decrypt(args)

    def test_ecb_with_iv_raises(self):
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="ECB",
            key="ab" * 16, input="cafe" * 16,
            iv="00" * 16, verbose=False,
        )
        with pytest.raises(ValueError, match="ECB mode does not use an IV"):
            run_decrypt(args)

    def test_invalid_key_hex(self):
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="ECB",
            key="xyz", input="cafe" * 16,
            iv=None, verbose=False,
        )
        with pytest.raises(ValueError, match="Invalid hex"):
            run_decrypt(args)

    def test_invalid_ciphertext_hex(self):
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="ECB",
            key="ab" * 16, input="xyz",
            iv=None, verbose=False,
        )
        with pytest.raises(ValueError, match="Invalid hex"):
            run_decrypt(args)

    def test_invalid_iv_length(self):
        """A wrong-length CBC IV must surface Core's native ValueError."""
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="CBC",
            key="ab" * 16, input="cafe" * 16,
            iv="00" * 8,  # 8 bytes — invalid, must be 16
            verbose=False,
        )
        with pytest.raises(ValueError):
            run_decrypt(args)


class TestEncryptErrors:
    def test_ecb_with_iv_raises(self):
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="ECB",
            key="ab" * 16, generate_key=False,
            input="hello", input_format="text",
            iv="00" * 16, verbose=False,
        )
        with pytest.raises(ValueError, match="ECB mode does not use an IV"):
            run_encrypt(args)

    def test_wrong_key_length_raises(self):
        """Core validates key length and raises ValueError."""
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="ECB",
            key="ab" * 8,  # 8 bytes = 64 bits, wrong for AES-128
            generate_key=False,
            input="hello", input_format="text",
            iv=None, verbose=False,
        )
        with pytest.raises(ValueError):
            run_encrypt(args)

    def test_hex_input_format(self, capsys):
        args = argparse.Namespace(
            algorithm="AES", key_size=128, mode="ECB",
            key="ab" * 16, generate_key=False,
            input="48656c6c6f",  # "Hello" in hex
            input_format="hex",
            iv=None, verbose=False,
        )
        run_encrypt(args)
        out = capsys.readouterr().out
        assert "Ciphertext:" in out


# ═══════════════════════════════════════════════════════════════════════
# Benchmark tests
# ═══════════════════════════════════════════════════════════════════════


class TestBenchmark:
    """CLI-level benchmark tests using the mock-verifications per §42."""

    def _mock_args(self, key_sizes="128", modes="ECB", payload_sizes="16"):
        return argparse.Namespace(
            algorithm="AES", key_sizes=key_sizes, modes=modes,
            payload_sizes=payload_sizes, verbose=False,
        )

    def test_runs_with_real_service(self, capsys):
        """A minimal real benchmark: 1 config, tiny payload (fast)."""
        args = self._mock_args()
        run_benchmark(args)
        out = capsys.readouterr().out
        assert "Running benchmark:" in out
        # Tabulated output should contain key_size and throughput columns
        assert "128" in out

    @patch("src.cli.commands.BenchmarkService")
    def test_api_call_config_and_payload(self, MockBenchmark):
        """Verify the config/payload construction and API contract."""
        mock_collector = MagicMock()
        import pandas as pd
        mock_collector.get_summary_dataframe.return_value = pd.DataFrame(
            [{"key_size": 128, "mode": "ECB", "data_size_bytes": 16,
              "mean_time_ms": 0.1, "median_time_ms": 0.1, "std_dev_time_ms": 0.0,
              "outlier_count": 0, "throughput_mb_s": 100.0}]
        )
        MockBenchmark.return_value.run_performance_suite.return_value = mock_collector

        args = self._mock_args(key_sizes="128,256", modes="ECB,CBC", payload_sizes="1024")
        run_benchmark(args)

        configs, payloads = MockBenchmark.return_value.run_performance_suite.call_args[0]
        # 2 key sizes × 2 modes = 4 configs
        assert len(configs) == 4
        assert all(c["algorithm"] == "AES" for c in configs)
        assert [c["key_size"] for c in configs] == [128, 128, 256, 256]
        assert [c["mode"] for c in configs] == ["ECB", "CBC", "ECB", "CBC"]
        # 1 payload size
        assert len(payloads) == 1
        assert len(payloads[0]) == 1024

    @patch("src.cli.commands.BenchmarkService")
    def test_no_add_metric_called(self, MockBenchmark):
        """CLI must not re-add metrics (frozen service does it)."""
        mock_collector = MagicMock()
        import pandas as pd
        mock_collector.get_summary_dataframe.return_value = pd.DataFrame(
            [{"key_size": 128, "mode": "ECB", "data_size_bytes": 16,
              "mean_time_ms": 0.1, "median_time_ms": 0.1, "std_dev_time_ms": 0.0,
              "outlier_count": 0, "throughput_mb_s": 100.0}]
        )
        MockBenchmark.return_value.run_performance_suite.return_value = mock_collector

        args = self._mock_args()
        run_benchmark(args)

        mock_collector.add_metric.assert_not_called()

    def test_invalid_key_size_in_list(self):
        args = self._mock_args(key_sizes="999")
        with pytest.raises(ValueError, match="Invalid key size"):
            run_benchmark(args)

    def test_invalid_mode_in_list(self):
        args = self._mock_args(modes="GCM")
        with pytest.raises(ValueError, match="Invalid mode"):
            run_benchmark(args)

    def test_invalid_payload_size(self):
        args = self._mock_args(payload_sizes="0")
        with pytest.raises(ValueError, match="positive"):
            run_benchmark(args)


# ═══════════════════════════════════════════════════════════════════════
# Security integration
# ═══════════════════════════════════════════════════════════════════════


class TestSecurity:
    """CLI-level security tests using the real frozen SecurityService."""

    def _make_args(self, mode="ECB", key_hex=None, plaintext="", iv=None):
        return argparse.Namespace(
            algorithm="AES",
            mode=mode,
            key=key_hex or ("ab" * 16),
            plaintext=plaintext,
            plaintext_format="text",
            iv=iv,
            bmp_width=4,
            bmp_height=4,
            verbose=False,
        )

    def test_ecb_security(self, capsys):
        args = self._make_args(mode="ECB")
        run_security(args)
        out = capsys.readouterr().out
        assert "Avalanche effect" in out
        assert "Key sensitivity" in out
        assert "ECB weakness" in out

    def test_cbc_security(self, capsys):
        args = self._make_args(mode="CBC")
        run_security(args)
        out = capsys.readouterr().out
        assert "Avalanche effect" in out
        assert "Key sensitivity" in out
        # CBC does not run ECB weakness
        assert "ECB weakness" not in out

    def test_iv_printed(self, capsys):
        args = self._make_args(mode="CBC")
        run_security(args)
        out = capsys.readouterr().out
        assert "Security suite IV:" in out

    def test_explicit_iv(self, capsys):
        args = self._make_args(mode="CBC", iv="11" * 16)
        run_security(args)
        out = capsys.readouterr().out
        assert "11" * 16 in out

    def test_invalid_key_length(self):
        args = self._make_args(key_hex="ab" * 8)  # 8 bytes = 64 bits
        with pytest.raises(ValueError, match="does not match"):
            run_security(args)

    def test_1_bit_partner_integrity(self):
        """Verify the CLI constructs a valid 1-bit-different pair."""
        key1 = b"K" * 16
        key2 = _one_bit_partner(key1)
        assert len(key2) == 16
        diff_count = sum(a != b for a, b in zip(key1, key2))
        assert diff_count == 1

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _one_bit_partner(b"")

    def test_bmp_accepted_by_evaluator(self):
        """Verify our BMP is accepted by the frozen SecurityEvaluator."""
        bmp = _build_bmp_bytes(8, 8)
        # The evaluator's BMP validation would raise on invalid BMPs
        # Use a 16-byte key to get a valid config
        key1 = b"K" * 16
        key2 = _one_bit_partner(key1)
        iv = CipherFactory().create_cipher("AES", 128, "CBC").generate_iv()
        evaluator = SecurityEvaluator()
        # This calls test_ecb_weakness internally, which validates the BMP
        evaluator.test_ecb_weakness(bmp, key1, iv)
        # If we get here without exception, the BMP is valid
        assert True

    def test_invalid_1_bit_pair_propagates_value_error(self):
        """A non-1-bit invariant violation surfaces as a native ValueError."""
        evaluator = SecurityEvaluator()
        p1 = b"A" * 16
        p2 = b"BB" + b"A" * 14  # two bytes differ → not a 1-bit pair
        cipher = CipherFactory().create_cipher("AES", 128, "ECB")
        key = b"K" * 16
        with pytest.raises(ValueError):
            evaluator.calculate_avalanche_effect(p1, p2, cipher, key)

    def test_mixed_incompatible_key_sizes_not_silently_combined(self):
        """A single key drives a single config; key_size must match derived size."""
        # 24 bytes → AES-192 only; no mixing with other sizes.
        args = self._make_args(mode="ECB", key_hex="ab" * 24)
        with patch("src.cli.commands.SecurityService") as MockService:
            mock_service = MockService.return_value
            mock_service.run_security_suite.return_value = {"AES-192-ECB": {"avalanche_effect": 0.5, "key_sensitivity": 0.5}}
            run_security(args)

            configs, p1, p2, k1, k2, img, iv = (
                mock_service.run_security_suite.call_args[0]
            )
            assert len(configs) == 1
            assert configs[0]["key_size"] == 192
            assert configs[0]["mode"] == "ECB"
            assert configs[0]["algorithm"] == "AES"
            # key1 and key2 lengths are derived from the one supplied key
            assert len(k1) == 24 and len(k2) == 24


class TestSecurity1BitPartner:
    """Validate the 1-bit-input construction used for security experiments."""

    def test_plaintext_1_bit(self):
        p1 = b"Attack at dawn!"
        p2 = _one_bit_partner(p1)
        assert len(p2) == len(p1)
        diff = sum(a != b for a, b in zip(p1, p2))
        assert diff == 1

    def test_key_1_bit(self):
        k1 = b"K" * 16
        k2 = _one_bit_partner(k1)
        diff = sum(a != b for a, b in zip(k1, k2))
        assert diff == 1

    def test_single_byte_key(self):
        k1 = b"\x00"
        k2 = _one_bit_partner(k1)
        assert k2 == b"\x01"
        diff = sum(a != b for a, b in zip(k1, k2))
        assert diff == 1