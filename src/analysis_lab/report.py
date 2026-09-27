"""
Standalone offline HTML report compiler for File-Specific Encryption Analysis Lab.

Generates self-contained, offline HTML experiment reports containing embedded Base64
static Matplotlib charts, comparative performance matrices, detailed statistical
distributions, PKCS#7 padding profiles, and security diffusion metrics.

Strictly adheres to:
- Offline self-containment (zero CDN or external network dependencies).
- Privacy and path masking (relative path default, absolute path masked, optional SHA-256 suppression).
- Secret hygiene (zero keys, IVs, or raw payload bytes in output).
- XSS escaping across all dynamic fields via html.escape(quote=True).
- Terminology restrictions (zero instances of "Winner" or "Best Configuration").
- Multi-tier failure handling (Level A chart fallback, Level B assembly error).
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import html
import io
from pathlib import Path
import platform
import re
import sys
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.analysis_lab.models import (
    ConfigurationResult,
    FileAnalysisResult,
    PerformanceMetrics,
    SecurityMetrics,
)
from src.analyzers.graph_generator import GraphGenerator
from src.analyzers.metric_collector import MetricCollector
from src.utils.file_handler import FileHandler


class ReportAssemblyError(RuntimeError):
    """Raised when HTML report assembly encounters an unrecoverable failure (Level B)."""
    pass


CHART_FALLBACK_NOTICE = (
    "[Notice: Performance chart rendering was unavailable for this run; "
    "refer to tabular metrics below]"
)


def _escape(value: Any) -> str:
    """Sanitize any runtime value for HTML insertion using html.escape(quote=True)."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _format_bytes(byte_count: int) -> str:
    """Format byte counts into human-readable strings."""
    if byte_count < 1024:
        return f"{byte_count:,} B"
    elif byte_count < 1024 * 1024:
        kib = byte_count / 1024.0
        return f"{byte_count:,} B ({kib:.2f} KiB)"
    else:
        mib = byte_count / (1024.0 * 1024.0)
        return f"{byte_count:,} B ({mib:.2f} MiB)"


def _format_ms(val: float | None) -> str:
    """Format millisecond latency with 3 decimal places."""
    if val is None:
        return "N/A"
    return f"{val:.3f} ms"


def _format_mb_s(val: float | None) -> str:
    """Format throughput in binary MB/s with 2 decimal places."""
    if val is None:
        return "N/A"
    return f"{val:.2f} MB/s"


def _format_pct(val: float | None) -> str:
    """Format percentage with 2 decimal places."""
    if val is None:
        return "N/A"
    return f"{val:.2f}%"


_REPORT_CSS = """
:root {
    --bg-primary: #0f172a;
    --bg-surface: #1e293b;
    --bg-card: #243049;
    --border-color: #334155;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent-blue: #3b82f6;
    --accent-cyan: #06b6d4;
    --accent-green: #10b981;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    padding: 2rem 1rem;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
}

header {
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 2rem;
}

.header-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

h1 {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.02em;
}

.subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-top: 0.25rem;
}

.badges {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.badge {
    display: inline-flex;
    align-items: center;
    padding: 0.35rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.badge-blue {
    background: rgba(59, 130, 246, 0.15);
    color: var(--accent-blue);
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-green {
    background: rgba(16, 185, 129, 0.15);
    color: var(--accent-green);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-amber {
    background: rgba(245, 158, 11, 0.15);
    color: var(--accent-amber);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-red {
    background: rgba(239, 68, 68, 0.15);
    color: var(--accent-red);
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge-neutral {
    background: rgba(148, 163, 184, 0.15);
    color: var(--text-secondary);
    border: 1px solid rgba(148, 163, 184, 0.3);
}

.metadata-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.25rem;
}

.meta-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.meta-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.meta-value {
    font-size: 0.9rem;
    color: var(--text-primary);
    word-break: break-all;
}

.font-mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.text-muted {
    color: var(--text-muted);
}

.section-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.75rem;
    margin-bottom: 2rem;
}

.section-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 1.25rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.summary-cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1rem;
}

.summary-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.card-label {
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}

.card-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
    word-break: break-word;
}

.card-sub {
    font-size: 0.8rem;
    color: var(--text-muted);
    line-height: 1.4;
}

.table-wrapper {
    overflow-x: auto;
    margin-top: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 8px;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
    text-align: left;
}

th {
    background: var(--bg-card);
    color: var(--text-secondary);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-color);
    white-space: nowrap;
}

td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-primary);
}

tr:last-child td {
    border-bottom: none;
}

tr:hover td {
    background: rgba(255, 255, 255, 0.02);
}

.num {
    text-align: right;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
    gap: 1.5rem;
    margin-top: 1.5rem;
}

.chart-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
}

.chart-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 1rem;
}

.chart-img {
    width: 100%;
    height: auto;
    border-radius: 6px;
    display: block;
}

.chart-fallback {
    background: rgba(30, 41, 59, 0.7);
    border: 1px dashed var(--border-color);
    border-radius: 6px;
    padding: 2.5rem 1.5rem;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
    font-style: italic;
    min-height: 220px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.alert-box {
    background: rgba(245, 158, 11, 0.08);
    border-left: 4px solid var(--accent-amber);
    border-radius: 4px;
    padding: 1rem 1.25rem;
    margin: 1.25rem 0;
    color: var(--text-primary);
    font-size: 0.875rem;
    line-height: 1.5;
}

.alert-box strong {
    color: var(--accent-amber);
}

.info-box {
    background: rgba(59, 130, 246, 0.08);
    border-left: 4px solid var(--accent-blue);
    border-radius: 4px;
    padding: 1rem 1.25rem;
    margin: 1.25rem 0;
    color: var(--text-primary);
    font-size: 0.875rem;
    line-height: 1.5;
}

.info-box strong {
    color: var(--accent-blue);
}

.methodology-list, .limitations-list {
    list-style: none;
    display: grid;
    gap: 1rem;
}

.methodology-item, .limitations-item {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.25rem;
}

.methodology-item strong, .limitations-item strong {
    color: var(--accent-cyan);
    font-size: 0.95rem;
    display: block;
    margin-bottom: 0.35rem;
}

.methodology-item p, .limitations-item p {
    color: var(--text-secondary);
    font-size: 0.85rem;
    line-height: 1.5;
}

.security-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

.security-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
}

.security-metrics-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
}

.progress-track {
    background: var(--bg-surface);
    border-radius: 9999px;
    height: 8px;
    overflow: hidden;
    margin-top: 0.35rem;
}

.progress-fill {
    background: var(--accent-blue);
    height: 100%;
    border-radius: 9999px;
}

footer {
    text-align: center;
    color: var(--text-muted);
    font-size: 0.75rem;
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border-color);
}
"""


class FileAnalysisReportGenerator:
    """
    Compiler for standalone, offline HTML File-Specific Encryption Analysis reports.

    Converts a FileAnalysisResult into an accessible, single-file HTML report with
    embedded Base64 static Matplotlib figures and complete statistical records.
    """

    DEFAULT_REPORT_DIR = Path("results/reports")

    def __init__(
        self,
        result: FileAnalysisResult,
        include_absolute_path: bool = False,
        no_hash: bool = False,
        encryption_collector: MetricCollector | None = None,
        decryption_collector: MetricCollector | None = None,
        file_handler: type[FileHandler] = FileHandler,
    ) -> None:
        if not isinstance(result, FileAnalysisResult):
            raise TypeError(
                f"result must be an instance of FileAnalysisResult, got {type(result).__name__}"
            )

        self.result = result
        self.include_absolute_path = include_absolute_path
        self.no_hash = no_hash
        self.encryption_collector = encryption_collector
        self.decryption_collector = decryption_collector
        self.file_handler = file_handler

    @staticmethod
    def figure_to_base64(fig: Any, dpi: int = 150) -> str:
        """
        Convert a Matplotlib figure into a Base64 data URI string.

        Guarantees that the figure is closed in a finally block to prevent memory leaks.
        """
        buf = io.BytesIO()
        try:
            fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
            buf.seek(0)
            encoded = base64.b64encode(buf.getvalue()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
        finally:
            buf.close()
            try:
                plt.close(fig)
            except Exception:
                pass

    def _get_summary_dataframe(
        self,
        collector: MetricCollector | None,
        is_decryption: bool = False,
    ) -> pd.DataFrame:
        """
        Extract or construct a summary DataFrame compatible with GraphGenerator.

        Uses collector summary if provided, otherwise reconstructs the DataFrame
        from successful ConfigurationResults in FileAnalysisResult.
        """
        if collector is not None:
            df = collector.get_summary_dataframe()
            if not df.empty:
                return df

        # Construct from result configurations
        rows = []
        for cfg in self.result.configurations:
            if cfg.status != "SUCCESS":
                continue

            metrics = cfg.decryption_metrics if is_decryption else cfg.encryption_metrics
            if metrics is None:
                continue

            rows.append({
                "algorithm": cfg.algorithm,
                "key_size": cfg.key_size,
                "mode": cfg.mode,
                "data_size_bytes": self.result.file_metadata.file_size_bytes,
                "mean_time_ms": metrics.mean_ms,
                "throughput_mb_s": metrics.throughput_mb_s or 0.0,
            })

        return pd.DataFrame(rows)

    def _generate_charts(self) -> tuple[str | None, str | None]:
        """
        Generate Key Size and Mode comparison charts using GraphGenerator.

        Returns (key_size_data_uri, mode_data_uri).
        Level A Handling: If GraphGenerator or Matplotlib raises any exception,
        the failure is caught gracefully, returning None for the failed chart.
        """
        key_size_chart: str | None = None
        mode_chart: str | None = None

        try:
            enc_df = self._get_summary_dataframe(self.encryption_collector, is_decryption=False)
            if not enc_df.empty:
                try:
                    fig_ks = GraphGenerator.generate_key_size_comparison(enc_df)
                    key_size_chart = self.figure_to_base64(fig_ks)
                except Exception:
                    key_size_chart = None

                try:
                    fig_mode = GraphGenerator.generate_mode_comparison(enc_df)
                    mode_chart = self.figure_to_base64(fig_mode)
                except Exception:
                    mode_chart = None
        except Exception:
            key_size_chart = None
            mode_chart = None

        return key_size_chart, mode_chart

    def _render_header(self) -> str:
        meta = self.result.file_metadata
        filename_esc = _escape(meta.file_name)
        display_path_esc = _escape(meta.display_path)

        if self.include_absolute_path:
            abs_path_esc = _escape(meta.absolute_path or "[NOT AVAILABLE]")
            abs_path_class = "font-mono"
        else:
            abs_path_esc = "[OMITTED FOR PRIVACY]"
            abs_path_class = "text-muted"

        if self.no_hash:
            hash_esc = "[OMITTED FOR PRIVACY]"
            hash_class = "text-muted"
        else:
            hash_esc = _escape(meta.sha256_hash or "[NOT COMPUTED]")
            hash_class = "font-mono"

        size_str = _format_bytes(meta.file_size_bytes)
        ts_esc = _escape(self.result.timestamp_utc)
        py_ver_esc = _escape(f"{platform.python_version()} ({platform.python_implementation()})")
        os_info_esc = _escape(f"{platform.system()} {platform.release()} ({platform.machine()})")

        return f"""
        <header>
            <div class="header-top">
                <div>
                    <h1>File-Specific Encryption Analysis Report</h1>
                    <div class="subtitle">Empirical cryptographic evaluation of {filename_esc}</div>
                </div>
                <div class="badges">
                    <span class="badge badge-blue">Offline Capable</span>
                    <span class="badge badge-green">Standalone Report</span>
                </div>
            </div>
            <div class="metadata-grid">
                <div class="meta-item">
                    <span class="meta-label">Target Filename</span>
                    <span class="meta-value font-mono"><strong>{filename_esc}</strong></span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Display Path</span>
                    <span class="meta-value font-mono">{display_path_esc}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Absolute Path</span>
                    <span class="meta-value {abs_path_class}">{abs_path_esc}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Payload Size</span>
                    <span class="meta-value font-mono">{_escape(size_str)}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">SHA-256 Fingerprint</span>
                    <span class="meta-value {hash_class}">{hash_esc}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Execution Timestamp</span>
                    <span class="meta-value font-mono">{ts_esc}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Python Environment</span>
                    <span class="meta-value">{py_ver_esc}</span>
                </div>
                <div class="meta-item">
                    <span class="meta-label">Operating System</span>
                    <span class="meta-value">{os_info_esc}</span>
                </div>
            </div>
        </header>
        """

    def _render_executive_summary(self) -> str:
        meta = self.result.file_metadata
        size_str = _format_bytes(meta.file_size_bytes)
        total_configs = len(self.result.configurations)
        success_count = self.result.success_count
        failure_count = self.result.failure_count

        # Fastest encryption configuration and underlying mean latency
        # Terminology strictly enforces:
        # "Fastest observed configuration in this experiment (lowest sample mean latency)"
        # and displays the underlying latency value (e.g. 0.350 ms).
        # Absolutely NO "Winner" or "Best Configuration".
        enc_candidates = [
            c
            for c in self.result.configurations
            if c.status == "SUCCESS" and c.encryption_metrics is not None
        ]
        if enc_candidates:
            fastest_enc = min(enc_candidates, key=lambda c: c.encryption_metrics.mean_ms)
            fastest_enc_name = _escape(fastest_enc.config_name)
            fastest_enc_latency = _format_ms(fastest_enc.encryption_metrics.mean_ms)
            fastest_enc_latency_html = (
                f'<div class="card-metric font-mono" style="font-size: 1.05rem; '
                f'color: var(--accent-cyan); font-weight: 600; margin-bottom: 0.25rem;">'
                f'{_escape(fastest_enc_latency)}</div>'
            )
            fastest_enc_sub = (
                "Fastest observed configuration in this experiment (lowest sample mean latency)"
            )
        else:
            fastest_enc_name = "None"
            fastest_enc_latency_html = ""
            fastest_enc_sub = "All configurations failed"

        # Fastest decryption configuration and underlying mean latency
        if self.result.skip_decryption:
            fastest_dec_name = "N/A (Skipped)"
            fastest_dec_latency_html = ""
            fastest_dec_sub = "Decryption benchmarking was skipped"
        else:
            dec_candidates = [
                c
                for c in self.result.configurations
                if c.status == "SUCCESS" and c.decryption_metrics is not None
            ]
            if dec_candidates:
                fastest_dec = min(dec_candidates, key=lambda c: c.decryption_metrics.mean_ms)
                fastest_dec_name = _escape(fastest_dec.config_name)
                fastest_dec_latency = _format_ms(fastest_dec.decryption_metrics.mean_ms)
                fastest_dec_latency_html = (
                    f'<div class="card-metric font-mono" style="font-size: 1.05rem; '
                    f'color: var(--accent-cyan); font-weight: 600; margin-bottom: 0.25rem;">'
                    f'{_escape(fastest_dec_latency)}</div>'
                )
                fastest_dec_sub = (
                    "Fastest observed configuration in this experiment (lowest sample mean latency)"
                )
            else:
                fastest_dec_name = "None"
                fastest_dec_latency_html = ""
                fastest_dec_sub = "All configurations failed"

        fail_badge_class = "badge-green" if failure_count == 0 else "badge-red"

        return f"""
        <section class="section-card">
            <h2 class="section-title">Executive Summary</h2>
            <div class="summary-cards-grid">
                <div class="summary-card">
                    <div class="card-label">Target File Size</div>
                    <div class="card-value">{_escape(size_str)}</div>
                    <div class="card-sub">{_escape(meta.file_size_bytes)} exact bytes</div>
                </div>
                <div class="summary-card">
                    <div class="card-label">Tested Configurations</div>
                    <div class="card-value">{success_count} / {total_configs}</div>
                    <div class="card-sub"><span class="badge {fail_badge_class}">{failure_count} Failed</span></div>
                </div>
                <div class="summary-card">
                    <div class="card-label">Fastest Observed Encryption</div>
                    <div class="card-value">{fastest_enc_name}</div>
                    {fastest_enc_latency_html}
                    <div class="card-sub">{fastest_enc_sub}</div>
                </div>
                <div class="summary-card">
                    <div class="card-label">Fastest Observed Decryption</div>
                    <div class="card-value">{fastest_dec_name}</div>
                    {fastest_dec_latency_html}
                    <div class="card-sub">{fastest_dec_sub}</div>
                </div>
            </div>
        </section>
        """

    def _render_matrix_table(self) -> str:
        rows = []
        is_zero_byte = self.result.file_metadata.is_zero_byte

        for cfg in self.result.configurations:
            conf_name = _escape(cfg.config_name)

            if cfg.status == "SUCCESS":
                status_badge = '<span class="badge badge-green">Success</span>'

                if cfg.ciphertext_metrics:
                    c_size = _format_bytes(cfg.ciphertext_metrics.ciphertext_size_bytes)
                    pad_bytes = f"{cfg.ciphertext_metrics.padding_overhead_bytes} B"
                    exp_pct = _format_pct(cfg.ciphertext_metrics.expansion_percentage)
                else:
                    c_size, pad_bytes, exp_pct = "N/A", "N/A", "N/A"

                if cfg.encryption_metrics:
                    enc_lat = _format_ms(cfg.encryption_metrics.mean_ms)
                    enc_tput = (
                        "N/A" if is_zero_byte else _format_mb_s(cfg.encryption_metrics.throughput_mb_s)
                    )
                else:
                    enc_lat, enc_tput = "N/A", "N/A"

                if self.result.skip_decryption:
                    dec_lat, dec_tput = "N/A (Skipped)", "N/A (Skipped)"
                elif cfg.decryption_metrics:
                    dec_lat = _format_ms(cfg.decryption_metrics.mean_ms)
                    dec_tput = (
                        "N/A" if is_zero_byte else _format_mb_s(cfg.decryption_metrics.throughput_mb_s)
                    )
                else:
                    dec_lat, dec_tput = "N/A", "N/A"

                rows.append(f"""
                <tr>
                    <td><strong>{conf_name}</strong></td>
                    <td>{status_badge}</td>
                    <td class="num">{_escape(c_size)}</td>
                    <td class="num">{_escape(pad_bytes)}</td>
                    <td class="num">{_escape(exp_pct)}</td>
                    <td class="num">{_escape(enc_lat)}</td>
                    <td class="num">{_escape(enc_tput)}</td>
                    <td class="num">{_escape(dec_lat)}</td>
                    <td class="num">{_escape(dec_tput)}</td>
                </tr>
                """)
            else:
                status_badge = '<span class="badge badge-red">Failed</span>'
                err_msg = _escape(cfg.error_message or "Execution failed")
                rows.append(f"""
                <tr>
                    <td><strong>{conf_name}</strong></td>
                    <td>{status_badge}</td>
                    <td colspan="7" class="text-muted" style="font-style: italic;">
                        Failure: {err_msg}
                    </td>
                </tr>
                """)

        zero_byte_notice = ""
        if is_zero_byte:
            zero_byte_notice = """
            <div class="info-box">
                <strong>Zero-Byte File Notice:</strong> Target payload is 0 bytes. Throughput (MB/s) is mathematically undefined (N/A). Latency measurements reflect block padding and cipher setup overhead.
            </div>
            """

        return f"""
        <section class="section-card">
            <h2 class="section-title">Comparative Configuration Matrix</h2>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Configuration</th>
                            <th>Status</th>
                            <th class="num">Ciphertext Size</th>
                            <th class="num">Padding Added</th>
                            <th class="num">Expansion</th>
                            <th class="num">Enc Latency (Mean)</th>
                            <th class="num">Enc Throughput</th>
                            <th class="num">Dec Latency (Mean)</th>
                            <th class="num">Dec Throughput</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
            {zero_byte_notice}
        </section>
        """

    def _render_performance_breakdown(
        self,
        key_size_chart: str | None,
        mode_chart: str | None,
    ) -> str:
        # Encryption detailed statistical table
        enc_rows = []
        dec_rows = []
        is_zero_byte = self.result.file_metadata.is_zero_byte

        for cfg in self.result.configurations:
            conf_name = _escape(cfg.config_name)

            if cfg.status == "SUCCESS" and cfg.encryption_metrics:
                m = cfg.encryption_metrics
                tput_str = "N/A" if is_zero_byte else _format_mb_s(m.throughput_mb_s)
                enc_rows.append(f"""
                <tr>
                    <td><strong>{conf_name}</strong></td>
                    <td class="num">{m.sample_count}</td>
                    <td class="num">{_format_ms(m.mean_ms)}</td>
                    <td class="num">{_format_ms(m.median_ms)}</td>
                    <td class="num">&plusmn;{m.std_dev_ms:.3f} ms</td>
                    <td class="num">{_format_ms(m.min_ms)}</td>
                    <td class="num">{_format_ms(m.max_ms)}</td>
                    <td class="num">{_format_ms(m.q1_ms)}</td>
                    <td class="num">{_format_ms(m.q3_ms)}</td>
                    <td class="num">{_format_ms(m.iqr_ms)}</td>
                    <td class="num">{m.outlier_count}</td>
                    <td class="num">{_escape(tput_str)}</td>
                </tr>
                """)

            if not self.result.skip_decryption:
                if cfg.status == "SUCCESS" and cfg.decryption_metrics:
                    dm = cfg.decryption_metrics
                    dtput_str = "N/A" if is_zero_byte else _format_mb_s(dm.throughput_mb_s)
                    dec_rows.append(f"""
                    <tr>
                        <td><strong>{conf_name}</strong></td>
                        <td class="num">{dm.sample_count}</td>
                        <td class="num">{_format_ms(dm.mean_ms)}</td>
                        <td class="num">{_format_ms(dm.median_ms)}</td>
                        <td class="num">&plusmn;{dm.std_dev_ms:.3f} ms</td>
                        <td class="num">{_format_ms(dm.min_ms)}</td>
                        <td class="num">{_format_ms(dm.max_ms)}</td>
                        <td class="num">{_format_ms(dm.q1_ms)}</td>
                        <td class="num">{_format_ms(dm.q3_ms)}</td>
                        <td class="num">{_format_ms(dm.iqr_ms)}</td>
                        <td class="num">{dm.outlier_count}</td>
                        <td class="num">{_escape(dtput_str)}</td>
                    </tr>
                    """)

        # Decryption table section
        if self.result.skip_decryption:
            dec_table_html = """
            <div class="info-box" style="margin-top: 1.5rem;">
                <strong>Decryption Benchmarking Skipped:</strong> Decryption timing analysis was disabled via <code>--skip-decryption</code>.
            </div>
            """
        elif dec_rows:
            dec_table_html = f"""
            <h3 style="font-size: 1.05rem; color: var(--text-primary); margin-top: 2rem; margin-bottom: 0.75rem;">
                Decryption Latency Distribution (30 Measured Iterations)
            </h3>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Configuration</th>
                            <th class="num">N</th>
                            <th class="num">Mean</th>
                            <th class="num">Median</th>
                            <th class="num">Std Dev</th>
                            <th class="num">Min</th>
                            <th class="num">Max</th>
                            <th class="num">Q1</th>
                            <th class="num">Q3</th>
                            <th class="num">IQR</th>
                            <th class="num">Outliers</th>
                            <th class="num">Throughput</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(dec_rows)}
                    </tbody>
                </table>
            </div>
            """
        else:
            dec_table_html = """
            <div class="alert-box" style="margin-top: 1.5rem;">
                <strong>Decryption Benchmarking Unavailable:</strong> No successful decryption measurements were recorded.
            </div>
            """

        # Chart rendering section with Level A fallback notice
        if key_size_chart:
            ks_chart_content = f'<img class="chart-img" src="{key_size_chart}" alt="Key Size Comparison Chart" />'
        else:
            ks_chart_content = f'<div class="chart-fallback">{_escape(CHART_FALLBACK_NOTICE)}</div>'

        if mode_chart:
            mode_chart_content = f'<img class="chart-img" src="{mode_chart}" alt="Mode Comparison Chart" />'
        else:
            mode_chart_content = f'<div class="chart-fallback">{_escape(CHART_FALLBACK_NOTICE)}</div>'

        return f"""
        <section class="section-card">
            <h2 class="section-title">Detailed Performance Analysis</h2>
            
            <h3 style="font-size: 1.05rem; color: var(--text-primary); margin-bottom: 0.75rem;">
                Encryption Latency Distribution (30 Measured Iterations)
            </h3>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Configuration</th>
                            <th class="num">N</th>
                            <th class="num">Mean</th>
                            <th class="num">Median</th>
                            <th class="num">Std Dev</th>
                            <th class="num">Min</th>
                            <th class="num">Max</th>
                            <th class="num">Q1</th>
                            <th class="num">Q3</th>
                            <th class="num">IQR</th>
                            <th class="num">Outliers</th>
                            <th class="num">Throughput</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(enc_rows) if enc_rows else '<tr><td colspan="12" class="text-muted">No successful encryption measurements recorded.</td></tr>'}
                    </tbody>
                </table>
            </div>

            {dec_table_html}

            <div class="charts-grid">
                <div class="chart-card">
                    <div class="chart-title">Key Size Comparison (AES 128 vs 192 vs 256)</div>
                    {ks_chart_content}
                </div>
                <div class="chart-card">
                    <div class="chart-title">Cipher Mode Comparison (CBC vs ECB)</div>
                    {mode_chart_content}
                </div>
            </div>
        </section>
        """

    def _render_padding_profile(self) -> str:
        meta = self.result.file_metadata
        p_size = meta.file_size_bytes

        # Derive representative ciphertext and padding if available
        c_size_str = "N/A"
        pad_str = "N/A"
        exp_str = "N/A"

        for cfg in self.result.configurations:
            if cfg.ciphertext_metrics is not None:
                c_size_str = _format_bytes(cfg.ciphertext_metrics.ciphertext_size_bytes)
                pad_str = f"{cfg.ciphertext_metrics.padding_overhead_bytes} bytes"
                exp_str = _format_pct(cfg.ciphertext_metrics.expansion_percentage)
                break

        return f"""
        <section class="section-card">
            <h2 class="section-title">Ciphertext &amp; PKCS#7 Padding Profile</h2>
            <div class="summary-cards-grid">
                <div class="summary-card">
                    <div class="card-label">Original Plaintext</div>
                    <div class="card-value">{_escape(_format_bytes(p_size))}</div>
                    <div class="card-sub">{p_size:,} bytes</div>
                </div>
                <div class="summary-card">
                    <div class="card-label">Padded Ciphertext</div>
                    <div class="card-value">{_escape(c_size_str)}</div>
                    <div class="card-sub">Exact 16-byte block multiple</div>
                </div>
                <div class="summary-card">
                    <div class="card-label">Padding Overhead</div>
                    <div class="card-value">{_escape(pad_str)}</div>
                    <div class="card-sub">1 to 16 bytes appended</div>
                </div>
                <div class="summary-card">
                    <div class="card-label">Storage Expansion</div>
                    <div class="card-value">{_escape(exp_str)}</div>
                    <div class="card-sub">((Ciphertext - Plaintext) / Plaintext) &times; 100</div>
                </div>
            </div>
            <div class="info-box">
                <strong>PKCS#7 Boundary Guarantees:</strong>
                AES strictly processes 128-bit (16-byte) blocks. Under PKCS#7 standard specification, padding length always ranges between 1 and 16 bytes. If the original payload is an exact multiple of 16 bytes (including 0-byte files), an entire additional 16-byte block is appended, with each padding byte set to <code>0x10</code>. This determinism guarantees unambiguous depadding upon decryption.
            </div>
        </section>
        """

    def _render_security_profile(self) -> str:
        if not self.result.security_enabled:
            return """
            <section class="section-card">
                <h2 class="section-title">Security &amp; Diffusion Profile</h2>
                <div class="info-box">
                    <strong>Security Analysis Not Enabled:</strong> Plaintext Avalanche Effect and Key Sensitivity evaluations were not requested for this experiment run. Pass <code>--security</code> to execute diffusion analysis.
                </div>
            </section>
            """

        cards = []
        for cfg in self.result.configurations:
            conf_name = _escape(cfg.config_name)
            sec = cfg.security_metrics

            if sec is None or sec.status == "SKIPPED":
                notes_esc = _escape(sec.notes if sec else "Diffusion metrics skipped.")
                cards.append(f"""
                <div class="security-card">
                    <div class="security-header">
                        <strong>{conf_name}</strong>
                        <span class="badge badge-neutral">Skipped</span>
                    </div>
                    <p class="text-muted" style="font-size: 0.85rem;">{notes_esc}</p>
                </div>
                """)
            elif sec.status == "FAILED":
                notes_esc = _escape(sec.notes or "Security evaluation failed.")
                cards.append(f"""
                <div class="security-card">
                    <div class="security-header">
                        <strong>{conf_name}</strong>
                        <span class="badge badge-red">Failed</span>
                    </div>
                    <p class="text-muted" style="font-size: 0.85rem;">{notes_esc}</p>
                </div>
                """)
            else:
                av_val = sec.avalanche_effect_pct
                ks_val = sec.key_sensitivity_pct

                av_str = _format_pct(av_val)
                ks_str = _format_pct(ks_val)

                av_width = f"{min(100.0, max(0.0, av_val or 0.0)):.1f}%"
                ks_width = f"{min(100.0, max(0.0, ks_val or 0.0)):.1f}%"

                # Check for BMP ECB structural weakness analysis
                ecb_notice = ""
                if sec.ecb_weakness_analyzed:
                    ecb_notice = """
                    <div class="alert-box" style="margin-top: 1rem;">
                        <strong>ECB Visual Redundancy Analysis:</strong> Structural block pattern leakage was evaluated on this 24-bpp uncompressed BMP image. Comparison CBC encryption utilized a fresh, randomly generated 16-byte initialization vector; results reflect empirical visual leakage difference rather than a deterministic single-run test.
                    </div>
                    """
                elif sec.notes:
                    ecb_notice = f"""
                    <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.75rem;">
                        Note: {_escape(sec.notes)}
                    </div>
                    """

                cards.append(f"""
                <div class="security-card">
                    <div class="security-header">
                        <strong>{conf_name}</strong>
                        <span class="badge badge-green">Evaluated</span>
                    </div>
                    <div class="security-metrics-row">
                        <div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                                <span class="meta-label">Plaintext Avalanche Effect (1-bit mutation)</span>
                                <strong>{_escape(av_str)}</strong>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill" style="width: {_escape(av_width)};"></div>
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Ideal theoretical: 50.0%</div>
                        </div>
                        <div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                                <span class="meta-label">Key Sensitivity (1-bit key mutation)</span>
                                <strong>{_escape(ks_str)}</strong>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill" style="width: {_escape(ks_width)};"></div>
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Ideal theoretical: 50.0%</div>
                        </div>
                    </div>
                    {ecb_notice}
                </div>
                """)

        return f"""
        <section class="section-card">
            <h2 class="section-title">Security &amp; Diffusion Profile</h2>
            <div class="alert-box">
                <strong>Cryptographic Notice &amp; Boundary Limitations:</strong>
                <p>Plaintext Avalanche Effect and Key Sensitivity measure empirical bit-diffusion across single-bit perturbations in the target file and key. An observed ~50% bit-flip rate reflects cryptographic confusion and diffusion properties but does NOT constitute a formal mathematical security proof.</p>
                <p style="margin-top: 0.5rem;">AES-CBC provides confidentiality only when used with an unpredictable, unique initialization vector (IV) per message. It does NOT provide message authentication, data integrity, or AEAD guarantees.</p>
            </div>
            {''.join(cards)}
        </section>
        """

    def _render_methodology(self) -> str:
        return """
        <section class="section-card">
            <h2 class="section-title">Experimental Methodology</h2>
            <ul class="methodology-list">
                <li class="methodology-item">
                    <strong>1. Warmup Cycles (Cache Priming)</strong>
                    <p>Each configuration undergoes 5 unmeasured warmup execution cycles prior to benchmarking. This eliminates transient latency penalties from operating system page faults, CPU instruction cache misses, and branch predictor initialization.</p>
                </li>
                <li class="methodology-item">
                    <strong>2. Measured Sample Size (N = 30)</strong>
                    <p>Following warmup, exactly 30 independent iterations are timed using Python's high-resolution monotonic timer (<code>time.perf_counter_ns</code>). This sample size provides robust statistical significance while bounding total benchmarking overhead.</p>
                </li>
                <li class="methodology-item">
                    <strong>3. In-Memory Timing Isolation</strong>
                    <p>Cryptographic key generation, IV generation, memory allocation, and ciphertext round-trip integrity checks are performed strictly outside the measured timing loop. The timed code block contains exclusively the core encryption or decryption operation.</p>
                </li>
                <li class="methodology-item">
                    <strong>4. Tukey Outlier Identification</strong>
                    <p>Outliers are identified using standard Tukey fences ([Q1 &minus; 1.5 &times; IQR, Q3 + 1.5 &times; IQR]). Outliers are recorded and counted for forensic visibility, but are retained in all mean and standard deviation computations to preserve total empirical truth.</p>
                </li>
                <li class="methodology-item">
                    <strong>5. Binary Throughput Calculation</strong>
                    <p>Throughput is computed using binary megabytes (1 MB = 1,048,576 bytes): <code>Throughput = (Bytes / 1,048,576) / Mean_Time_Seconds</code>. For zero-byte files, throughput is reported as N/A to prevent misleading claims of zero bandwidth.</p>
                </li>
            </ul>
        </section>
        """

    def _render_limitations(self) -> str:
        return """
        <section class="section-card">
            <h2 class="section-title">Limitations &amp; Scientific Caveats</h2>
            <ul class="limitations-list">
                <li class="limitations-item">
                    <strong>Hardware and Environment Specificity</strong>
                    <p>Benchmark figures reflect the specific CPU microarchitecture, memory bandwidth, cache hierarchy, and operating system scheduling policies of the execution host. These metrics should not be extrapolated across heterogeneous server environments.</p>
                </li>
                <li class="limitations-item">
                    <strong>Single-File Non-Generalizability</strong>
                    <p>Performance on this specific file does not predict performance on significantly smaller or larger workloads. Cryptographic throughput exhibits non-linear scaling across different payload sizes and memory alignment boundaries.</p>
                </li>
                <li class="limitations-item">
                    <strong>Confidentiality vs. Authenticity</strong>
                    <p>AES-CBC provides confidentiality against passive eavesdropping when coupled with a cryptographically secure, unique IV. It does not provide cryptographic integrity or authenticity against active chosen-ciphertext or padding oracle attacks.</p>
                </li>
                <li class="limitations-item">
                    <strong>Absence of Universal Selection Claims</strong>
                    <p>This report strictly avoids declaring any configuration as a universal optimal choice. Cryptographic selection requires a balanced engineering trade-off among required security margin, compliance requirements, memory constraints, and execution latency.</p>
                </li>
            </ul>
        </section>
        """

    def generate_html(self) -> str:
        """
        Assemble the complete standalone HTML document.

        Level B Handling: Any unexpected error during assembly raises ReportAssemblyError,
        signaling failure to caller.
        """
        try:
            filename_esc = _escape(self.result.file_metadata.file_name)
            key_size_chart, mode_chart = self._generate_charts()

            header_html = self._render_header()
            exec_html = self._render_executive_summary()
            matrix_html = self._render_matrix_table()
            perf_html = self._render_performance_breakdown(key_size_chart, mode_chart)
            padding_html = self._render_padding_profile()
            security_html = self._render_security_profile()
            methodology_html = self._render_methodology()
            limitations_html = self._render_limitations()

            doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>File-Specific Encryption Analysis - {filename_esc}</title>
    <style>
{_REPORT_CSS}
    </style>
</head>
<body>
    <div class="container">
{header_html}
{exec_html}
{matrix_html}
{perf_html}
{padding_html}
{security_html}
{methodology_html}
{limitations_html}
        <footer>
            File-Specific Encryption Analysis Lab &bull; Post-V2 Usability &amp; Cryptographic Performance Suite
        </footer>
    </div>
</body>
</html>
"""
            return doc
        except Exception as exc:
            raise ReportAssemblyError(f"Failed to assemble HTML report: {exc}") from exc

    def save_report(self, output_path: str | Path | None = None) -> Path:
        """
        Compile and save the standalone HTML report to disk.

        If output_path is omitted, defaults to:
            results/reports/file_analysis_<slug>_<timestamp>.html
        """
        html_content = self.generate_html()

        if output_path is not None:
            target_path = Path(output_path)
        else:
            meta = self.result.file_metadata
            # Create safe slug from filename
            safe_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", meta.file_name)
            ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            target_path = self.DEFAULT_REPORT_DIR / f"file_analysis_{safe_slug}_{ts_str}.html"

        self.file_handler.write_text(target_path, html_content, encoding="utf-8")
        return target_path
