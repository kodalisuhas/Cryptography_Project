"""
Security and diffusion experiment runner for File-Specific Encryption Analysis Lab.

Executes opt-in cryptanalytic diffusion evaluations (1-bit Plaintext Avalanche Effect
and 1-bit Key Sensitivity) using the frozen SecurityEvaluator engine.
"""

from __future__ import annotations

import os
from typing import Any, Sequence

from src.analysis_lab.experiment import SUPPORTED_CONFIGURATIONS
from src.analysis_lab.models import SecurityMetrics
from src.analyzers.security_evaluator import SecurityEvaluator
from src.engines.cipher_factory import CipherFactory


class SecurityExperiment:
    """
    Decoupled cryptanalysis experiment runner.

    Evaluates Plaintext Avalanche Effect and Key Sensitivity under controlled
    1-bit mutations without entangling with microbenchmark timing loops.
    """

    def __init__(
        self,
        payload: bytes,
        configurations: Sequence[dict[str, Any]] | None = None,
        cipher_factory: CipherFactory | None = None,
        security_evaluator: SecurityEvaluator | None = None,
    ) -> None:
        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError(
                f"payload must be bytes or bytearray, got {type(payload).__name__}"
            )

        self.payload = bytes(payload)
        self.configurations = tuple(configurations or SUPPORTED_CONFIGURATIONS)
        self.factory = cipher_factory or CipherFactory()
        self.evaluator = security_evaluator or SecurityEvaluator()

    @staticmethod
    def is_valid_supported_bmp(data: bytes) -> tuple[bool, str]:
        """
        Validate whether data conforms to a supported 24-bpp uncompressed BMP.

        Validates all structural constraints required by SecurityEvaluator.test_ecb_weakness:
        - Minimum length >= 54 bytes
        - Magic signature == b'BM'
        - Declared file size matches len(data)
        - Data offset >= 14 and <= len(data)
        - DIB header size in (40, 108, 124)
        - Width > 0, Height != 0
        - Planes == 1
        - Bits per pixel == 24
        - Compression == 0 (BI_RGB uncompressed)
        - Pixel data buffer length >= row_stride * abs(height)

        Returns:
            tuple[bool, str]: (is_valid, descriptive_reason)
        """
        if len(data) < 54:
            return False, "Data is too small for standard 54-byte BMP header."
        if data[0:2] != b"BM":
            return False, "Missing BMP signature (expected b'BM')."

        file_size_field = int.from_bytes(data[0x02:0x06], byteorder="little")
        if file_size_field != len(data):
            return (
                False,
                f"Declared BMP file size ({file_size_field}) does not match payload length ({len(data)}).",
            )

        offset = int.from_bytes(data[0x0A:0x0E], byteorder="little")
        if offset > len(data) or offset < 14:
            return False, f"Invalid pixel data offset ({offset})."

        dib_header_size = int.from_bytes(data[0x0E:0x12], byteorder="little")
        if dib_header_size not in (40, 108, 124):
            return (
                False,
                f"Unsupported DIB header size ({dib_header_size}; must be 40, 108, or 124).",
            )

        width = int.from_bytes(data[0x12:0x16], byteorder="little", signed=True)
        height = int.from_bytes(data[0x16:0x1A], byteorder="little", signed=True)
        if width <= 0 or height == 0:
            return False, f"Invalid BMP dimensions ({width}x{height})."

        planes = int.from_bytes(data[0x1A:0x1C], byteorder="little")
        if planes != 1:
            return False, f"Unsupported plane count ({planes}; must be 1)."

        bpp = int.from_bytes(data[0x1C:0x1E], byteorder="little")
        if bpp != 24:
            return False, f"Unsupported bits-per-pixel ({bpp}; must be 24-bpp)."

        comp = int.from_bytes(data[0x1E:0x22], byteorder="little")
        if comp != 0:
            return (
                False,
                f"Unsupported compression method ({comp}; must be uncompressed BI_RGB).",
            )

        row_bytes = width * 3
        row_stride = ((row_bytes + 3) // 4) * 4
        expected_pixel_bytes = row_stride * abs(height)

        image_size_field = int.from_bytes(data[0x22:0x26], byteorder="little")
        if image_size_field != 0 and image_size_field < expected_pixel_bytes:
            return (
                False,
                "Declared image size is inconsistent with pixel geometry.",
            )

        if len(data[offset:]) < expected_pixel_bytes:
            return (
                False,
                "Pixel data buffer is smaller than required by dimensions.",
            )

        return True, f"Valid 24-bpp uncompressed BMP ({width}x{abs(height)})."

    def evaluate_configuration(self, config_spec: dict[str, Any]) -> SecurityMetrics:
        """
        Evaluate diffusion metrics for a single cryptographic configuration.

        Args:
            config_spec: Dictionary containing 'algorithm', 'key_size', and 'mode'.

        Returns:
            SecurityMetrics: Observed diffusion percentages and contextual notes.
        """
        if len(self.payload) == 0:
            return SecurityMetrics(
                status="SKIPPED",
                notes="Diffusion metrics require non-empty payload.",
                ecb_weakness_analyzed=False,
            )

        algo = config_spec["algorithm"]
        key_size = config_spec["key_size"]
        mode = config_spec["mode"]

        try:
            cipher = self.factory.create_cipher(algo, key_size, mode)
            key = cipher.generate_key()
            iv = cipher.generate_iv() if mode == "CBC" else None

            # 1. Plaintext Avalanche Effect (flip bit 0 of byte 0)
            mutated_plaintext = bytearray(self.payload)
            mutated_plaintext[0] ^= 0x01
            avalanche_pct = self.evaluator.calculate_avalanche_effect(
                self.payload, bytes(mutated_plaintext), cipher, key, iv
            )

            # 2. Key Sensitivity (flip bit 0 of byte 0)
            mutated_key = bytearray(key)
            mutated_key[0] ^= 0x01
            key_sens_pct = self.evaluator.test_key_sensitivity(
                cipher, self.payload, key, bytes(mutated_key), iv
            )

            # 3. BMP Structural Guard & Evaluation
            is_bmp, _ = self.is_valid_supported_bmp(self.payload)
            if is_bmp:
                # SecurityEvaluator.test_ecb_weakness requires a 16-byte IV for the CBC comparison
                comparison_iv = iv if iv is not None else os.urandom(16)
                ecb_result = self.evaluator.test_ecb_weakness(
                    self.payload, key, comparison_iv
                )
                note = (
                    f"24-bpp uncompressed BMP analyzed for structural ECB pattern leakage "
                    f"({len(ecb_result['ecb_ciphertext'])} bytes ciphertext)."
                )
                ecb_analyzed = True
            else:
                note = "Structural pattern test is specific to 24-bpp uncompressed BMP images."
                ecb_analyzed = False

            return SecurityMetrics(
                status="SUCCESS",
                avalanche_effect_pct=avalanche_pct,
                key_sensitivity_pct=key_sens_pct,
                notes=note,
                ecb_weakness_analyzed=ecb_analyzed,
            )

        except (ValueError, RuntimeError) as exc:
            return SecurityMetrics(
                status="FAILED",
                notes=f"Security evaluation failed: {exc}",
                ecb_weakness_analyzed=False,
            )

    def run(self) -> dict[str, SecurityMetrics]:
        """
        Execute security diffusion analysis across all configurations.

        Returns:
            dict mapping canonical configuration name to SecurityMetrics.
        """
        results: dict[str, SecurityMetrics] = {}
        for config_spec in self.configurations:
            config_name = (
                f"{config_spec['algorithm']}-{config_spec['key_size']}-{config_spec['mode']}"
            )
            results[config_name] = self.evaluate_configuration(config_spec)
        return results
