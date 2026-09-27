"""
Ciphertext and PKCS#7 padding overhead derivation.

Stateless utility analyzing exact output dimensions, overhead bytes,
and expansion ratios directly from realized cipher outputs.
"""

from __future__ import annotations

from src.analysis_lab.models import CiphertextMetrics


class CiphertextAnalyzer:
    """Stateless cryptanalysis utility for ciphertext size and padding derivation."""

    @staticmethod
    def analyze(plaintext: bytes, ciphertext: bytes) -> CiphertextMetrics:
        """
        Derive ciphertext dimensions, padding overhead bytes, and expansion percentage.

        Args:
            plaintext (bytes): The original in-memory payload bytes.
            ciphertext (bytes): The realized ciphertext bytes produced by the cipher engine.

        Returns:
            CiphertextMetrics: Dimensions and expansion metrics.

        Raises:
            TypeError: If plaintext or ciphertext is not bytes or bytearray.
        """
        if not isinstance(plaintext, (bytes, bytearray)):
            raise TypeError(
                f"plaintext must be bytes or bytearray, got {type(plaintext).__name__}"
            )
        if not isinstance(ciphertext, (bytes, bytearray)):
            raise TypeError(
                f"ciphertext must be bytes or bytearray, got {type(ciphertext).__name__}"
            )

        plaintext_size = len(plaintext)
        ciphertext_size = len(ciphertext)
        padding_overhead = ciphertext_size - plaintext_size

        expansion_pct: float | None = None
        if plaintext_size > 0:
            expansion_pct = (padding_overhead / plaintext_size) * 100.0

        return CiphertextMetrics(
            plaintext_size_bytes=plaintext_size,
            ciphertext_size_bytes=ciphertext_size,
            padding_overhead_bytes=padding_overhead,
            expansion_percentage=expansion_pct,
        )
