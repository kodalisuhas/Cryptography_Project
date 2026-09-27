"""
Unit tests for File-Specific Encryption Analysis Lab data models.
"""

from dataclasses import FrozenInstanceError
import pytest

from src.analysis_lab.models import (
    CiphertextMetrics,
    ConfigurationResult,
    FileAnalysisResult,
    FileMetadata,
    PerformanceMetrics,
    SecurityMetrics,
)


class TestFileMetadata:
    """Tests for FileMetadata container."""

    def test_creation_and_properties(self):
        meta = FileMetadata(
            file_name="sample.txt",
            display_path="data/sample.txt",
            file_size_bytes=1024,
            absolute_path="C:/full/data/sample.txt",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            is_bmp=False,
        )
        assert meta.file_name == "sample.txt"
        assert meta.display_path == "data/sample.txt"
        assert meta.file_size_bytes == 1024
        assert meta.absolute_path == "C:/full/data/sample.txt"
        assert meta.sha256_hash is not None
        assert not meta.is_zero_byte
        assert not meta.is_bmp

    def test_zero_byte_detection(self):
        meta = FileMetadata(
            file_name="empty.bin",
            display_path="empty.bin",
            file_size_bytes=0,
        )
        assert meta.is_zero_byte
        assert meta.file_size_bytes == 0

    def test_immutability(self):
        meta = FileMetadata(
            file_name="immutable.txt",
            display_path="immutable.txt",
            file_size_bytes=100,
        )
        with pytest.raises(FrozenInstanceError):
            meta.file_name = "modified.txt"  # type: ignore[misc]


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics container."""

    def test_creation_and_fields(self):
        metrics = PerformanceMetrics(
            sample_count=30,
            mean_ms=1.25,
            median_ms=1.20,
            std_dev_ms=0.08,
            min_ms=1.10,
            max_ms=1.50,
            q1_ms=1.18,
            q3_ms=1.28,
            iqr_ms=0.10,
            outlier_count=1,
            throughput_mb_s=800.5,
            raw_times_ms=(1.2, 1.3, 1.25),
        )
        assert metrics.sample_count == 30
        assert metrics.mean_ms == 1.25
        assert metrics.throughput_mb_s == 800.5
        assert len(metrics.raw_times_ms) == 3

    def test_zero_byte_throughput_none(self):
        metrics = PerformanceMetrics(
            sample_count=30,
            mean_ms=0.05,
            median_ms=0.05,
            std_dev_ms=0.01,
            min_ms=0.04,
            max_ms=0.08,
            q1_ms=0.045,
            q3_ms=0.055,
            iqr_ms=0.01,
            outlier_count=0,
            throughput_mb_s=None,
        )
        assert metrics.throughput_mb_s is None

    def test_immutability(self):
        metrics = PerformanceMetrics(
            sample_count=30,
            mean_ms=1.0,
            median_ms=1.0,
            std_dev_ms=0.1,
            min_ms=0.9,
            max_ms=1.2,
            q1_ms=0.95,
            q3_ms=1.05,
            iqr_ms=0.1,
            outlier_count=0,
            throughput_mb_s=100.0,
        )
        with pytest.raises(FrozenInstanceError):
            metrics.mean_ms = 2.0  # type: ignore[misc]


class TestCiphertextMetrics:
    """Tests for CiphertextMetrics container."""

    def test_creation_and_immutability(self):
        cm = CiphertextMetrics(
            plaintext_size_bytes=16,
            ciphertext_size_bytes=32,
            padding_overhead_bytes=16,
            expansion_percentage=100.0,
        )
        assert cm.plaintext_size_bytes == 16
        assert cm.ciphertext_size_bytes == 32
        assert cm.padding_overhead_bytes == 16
        assert cm.expansion_percentage == 100.0

        with pytest.raises(FrozenInstanceError):
            cm.padding_overhead_bytes = 0  # type: ignore[misc]


class TestSecurityMetrics:
    """Tests for SecurityMetrics container."""

    def test_success_and_skipped(self):
        sec_success = SecurityMetrics(
            status="SUCCESS",
            avalanche_effect_pct=50.2,
            key_sensitivity_pct=49.8,
        )
        assert sec_success.status == "SUCCESS"
        assert sec_success.avalanche_effect_pct == 50.2

        sec_skipped = SecurityMetrics(
            status="SKIPPED",
            notes="Diffusion metrics require non-empty payload.",
        )
        assert sec_skipped.status == "SKIPPED"
        assert sec_skipped.avalanche_effect_pct is None


class TestConfigurationResult:
    """Tests for ConfigurationResult container."""

    def test_config_name_and_fields(self):
        cr = ConfigurationResult(
            algorithm="AES",
            key_size=256,
            mode="CBC",
            status="SUCCESS",
        )
        assert cr.config_name == "AES-256-CBC"
        assert cr.status == "SUCCESS"
        assert cr.error_message is None

    def test_failed_configuration(self):
        cr = ConfigurationResult(
            algorithm="AES",
            key_size=128,
            mode="ECB",
            status="FAILED",
            error_message="Simulated key setup error",
        )
        assert cr.status == "FAILED"
        assert cr.error_message == "Simulated key setup error"
        assert cr.encryption_metrics is None


class TestFileAnalysisResult:
    """Tests for FileAnalysisResult container and partial-run ranking semantics."""

    @pytest.fixture
    def sample_metadata(self):
        return FileMetadata(
            file_name="test.dat",
            display_path="test.dat",
            file_size_bytes=1000,
        )

    def _make_perf(self, mean_ms: float) -> PerformanceMetrics:
        return PerformanceMetrics(
            sample_count=30,
            mean_ms=mean_ms,
            median_ms=mean_ms,
            std_dev_ms=0.05,
            min_ms=mean_ms - 0.1,
            max_ms=mean_ms + 0.1,
            q1_ms=mean_ms - 0.02,
            q3_ms=mean_ms + 0.02,
            iqr_ms=0.04,
            outlier_count=0,
            throughput_mb_s=500.0,
        )

    def test_counts_and_fastest_ranking_all_success(self, sample_metadata):
        c1 = ConfigurationResult(
            algorithm="AES",
            key_size=128,
            mode="CBC",
            status="SUCCESS",
            encryption_metrics=self._make_perf(0.50),
            decryption_metrics=self._make_perf(0.40),
        )
        c2 = ConfigurationResult(
            algorithm="AES",
            key_size=256,
            mode="CBC",
            status="SUCCESS",
            encryption_metrics=self._make_perf(0.70),
            decryption_metrics=self._make_perf(0.60),
        )
        c3 = ConfigurationResult(
            algorithm="AES",
            key_size=128,
            mode="ECB",
            status="SUCCESS",
            encryption_metrics=self._make_perf(0.30),
            decryption_metrics=self._make_perf(0.35),
        )

        result = FileAnalysisResult(
            file_metadata=sample_metadata,
            configurations=(c1, c2, c3),
            timestamp_utc="2026-09-27T20:00:00Z",
        )

        assert result.success_count == 3
        assert result.failure_count == 0
        assert result.fastest_encryption_config == "AES-128-ECB (0.30 ms)"
        assert result.fastest_decryption_config == "AES-128-ECB (0.35 ms)"

    def test_fastest_ranking_partial_failure(self, sample_metadata):
        # c1 has lowest latency, but failed! It must be excluded from ranking.
        c1 = ConfigurationResult(
            algorithm="AES",
            key_size=128,
            mode="ECB",
            status="FAILED",
            error_message="Device error",
            encryption_metrics=self._make_perf(0.10),
            decryption_metrics=self._make_perf(0.10),
        )
        c2 = ConfigurationResult(
            algorithm="AES",
            key_size=128,
            mode="CBC",
            status="SUCCESS",
            encryption_metrics=self._make_perf(0.45),
            decryption_metrics=self._make_perf(0.42),
        )
        c3 = ConfigurationResult(
            algorithm="AES",
            key_size=256,
            mode="CBC",
            status="SUCCESS",
            encryption_metrics=self._make_perf(0.65),
            decryption_metrics=self._make_perf(0.58),
        )

        result = FileAnalysisResult(
            file_metadata=sample_metadata,
            configurations=(c1, c2, c3),
            timestamp_utc="2026-09-27T20:00:00Z",
        )

        assert result.success_count == 2
        assert result.failure_count == 1
        # c1 is excluded despite 0.10 ms latency
        assert result.fastest_encryption_config == "AES-128-CBC (0.45 ms)"
        assert result.fastest_decryption_config == "AES-128-CBC (0.42 ms)"

    def test_all_failed_returns_none(self, sample_metadata):
        c1 = ConfigurationResult(
            algorithm="AES",
            key_size=128,
            mode="CBC",
            status="FAILED",
            error_message="Error 1",
        )
        c2 = ConfigurationResult(
            algorithm="AES",
            key_size=256,
            mode="CBC",
            status="FAILED",
            error_message="Error 2",
        )

        result = FileAnalysisResult(
            file_metadata=sample_metadata,
            configurations=(c1, c2),
            timestamp_utc="2026-09-27T20:00:00Z",
        )

        assert result.success_count == 0
        assert result.failure_count == 2
        assert result.fastest_encryption_config is None
        assert result.fastest_decryption_config is None

    def test_skip_decryption_returns_none(self, sample_metadata):
        c1 = ConfigurationResult(
            algorithm="AES",
            key_size=128,
            mode="CBC",
            status="SUCCESS",
            encryption_metrics=self._make_perf(0.50),
            decryption_metrics=None,
        )

        result = FileAnalysisResult(
            file_metadata=sample_metadata,
            configurations=(c1,),
            timestamp_utc="2026-09-27T20:00:00Z",
            skip_decryption=True,
        )

        assert result.fastest_encryption_config == "AES-128-CBC (0.50 ms)"
        assert result.fastest_decryption_config is None
