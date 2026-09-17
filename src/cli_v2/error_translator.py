"""3-tier error diagnostics for V2 guided wizards.

Maps native Python exceptions to structured user-facing guidance
(What Failed / Probable Cause / Action Steps) per the frozen DSEL-013
contract, without introducing a custom exception class hierarchy.

Security: the diagnostic text is static guidance and never echoes the
exception's own message. In verbose mode the appended traceback exposes
location (file / line / function) only and suppresses the exception payload,
so secret key material can never leak into error output.
"""

from __future__ import annotations

import sys
import traceback


class ErrorTranslator:
    """Translate native exceptions to 3-tier diagnostics and render them."""

    # --- Static guidance templates (no exception payload is echoed) ---
    _PADDING = {
        "what": "Decryption failed.",
        "why": "Wrong key selected, incorrect cipher mode, or corrupt ciphertext payload.",
        "actions": [
            "Check that the companion .key matches the ciphertext.",
            "For CBC mode, ensure the matching .iv is present.",
            "Verify the correct mode (CBC vs ECB) was selected.",
        ],
    }

    _KEY_FORMAT = {
        "what": "Key loading failed.",
        "why": "The .key file contains non-hexadecimal characters or an invalid length.",
        "actions": [
            "Ensure the key contains only hex digits [0-9a-fA-F].",
            "Verify the length is exactly 32, 48, or 64 hex characters (128/192/256 bits).",
        ],
    }

    _MISSING_FILE = {
        "what": "Required file not found.",
        "why": "Specified file path does not exist or a companion .iv sidecar is missing.",
        "actions": [
            "Verify the file path is correct.",
            "If decrypting CBC, ensure <file>.iv exists in the same folder.",
        ],
    }

    _PERMISSION = {
        "what": "Cannot read or write file.",
        "why": "File is locked by another process or the destination directory is read-only.",
        "actions": [
            "Close any application currently accessing the file.",
            "Check folder write permissions or select another output directory.",
        ],
    }

    _OS_ERROR = {
        "what": "I/O operation failed.",
        "why": "Disk full or filesystem path limit exceeded.",
        "actions": [
            "Free up disk space on the target drive.",
            "Check for invalid path characters.",
        ],
    }

    _UNKNOWN = {
        "what": "An unexpected error occurred.",
        "why": "The operation failed for a reason outside the usual set of failure modes.",
        "actions": [
            "Retry the operation with the same inputs.",
            "If the problem persists, run with --verbose and share the details.",
        ],
    }

    @staticmethod
    def translate(exc: Exception, context: str = "") -> tuple[str, str, list[str]]:
        """Map a Python exception to a (what_failed, probable_cause, actions) tuple.

        Args:
            exc: The exception to translate.
            context: Optional short operation label prepended to the "What Failed" text.

        Returns:
            Tuple of (what_failed, probable_cause, list_of_action_steps).
        """
        message = str(exc).lower()

        # Order matters: FileNotFoundError and PermissionError are OSError subclasses.
        if isinstance(exc, FileNotFoundError):
            spec = ErrorTranslator._MISSING_FILE
        elif isinstance(exc, PermissionError):
            spec = ErrorTranslator._PERMISSION
        elif isinstance(exc, ValueError):
            # ValueError is ambiguous; disambiguate by message substring.
            if "padding" in message:
                spec = ErrorTranslator._PADDING
            elif "hex" in message or "length" in message:
                spec = ErrorTranslator._KEY_FORMAT
            else:
                spec = ErrorTranslator._UNKNOWN
        elif isinstance(exc, OSError):
            spec = ErrorTranslator._OS_ERROR
        else:
            spec = ErrorTranslator._UNKNOWN

        what = spec["what"]
        if context:
            what = f"{context}: {what}"

        return what, spec["why"], list(spec["actions"])

    @staticmethod
    def _format_traceback(exc: Exception) -> str:
        """Format a location-only traceback, suppressing the exception payload."""
        frames = traceback.extract_tb(exc.__traceback__)
        lines = [f"  File \"{f.filename}\", line {f.lineno}, in {f.name}" for f in frames]
        body = "\n".join(lines) if lines else "  (no traceback available)"
        return f"{body}\n  {type(exc).__name__}: (details suppressed for security)"

    @staticmethod
    def display_error(
        exc: Exception,
        context: str = "",
        verbose: bool = False,
    ) -> None:
        """Print a 3-tier diagnostic box to stderr; append traceback if verbose.

        Args:
            exc: The exception to report.
            context: Optional short operation label.
            verbose: When True, append a location-only traceback.
        """
        what, why, actions = ErrorTranslator.translate(exc, context)

        lines = [
            f"[!] Operation Failed: {what}",
            "-" * 60,
            f"What Failed    : {what}",
            f"Probable Cause : {why}",
            "Action Steps   :",
        ]
        for i, action in enumerate(actions, 1):
            lines.append(f"                {i}. {action}")

        text = "\n".join(lines)

        if verbose:
            text += "\n\nVerbose traceback (location only):\n"
            text += ErrorTranslator._format_traceback(exc)

        print(text, file=sys.stderr)