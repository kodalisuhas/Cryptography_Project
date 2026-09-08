"""AES encryption/decryption engine (ECB, CBC)."""

import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from src.utils.padding import Padding


class AESCipher:
    """
    AES encryption/decryption implementation.

    Supports 128, 192, and 256-bit keys with ECB and CBC modes.
    """

    VALID_KEY_SIZES = (128, 192, 256)
    VALID_MODES = ("ECB", "CBC")
    BLOCK_SIZE = 16

    def __init__(self, key_size: int, mode: str):
        """
        Initialize the AES cipher.

        Args:
            key_size (int): Key size in bits (128, 192, or 256).
            mode (str): Mode of operation ('ECB' or 'CBC').

        Raises:
            ValueError: If key_size or mode is invalid.
        """
        if key_size not in AESCipher.VALID_KEY_SIZES:
            raise ValueError(
                f"key_size must be one of {AESCipher.VALID_KEY_SIZES}, got {key_size!r}"
            )
        if mode not in AESCipher.VALID_MODES:
            raise ValueError(
                f"mode must be one of {AESCipher.VALID_MODES}, got {mode!r}"
            )
        self.key_size = key_size
        self.mode = mode

    def generate_key(self) -> bytes:
        """
        Generate a random key of the configured size.

        Returns:
            bytes: Random key of length key_size/8 bytes.
        """
        return os.urandom(self.key_size // 8)

    def generate_iv(self) -> bytes:
        """
        Generate a random 16-byte IV for CBC mode.

        Returns:
            bytes: 16-byte random IV.

        Raises:
            ValueError: If mode is ECB (IV not used).
        """
        if self.mode == "ECB":
            raise ValueError("IV is not used in ECB mode")
        return os.urandom(AESCipher.BLOCK_SIZE)

    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes = None) -> bytes:
        """
        Encrypt plaintext using AES.

        Args:
            plaintext (bytes): Data to encrypt.
            key (bytes): Encryption key (must match key_size).
            iv (bytes, optional): IV for CBC mode (required for CBC).

        Returns:
            bytes: Encrypted ciphertext.

        Raises:
            ValueError: If key size doesn't match, key is invalid (wrong type or
                length), IV missing for CBC, or plaintext type is invalid.
        """
        data = self._validate_data(plaintext, "plaintext")
        key_bytes = self._validate_key(key)
        validated_iv = self._validate_iv(iv)

        padded = Padding.pad(data, AESCipher.BLOCK_SIZE)
        cipher = self._build_cipher(key_bytes, validated_iv)
        encryptor = cipher.encryptor()
        return encryptor.update(padded) + encryptor.finalize()

    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes = None) -> bytes:
        """
        Decrypt ciphertext using AES.

        Args:
            ciphertext (bytes): Data to decrypt.
            key (bytes): Encryption key (must match key_size).
            iv (bytes, optional): IV for CBC mode (required for CBC).

        Returns:
            bytes: Decrypted plaintext.

        Raises:
            ValueError: If key size doesn't match, key is invalid (wrong type or
                length), IV missing for CBC, ciphertext is not block-aligned, or
                padding is invalid.
        """
        data = self._validate_data(ciphertext, "ciphertext")
        if len(data) % AESCipher.BLOCK_SIZE != 0:
            raise ValueError(
                "ciphertext length must be a multiple of "
                f"{AESCipher.BLOCK_SIZE}, got {len(data)}"
            )
        key_bytes = self._validate_key(key)
        validated_iv = self._validate_iv(iv)

        cipher = self._build_cipher(key_bytes, validated_iv)
        decryptor = cipher.decryptor()
        padded = decryptor.update(data) + decryptor.finalize()
        return Padding.unpad(padded, AESCipher.BLOCK_SIZE)

    def _validate_data(self, data: bytes, name: str) -> bytes:
        """
        Validate that data is bytes/bytearray.

        Args:
            data: Data to validate.
            name (str): Parameter name for error message.

        Returns:
            bytes: Normalized data.

        Raises:
            ValueError: If data is not bytes or bytearray.
        """
        if not isinstance(data, (bytes, bytearray)):
            raise ValueError(f"{name} must be bytes or bytearray")
        return bytes(data)

    def _validate_key(self, key: bytes) -> bytes:
        """
        Validate key type and length against the configured key size.

        Args:
            key: Encryption key.

        Returns:
            bytes: Normalized key.

        Raises:
            ValueError: If key type is invalid or length does not match key_size.
        """
        if not isinstance(key, (bytes, bytearray)):
            raise ValueError("key must be bytes or bytearray")
        expected_length = self.key_size // 8
        if len(key) != expected_length:
            raise ValueError(
                f"key length must be {expected_length} bytes for "
                f"{self.key_size}-bit keys, got {len(key)}"
            )
        return bytes(key)

    def _validate_iv(self, iv: bytes):
        """
        Validate the IV according to the configured mode.

        Args:
            iv: Initialization vector or None.

        Returns:
            bytes or None: Normalized IV (None for ECB).

        Raises:
            ValueError: If an IV is supplied to ECB, or if a CBC IV is missing
                or not exactly 16 bytes.
        """
        if self.mode == "ECB":
            if iv is not None:
                raise ValueError("IV is not used in ECB mode")
            return None
        if iv is None:
            raise ValueError("IV is required for CBC mode")
        if not isinstance(iv, (bytes, bytearray)):
            raise ValueError("IV must be bytes or bytearray")
        if len(iv) != AESCipher.BLOCK_SIZE:
            raise ValueError(
                "IV length must be exactly "
                f"{AESCipher.BLOCK_SIZE} bytes, got {len(iv)}"
            )
        return bytes(iv)

    def _build_cipher(self, key: bytes, iv):
        """
        Construct the PyCA Cipher object for the configured mode.

        Args:
            key (bytes): Normalized AES key.
            iv: Normalized IV (None for ECB).

        Returns:
            Cipher: Configured PyCA cipher.
        """
        if self.mode == "ECB":
            mode = modes.ECB()
        else:
            mode = modes.CBC(iv)
        return Cipher(algorithms.AES(key), mode)
