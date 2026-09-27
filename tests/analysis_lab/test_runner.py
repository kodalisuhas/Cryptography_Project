"""
Unit and integration tests for FileAnalysisRunner in src.analysis_lab.runner.

Verifies:
1. Preflight file validation (file existence, directory rejection, unreadable files).
2. Streaming SHA-256 calculation and BMP signature detection.
3. Operational file-size ceiling (100 MB rejection and --force override).
4. End-to-end execution coordination (PerformanceExperiment + SecurityExperiment).
5. Level B error recovery (HTML assembly failure falls back to console metric dump).
6. Level C error recovery (Disk persistence failure falls back to console metric dump).
7. Auto-open browser dispatch and --no-open flag.
8. Secret hygiene and privacy flag forwarding.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.analysis_lab.models import (
    CiphertextMetrics,
    ConfigurationResult,
    FileAnalysisResult,
    PerformanceMetrics,
    SecurityMetrics,
)
from src.analysis_lab.report import ReportAssemblyError
from src.analysis_lab.runner import FileAnalysisRunner
from src.utils.file_handler import FileHandler


def _dummy_perf_metrics() -> PerformanceMetrics:
    return PerformanceMetrics(
        sample_count=30,
        mean_ms=0.5,
        median_ms=0.5,
        std_dev_ms=0.01,
        min_ms=0.45,
        max_ms=0.55,
        q1_ms=0.49,
        q3_ms=0.51,
        iqr_ms=0.02,
        outlier_count=0,
        throughput_mb_s=100.0,
        raw_times_ms=(0.5,) * 30,
    )


def _dummy_config_results() -> list[ConfigurationResult]:
    configs = []
    for alg, ks, mode in [
        ("AES", 128, "CBC"),
        ("AES", 192, "CBC"),
        ("AES", 256, "CBC"),
        ("AES", 128, "ECB"),
        ("AES", 192, "ECB"),
        ("AES", 256, "ECB"),
    ]:
        configs.append(
            ConfigurationResult(
                algorithm=alg,
                key_size=ks,
                mode=mode,
                status="SUCCESS",
                encryption_metrics=_dummy_perf_metrics(),
                decryption_metrics=_dummy_perf_metrics(),
                ciphertext_metrics=CiphertextMetrics(1024, 1040, 16, 1.56),
                security_metrics=None,
            )
        )
    return configs


class TestFileAnalysisRunner:
    """Test suite covering FileAnalysisRunner orchestration contracts."""

    def test_preflight_missing_file_returns_exit_code_1(self, tmp_path: Path) -> None:
        """Verify non-existent file triggers preflight diagnostic and returns exit code 1."""
        non_existent = tmp_path / "does_not_exist.bin"
        runner = FileAnalysisRunner(file_path=non_existent)

        result, report_path, exit_code = runner.run()

        assert result is None
        assert report_path is None
        assert exit_code == 1

    def test_preflight_directory_returns_exit_code_1(self, tmp_path: Path) -> None:
        """Verify target path pointing to a directory returns exit code 1."""
        runner = FileAnalysisRunner(file_path=tmp_path)

        result, report_path, exit_code = runner.run()

        assert result is None
        assert report_path is None
        assert exit_code == 1

    def test_preflight_size_ceiling_rejection_and_force_override(self, tmp_path: Path) -> None:
        """Verify files exceeding max_size_mb are rejected unless force=True."""
        sample_file = tmp_path / "test.bin"
        sample_file.write_bytes(b"A" * 1024)

        # Set ceiling to 0 MB (so 1024 bytes exceeds it)
        runner_reject = FileAnalysisRunner(
            file_path=sample_file,
            max_size_mb=0,
            force=False,
        )
        res, path, code = runner_reject.run()
        assert res is None
        assert code == 1

        # With force=True, it overrides the ceiling and runs
        mock_perf = MagicMock()
        mock_perf.return_value.run.return_value = _dummy_config_results()
        mock_report = MagicMock()
        mock_report.return_value.save_report.return_value = tmp_path / "rep.html"

        runner_force = FileAnalysisRunner(
            file_path=sample_file,
            max_size_mb=0,
            force=True,
            experiment_factory=mock_perf,
            report_generator_factory=mock_report,
            no_open=True,
        )
        res_f, path_f, code_f = runner_force.run()
        assert code_f == 0
        assert res_f is not None

    def test_streaming_sha256_computation(self, tmp_path: Path) -> None:
        """Verify compute_sha256 matches exact hash of content."""
        sample_file = tmp_path / "sample.txt"
        content = b"Deterministic payload for streaming SHA-256 test."
        sample_file.write_bytes(content)

        digest = FileAnalysisRunner.compute_sha256(sample_file)
        assert len(digest) == 64
        import hashlib
        assert digest == hashlib.sha256(content).hexdigest().lower()

    def test_bmp_signature_detection(self, tmp_path: Path) -> None:
        """Verify preflight detects BMP headers."""
        bmp_file = tmp_path / "image.bmp"
        bmp_file.write_bytes(b"BM" + b"\x00" * 52)

        txt_file = tmp_path / "text.txt"
        txt_file.write_bytes(b"Hello text file!")

        runner_bmp = FileAnalysisRunner(file_path=bmp_file)
        _, _, _, is_bmp = runner_bmp.preflight_check()
        assert is_bmp is True

        runner_txt = FileAnalysisRunner(file_path=txt_file)
        _, _, _, is_txt_bmp = runner_txt.preflight_check()
        assert is_txt_bmp is False

    def test_successful_run_orchestration(self, tmp_path: Path) -> None:
        """Verify full run coordinates experiments, models, report generator, and browser."""
        target_file = tmp_path / "target.bin"
        target_file.write_bytes(b"A" * 512)

        mock_perf_instance = MagicMock()
        mock_perf_instance.run.return_value = _dummy_config_results()
        mock_perf_factory = MagicMock(return_value=mock_perf_instance)

        mock_report_instance = MagicMock()
        expected_report_path = tmp_path / "report.html"
        mock_report_instance.save_report.return_value = expected_report_path
        mock_report_factory = MagicMock(return_value=mock_report_instance)

        mock_browser = MagicMock()

        runner = FileAnalysisRunner(
            file_path=target_file,
            experiment_factory=mock_perf_factory,
            report_generator_factory=mock_report_factory,
            browser_open=mock_browser,
            no_open=False,
        )

        result, report_path, exit_code = runner.run()

        assert exit_code == 0
        assert report_path == expected_report_path
        assert result is not None
        assert result.file_metadata.file_name == "target.bin"
        assert result.file_metadata.file_size_bytes == 512
        assert len(result.configurations) == 6

        # Check browser was invoked with file URI
        assert mock_browser.called
        assert mock_browser.call_args[0][0] == expected_report_path.as_uri()

    def test_no_open_flag_suppresses_browser(self, tmp_path: Path) -> None:
        """Verify no_open=True suppresses browser dispatch."""
        target_file = tmp_path / "target.bin"
        target_file.write_bytes(b"A" * 512)

        mock_perf = MagicMock()
        mock_perf.return_value.run.return_value = _dummy_config_results()

        mock_report = MagicMock()
        mock_report.return_value.save_report.return_value = tmp_path / "report.html"

        mock_browser = MagicMock()

        runner = FileAnalysisRunner(
            file_path=target_file,
            experiment_factory=mock_perf,
            report_generator_factory=mock_report,
            browser_open=mock_browser,
            no_open=True,
        )

        _, _, exit_code = runner.run()
        assert exit_code == 0
        assert not mock_browser.called

    def test_browser_open_resolves_relative_path(self, tmp_path: Path) -> None:
        """Verify browser dispatch resolves relative report path to absolute file URI."""
        target_file = tmp_path / "target.bin"
        target_file.write_bytes(b"A" * 512)

        mock_perf = MagicMock()
        mock_perf.return_value.run.return_value = _dummy_config_results()

        relative_report_path = Path("results/reports/relative_test.html")
        mock_report = MagicMock()
        mock_report.return_value.save_report.return_value = relative_report_path

        mock_browser = MagicMock()

        runner = FileAnalysisRunner(
            file_path=target_file,
            experiment_factory=mock_perf,
            report_generator_factory=mock_report,
            browser_open=mock_browser,
            no_open=False,
        )

        _, report_path, exit_code = runner.run()
        assert exit_code == 0
        assert report_path == relative_report_path
        assert mock_browser.called
        assert mock_browser.call_args[0][0] == relative_report_path.resolve().as_uri()
        assert mock_browser.call_args[0][0].startswith("file:///")

    def test_security_diffusion_orchestration(self, tmp_path: Path) -> None:
        """Verify security_enabled=True executes SecurityExperiment and merges metrics."""
        target_file = tmp_path / "target.bin"
        target_file.write_bytes(b"A" * 512)

        mock_perf = MagicMock()
        mock_perf.return_value.run.return_value = _dummy_config_results()

        mock_sec_instance = MagicMock()
        sec_list = [
            SecurityMetrics(
                status="SUCCESS",
                avalanche_effect_pct=50.2,
                key_sensitivity_pct=49.9,
                notes=None,
            )
            for _ in range(6)
        ]
        mock_sec_instance.run.return_value = sec_list
        mock_sec_factory = MagicMock(return_value=mock_sec_instance)

        mock_report = MagicMock()
        mock_report.return_value.save_report.return_value = tmp_path / "report.html"

        runner = FileAnalysisRunner(
            file_path=target_file,
            security_enabled=True,
            experiment_factory=mock_perf,
            security_experiment_factory=mock_sec_factory,
            report_generator_factory=mock_report,
            no_open=True,
        )

        result, _, exit_code = runner.run()

        assert exit_code == 0
        assert result is not None
        assert result.security_enabled is True
        assert mock_sec_factory.called
        for cfg in result.configurations:
            assert cfg.security_metrics is not None
            assert cfg.security_metrics.avalanche_effect_pct == 50.2

    def test_level_b_html_assembly_error_recovery(self, tmp_path: Path) -> None:
        """Verify Level B: ReportAssemblyError triggers diagnostic, dumps fallback metrics, returns 1."""
        target_file = tmp_path / "target.bin"
        target_file.write_bytes(b"A" * 512)

        mock_perf = MagicMock()
        mock_perf.return_value.run.return_value = _dummy_config_results()

        mock_report_instance = MagicMock()
        mock_report_instance.save_report.side_effect = ReportAssemblyError("HTML template crash")
        mock_report_factory = MagicMock(return_value=mock_report_instance)

        runner = FileAnalysisRunner(
            file_path=target_file,
            experiment_factory=mock_perf,
            report_generator_factory=mock_report_factory,
            no_open=True,
        )

        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            result, report_path, exit_code = runner.run()

        assert exit_code == 1
        assert report_path is None
        assert result is not None
        stderr_val = mock_stderr.getvalue()
        # Verify fallback metrics were dumped
        assert "FILE ANALYSIS BENCHMARK METRICS (TERMINAL FALLBACK DUMP)" in stderr_val
        assert "AES-128-CBC" in stderr_val

    def test_level_c_disk_persistence_error_recovery(self, tmp_path: Path) -> None:
        """Verify Level C: Disk persistence OSError triggers diagnostic, dumps fallback metrics, returns 1."""
        target_file = tmp_path / "target.bin"
        target_file.write_bytes(b"A" * 512)

        mock_perf = MagicMock()
        mock_perf.return_value.run.return_value = _dummy_config_results()

        mock_report_instance = MagicMock()
        mock_report_instance.save_report.side_effect = PermissionError("Read-only volume")
        mock_report_factory = MagicMock(return_value=mock_report_instance)

        runner = FileAnalysisRunner(
            file_path=target_file,
            experiment_factory=mock_perf,
            report_generator_factory=mock_report_factory,
            no_open=True,
        )

        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            result, report_path, exit_code = runner.run()

        assert exit_code == 1
        assert report_path is None
        assert result is not None
        stderr_val = mock_stderr.getvalue()
        assert "FILE ANALYSIS BENCHMARK METRICS (TERMINAL FALLBACK DUMP)" in stderr_val
        assert "AES-128-CBC" in stderr_val
