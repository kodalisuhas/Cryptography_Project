"""Key & IV sidecar persistence for V2 guided wizards.

Owns persistence, loading, normalization, validation, and sidecar detection
for raw-hexadecimal ``.key`` and ``.iv`` files per the frozen V2 Selection
(DSEL-003 / DSEL-004 / DSEL-005, Key Management Contract §11).

It deliberately performs no cryptography itself: V1 cryptographic components
retain responsibility for key generation and use. KeyManager only moves key
material between memory and disk, and validates the representation.

Security: this module handles secret key material. It never logs or prints
key/IV values, never writes secrets into exception messages, and never caches
key material in module state.
"""

from __future__ import annotations

from pathlib import Path

from src.utils.file_handler import FileHandler


class KeyManager:
    """Static-method persistence/validation layer for key and IV sidecars."""

    # Valid hexadecimal characters (validation is strictly charset- and
    # length-bounded, so filesystem paths can never be mistaken for hex).
    _HEX_CHARS = frozenset("0123456789abcdefABCDEF")

    # IV is exactly 16 bytes -> 32 hexadecimal characters.
    _IV_HEX_LENGTH = 32

    @staticmethod
    def normalize_hex(raw_text: str) -> str:
        """Return canonical lowercase hex from raw sidecar text.

        Strips both a UTF-8 BOM (``\\ufeff``) and surrounding whitespace
        (``\\r``, ``\\n``, ``\\t``, spaces) in any leading interleaving, then
        lowercases the remaining text. Purely normalizing: it does not
        validate the result.

        The double ``strip()`` around ``lstrip()`` handles both a BOM wrapped
        in surrounding whitespace and whitespace following a leading BOM, so
        the frozen permissive normalization works consistently either way.

        Args:
            raw_text: Raw file content or serialized hex input.

        Returns:
            Canonical lowercase hex text.
        """
        return raw_text.strip().lstrip("﻿").strip().lower()

    @staticmethod
    def validate_key_hex(hex_str: str) -> int:
        """Validate key hex text and return the AES key size in bits.

        Enforces the character set ``[0-9a-fA-F]``, an even number of
        characters, and exactly 32, 48, or 64 characters (128/192/256 bits).

        Args:
            hex_str: Hexadecimal key representation.

        Returns:
            Key size in bits (128, 192, or 256).

        Raises:
            ValueError: Invalid characters, odd length, or unsupported length.
        """
        KeyManager._check_hex_representation(hex_str)

        size_bits = len(hex_str) * 4
        if size_bits not in (128, 192, 256):
            raise ValueError(
                f"AES key must be 32, 48, or 64 hex characters "
                f"(128/192/256 bits), got {len(hex_str)}"
            )
        return size_bits

    @staticmethod
    def validate_iv_hex(hex_str: str) -> bytes:
        """Validate IV hex text and return the 16-byte IV.

        Enforces the character set ``[0-9a-fA-F]`` and exactly 32 hex
        characters (16 bytes).

        Args:
            hex_str: Hexadecimal IV representation.

        Returns:
            The 16-byte IV.

        Raises:
            ValueError: Invalid characters or incorrect IV length.
        """
        KeyManager._check_hex_representation(hex_str)

        if len(hex_str) != KeyManager._IV_HEX_LENGTH:
            raise ValueError(
                f"IV must be exactly 32 hex characters (16 bytes), "
                f"got {len(hex_str)}"
            )
        return bytes.fromhex(hex_str)

    @staticmethod
    def _check_hex_representation(hex_str: str) -> None:
        """Reject empty, non-hex, or odd-length hexadecimal input."""
        if not hex_str:
            raise ValueError("Hexadecimal key/IV text is empty")

        if any(ch not in KeyManager._HEX_CHARS for ch in hex_str):
            raise ValueError("Key/IV contains non-hexadecimal characters")

        if len(hex_str) % 2 != 0:
            raise ValueError(f"Hexadecimal text has odd length ({len(hex_str)})")

    @staticmethod
    def save_key(key_bytes: bytes, output_path: Path) -> Path:
        """Save key bytes as canonical hex text and print the lab notice.

        Validates that the key material is 16, 24, or 32 bytes, writes the
        lowercase hex representation plus a trailing newline to ``output_path``
        (creating parent directories as needed), and displays the selected
        educational laboratory security notice naming the saved file.

        Args:
            key_bytes: AES key material (16, 24, or 32 bytes).
            output_path: Destination for the ``.key`` sidecar file.

        Returns:
            The resulting key file Path.

        Raises:
            TypeError: Key material is not a bytes object.
            ValueError: Key material is not an accepted AES key length.
            OSError: Filesystem or I/O failure (propagated).
        """
        if not isinstance(key_bytes, bytes):
            raise TypeError(
                f"key_bytes must be bytes, got {type(key_bytes).__name__}"
            )

        if len(key_bytes) not in (16, 24, 32):
            raise ValueError(
                f"AES key bytes must be 16, 24, or 32, got {len(key_bytes)}"
            )

        FileHandler.write_text(output_path, key_bytes.hex() + "\n")

        print(f"[!] Laboratory Notice: Encryption key saved to '{output_path}'.")
        print("    Plaintext key storage is provided for laboratory and "
              "testing convenience.")
        print("    In production environments, keys must be stored in secure "
              "key vaults.")

        return output_path

    @staticmethod
    def load_key(key_path: Path) -> tuple[bytes, int]:
        """Load and normalize a ``.key`` file.

        Reads the file, normalizes (BOM / whitespace / lowercase), validates
        the representation, converts it to bytes, and infers the key size in
        bits from the byte length.

        Args:
            key_path: Path to the ``.key`` sidecar file.

        Returns:
            Tuple of ``(key_bytes, key_size_bits)`` — e.g. ``(... , 128)``.

        Raises:
            FileNotFoundError: The file is missing.
            ValueError: The content is not a valid AES key representation.
            OSError: Filesystem or I/O failure (propagated).
        """
        hex_str = KeyManager.normalize_hex(FileHandler.read_text(key_path))
        size_bits = KeyManager.validate_key_hex(hex_str)
        return bytes.fromhex(hex_str), size_bits

    @staticmethod
    def save_iv(iv_bytes: bytes, output_path: Path) -> Path:
        """Save IV bytes as canonical hex text.

        Validates that the IV is exactly 16 bytes, then writes the lowercase
        hex representation plus a trailing newline to ``output_path`` (creating
        parent directories as needed). No security notice is emitted for IV
        creation per the frozen Selection.

        Args:
            iv_bytes: IV material (exactly 16 bytes).
            output_path: Destination for the ``.iv`` sidecar file.

        Returns:
            The resulting IV file Path.

        Raises:
            TypeError: IV material is not a bytes object.
            ValueError: IV material is not exactly 16 bytes.
            OSError: Filesystem or I/O failure (propagated).
        """
        if not isinstance(iv_bytes, bytes):
            raise TypeError(
                f"iv_bytes must be bytes, got {type(iv_bytes).__name__}"
            )

        if len(iv_bytes) != 16:
            raise ValueError(f"IV bytes must be exactly 16, got {len(iv_bytes)}")

        FileHandler.write_text(output_path, iv_bytes.hex() + "\n")
        return output_path

    @staticmethod
    def load_iv(iv_path: Path) -> bytes:
        """Load and normalize a ``.iv`` file.

        Reads the file, normalizes (BOM / whitespace / lowercase), validates
        the representation, and converts it to the 16-byte IV.

        Args:
            iv_path: Path to the ``.iv`` sidecar file.

        Returns:
            The 16-byte IV.

        Raises:
            FileNotFoundError: The file is missing.
            ValueError: The content is not a valid 16-byte IV representation.
            OSError: Filesystem or I/O failure (propagated).
        """
        hex_str = KeyManager.normalize_hex(FileHandler.read_text(iv_path))
        return KeyManager.validate_iv_hex(hex_str)

    @staticmethod
    def auto_detect_sidecars(
        ciphertext_path: Path,
    ) -> tuple[Path | None, Path | None]:
        """Detect companion ``.key`` and ``.iv`` sidecars for a ciphertext.

        Checks for ``<ciphertext_path>.key`` and ``<ciphertext_path>.iv`` in
        the same directory, mirroring V1's ``output_file + ".iv"`` sidecar
        convention. Presence is checked by path existence only — sidecar
        contents are never read and missing files are never fabricated.

        Args:
            ciphertext_path: Path to the ciphertext file.

        Returns:
            Tuple of ``(key_path_or_none, iv_path_or_none)``. The IV sidecar
            is only reported when present, preserving the ECB (no IV) vs CBC
            (IV sidecar) distinction.
        """
        key_path = Path(str(ciphertext_path) + ".key")
        iv_path = Path(str(ciphertext_path) + ".iv")
        return (
            key_path if key_path.exists() else None,
            iv_path if iv_path.exists() else None,
        )