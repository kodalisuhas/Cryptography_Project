"""Tests for the V2 key manager (key/IV sidecar persistence).

Behavioral coverage for normalization, key/IV validation, save/load round
trips, sidecar auto-detection, and secret-boundary guarantees.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.cli_v2.key_manager import KeyManager


# Deterministic (non-secret, lab-suitable) test material.
KEY_128 = bytes.fromhex("000102030405060708090a0b0c0d0e0f")              # 16 B
KEY_192 = bytes.fromhex("101112131415161718191a1b1c1d1e1f2021222324252627")  # 24 B
KEY_256 = bytes.fromhex("00" * 16 + "ff" * 16)                            # 32 B
IV_16 = bytes.fromhex("0123456789abcdef0123456789abcdef")                # 16 B

KEY_128_HEX = KEY_128.hex()
KEY_192_HEX = KEY_192.hex()
KEY_256_HEX = KEY_256.hex()
IV_HEX = IV_16.hex()


def _read_text(path: Path) -> str:
    """Return raw file text without any normalization."""
    return path.read_text(encoding="utf-8")


class TestNormalizeHex:
    """Normalization behavior (category A)."""

    def test_valid_lowercase_hex(self):
        """Lowercase hex passes through unchanged."""
        assert KeyManager.normalize_hex(KEY_128_HEX) == KEY_128_HEX

    def test_uppercase_hex_lowercased(self):
        """Uppercase hex is normalized to lowercase."""
        assert KeyManager.normalize_hex(KEY_128_HEX.upper()) == KEY_128_HEX

    def test_surrounding_whitespace_stripped(self):
        """Leading/trailing CR/LF/TAB/space are all stripped."""
        raw = f"  \t{KEY_128_HEX}\r\n\t  "
        assert KeyManager.normalize_hex(raw) == KEY_128_HEX

    def test_utf8_bom_stripped(self):
        """A leading UTF-8 BOM (U+FEFF) is removed."""
        assert KeyManager.normalize_hex("\ufeff" + KEY_128_HEX) == KEY_128_HEX

    def test_bom_plus_whitespace_stripped(self):
        """BOM combined with surrounding whitespace normalizes cleanly."""
        raw = "\ufeff\r\n" + KEY_128_HEX.upper() + "\n"
        assert KeyManager.normalize_hex(raw) == KEY_128_HEX

    def test_whitespace_wrapped_bom_stripped(self):
        """Regression: whitespace BEFORE the BOM must not trap it at the head."""
        raw = "  \ufeff" + KEY_128_HEX + "\n"
        assert KeyManager.normalize_hex(raw) == KEY_128_HEX

    def test_bom_wrapped_in_whitespace_both_sides(self):
        """BOM and whitespace in either leading order normalize consistently."""
        # Whitespace -> BOM -> hex (the edge case) ...
        assert (
            KeyManager.normalize_hex("  \ufeff" + KEY_128_HEX + "\n")
            == KEY_128_HEX
        )
        # ... and BOM -> whitespace -> hex (the original locked order).
        assert (
            KeyManager.normalize_hex("\ufeff  " + KEY_128_HEX + "\n")
            == KEY_128_HEX
        )

    def test_empty_input(self):
        """Empty input normalizes to empty string (rejected later by validation)."""
        assert KeyManager.normalize_hex("") == ""

    def test_windows_path_never_valid_hex(self):
        """A Windows path is never accepted as hexadecimal key material."""
        normalized = KeyManager.normalize_hex(r"C:\Users\kodal\file.txt")
        with pytest.raises(ValueError):
            KeyManager.validate_key_hex(normalized)

    def test_internal_whitespace_invalid(self):
        """Internal whitespace is malformed content (single-logical-line rule)."""
        with pytest.raises(ValueError):
            KeyManager.validate_key_hex(f"{KEY_128_HEX[:16]} {KEY_128_HEX[16:]}")


class TestValidateKeyHex:
    """Key validation behavior (category B)."""

    def test_128_bit_key(self):
        """32 hex chars validate as 128-bit."""
        assert KeyManager.validate_key_hex(KEY_128_HEX) == 128

    def test_192_bit_key(self):
        """48 hex chars validate as 192-bit."""
        assert KeyManager.validate_key_hex(KEY_192_HEX) == 192

    def test_256_bit_key(self):
        """64 hex chars validate as 256-bit."""
        assert KeyManager.validate_key_hex(KEY_256_HEX) == 256

    def test_uppercase_hex_valid(self):
        """Uppercase hex is accepted."""
        assert KeyManager.validate_key_hex(KEY_128_HEX.upper()) == 128

    def test_invalid_length(self):
        """Unsupported length (24 hex chars -> 96 bits) is rejected."""
        with pytest.raises(ValueError):
            KeyManager.validate_key_hex("ab" * 12)

    def test_invalid_characters(self):
        """Non-hex characters are rejected."""
        with pytest.raises(ValueError):
            KeyManager.validate_key_hex("gg" + KEY_128_HEX[2:])

    def test_empty_input(self):
        """Empty input is rejected."""
        with pytest.raises(ValueError):
            KeyManager.validate_key_hex("")

    def test_odd_length(self):
        """Odd-length hex is rejected."""
        with pytest.raises(ValueError):
            KeyManager.validate_key_hex(KEY_128_HEX[:-1])

    def test_returned_size_is_bits(self):
        """The returned value is the bit length (chars * 4)."""
        assert KeyManager.validate_key_hex(KEY_256_HEX) == len(KEY_256_HEX) * 4


class TestValidateIvHex:
    """IV validation behavior (category C)."""

    def test_valid_16_byte_iv(self):
        """32 hex chars validate to the exact 16 bytes."""
        assert KeyManager.validate_iv_hex(IV_HEX) == IV_16

    def test_invalid_length(self):
        """31 or 33 chars are rejected (IV must be exactly 32)."""
        for bad in (IV_HEX[:-1], IV_HEX + "0"):
            with pytest.raises(ValueError):
                KeyManager.validate_iv_hex(bad)

    def test_invalid_characters(self):
        """Non-hex characters are rejected."""
        with pytest.raises(ValueError):
            KeyManager.validate_iv_hex("z" + IV_HEX[1:])

    def test_empty_input(self):
        """Empty input is rejected."""
        with pytest.raises(ValueError):
            KeyManager.validate_iv_hex("")

    def test_odd_length_rejected(self):
        """Odd-length IV hex is rejected."""
        with pytest.raises(ValueError):
            KeyManager.validate_iv_hex(IV_HEX[:-1])

    def test_uppercase_iv_valid(self):
        """Uppercase IV hex validates to the same bytes."""
        assert KeyManager.validate_iv_hex(IV_HEX.upper()) == IV_16


class TestSaveKey:
    """Key save behavior (category D)."""

    def test_creates_file_and_returns_path(self, tmp_path: Path):
        """Saving creates the file, returns the Path, writes lowercase hex + newline."""
        out = tmp_path / "subdir" / "sample.enc.key"
        result = KeyManager.save_key(KEY_128, out)

        assert result == out
        assert out.exists()
        assert _read_text(out) == KEY_128_HEX + "\n"

    def test_trailing_newline(self, tmp_path: Path):
        """File content ends with a single trailing newline."""
        out = tmp_path / "k.key"
        KeyManager.save_key(KEY_256, out)
        assert _read_text(out).endswith("\n")

    def test_all_three_key_sizes(self, tmp_path: Path):
        """128/192/256-bit keys save without error."""
        for size, key, expected in (
            (128, KEY_128, KEY_128_HEX),
            (192, KEY_192, KEY_192_HEX),
            (256, KEY_256, KEY_256_HEX),
        ):
            out = tmp_path / f"key_{size}.key"
            KeyManager.save_key(key, out)
            assert _read_text(out) == expected + "\n"

    def test_invalid_key_length(self, tmp_path: Path):
        """A non-AES key length (e.g. 15 bytes) is rejected before writing."""
        out = tmp_path / "bad.key"
        with pytest.raises(ValueError):
            KeyManager.save_key(b"\x00" * 15, out)
        assert not out.exists()

    def test_security_notice_displayed(self, tmp_path: Path, capsys):
        """Saving shows the laboratory notice on stdout."""
        out = tmp_path / "sample.enc.key"
        KeyManager.save_key(KEY_128, out)
        captured = capsys.readouterr()
        assert "Laboratory Notice" in captured.out
        assert str(out) in captured.out
        assert "secure key vaults" in captured.out

    def test_notice_never_contains_key(self, tmp_path: Path, capsys):
        """The notice names the file but never echoes the key hex."""
        out = tmp_path / "sample.enc.key"
        KeyManager.save_key(KEY_128, out)
        captured = capsys.readouterr()
        assert KEY_128_HEX not in captured.out
        assert KEY_128_HEX not in captured.err

    def test_save_key_str_raises_type_error(self, tmp_path: Path):
        """Regression: a str of acceptable length raises TypeError, not AttributeError."""
        out = tmp_path / "k.key"
        with pytest.raises(TypeError):
            KeyManager.save_key(KEY_128_HEX, out)  # str has no .hex()
        assert not out.exists()

    def test_save_key_bytearray_raises_type_error(self, tmp_path: Path):
        """Regression: bytearray (bytes-like but non-bytes) is rejected, never written."""
        out = tmp_path / "k.key"
        with pytest.raises(TypeError):
            KeyManager.save_key(bytearray(KEY_128), out)
        assert not out.exists()


class TestLoadKey:
    """Key load behavior (category E)."""

    def test_successful_load_bytes_and_bits(self, tmp_path: Path):
        """Loading returns the exact key bytes and correct bit size."""
        path = tmp_path / "k.key"
        KeyManager.save_key(KEY_192, path)
        key_bytes, size_bits = KeyManager.load_key(path)
        assert key_bytes == KEY_192
        assert size_bits == 192

    def test_missing_file(self, tmp_path: Path):
        """A missing key file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            KeyManager.load_key(tmp_path / "nope.key")

    def test_invalid_content(self, tmp_path: Path):
        """Non-hex content raises ValueError."""
        path = tmp_path / "bad.key"
        path.write_text("not-hex-at-all", encoding="utf-8")
        with pytest.raises(ValueError):
            KeyManager.load_key(path)

    def test_odd_length_content(self, tmp_path: Path):
        """Odd-length hex content raises ValueError."""
        path = tmp_path / "odd.key"
        path.write_text("abc", encoding="utf-8")
        with pytest.raises(ValueError):
            KeyManager.load_key(path)

    def test_invalid_key_length(self, tmp_path: Path):
        """Valid hex but unsupported length (64-bit) raises ValueError."""
        path = tmp_path / "short.key"
        path.write_text("ab" * 8, encoding="utf-8")
        with pytest.raises(ValueError):
            KeyManager.load_key(path)

    def test_uppercase_and_whitespace_normalized(self, tmp_path: Path):
        """Uppercase + BOM + whitespace content still loads to correct bytes."""
        path = tmp_path / "messy.key"
        path.write_text("\ufeff\r\n" + KEY_256_HEX.upper() + "\n", encoding="utf-8")
        key_bytes, size_bits = KeyManager.load_key(path)
        assert key_bytes == KEY_256
        assert size_bits == 256

    def test_round_trip_through_hex_boundary(self, tmp_path: Path):
        """Saved hex equals the canonical V1 --key representation."""
        path = tmp_path / "k.key"
        KeyManager.save_key(KEY_128, path)
        key_bytes, _ = KeyManager.load_key(path)
        assert key_bytes.hex() == KEY_128_HEX  # matches V1 hex interface


class TestSaveIv:
    """IV save behavior (category F)."""

    def test_creates_file_and_returns_path(self, tmp_path: Path):
        """Saving creates the file, returns the Path, writes lowercase hex + newline."""
        out = tmp_path / "dir" / "sample.enc.iv"
        result = KeyManager.save_iv(IV_16, out)
        assert result == out
        assert out.exists()
        assert _read_text(out) == IV_HEX + "\n"

    def test_invalid_iv_length(self, tmp_path: Path):
        """A non-16-byte IV is rejected before writing."""
        out = tmp_path / "bad.iv"
        with pytest.raises(ValueError):
            KeyManager.save_iv(b"\x00" * 15, out)
        assert not out.exists()

    def test_no_secret_on_stdout(self, tmp_path: Path, capsys):
        """IV saving prints nothing (no notice, no IV value)."""
        out = tmp_path / "sample.enc.iv"
        KeyManager.save_iv(IV_16, out)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_save_iv_str_raises_type_error(self, tmp_path: Path):
        """Regression: a str of acceptable length raises TypeError, not AttributeError."""
        out = tmp_path / "i.iv"
        with pytest.raises(TypeError):
            KeyManager.save_iv(IV_HEX, out)  # str has no .hex()
        assert not out.exists()

    def test_save_iv_bytearray_raises_type_error(self, tmp_path: Path):
        """Regression: bytearray (bytes-like but non-bytes) is rejected, never written."""
        out = tmp_path / "i.iv"
        with pytest.raises(TypeError):
            KeyManager.save_iv(bytearray(IV_16), out)
        assert not out.exists()


class TestLoadIv:
    """IV load behavior (category G)."""

    def test_successful_load(self, tmp_path: Path):
        """Loading returns the exact 16-byte IV."""
        path = tmp_path / "i.iv"
        KeyManager.save_iv(IV_16, path)
        assert KeyManager.load_iv(path) == IV_16

    def test_missing_file(self, tmp_path: Path):
        """A missing IV file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            KeyManager.load_iv(tmp_path / "nope.iv")

    def test_malformed_content(self, tmp_path: Path):
        """Non-hex content raises ValueError."""
        path = tmp_path / "bad.iv"
        path.write_text("zzzz", encoding="utf-8")
        with pytest.raises(ValueError):
            KeyManager.load_iv(path)

    def test_invalid_length(self, tmp_path: Path):
        """Content that is valid hex but wrong length raises ValueError."""
        path = tmp_path / "short.iv"
        path.write_text("ab" * 8, encoding="utf-8")  # 16 chars -> 8 bytes
        with pytest.raises(ValueError):
            KeyManager.load_iv(path)

    def test_uppercase_and_whitespace_normalized(self, tmp_path: Path):
        """Uppercase + newline content loads to the exact IV bytes."""
        path = tmp_path / "messy.iv"
        path.write_text(IV_HEX.upper() + "\r\n", encoding="utf-8")
        assert KeyManager.load_iv(path) == IV_16


class TestAutoDetectSidecars:
    """Sidecar auto-detection behavior (category H)."""

    def test_both_sidecars_present(self, tmp_path: Path):
        """Both .key and .iv exist -> both returned."""
        ct = tmp_path / "sample.enc"
        ct.write_bytes(b"cipher")
        (tmp_path / "sample.enc.key").write_text(KEY_128_HEX + "\n")
        (tmp_path / "sample.enc.iv").write_text(IV_HEX + "\n")

        key, iv = KeyManager.auto_detect_sidecars(ct)
        assert key == tmp_path / "sample.enc.key"
        assert iv == tmp_path / "sample.enc.iv"

    def test_only_key_present(self, tmp_path: Path):
        """Only .key exists -> iv is None (ECB has no IV sidecar)."""
        ct = tmp_path / "sample.enc"
        ct.write_bytes(b"cipher")
        (tmp_path / "sample.enc.key").write_text(KEY_128_HEX + "\n")

        key, iv = KeyManager.auto_detect_sidecars(ct)
        assert key == tmp_path / "sample.enc.key"
        assert iv is None

    def test_only_iv_present(self, tmp_path: Path):
        """Only .iv exists -> key is None."""
        ct = tmp_path / "sample.enc"
        ct.write_bytes(b"cipher")
        (tmp_path / "sample.enc.iv").write_text(IV_HEX + "\n")

        key, iv = KeyManager.auto_detect_sidecars(ct)
        assert key is None
        assert iv == tmp_path / "sample.enc.iv"

    def test_neither_present(self, tmp_path: Path):
        """No sidecars -> (None, None), never fabricating paths."""
        ct = tmp_path / "isolated.enc"
        ct.write_bytes(b"cipher")

        assert KeyManager.auto_detect_sidecars(ct) == (None, None)

    def test_exact_naming_convention(self, tmp_path: Path):
        """Sidecars are looked up as <ciphertext_path> + '.key' / '.iv'."""
        ct = tmp_path / "doc.pdf"  # ciphertext without .enc suffix
        ct.write_bytes(b"cipher")
        (tmp_path / "doc.pdf.key").write_text("")
        (tmp_path / "doc.pdf.iv").write_text("")

        key, iv = KeyManager.auto_detect_sidecars(ct)
        assert key == tmp_path / "doc.pdf.key"
        assert iv == tmp_path / "doc.pdf.iv"

    def test_detection_never_reads_contents(self, tmp_path: Path):
        """Detection is existence-only; a path with a '+' or other file is fine."""
        ct = tmp_path / "data.enc"
        ct.write_bytes(b"cipher")
        # A sidecar named exactly <ct>.key exists but is empty/invalid — the
        # detector must still report it (existence check only).
        (tmp_path / "data.enc.key").touch()

        key, iv = KeyManager.auto_detect_sidecars(ct)
        assert key == tmp_path / "data.enc.key"
        assert iv is None


class TestSecurityBoundaries:
    """Secret-handling guarantees (category I)."""

    def test_load_error_message_does_not_echo_secret(self, tmp_path: Path):
        """Validation errors never echo key/IV values in their message."""
        sentinel = "S3CR3T-SENTINEL-B3FC00D"
        path = tmp_path / "leak.key"
        path.write_text(sentinel, encoding="utf-8")

        with pytest.raises(ValueError) as excinfo:
            KeyManager.load_key(path)
        assert sentinel.lower() not in str(excinfo.value)
        assert sentinel not in str(excinfo.value)

    def test_validation_error_message_excludes_input(self):
        """validate_* errors do not embed the submitted hex string."""
        distinctive = "DEADBEEFCAFE" * 2  # 24 chars -> invalid 96-bit length
        with pytest.raises(ValueError) as excinfo:
            KeyManager.validate_key_hex(distinctive)
        assert distinctive not in str(excinfo.value)
        assert distinctive.lower() not in str(excinfo.value)

    def test_no_sidecar_creation_on_failed_save(self, tmp_path: Path):
        """Invalid key/IV material never leaves a partial file behind."""
        out = tmp_path / "x.key"
        with pytest.raises(ValueError):
            KeyManager.save_key(b"\x00" * 7, out)
        assert not out.exists()
        with pytest.raises(ValueError):
            KeyManager.save_iv(b"\x00" * 7, tmp_path / "x.iv")
        assert not (tmp_path / "x.iv").exists()