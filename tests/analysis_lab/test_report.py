"""
Unit and integration tests for FileAnalysisReportGenerator in src.analysis_lab.report.

Verifies:
1. Standalone HTML document structure (HTML5, offline CSS, zero external CDN scripts/styles).
2. Base64 static Matplotlib chart embedding and Level A fallback handling.
3. Comparative matrix table and detailed statistical breakdown tables.
4. Zero-byte file representation (N/A throughput, 16-byte padding, boundary notice).
5. Partial-run and full-failure resilience (error messages, exclusion from fastest ranking).
6. Skip decryption mode representation.
7. Security diffusion profile (Avalanche Effect, Key Sensitivity, cryptographic disclaimer, BMP notice).
8. Privacy and path masking rules (relative path default, absolute masked, SHA-256 suppression).
9. Strict XSS sanitization across all user-controlled text strings.
10. Terminology discipline: Zero instances of "Winner", "Best Configuration", or "Best".
11. Multi-tier failure handling: Level A graceful fallback and Level B ReportAssemblyError.
12. Filesystem report persistence (default and custom paths).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import matplotlib.pyplot as plt
import pytest

from src.analysis_lab.models import (
    CiphertextMetrics,
    ConfigurationResult,
    FileAnalysisResult,
    FileMetadata,
    PerformanceMetrics,
    SecurityMetrics,
)
from src.analysis_lab.report import (
    CHART_FALLBACK_NOTICE,
    FileAnalysisReportGenerator,
    ReportAssemblyError,
)
from src.analyzers.graph_generator import GraphGenerator
from src.utils.file_handler import FileHandler


def _make_perf_metrics(mean_ms: float = 0.5, tput: float | None = 100.0) -> PerformanceMetrics:
    return PerformanceMetrics(
        sample_count=30,
        mean_ms=mean_ms,
        median_ms=mean_ms,
        std_dev_ms=0.02,
        min_ms=mean_ms - 0.05,
        max_ms=mean_ms + 0.05,
        q1_ms=mean_ms - 0.01,
        q3_ms=mean_ms + 0.01,
        iqr_ms=0.02,
        outlier_count=1,
        throughput_mb_s=tput,
        raw_times_ms=tuple([mean_ms] * 30),
    )


def _make_sample_result(
    file_name: str = "benchmark.bin",
    display_path: str = "data/benchmark.bin",
    absolute_path: str = "C:/Users/Alice/Projects/data/benchmark.bin",
    file_size_bytes: int = 1024,
    sha256_hash: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    skip_decryption: bool = False,
    security_enabled: bool = False,
    fail_config: str | None = None,
    all_failed: bool = False,
    is_bmp: bool = False,
    ecb_weakness_analyzed: bool = False,
) -> FileAnalysisResult:
    configs = []
    specs = [
        ("AES", 128, "CBC", 0.40, 0.38),
        ("AES", 192, "CBC", 0.50, 0.48),
        ("AES", 256, "CBC", 0.60, 0.58),
        ("AES", 128, "ECB", 0.35, 0.33),
        ("AES", 192, "ECB", 0.45, 0.43),
        ("AES", 256, "ECB", 0.55, 0.53),
    ]

    is_zero = (file_size_bytes == 0)
    pad_bytes = 16 - (file_size_bytes % 16) if not is_zero else 16
    c_bytes = file_size_bytes + pad_bytes
    exp_pct = ((pad_bytes / file_size_bytes) * 100.0) if not is_zero else None

    c_metrics = CiphertextMetrics(
        plaintext_size_bytes=file_size_bytes,
        ciphertext_size_bytes=c_bytes,
        padding_overhead_bytes=pad_bytes,
        expansion_percentage=exp_pct,
    )

    for alg, ks, mode, enc_lat, dec_lat in specs:
        cfg_name = f"{alg}-{ks}-{mode}"
        if all_failed or (fail_config and cfg_name == fail_config):
            configs.append(
                ConfigurationResult(
                    algorithm=alg,
                    key_size=ks,
                    mode=mode,
                    status="FAILED",
                    error_message=f"Simulated execution error for {cfg_name}",
                )
            )
        else:
            enc_tput = None if is_zero else (file_size_bytes / 1048576.0) / (enc_lat / 1000.0)
            dec_tput = None if is_zero else (file_size_bytes / 1048576.0) / (dec_lat / 1000.0)

            enc_m = _make_perf_metrics(enc_lat, enc_tput)
            dec_m = _make_perf_metrics(dec_lat, dec_tput) if not skip_decryption else None

            sec_m = None
            if security_enabled:
                sec_m = SecurityMetrics(
                    status="SUCCESS",
                    avalanche_effect_pct=50.12,
                    key_sensitivity_pct=49.85,
                    notes="Evaluated 1-bit mutations.",
                    ecb_weakness_analyzed=ecb_weakness_analyzed,
                )

            configs.append(
                ConfigurationResult(
                    algorithm=alg,
                    key_size=ks,
                    mode=mode,
                    status="SUCCESS",
                    encryption_metrics=enc_m,
                    decryption_metrics=dec_m,
                    ciphertext_metrics=c_metrics,
                    security_metrics=sec_m,
                )
            )

    meta = FileMetadata(
        file_name=file_name,
        display_path=display_path,
        absolute_path=absolute_path,
        file_size_bytes=file_size_bytes,
        sha256_hash=sha256_hash,
        is_bmp=is_bmp,
    )

    return FileAnalysisResult(
        file_metadata=meta,
        configurations=tuple(configs),
        timestamp_utc="2026-09-27T22:00:00Z",
        skip_decryption=skip_decryption,
        security_enabled=security_enabled,
    )


class TestFileAnalysisReportGenerator:
    """Test suite covering FileAnalysisReportGenerator contracts."""

    def test_standalone_html_structure_and_offline_integrity(self) -> None:
        """Verify report compiles to valid standalone HTML5 with embedded CSS and zero external CDNs."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert html_doc.startswith("<!DOCTYPE html>")
        assert "<html lang=\"en\">" in html_doc
        assert "<meta charset=\"UTF-8\">" in html_doc
        assert "<meta name=\"viewport\"" in html_doc
        assert "<style>" in html_doc
        assert "</style>" in html_doc
        assert "</html>" in html_doc

        # Verify offline integrity: zero external CDN scripts or stylesheet links
        assert "<script src=" not in html_doc.lower()
        assert "<link rel=\"stylesheet\"" not in html_doc.lower()
        assert "http://" not in html_doc
        assert "https://" not in html_doc

        # Verify all 8 core report sections are present
        assert "File-Specific Encryption Analysis Report" in html_doc
        assert "Executive Summary" in html_doc
        assert "Comparative Configuration Matrix" in html_doc
        assert "Detailed Performance Analysis" in html_doc
        assert "Ciphertext &amp; PKCS#7 Padding Profile" in html_doc
        assert "Security &amp; Diffusion Profile" in html_doc
        assert "Experimental Methodology" in html_doc
        assert "Limitations &amp; Scientific Caveats" in html_doc

    def test_base64_charts_embedded_in_normal_run(self) -> None:
        """Verify Base64 static Matplotlib figures are embedded inline."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        # Both Key Size and Mode charts should be embedded
        assert 'src="data:image/png;base64,' in html_doc
        assert "Key Size Comparison (AES 128 vs 192 vs 256)" in html_doc
        assert "Cipher Mode Comparison (CBC vs ECB)" in html_doc

    def test_level_a_chart_fallback_handling(self) -> None:
        """Verify Level A: If chart generation fails, the report compiles with the fallback notice."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)

        with patch.object(
            GraphGenerator,
            "generate_key_size_comparison",
            side_effect=RuntimeError("Matplotlib OOM error"),
        ):
            html_doc = gen.generate_html()

        # Report must still compile cleanly
        assert "<!DOCTYPE html>" in html_doc
        assert "Comparative Configuration Matrix" in html_doc
        # Must contain the frozen Level A chart fallback notice
        assert CHART_FALLBACK_NOTICE in html_doc

    def test_comparative_matrix_and_detailed_statistics(self) -> None:
        """Verify comparative matrix and detailed statistical distributions render all 6 configurations."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        for alg, ks, mode in [
            ("AES", 128, "CBC"),
            ("AES", 192, "CBC"),
            ("AES", 256, "CBC"),
            ("AES", 128, "ECB"),
            ("AES", 192, "ECB"),
            ("AES", 256, "ECB"),
        ]:
            cfg_name = f"{alg}-{ks}-{mode}"
            assert cfg_name in html_doc

        # Statistical headers check
        assert "Mean" in html_doc
        assert "Median" in html_doc
        assert "Std Dev" in html_doc
        assert "Min" in html_doc
        assert "Max" in html_doc
        assert "Q1" in html_doc
        assert "Q3" in html_doc
        assert "IQR" in html_doc
        assert "Outliers" in html_doc
        assert "Throughput" in html_doc

    def test_zero_byte_file_contract(self) -> None:
        """Verify zero-byte payload produces 16-byte padding and throughput reported strictly as N/A."""
        res = _make_sample_result(file_size_bytes=0)
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "Zero-Byte File Notice" in html_doc
        assert "Throughput (MB/s) is mathematically undefined (N/A)" in html_doc
        assert "0 B" in html_doc
        # Check that throughput column displays N/A
        assert ">N/A</td>" in html_doc

    def test_partial_failure_handling_and_fastest_ranking(self) -> None:
        """Verify failed configuration is isolated, reported in matrix, and excluded from ranking."""
        res = _make_sample_result(fail_config="AES-256-CBC")
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "5 / 6" in html_doc
        assert "1 Failed" in html_doc
        assert "Simulated execution error for AES-256-CBC" in html_doc
        # Fastest encryption should still be identified (AES-128-ECB at 0.350 ms)
        assert "AES-128-ECB" in html_doc
        assert "0.350 ms" in html_doc

    def test_fastest_observed_displays_configuration_and_underlying_latency(self) -> None:
        """Verify Executive Summary displays fastest configuration name AND its underlying sample mean latency."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        # In _make_sample_result, AES-128-ECB is fastest encryption (0.350 ms) and decryption (0.330 ms)
        assert "Fastest Observed Encryption" in html_doc
        assert "AES-128-ECB" in html_doc
        assert "0.350 ms" in html_doc
        assert "Fastest observed configuration in this experiment (lowest sample mean latency)" in html_doc

        assert "Fastest Observed Decryption" in html_doc
        assert "0.330 ms" in html_doc

    def test_fastest_observed_partial_failure_selects_and_displays_latency(self) -> None:
        """Verify fastest ranking correctly selects remaining configuration and displays its latency."""
        # Fail the fastest one (AES-128-ECB), so AES-128-CBC (0.400 ms) becomes fastest
        res = _make_sample_result(fail_config="AES-128-ECB")
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "Fastest Observed Encryption" in html_doc
        assert "AES-128-CBC" in html_doc
        assert "0.400 ms" in html_doc
        assert "Fastest observed configuration in this experiment (lowest sample mean latency)" in html_doc

    def test_all_failed_handling(self) -> None:
        """Verify report compiles cleanly even when all configurations fail."""
        res = _make_sample_result(all_failed=True)
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "0 / 6" in html_doc
        assert "6 Failed" in html_doc
        assert "None" in html_doc
        assert "All configurations failed" in html_doc
        assert CHART_FALLBACK_NOTICE in html_doc

    def test_skip_decryption_mode(self) -> None:
        """Verify skip-decryption mode is cleanly rendered across cards and tables."""
        res = _make_sample_result(skip_decryption=True)
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "N/A (Skipped)" in html_doc
        assert "Decryption Benchmarking Skipped" in html_doc
        assert "Decryption benchmarking was skipped" in html_doc

    def test_security_diffusion_disabled_notice(self) -> None:
        """Verify informative notice is rendered when security analysis is disabled."""
        res = _make_sample_result(security_enabled=False)
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "Security Analysis Not Enabled" in html_doc
        assert "--security" in html_doc

    def test_security_diffusion_enabled_and_disclaimer(self) -> None:
        """Verify Avalanche Effect, Key Sensitivity, and cryptographic disclaimer are rendered."""
        res = _make_sample_result(security_enabled=True)
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "Plaintext Avalanche Effect (1-bit mutation)" in html_doc
        assert "Key Sensitivity (1-bit key mutation)" in html_doc
        assert "50.12%" in html_doc
        assert "49.85%" in html_doc
        # Check cryptographic disclaimer
        assert "Cryptographic Notice &amp; Boundary Limitations" in html_doc
        assert "does NOT constitute a formal mathematical security proof" in html_doc
        assert "AES-CBC provides confidentiality only" in html_doc

    def test_security_bmp_ecb_weakness_analyzed(self) -> None:
        """Verify BMP structural pattern analysis notice is rendered when ecb_weakness_analyzed=True."""
        res = _make_sample_result(security_enabled=True, is_bmp=True, ecb_weakness_analyzed=True)
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "ECB Visual Redundancy Analysis" in html_doc
        assert "randomly generated 16-byte initialization vector" in html_doc

    def test_privacy_default_masks_absolute_path(self) -> None:
        """Verify absolute path is masked as [OMITTED FOR PRIVACY] by default."""
        secret_path = "C:/Users/SecretUser/PrivateDir/target.bin"
        res = _make_sample_result(absolute_path=secret_path)
        gen = FileAnalysisReportGenerator(res, include_absolute_path=False)
        html_doc = gen.generate_html()

        assert "[OMITTED FOR PRIVACY]" in html_doc
        assert secret_path not in html_doc

    def test_privacy_include_absolute_path_flag(self) -> None:
        """Verify absolute path is rendered when include_absolute_path=True."""
        custom_path = "C:/Users/CustomUser/data/target.bin"
        res = _make_sample_result(absolute_path=custom_path)
        gen = FileAnalysisReportGenerator(res, include_absolute_path=True)
        html_doc = gen.generate_html()

        assert custom_path in html_doc

    def test_privacy_default_includes_sha256(self) -> None:
        """Verify SHA-256 fingerprint is included by default."""
        sha = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"
        res = _make_sample_result(sha256_hash=sha)
        gen = FileAnalysisReportGenerator(res, no_hash=False)
        html_doc = gen.generate_html()

        assert sha in html_doc

    def test_privacy_no_hash_flag_suppresses_sha256(self) -> None:
        """Verify SHA-256 fingerprint is suppressed when no_hash=True."""
        sha = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"
        res = _make_sample_result(sha256_hash=sha)
        gen = FileAnalysisReportGenerator(res, no_hash=True)
        html_doc = gen.generate_html()

        assert sha not in html_doc
        assert "[OMITTED FOR PRIVACY]" in html_doc

    def test_strict_xss_escaping(self) -> None:
        """Verify all user-controlled text strings are sanitized via html.escape(quote=True)."""
        xss_filename = "<script>alert('xss')</script>"
        xss_path = "<img src=x onerror=alert(1)>"
        res = _make_sample_result(file_name=xss_filename, display_path=xss_path)
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "<script>alert('xss')</script>" not in html_doc
        assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in html_doc
        assert "<img src=x onerror=alert(1)>" not in html_doc
        assert "&lt;img src=x onerror=alert(1)&gt;" in html_doc

    def test_secret_hygiene_no_key_or_payload_leakage(self) -> None:
        """Verify no encryption keys, IVs, or raw bytes appear in HTML."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        assert "AES Key:" not in html_doc
        assert "Ciphertext Bytes:" not in html_doc
        assert "IV Bytes:" not in html_doc

    def test_terminology_discipline_strictly_enforced(self) -> None:
        """Verify zero occurrences of 'Winner' or 'Best' and check strict fastest phrasing."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)
        html_doc = gen.generate_html()

        lower_doc = html_doc.lower()
        assert "winner" not in lower_doc
        assert "best configuration" not in lower_doc
        assert "best" not in lower_doc

        # Verify exact required fastest phrasing
        expected_phrase = (
            "Fastest observed configuration in this experiment (lowest sample mean latency)"
        )
        assert expected_phrase in html_doc

    def test_level_b_assembly_failure_raises_report_assembly_error(self) -> None:
        """Verify Level B: Unexpected assembly failure raises ReportAssemblyError."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)

        with patch.object(
            gen,
            "_render_header",
            side_effect=RuntimeError("Template formatting error"),
        ):
            with pytest.raises(ReportAssemblyError) as exc_info:
                gen.generate_html()

        assert "Failed to assemble HTML report" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, RuntimeError)

    def test_save_report_custom_path(self, tmp_path: Path) -> None:
        """Verify save_report persists HTML to a custom specified path."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)
        out_file = tmp_path / "custom_report.html"

        saved_path = gen.save_report(out_file)
        assert saved_path == out_file
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert content.startswith("<!DOCTYPE html>")

    def test_save_report_default_path(self, tmp_path: Path) -> None:
        """Verify save_report persists to default directory if path not specified."""
        res = _make_sample_result()
        gen = FileAnalysisReportGenerator(res)

        mock_handler = MagicMock(spec=FileHandler)
        gen.file_handler = mock_handler

        saved_path = gen.save_report(None)
        assert saved_path.parent == FileAnalysisReportGenerator.DEFAULT_REPORT_DIR
        assert "file_analysis_benchmark_bin_" in saved_path.name
        assert saved_path.suffix == ".html"
        assert mock_handler.write_text.called

    def test_figure_to_base64_closes_figure(self) -> None:
        """Verify figure_to_base64 produces valid URI and closes figure to prevent memory leaks."""
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4])
        fignum = fig.number

        uri = FileAnalysisReportGenerator.figure_to_base64(fig)
        assert uri.startswith("data:image/png;base64,")
        assert len(uri) > 100
        # Check that matplotlib closed the figure
        assert not plt.fignum_exists(fignum)
