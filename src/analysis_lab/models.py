"""
Data models for the File-Specific Encryption Analysis Lab.

Defines strictly typed, immutable data structures representing target file metadata,
cryptographic performance benchmarks, ciphertext overhead analysis, and security diffusion metrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class FileMetadata:
    """Metadata describing a target file evaluated in the laboratory."""

    file_name: str
    display_path: str
    file_size_bytes: int
    absolute_path: str | None = None
    sha256_hash: str | None = None
    is_bmp: bool = False

    @property
    def is_zero_byte(self) -> bool:
        """Return True if the target file has a size of 0 bytes."""
        return self.file_size_bytes == 0


@dataclass(frozen=True)
class PerformanceMetrics:
    """Statistical summary metrics for a microbenchmark execution run."""

    sample_count: int
    mean_ms: float
    median_ms: float
    std_dev_ms: float
    min_ms: float
    max_ms: float
    q1_ms: float
    q3_ms: float
    iqr_ms: float
    outlier_count: int
    throughput_mb_s: float | None
    raw_times_ms: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CiphertextMetrics:
    """Exact dimensions and PKCS#7 padding overhead derived from ciphertext."""

    plaintext_size_bytes: int
    ciphertext_size_bytes: int
    padding_overhead_bytes: int
    expansion_percentage: float | None


@dataclass(frozen=True)
class SecurityMetrics:
    """Empirical diffusion metrics obtained from 1-bit mutation tests."""

    status: str  # "SUCCESS", "SKIPPED", "FAILED"
    avalanche_effect_pct: float | None = None
    key_sensitivity_pct: float | None = None
    notes: str | None = None
    ecb_weakness_analyzed: bool = False


@dataclass(frozen=True)
class ConfigurationResult:
    """Laboratory evaluation result for a single cryptographic configuration."""

    algorithm: str
    key_size: int
    mode: str
    status: str  # "SUCCESS", "FAILED"
    error_message: str | None = None
    encryption_metrics: PerformanceMetrics | None = None
    decryption_metrics: PerformanceMetrics | None = None
    ciphertext_metrics: CiphertextMetrics | None = None
    security_metrics: SecurityMetrics | None = None

    @property
    def config_name(self) -> str:
        """Formatted canonical name of configuration (e.g. 'AES-128-CBC')."""
        return f"{self.algorithm}-{self.key_size}-{self.mode}"


@dataclass(frozen=True)
class FileAnalysisResult:
    """Consolidated laboratory report container for an evaluated target file."""

    file_metadata: FileMetadata
    configurations: tuple[ConfigurationResult, ...]
    timestamp_utc: str
    skip_decryption: bool = False
    security_enabled: bool = False

    @property
    def success_count(self) -> int:
        """Count of configurations that executed successfully."""
        return sum(1 for c in self.configurations if c.status == "SUCCESS")

    @property
    def failure_count(self) -> int:
        """Count of configurations that failed during setup or benchmarking."""
        return sum(1 for c in self.configurations if c.status == "FAILED")

    @property
    def fastest_encryption_config(self) -> str | None:
        """
        Identify fastest configuration in this experiment by lowest sample mean latency.

        Partial-run semantics:
        - Evaluated strictly across configurations where status == 'SUCCESS' and
          encryption_metrics is not None.
        - Failed configurations are strictly excluded.
        - Ranked strictly by lowest sample mean latency (mean_ms).
        - If zero configurations succeeded, returns None.
        """
        candidates = [
            c
            for c in self.configurations
            if c.status == "SUCCESS" and c.encryption_metrics is not None
        ]
        if not candidates:
            return None
        best = min(candidates, key=lambda c: c.encryption_metrics.mean_ms)  # type: ignore[union-attr]
        return f"{best.config_name} ({best.encryption_metrics.mean_ms:.2f} ms)"  # type: ignore[union-attr]

    @property
    def fastest_decryption_config(self) -> str | None:
        """
        Identify fastest decryption configuration by lowest sample mean latency.

        Partial-run semantics:
        - Evaluated strictly across configurations where status == 'SUCCESS' and
          decryption_metrics is not None.
        - Failed configurations are strictly excluded.
        - If decryption was skipped (skip_decryption=True) or zero configurations
          succeeded in decryption, returns None.
        - Ranked strictly by lowest sample mean latency (mean_ms).
        """
        if self.skip_decryption:
            return None
        candidates = [
            c
            for c in self.configurations
            if c.status == "SUCCESS" and c.decryption_metrics is not None
        ]
        if not candidates:
            return None
        best = min(candidates, key=lambda c: c.decryption_metrics.mean_ms)  # type: ignore[union-attr]
        return f"{best.config_name} ({best.decryption_metrics.mean_ms:.2f} ms)"  # type: ignore[union-attr]
