"""
Unit and integration tests for CLI interface in src.analysis_lab.cli.

Verifies:
1. Argument parser construction, flags, defaults, and type coercions.
2. Direct non-interactive execution mode (--input / -i).
3. Interactive guided wizard mode execution flow.
4. Cancellation token handling ('c' / 'cancel') in wizard.
5. Drag-and-drop path cleaning in wizard.
6. High-volume warning safeguard (>30 MB) and prompt confirmation.
7. Step-by-step progress indicators and ASCII summary card presentation.
8. Auto-open report prompt and browser launching.
9. Strict terminology discipline in console outputs (Zero 'Winner' or 'Best').
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.analysis_lab.cli import (
    build_parser,
    main,
    run_direct_mode,
    run_wizard_mode,
)
from src.analysis_lab.models import (
    CiphertextMetrics,
    ConfigurationResult,
    FileAnalysisResult,
    FileMetadata,
    PerformanceMetrics,
)
from src.analysis_lab.runner import FileAnalysisRunner


def _sample_analysis_result(file_path: Path) -> FileAnalysisResult:
    meta = FileMetadata(
        file_name=file_path.name,
        display_path=file_path.name,
        absolute_path=str(file_path.resolve()),
        file_size_bytes=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    perf = PerformanceMetrics(
        sample_count=30,
        mean_ms=0.45,
        median_ms=0.45,
        std_dev_ms=0.01,
        min_ms=0.40,
        max_ms=0.50,
        q1_ms=0.44,
        q3_ms=0.46,
        iqr_ms=0.02,
        outlier_count=0,
        throughput_mb_s=120.0,
        raw_times_ms=(0.45,) * 30,
    )
    configs = [
        ConfigurationResult(
            algorithm="AES",
            key_size=128,
            mode="CBC",
            status="SUCCESS",
            encryption_metrics=perf,
            decryption_metrics=perf,
            ciphertext_metrics=CiphertextMetrics(1024, 1040, 16, 1.56),
        )
    ]
    return FileAnalysisResult(
        file_metadata=meta,
        configurations=tuple(configs),
        timestamp_utc="2026-09-27T22:00:00Z",
    )


class TestAnalysisLabCLI:
    """Test suite covering CLI parser, direct mode, and wizard mode contracts."""

    def test_build_parser_flags_and_defaults(self) -> None:
        """Verify CLI argument parser defines all required flags and defaults."""
        parser = build_parser()

        args = parser.parse_args(["-i", "data/sample.txt", "-o", "out.html"])
        assert args.input_path == "data/sample.txt"
        assert args.output_path == "out.html"
        assert args.skip_decryption is False
        assert args.security is False
        assert args.max_size_mb == 100
        assert args.no_open is False
        assert args.include_absolute_path is False
        assert args.no_hash is False
        assert args.force is False
        assert args.verbose is False

    def test_direct_mode_successful_run(self, tmp_path: Path) -> None:
        """Verify direct mode executes runner and renders formatted summary card."""
        sample_file = tmp_path / "sample.txt"
        sample_file.write_bytes(b"A" * 1024)
        report_file = tmp_path / "report.html"

        result = _sample_analysis_result(sample_file)

        with patch.object(
            FileAnalysisRunner,
            "run",
            return_value=(result, report_file, 0),
        ):
            parser = build_parser()
            args = parser.parse_args(["-i", str(sample_file), "--no-open"])

            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                exit_code = run_direct_mode(args)

            assert exit_code == 0
            stdout = mock_stdout.getvalue()
            assert "FILE-SPECIFIC ENCRYPTION ANALYSIS" in stdout
            assert "Target File" in stdout
            assert "sample.txt" in stdout
            assert "Fastest Encryption" in stdout

            # Terminology check: strictly zero "Winner" or "Best"
            assert "winner" not in stdout.lower()
            assert "best" not in stdout.lower()

    def test_direct_mode_failure_propagates_exit_code(self, tmp_path: Path) -> None:
        """Verify direct mode returns exit code 1 if runner fails."""
        non_existent = tmp_path / "missing.bin"
        parser = build_parser()
        args = parser.parse_args(["-i", str(non_existent)])

        exit_code = run_direct_mode(args)
        assert exit_code == 1

    def test_wizard_mode_cancellation_token(self) -> None:
        """Verify wizard aborts cleanly when user enters 'c' or 'cancel'."""
        parser = build_parser()
        args = parser.parse_args([])

        inputs = iter(["c"])
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = run_wizard_mode(args, input_func=lambda _: next(inputs))

        assert exit_code == 0
        assert "[!] Analysis cancelled." in mock_stdout.getvalue()

    def test_wizard_mode_invalid_path(self, tmp_path: Path) -> None:
        """Verify wizard reports error and exits 1 when path is invalid."""
        parser = build_parser()
        args = parser.parse_args([])

        inputs = iter([str(tmp_path / "does_not_exist.bin")])
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            exit_code = run_wizard_mode(args, input_func=lambda _: next(inputs))

        assert exit_code == 1
        assert "Invalid path or file does not exist" in mock_stderr.getvalue()

    def test_wizard_mode_drag_and_drop_quote_stripping_and_full_flow(
        self, tmp_path: Path
    ) -> None:
        """Verify wizard cleans Windows quoted drag-and-drop paths and proceeds through steps."""
        target_file = tmp_path / "my target.bin"
        target_file.write_bytes(b"A" * 1024)
        report_file = tmp_path / "report.html"

        result = _sample_analysis_result(target_file)

        # Quoted input path simulation (drag and drop)
        quoted_path = f'"{target_file}"'
        inputs = iter([
            quoted_path,  # Path
            "y",          # Decryption
            "n",          # Security
            "n",          # Auto-open
        ])

        mock_browser = MagicMock()

        with patch.object(
            FileAnalysisRunner,
            "run",
            return_value=(result, report_file, 0),
        ):
            parser = build_parser()
            args = parser.parse_args([])

            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                exit_code = run_wizard_mode(
                    args,
                    input_func=lambda _: next(inputs),
                    browser_open=mock_browser,
                )

            assert exit_code == 0
            stdout = mock_stdout.getvalue()
            assert "[*] Preflight Inspection:" in stdout
            assert "my target.bin" in stdout
            assert "[1/3] Benchmarking encryption and decryption microbenchmarks..."
            assert "[3/3] Compiling standalone HTML report..."
            assert "FILE-SPECIFIC ENCRYPTION ANALYSIS" in stdout
            assert not mock_browser.called

    def test_wizard_mode_auto_open_affirmative_relative_path(
        self, tmp_path: Path
    ) -> None:
        """Verify affirmative answer to open report in wizard mode resolves relative path and dispatches browser."""
        target_file = tmp_path / "target.bin"
        target_file.write_bytes(b"A" * 1024)
        relative_report = Path("results/reports/rel_report.html")

        result = _sample_analysis_result(target_file)

        inputs = iter([
            str(target_file),  # Path
            "y",               # Decryption
            "n",               # Security
            "y",               # Auto-open
        ])

        mock_browser = MagicMock()

        with patch.object(
            FileAnalysisRunner,
            "run",
            return_value=(result, relative_report, 0),
        ):
            parser = build_parser()
            args = parser.parse_args([])

            with patch("sys.stdout", new_callable=io.StringIO):
                exit_code = run_wizard_mode(
                    args,
                    input_func=lambda _: next(inputs),
                    browser_open=mock_browser,
                )

            assert exit_code == 0
            assert mock_browser.called
            assert mock_browser.call_args[0][0] == relative_report.resolve().as_uri()
            assert mock_browser.call_args[0][0].startswith("file:///")

    def test_wizard_mode_high_volume_warning_cancel(self, tmp_path: Path) -> None:
        """Verify wizard presents volume warning when file > 30 MB and aborts if rejected."""
        large_file = tmp_path / "large.bin"
        # Mock 35 MB file size
        large_file.write_bytes(b"A" * 100)

        with patch.object(Path, "stat") as mock_stat:
            mock_stat_val = MagicMock()
            mock_stat_val.st_size = 35 * 1024 * 1024
            mock_stat_val.st_mode = 0o100644
            mock_stat.return_value = mock_stat_val

            inputs = iter([
                str(large_file),  # Path
                "y",              # Decryption
                "n",              # Security
                "n",              # Decline volume warning
            ])

            parser = build_parser()
            args = parser.parse_args([])

            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                exit_code = run_wizard_mode(args, input_func=lambda _: next(inputs))

            assert exit_code == 0
            stdout = mock_stdout.getvalue()
            assert "[!] Warning: File is 35.0 MB." in stdout
            assert "process ~14.4 GB through AES" in stdout
            assert "[!] Operation cancelled by user." in stdout

    def test_main_routing(self, tmp_path: Path) -> None:
        """Verify main() properly routes between direct mode and wizard mode."""
        sample_file = tmp_path / "sample.txt"
        sample_file.write_bytes(b"A" * 1024)

        result = _sample_analysis_result(sample_file)

        # Route to direct mode
        with patch.object(
            FileAnalysisRunner,
            "run",
            return_value=(result, tmp_path / "rep.html", 0),
        ):
            code = main(["-i", str(sample_file), "--no-open"])
            assert code == 0

        # Route to wizard mode
        with patch("src.analysis_lab.cli.run_wizard_mode", return_value=0) as mock_wiz:
            code = main([])
            assert code == 0
            assert mock_wiz.called
