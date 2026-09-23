"""Tests for the V2 error translator (3-tier diagnostics)."""

from __future__ import annotations

import pytest

from src.cli_v2.error_translator import ErrorTranslator


class TestTranslate:
    """Tests for mapping exceptions to (what, why, actions) tuples."""

    def test_padding_value_error(self):
        """ValueError mentioning padding maps to the padding diagnostic."""
        what, why, actions = ErrorTranslator.translate(ValueError("Invalid padding bytes"))
        assert what == "Decryption failed."
        assert "key" in why.lower()
        assert len(actions) == 3
        assert actions[0].startswith("Check that the companion .key")

    def test_key_format_value_error(self):
        """ValueError mentioning hex maps to the key-format diagnostic."""
        what, why, actions = ErrorTranslator.translate(ValueError("Invalid hex for key"))
        assert what == "Key loading failed."
        assert "hex" in why.lower()
        assert len(actions) == 2

    def test_key_format_length_value_error(self):
        """ValueError mentioning length maps to the key-format diagnostic."""
        what, _, _ = ErrorTranslator.translate(ValueError("Invalid key length: 15 bytes"))
        assert what == "Key loading failed."

    def test_file_not_found(self):
        """FileNotFoundError maps to the missing-file diagnostic."""
        what, why, actions = ErrorTranslator.translate(FileNotFoundError("no such file"))
        assert what == "Required file not found."
        assert ".iv" in why.lower()
        assert len(actions) == 2

    def test_permission_error(self):
        """PermissionError maps to the file-lock / read-only diagnostic."""
        what, _, actions = ErrorTranslator.translate(PermissionError(13, "Access denied"))
        assert what == "Cannot read or write file."
        assert len(actions) == 2

    def test_os_error(self):
        """A general OSError maps to the I/O diagnostic."""
        what, _, actions = ErrorTranslator.translate(OSError(28, "No space left on device"))
        assert what == "I/O operation failed."
        assert len(actions) == 2

    def test_unknown_exception_fallback(self):
        """Unknown exception types fall back to a generic diagnostic."""
        what, _, actions = ErrorTranslator.translate(RuntimeError("boom"))
        assert what == "An unexpected error occurred."
        assert len(actions) == 2

    def test_unrecognized_value_error_fallback(self):
        """ValueError without a recognized message substring falls back."""
        what, _, _ = ErrorTranslator.translate(ValueError("something unrelated"))
        assert what == "An unexpected error occurred."

    def test_nested_exception_uses_top_level(self):
        """Raised-from exceptions translate by the top-level exception type."""
        try:
            try:
                raise FileNotFoundError("missing sidecar")
            except FileNotFoundError as original:
                raise ValueError("Invalid hex for key") from original
        except ValueError as exc:
            what, _, _ = ErrorTranslator.translate(exc)

        assert what == "Key loading failed."

    def test_context_prefixes_what(self):
        """A context label is prepended to the What Failed text."""
        what, _, _ = ErrorTranslator.translate(
            FileNotFoundError("x"), context="Encrypting assignment"
        )
        assert what.startswith("Encrypting assignment:")
        assert what.endswith("Required file not found.")

    def test_no_context_returns_plain_what(self):
        """Without context, What Failed matches the diagnostic exactly."""
        what, _, _ = ErrorTranslator.translate(FileNotFoundError("x"))
        assert what == "Required file not found."

    def test_translate_never_echoes_payload(self):
        """Diagnostic text never contains the raw exception message."""
        secret = "S3CR3T-KEY-HEX"
        _, _, _ = ErrorTranslator.translate(ValueError(f"Invalid padding for {secret}"))
        what, why, actions = ErrorTranslator.translate(ValueError(f"Invalid hex for {secret}"))
        combined = what + why + "".join(actions)
        assert secret not in combined


class TestDisplayError:
    """Tests for rendering the 3-tier diagnostic box to stderr."""

    def test_display_prints_to_stderr(self, capsys):
        """The diagnostic box goes to stderr, never stdout."""
        ErrorTranslator.display_error(FileNotFoundError("missing.txt"))
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "[!] Operation Failed" in captured.err
        assert "What Failed" in captured.err
        assert "Probable Cause" in captured.err
        assert "Action Steps" in captured.err

    def test_display_actions_numbered(self, capsys):
        """Action steps are rendered as a numbered list."""
        ErrorTranslator.display_error(ValueError("Invalid padding"))
        captured = capsys.readouterr()
        assert "1." in captured.err
        assert "2." in captured.err

    def test_display_verbose_has_traceback(self, capsys):
        """Verbose mode appends a traceback block."""
        try:
            raise ValueError("Invalid padding")
        except ValueError as exc:
            ErrorTranslator.display_error(exc, verbose=True)
        captured = capsys.readouterr()
        assert "traceback" in captured.err.lower()
        assert "line" in captured.err.lower()

    def test_verbose_suppresses_exception_message(self, capsys):
        """Verbose traceback exposes location but never the secret payload."""
        secret = "S3R1OUS-M1S11VED-KEY"
        try:
            raise ValueError(f"Invalid padding using key {secret}")
        except ValueError as exc:
            ErrorTranslator.display_error(exc, verbose=True)
        captured = capsys.readouterr()
        assert secret not in captured.out
        assert secret not in captured.err

    def test_display_context_in_header(self, capsys):
        """Context appears in the diagnostic header."""
        ErrorTranslator.display_error(PermissionError(13, "nope"), context="Writing output")
        captured = capsys.readouterr()
        assert "Writing output:" in captured.err

    def test_display_category_header_matches_matrix(self, capsys):
        """The section separator renders under the failed-operation title."""
        ErrorTranslator.display_error(OSError(28, "disk full"))
        captured = capsys.readouterr()
        assert captured.err.startswith("[!] Operation Failed: I/O operation failed.")
        assert "-" * 60 in captured.err