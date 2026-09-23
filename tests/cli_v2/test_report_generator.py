"""Comprehensive behavioral test suite for V2 ReportGenerator (Stage 3.2).

Verifies standalone HTML report generation, in-memory Matplotlib figure
serialization to Base64 PNG Data URIs, figure lifecycle / closure guarantees,
3-tier metadata, executive summaries, benchmark tables, cryptanalysis metrics,
ECB vs. CBC structural comparisons, methodology sections, XSS entity escaping,
browser auto-open dispatch, and real V1 integration.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import html
import io
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import matplotlib
matplotlib.use("Agg")  # Ensure headless mode for test suite
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from src.analyzers.metric_collector import MetricCollector
from src.analyzers.security_evaluator import SecurityEvaluator
from src.cli_v2.report_generator import (
    ReportGenerator,
    _escape,
    _file_timestamp,
    _iso_timestamp,
    _utc_now,
)
from src.engines.cipher_factory import CipherFactory
from src.engines.security_service import SecurityService
from src.utils.file_handler import FileHandler


# ===========================================================================
# Helper Fixtures & Test Data
# ===========================================================================


@pytest.fixture
def sample_summary_df() -> pd.DataFrame:
    """Create a realistic benchmark summary DataFrame with multiple configs."""
    rows = [
        {
            "algorithm": "AES",
            "key_size": 128,
            "mode": "CBC",
            "data_size_bytes": 1048576,
            "count": 30,
            "mean_time_ms": 12.50,
            "median_time_ms": 12.30,
            "std_dev_time_ms": 0.45,
            "min_time_ms": 11.80,
            "max_time_ms": 13.90,
            "q1_ms": 12.10,
            "q3_ms": 12.70,
            "iqr_ms": 0.60,
            "outlier_count": 1,
            "throughput_mb_s": 80.00,
            "memory_delta_mb": 0.0,
        },
        {
            "algorithm": "AES",
            "key_size": 256,
            "mode": "CBC",
            "data_size_bytes": 1048576,
            "count": 30,
            "mean_time_ms": 17.00,
            "median_time_ms": 16.80,
            "std_dev_time_ms": 0.60,
            "min_time_ms": 16.00,
            "max_time_ms": 18.50,
            "q1_ms": 16.50,
            "q3_ms": 17.30,
            "iqr_ms": 0.80,
            "outlier_count": 2,
            "throughput_mb_s": 58.82,
            "memory_delta_mb": 0.0,
        },
        {
            "algorithm": "AES",
            "key_size": 128,
            "mode": "ECB",
            "data_size_bytes": 1048576,
            "count": 30,
            "mean_time_ms": 11.00,
            "median_time_ms": 10.90,
            "std_dev_time_ms": 0.35,
            "min_time_ms": 10.50,
            "max_time_ms": 12.00,
            "q1_ms": 10.75,
            "q3_ms": 11.20,
            "iqr_ms": 0.45,
            "outlier_count": 0,
            "throughput_mb_s": 90.91,
            "memory_delta_mb": 0.0,
        },
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def multi_size_summary_df() -> pd.DataFrame:
    """Create a benchmark summary DataFrame with multiple payload sizes."""
    rows = [
        # 1 KB size
        {
            "algorithm": "AES",
            "key_size": 128,
            "mode": "CBC",
            "data_size_bytes": 1024,
            "count": 30,
            "mean_time_ms": 0.05,
            "median_time_ms": 0.05,
            "std_dev_time_ms": 0.005,
            "min_time_ms": 0.04,
            "max_time_ms": 0.07,
            "q1_ms": 0.048,
            "q3_ms": 0.052,
            "iqr_ms": 0.004,
            "outlier_count": 0,
            "throughput_mb_s": 19.53,
            "memory_delta_mb": 0.0,
        },
        {
            "algorithm": "AES",
            "key_size": 256,
            "mode": "CBC",
            "data_size_bytes": 1024,
            "count": 30,
            "mean_time_ms": 0.07,
            "median_time_ms": 0.07,
            "std_dev_time_ms": 0.006,
            "min_time_ms": 0.06,
            "max_time_ms": 0.09,
            "q1_ms": 0.068,
            "q3_ms": 0.072,
            "iqr_ms": 0.004,
            "outlier_count": 0,
            "throughput_mb_s": 13.95,
            "memory_delta_mb": 0.0,
        },
        # 1 MB size
        {
            "algorithm": "AES",
            "key_size": 128,
            "mode": "CBC",
            "data_size_bytes": 1048576,
            "count": 30,
            "mean_time_ms": 12.50,
            "median_time_ms": 12.30,
            "std_dev_time_ms": 0.45,
            "min_time_ms": 11.80,
            "max_time_ms": 13.90,
            "q1_ms": 12.10,
            "q3_ms": 12.70,
            "iqr_ms": 0.60,
            "outlier_count": 1,
            "throughput_mb_s": 80.00,
            "memory_delta_mb": 0.0,
        },
        {
            "algorithm": "AES",
            "key_size": 256,
            "mode": "CBC",
            "data_size_bytes": 1048576,
            "count": 30,
            "mean_time_ms": 17.00,
            "median_time_ms": 16.80,
            "std_dev_time_ms": 0.60,
            "min_time_ms": 16.00,
            "max_time_ms": 18.50,
            "q1_ms": 16.50,
            "q3_ms": 17.30,
            "iqr_ms": 0.80,
            "outlier_count": 2,
            "throughput_mb_s": 58.82,
            "memory_delta_mb": 0.0,
        },
    ]
    return pd.DataFrame(rows)


@pytest.fixture
def sample_security_results() -> dict:
    """Create a realistic security evaluation results dictionary."""
    return {
        "AES-256-CBC": {
            "avalanche_effect": 49.85,
            "key_sensitivity": 50.12,
        },
        "AES-256-ECB": {
            "avalanche_effect": 50.05,
            "key_sensitivity": 49.90,
            "ecb_weakness": {
                "original_header": b"BM" + b"\x00" * 52,
                "original_pixel_data": b"\xAA" * 12288,
                "ecb_ciphertext": b"\xBB" * 12304,
                "cbc_ciphertext": b"\xCC" * 12304,
                "bmp_trailing_data": b"",
            },
        },
    }


# ===========================================================================
# A. figure_to_base64 Tests
# ===========================================================================


class TestFigureToBase64:
    """Verify figure serialization, DPI scaling, and memory lifecycle."""

    def test_valid_data_uri_format(self):
        """Serialization produces a valid data:image/png;base64,... URI."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [4, 5, 6])

        uri = ReportGenerator.figure_to_base64(fig)
        assert isinstance(uri, str)
        assert uri.startswith("data:image/png;base64,")

    def test_valid_png_magic_bytes(self):
        """Decoded base64 data contains valid PNG magic bytes."""
        fig, ax = plt.subplots()
        ax.bar(["A", "B"], [10, 20])

        uri = ReportGenerator.figure_to_base64(fig)
        b64_payload = uri.split("data:image/png;base64,")[1]
        raw_bytes = base64.b64decode(b64_payload)

        # Standard PNG magic signature: \x89PNG\r\n\x1a\n
        assert raw_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    def test_custom_dpi_respected(self):
        """Different DPI parameters yield different image byte payload sizes."""
        fig1, ax1 = plt.subplots(figsize=(4, 3))
        ax1.plot([1, 2], [1, 2])
        uri_low = ReportGenerator.figure_to_base64(fig1, dpi=72)

        fig2, ax2 = plt.subplots(figsize=(4, 3))
        ax2.plot([1, 2], [1, 2])
        uri_high = ReportGenerator.figure_to_base64(fig2, dpi=200)

        # Higher DPI creates more pixels, resulting in a larger base64 string
        assert len(uri_high) > len(uri_low)

    def test_figure_closed_on_success(self):
        """Figure is closed and freed from pyplot after successful encoding."""
        fig, ax = plt.subplots()
        fig_num = fig.number
        assert plt.fignum_exists(fig_num)

        ReportGenerator.figure_to_base64(fig)
        assert not plt.fignum_exists(fig_num)

    def test_figure_closed_on_failure(self):
        """Figure is closed even when savefig / encoding raises an exception."""
        fig, ax = plt.subplots()
        fig_num = fig.number
        assert plt.fignum_exists(fig_num)

        # Mock savefig to raise an exception
        with patch.object(fig, "savefig", side_effect=RuntimeError("Mock savefig error")):
            with pytest.raises(RuntimeError, match="Mock savefig error"):
                ReportGenerator.figure_to_base64(fig)

        # Confirm figure was closed in finally block despite exception
        assert not plt.fignum_exists(fig_num)


# ===========================================================================
# B. Benchmark Report Tests
# ===========================================================================


class TestBenchmarkReport:
    """Verify HTML benchmark report generation, sections, charts, and fallback."""

    def test_full_benchmark_report_generation(self, tmp_path, sample_summary_df):
        """Generate benchmark report with valid data and verify all sections."""
        out_file = tmp_path / "custom_benchmark_report.html"
        result_path = ReportGenerator.build_benchmark_report(sample_summary_df, out_file)

        assert result_path == out_file
        assert out_file.exists()

        content = out_file.read_text(encoding="utf-8")

        # HTML5 structure & charset
        assert "<!DOCTYPE html>" in content
        assert '<meta charset="UTF-8">' in content
        assert 'data-report-version="2.0"' in content

        # Required sections
        assert "Cryptography Testing Lab — Benchmark Performance Report" in content
        assert "Executive Summary" in content
        assert "Performance Benchmarks" in content
        assert "Experimental Methodology" in content

        # Metadata
        assert "Python Version" in content
        assert "Platform / OS" in content
        assert "Generated UTC" in content

        # Methodology parameters
        assert "5 unmeasured warmup iterations" in content
        assert "30 measured iterations" in content
        assert "Tukey Outlier Fences" in content
        assert "1,048,576 bytes" in content

        # Table data
        assert "AES-128-CBC" in content
        assert "AES-256-CBC" in content
        assert "AES-128-ECB" in content

        # Embedded Base64 Matplotlib Charts
        assert "data:image/png;base64," in content
        assert "AES Performance by Key Size" in content
        assert "AES Performance by Mode" in content
        assert "AES Throughput Scaling" in content

    def test_multi_payload_size_filtering_for_charts(self, tmp_path, multi_size_summary_df):
        """When multi-size benchmark data is provided, charts filter correctly."""
        out_file = tmp_path / "multi_size_report.html"
        result_path = ReportGenerator.build_benchmark_report(multi_size_summary_df, out_file)

        assert result_path.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "AES Performance by Key Size" in content
        assert "AES Performance by Mode" in content
        assert "AES Throughput Scaling" in content

    def test_empty_collector_fallback(self, tmp_path):
        """Empty MetricCollector produces a graceful fallback without crashing."""
        empty_collector = MetricCollector()
        out_file = tmp_path / "empty_report.html"

        result_path = ReportGenerator.build_benchmark_report(empty_collector, out_file)
        assert result_path.exists()

        content = out_file.read_text(encoding="utf-8")
        assert "No benchmark data recorded for this session." in content
        assert "No benchmark metrics recorded." in content
        # No chart images when data is empty
        assert '<div class="chart-card">' not in content

    def test_none_collector_fallback(self, tmp_path):
        """Passing None as collector falls back gracefully."""
        out_file = tmp_path / "none_report.html"
        result_path = ReportGenerator.build_benchmark_report(None, out_file)
        assert result_path.exists()

        content = out_file.read_text(encoding="utf-8")
        assert "No benchmark data recorded for this session." in content

    def test_default_output_path_generation(self, monkeypatch, tmp_path, sample_summary_df):
        """When output_path is None, report is saved to results/reports/cryptography_report_*.html."""
        fake_reports_dir = tmp_path / "results" / "reports"
        monkeypatch.setattr(ReportGenerator, "DEFAULT_REPORT_DIR", fake_reports_dir)

        result_path = ReportGenerator.build_benchmark_report(sample_summary_df, output_path=None)

        assert result_path.exists()
        assert result_path.parent == fake_reports_dir
        assert result_path.name.startswith("cryptography_report_")
        assert result_path.name.endswith(".html")


# ===========================================================================
# C. Security Report Tests
# ===========================================================================


class TestSecurityReport:
    """Verify HTML security report generation, diffusion metrics, and ECB visuals."""

    def test_full_security_report_generation(self, tmp_path, sample_security_results):
        """Generate security report with avalanche, key sensitivity, and ECB comparisons."""
        out_file = tmp_path / "custom_security_report.html"
        result_path = ReportGenerator.build_security_report(sample_security_results, out_file)

        assert result_path == out_file
        assert out_file.exists()

        content = out_file.read_text(encoding="utf-8")

        # HTML5 structure & charset
        assert "<!DOCTYPE html>" in content
        assert '<meta charset="UTF-8">' in content
        assert 'data-report-version="2.0"' in content

        # Required sections
        assert "Cryptography Testing Lab — Security &amp; Cryptanalysis Report" in content or "Cryptography Testing Lab — Security & Cryptanalysis Report" in content
        assert "Executive Summary" in content
        assert "Security &amp; Cryptanalysis" in content or "Security & Cryptanalysis" in content
        assert "Experimental Methodology" in content

        # Avalanche & Key Sensitivity Metrics
        assert "49.85%" in content
        assert "50.12%" in content
        assert "Plaintext Avalanche Effect" in content
        assert "Key Sensitivity" in content

        # ECB vs CBC Structural Comparison Table
        assert "ECB vs. CBC Structural Pattern Comparison" in content
        assert "BMP Header Size" in content
        assert "54 bytes" in content
        assert "12288 bytes" in content
        assert "12304 bytes" in content
        assert "Observed" in content
        assert "Masked" in content

        # Confidentiality disclaimer
        assert "AES-CBC provides confidentiality only" in content

    def test_empty_security_results_fallback(self, tmp_path):
        """Empty security dictionary generates a graceful fallback notice."""
        out_file = tmp_path / "empty_sec_report.html"
        result_path = ReportGenerator.build_security_report({}, out_file)

        assert result_path.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "No security evaluation recorded for this session." in content
        assert "No security data recorded." in content

    def test_none_security_results_fallback(self, tmp_path):
        """Passing None generates a graceful fallback notice."""
        out_file = tmp_path / "none_sec_report.html"
        result_path = ReportGenerator.build_security_report(None, out_file)

        assert result_path.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "No security evaluation recorded for this session." in content

    def test_secret_privacy_contract(self, tmp_path):
        """Raw encryption keys, hex keys, and plaintext payloads must NEVER appear in HTML."""
        secret_key_hex = "00112233445566778899aabbccddeeff"
        secret_plaintext = "CONFIDENTIAL_PAYLOAD_TOP_SECRET"

        security_data = {
            "AES-128-CBC": {
                "avalanche_effect": 49.9,
                "key_sensitivity": 50.1,
                "raw_key_secret": secret_key_hex,
                "plaintext_secret": secret_plaintext,
            }
        }

        out_file = tmp_path / "privacy_test_report.html"
        ReportGenerator.build_security_report(security_data, out_file)

        content = out_file.read_text(encoding="utf-8")
        assert secret_key_hex not in content
        assert secret_plaintext not in content


# ===========================================================================
# D. XSS & Injection Safety Tests
# ===========================================================================


class TestHtmlEscaping:
    """Verify strict HTML entity escaping on dynamic data and hostile values."""

    def test_escape_helper_behavior(self):
        """Centralized _escape helper escapes <, >, &, \", and ' correctly."""
        assert _escape(None) == ""
        assert _escape(123) == "123"
        assert _escape("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert _escape('"><b onclick="x">test</b>') == "&quot;&gt;&lt;b onclick=&quot;x&quot;&gt;test&lt;/b&gt;"

    def test_hostile_algorithm_and_mode_escaping_in_benchmark(self, tmp_path):
        """Hostile script tags in benchmark metadata/rows are strictly escaped."""
        hostile_df = pd.DataFrame([
            {
                "algorithm": "<script>alert('xss-algo')</script>",
                "key_size": 128,
                "mode": '<b onmouseover="alert(\'xss-mode\')">CBC</b>',
                "data_size_bytes": 1024,
                "count": 30,
                "mean_time_ms": 1.0,
                "median_time_ms": 1.0,
                "std_dev_time_ms": 0.1,
                "min_time_ms": 0.9,
                "max_time_ms": 1.1,
                "q1_ms": 0.95,
                "q3_ms": 1.05,
                "iqr_ms": 0.1,
                "outlier_count": 0,
                "throughput_mb_s": 1.0,
                "memory_delta_mb": 0.0,
            }
        ])

        out_file = tmp_path / "xss_bench_report.html"
        ReportGenerator.build_benchmark_report(hostile_df, out_file)

        content = out_file.read_text(encoding="utf-8")

        # Must contain escaped version
        assert "&lt;script&gt;alert(&#x27;xss-algo&#x27;)&lt;/script&gt;" in content
        # Must NOT contain raw executable tag
        assert "<script>alert('xss-algo')</script>" not in content
        assert '<b onmouseover="alert(\'xss-mode\')">' not in content

    def test_hostile_config_name_escaping_in_security(self, tmp_path):
        """Hostile config names in security reports are strictly escaped."""
        hostile_sec = {
            '<img src=x onerror=alert("sec-xss")>': {
                "avalanche_effect": 50.0,
                "key_sensitivity": 50.0,
            }
        }

        out_file = tmp_path / "xss_sec_report.html"
        ReportGenerator.build_security_report(hostile_sec, out_file)

        content = out_file.read_text(encoding="utf-8")
        assert "&lt;img src=x onerror=alert(&quot;sec-xss&quot;)&gt;" in content
        assert '<img src=x onerror=alert("sec-xss")>' not in content


# ===========================================================================
# E. Browser Auto-Open Tests
# ===========================================================================


class TestOpenInBrowser:
    """Verify cross-platform URI conversion, launch dispatch, and error fallbacks."""

    def test_nonexistent_file_returns_false(self, tmp_path):
        """Nonexistent report path returns False without attempting to launch."""
        missing = tmp_path / "does_not_exist.html"
        assert not ReportGenerator.open_in_browser(missing)

    def test_directory_path_returns_false(self, tmp_path):
        """Passing a directory instead of a file returns False."""
        assert not ReportGenerator.open_in_browser(tmp_path)

    def test_successful_browser_launch(self, tmp_path):
        """Valid file triggers webbrowser.open with proper file:// URI."""
        report = tmp_path / "report.html"
        report.write_text("<html></html>", encoding="utf-8")

        with patch("webbrowser.open", return_value=True) as mock_open:
            result = ReportGenerator.open_in_browser(report)

            assert result is True
            mock_open.assert_called_once()
            called_uri = mock_open.call_args[0][0]
            assert called_uri.startswith("file://")
            assert "report.html" in called_uri

    def test_browser_returns_false(self, tmp_path):
        """When webbrowser.open returns False, open_in_browser returns False."""
        report = tmp_path / "report.html"
        report.write_text("<html></html>", encoding="utf-8")

        with patch("webbrowser.open", return_value=False):
            assert ReportGenerator.open_in_browser(report) is False

    def test_browser_exception_handled_gracefully(self, tmp_path):
        """When webbrowser.open raises an exception, open_in_browser returns False without crashing."""
        report = tmp_path / "report.html"
        report.write_text("<html></html>", encoding="utf-8")

        with patch("webbrowser.open", side_effect=OSError("Browser launcher failed")):
            assert ReportGenerator.open_in_browser(report) is False


# ===========================================================================
# F. Real V1 Integration Tests
# ===========================================================================


class TestV1Integration:
    """Verify ReportGenerator directly with real V1 MetricCollector and SecurityService."""

    def test_real_metric_collector_integration(self, tmp_path):
        """Real MetricCollector populated with raw observations generates complete report."""
        collector = MetricCollector()

        # Add 128-bit CBC metric
        collector.add_metric({
            "algorithm": "AES",
            "key_size": 128,
            "mode": "CBC",
            "data_size_bytes": 1048576,
            "raw_times_ms": [10.0, 10.5, 9.8, 10.2, 10.1, 10.3, 9.9, 10.4] * 4,  # 32 observations
        })

        # Add 256-bit CBC metric
        collector.add_metric({
            "algorithm": "AES",
            "key_size": 256,
            "mode": "CBC",
            "data_size_bytes": 1048576,
            "raw_times_ms": [15.0, 15.5, 14.8, 15.2, 15.1, 15.3, 14.9, 15.4] * 4,
        })

        out_file = tmp_path / "v1_collector_report.html"
        result_path = ReportGenerator.build_benchmark_report(collector, out_file)

        assert result_path.exists()
        content = out_file.read_text(encoding="utf-8")

        assert "AES-128-CBC" in content
        assert "AES-256-CBC" in content
        assert "data:image/png;base64," in content

    def test_real_security_evaluator_integration(self, tmp_path):
        """Real SecurityService execution results generate complete security report."""
        service = SecurityService()
        configs = [
            {"algorithm": "AES", "key_size": 128, "mode": "CBC"},
            {"algorithm": "AES", "key_size": 128, "mode": "ECB"},
        ]

        # Construct minimal valid 24-bpp BMP
        width, height = 4, 4
        row_bytes = width * 3
        row_stride = ((row_bytes + 3) // 4) * 4
        pixel_size = row_stride * height
        file_size = 54 + pixel_size

        # BMP 14-byte file header + 40-byte DIB header
        header = bytearray(54)
        header[0:2] = b"BM"
        header[2:6] = file_size.to_bytes(4, "little")
        header[10:14] = (54).to_bytes(4, "little")
        header[14:18] = (40).to_bytes(4, "little")
        header[18:22] = width.to_bytes(4, "little", signed=True)
        header[22:26] = height.to_bytes(4, "little", signed=True)
        header[26:28] = (1).to_bytes(2, "little")  # planes
        header[28:30] = (24).to_bytes(2, "little")  # bpp
        header[30:34] = (0).to_bytes(4, "little")  # compression
        header[34:38] = pixel_size.to_bytes(4, "little")

        bmp_bytes = bytes(header) + b"\x55" * pixel_size

        p1 = b"A" * 16
        p2 = b"B" * 16  # Different
        # Ensure exactly 1-bit difference for avalanche
        p2 = bytearray(p1)
        p2[0] ^= 0x01
        p2 = bytes(p2)

        k1 = b"\x01" * 16
        k2 = bytearray(k1)
        k2[0] ^= 0x01
        k2 = bytes(k2)

        iv = b"\x02" * 16

        results = service.run_security_suite(
            configs=configs,
            plaintext1=p1,
            plaintext2=p2,
            key1=k1,
            key2=k2,
            image_bytes=bmp_bytes,
            iv=iv,
        )

        out_file = tmp_path / "v1_sec_report.html"
        result_path = ReportGenerator.build_security_report(results, out_file)

        assert result_path.exists()
        content = out_file.read_text(encoding="utf-8")

        assert "AES-128-CBC" in content
        assert "AES-128-ECB" in content
        assert "Key Sensitivity" in content
        assert "ECB vs. CBC Structural Pattern Comparison" in content

    def test_security_output_path_generation(self, monkeypatch, tmp_path, sample_security_results):
        """Security report generates to default timestamped path when output_path is None."""
        fake_reports_dir = tmp_path / "results" / "reports"
        monkeypatch.setattr(ReportGenerator, "DEFAULT_REPORT_DIR", fake_reports_dir)

        result_path = ReportGenerator.build_security_report(sample_security_results, output_path=None)

        assert result_path.exists()
        assert result_path.parent == fake_reports_dir
        assert result_path.name.startswith("cryptography_report_")
        assert result_path.name.endswith(".html")

        # Custom path works
        custom_path = tmp_path / "custom_sec.html"
        result_path2 = ReportGenerator.build_security_report(sample_security_results, output_path=custom_path)
        assert result_path2 == custom_path
        assert custom_path.exists()

    def test_utf8_encoding_in_security_report(self, tmp_path):
        """Security report correctly handles and writes UTF-8 non-ASCII characters."""
        utf8_results = {
            "AES-256-Ωμ": {
                "avalanche_effect": 50.0,
                "key_sensitivity": 50.0,
            }
        }
        out_file = tmp_path / "utf8_sec_report.html"
        ReportGenerator.build_security_report(utf8_results, out_file)

        content = out_file.read_text(encoding="utf-8")
        assert "AES-256-Ωμ" in content

    def test_progress_width_escaping(self, tmp_path):
        """Progress width values are properly escaped (even though derived from floats)."""
        width_results = {
            "TEST-128-CBC": {
                "avalanche_effect": 45.67,
                "key_sensitivity": 55.43,
            }
        }
        out_file = tmp_path / "width_escape_report.html"
        ReportGenerator.build_security_report(width_results, out_file)

        content = out_file.read_text(encoding="utf-8")
        # 45.7% and 55.4% (capped at 100) are the widths
        assert 'style="width: 45.7%;"' in content
        assert 'style="width: 55.4%;"' in content

# ===========================================================================
# G. Timestamp Helper Tests
# ===========================================================================


class TestTimestampHelpers:
    """Verify internal timestamp formatting behavior."""

    def test_iso_timestamp_formatting(self):
        """_iso_timestamp formats correctly with trailing Z."""
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        assert _iso_timestamp(dt) == "2024-01-15T14:30:45Z"

    def test_file_timestamp_formatting(self):
        """_file_timestamp formats correctly for filenames."""
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=timezone.utc)
        assert _file_timestamp(dt) == "20240115_143045"


# ===========================================================================
# H. Backend Initialization Tests
# ===========================================================================


class TestBackendInitialization:
    """Verify ReportGenerator module safely initializes the Matplotlib backend."""

    def test_report_generator_forces_agg_backend(self):
        """Verify ReportGenerator module forces Matplotlib to use the headless Agg backend on import."""
        import subprocess
        import sys
        from pathlib import Path
        
        root_dir = str(Path(__file__).parent.parent.parent.absolute())
        
        # Run in a clean subprocess to verify the module's own import order contract
        # without interference from pytest or other test file imports.
        script = (
            "import sys\n"
            f"sys.path.insert(0, r'{root_dir}')\n"
            "from src.cli_v2.report_generator import ReportGenerator\n"
            "import matplotlib\n"
            "print(matplotlib.get_backend().lower())\n"
        )
        
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        if result.returncode != 0:
            print("STDERR:", result.stderr)
        assert result.returncode == 0, f"Subprocess failed: {result.stderr}"
        assert result.stdout.strip() == "agg"
