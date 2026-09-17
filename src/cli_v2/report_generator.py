"""Standalone HTML report generator for V2 usability layer.

Builds single-document HTML reports with embedded Base64 Matplotlib charts,
3-tier metadata, executive summaries, performance benchmark tables,
cryptanalysis metrics, and experimental methodology — per the frozen V2
Reporting Contract (§13, DSEL-010, DSEL-011).

This module owns presentation and report assembly only.  Benchmark figures
originate strictly from the V1 ``GraphGenerator``; metric data is consumed
from V1 ``MetricCollector`` and ``SecurityService``/``SecurityEvaluator``;
low-level I/O reuses ``FileHandler``.  No cryptography or analysis math is
implemented here.

Security: raw encryption keys, hex keys, and plaintext payloads are never
included in generated HTML reports.  All dynamic strings and runtime values
pass through strict HTML entity escaping to safeguard against local injection.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import html
import io
from pathlib import Path
import platform
import sys
from typing import Any
import webbrowser

import matplotlib.pyplot as plt
import pandas as pd

from src.analyzers.graph_generator import GraphGenerator
from src.utils.file_handler import FileHandler


def _escape(value: Any) -> str:
    """Sanitize any runtime value for HTML insertion using html.escape(quote=True)."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _utc_now() -> datetime:
    """Return current UTC datetime (isolated for testing/monkeypatching)."""
    return datetime.now(timezone.utc)


def _iso_timestamp(dt: datetime) -> str:
    """Format datetime as UTC ISO-8601 with trailing 'Z'."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_timestamp(dt: datetime) -> str:
    """Format datetime for report filenames (YYYYMMDD_HHMMSS)."""
    return dt.strftime("%Y%m%d_%H%M%S")


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
    --accent-indigo: #6366f1;
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
    max-width: 1100px;
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

.badge {
    display: inline-flex;
    align-items: center;
    background: rgba(59, 130, 246, 0.15);
    color: var(--accent-blue);
    border: 1px solid rgba(59, 130, 246, 0.3);
    padding: 0.35rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.metadata-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    padding-top: 1.25rem;
    border-top: 1px solid var(--border-color);
}

.meta-item {
    font-size: 0.875rem;
}

.meta-label {
    color: var(--text-muted);
    font-weight: 500;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
}

.meta-value {
    color: var(--text-secondary);
    font-weight: 600;
    margin-top: 0.15rem;
    word-break: break-all;
}

.section {
    background: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 2rem;
}

h2 {
    font-size: 1.3rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 1.25rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.25rem;
    margin-bottom: 1.5rem;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.25rem;
}

.metric-title {
    font-size: 0.8rem;
    color: var(--text-muted);
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.05em;
}

.metric-val {
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0.35rem 0;
}

.metric-sub {
    font-size: 0.8rem;
    color: var(--text-secondary);
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    font-size: 0.9rem;
}

th, td {
    padding: 0.85rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

th {
    background: var(--bg-card);
    color: var(--text-secondary);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
}

tbody tr:hover {
    background: rgba(255, 255, 255, 0.02);
}

.num {
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.chart-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 2rem;
    margin-top: 1.5rem;
}

.chart-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1.5rem;
    text-align: center;
}

.chart-card h3 {
    font-size: 1.05rem;
    color: var(--text-secondary);
    margin-bottom: 1rem;
    text-align: left;
}

.chart-card img {
    max-width: 100%;
    height: auto;
    border-radius: 6px;
    background: #ffffff;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
}

.progress-track {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 9999px;
    height: 12px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-blue), var(--accent-green));
    border-radius: 9999px;
}

.alert-box {
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-top: 1.25rem;
    color: #fbbf24;
    font-size: 0.9rem;
}

.alert-box strong {
    color: #fef3c7;
}

.methodology-list {
    list-style: none;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
}

.methodology-item {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1rem;
}

.methodology-item strong {
    display: block;
    color: var(--accent-blue);
    font-size: 0.85rem;
    margin-bottom: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.methodology-item p {
    color: var(--text-secondary);
    font-size: 0.875rem;
}

footer {
    text-align: center;
    padding: 2rem;
    color: var(--text-muted);
    font-size: 0.8rem;
}

@media print {
    body {
        background: #ffffff !important;
        color: #000000 !important;
        padding: 0;
        font-size: 10pt;
    }
    .container {
        max-width: 100%;
    }
    header, .section, .metric-card, .chart-card, .methodology-item {
        background: #ffffff !important;
        border: 1px solid #cccccc !important;
        color: #000000 !important;
        box-shadow: none !important;
        break-inside: avoid;
    }
    h1, h2, h3, .metric-val, strong {
        color: #000000 !important;
    }
    .meta-label, .meta-value, .metric-title, .metric-sub, .subtitle, p, td, th {
        color: #333333 !important;
    }
    .badge {
        border: 1px solid #666666 !important;
        color: #000000 !important;
        background: #f0f0f0 !important;
    }
    th {
        background: #f0f0f0 !important;
    }
    .chart-card img {
        box-shadow: none !important;
        border: 1px solid #cccccc !important;
    }
}
"""


class ReportGenerator:
    """Static-method standalone HTML report generator for V2 usability layer."""

    DEFAULT_REPORT_DIR = Path("results/reports")

    @staticmethod
    def figure_to_base64(fig: Any, dpi: int = 150) -> str:
        """Convert a Matplotlib figure to an in-memory Base64 PNG Data URI.

        Serializes the figure into a BytesIO buffer using the specified DPI,
        encodes it as base64, and returns the Data URI string.
        Always closes the figure in a finally block to free memory.

        Args:
            fig: Matplotlib Figure instance.
            dpi: Resolution in dots per inch (default 150).

        Returns:
            Data URI string formatted as 'data:image/png;base64,...'.
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

    @staticmethod
    def build_benchmark_report(collector: Any, output_path: str | Path | None = None) -> Path:
        """Generate a standalone HTML performance benchmark report.

        Extracts statistical summary metrics from the MetricCollector, builds
        embedded Base64 Matplotlib comparison charts via GraphGenerator, and
        persists the self-contained HTML artifact.

        Args:
            collector: MetricCollector instance or DataFrame with benchmark data.
            output_path: Optional destination path. Defaults to
                results/reports/cryptography_report_YYYYMMDD_HHMMSS.html.

        Returns:
            Path to the written HTML report.
        """
        now = _utc_now()
        iso_ts = _iso_timestamp(now)
        file_ts = _file_timestamp(now)

        if output_path is None:
            dest_path = ReportGenerator.DEFAULT_REPORT_DIR / f"cryptography_report_{file_ts}.html"
        else:
            dest_path = Path(output_path)

        # Extract summary dataframe
        if collector is None:
            summary_df = pd.DataFrame()
        elif hasattr(collector, "get_summary_dataframe"):
            summary_df = collector.get_summary_dataframe()
        elif isinstance(collector, pd.DataFrame):
            summary_df = collector
        else:
            summary_df = pd.DataFrame()

        title = "Cryptography Testing Lab — Benchmark Performance Report"
        py_ver = platform.python_version()
        plat_str = platform.platform()

        # Build content sections
        if summary_df.empty:
            exec_summary_html = """
            <div class="alert-box">
                <strong>Notice:</strong> No benchmark data recorded for this session.
            </div>
            """
            bench_section_html = """
            <div class="alert-box">
                <strong>Notice:</strong> No benchmark metrics recorded.
            </div>
            """
            charts_section_html = ""
        else:
            # Executive summary metrics
            total_configs = len(summary_df)
            peak_tp = summary_df["throughput_mb_s"].max() if "throughput_mb_s" in summary_df.columns else 0.0
            
            # Fastest configuration
            if "mean_time_ms" in summary_df.columns and not summary_df["mean_time_ms"].isna().all():
                fastest_row = summary_df.loc[summary_df["mean_time_ms"].idxmin()]
                fastest_name = f"{fastest_row.get('algorithm', '')}-{fastest_row.get('key_size', '')}-{fastest_row.get('mode', '')}"
                fastest_time = f"{fastest_row.get('mean_time_ms', 0.0):.2f} ms"
            else:
                fastest_name = "N/A"
                fastest_time = "N/A"

            total_outliers = int(summary_df["outlier_count"].sum()) if "outlier_count" in summary_df.columns else 0

            exec_summary_html = f"""
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">Peak Throughput</div>
                    <div class="metric-val">{_escape(f"{peak_tp:.2f}")} <span style="font-size: 1rem; font-weight: normal; color: var(--text-muted);">MB/s</span></div>
                    <div class="metric-sub">Highest measured throughput</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Fastest Configuration</div>
                    <div class="metric-val" style="font-size: 1.3rem;">{_escape(fastest_name)}</div>
                    <div class="metric-sub">{_escape(fastest_time)} mean execution</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Configurations Tested</div>
                    <div class="metric-val">{_escape(total_configs)}</div>
                    <div class="metric-sub">Across benchmark matrix</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">Tukey Outliers</div>
                    <div class="metric-val">{_escape(total_outliers)}</div>
                    <div class="metric-sub">Retained in primary stats</div>
                </div>
            </div>
            """

            # Summary table
            table_rows = []
            for _, row in summary_df.iterrows():
                cfg_str = f"{row.get('algorithm', '')}-{row.get('key_size', '')}-{row.get('mode', '')}"
                data_size = row.get("data_size_bytes", 0)
                mean_ms = row.get("mean_time_ms", 0.0)
                median_ms = row.get("median_time_ms", 0.0)
                std_ms = row.get("std_dev_time_ms", 0.0)
                min_ms = row.get("min_time_ms", 0.0)
                max_ms = row.get("max_time_ms", 0.0)
                outliers = row.get("outlier_count", 0)
                tp = row.get("throughput_mb_s", 0.0)

                table_rows.append(f"""
                <tr>
                    <td><strong>{_escape(cfg_str)}</strong></td>
                    <td class="num">{_escape(f"{data_size:,}")} B</td>
                    <td class="num">{_escape(f"{mean_ms:.3f}")}</td>
                    <td class="num">{_escape(f"{median_ms:.3f}")}</td>
                    <td class="num">&plusmn; {_escape(f"{std_ms:.3f}")}</td>
                    <td class="num">{_escape(f"{min_ms:.3f}")}</td>
                    <td class="num">{_escape(f"{max_ms:.3f}")}</td>
                    <td class="num">{_escape(outliers)}</td>
                    <td class="num"><strong>{_escape(f"{tp:.2f}")}</strong></td>
                </tr>
                """)

            bench_section_html = f"""
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Configuration</th>
                            <th class="num">Data Size</th>
                            <th class="num">Mean (ms)</th>
                            <th class="num">Median (ms)</th>
                            <th class="num">Std Dev (ms)</th>
                            <th class="num">Min (ms)</th>
                            <th class="num">Max (ms)</th>
                            <th class="num">Outliers</th>
                            <th class="num">Throughput (MB/s)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(table_rows)}
                    </tbody>
                </table>
            </div>
            """

            # Generate Figures via GraphGenerator
            compare_df = summary_df
            if "data_size_bytes" in summary_df.columns and summary_df["data_size_bytes"].nunique() > 1:
                first_size = summary_df["data_size_bytes"].min()
                compare_df = summary_df[summary_df["data_size_bytes"] == first_size]

            charts = []
            
            # Key Size Comparison
            key_fig = GraphGenerator.generate_key_size_comparison(compare_df)
            key_b64 = ReportGenerator.figure_to_base64(key_fig)
            charts.append(f"""
            <div class="chart-card">
                <h3>AES Performance by Key Size</h3>
                <img src="{key_b64}" alt="AES Performance by Key Size">
            </div>
            """)

            # Mode Comparison
            mode_fig = GraphGenerator.generate_mode_comparison(compare_df)
            mode_b64 = ReportGenerator.figure_to_base64(mode_fig)
            charts.append(f"""
            <div class="chart-card">
                <h3>AES Performance by Mode</h3>
                <img src="{mode_b64}" alt="AES Performance by Mode">
            </div>
            """)

            # Throughput Scaling
            tp_fig = GraphGenerator.generate_throughput_analysis(summary_df)
            tp_b64 = ReportGenerator.figure_to_base64(tp_fig)
            charts.append(f"""
            <div class="chart-card">
                <h3>AES Throughput Scaling</h3>
                <img src="{tp_b64}" alt="AES Throughput Scaling">
            </div>
            """)

            charts_section_html = f"""
            <div class="chart-grid">
                {''.join(charts)}
            </div>
            """

        methodology_html = """
        <ul class="methodology-list">
            <li class="methodology-item">
                <strong>Warmup Phase</strong>
                <p>5 unmeasured warmup iterations per configuration to stabilize CPU caches and execution state.</p>
            </li>
            <li class="methodology-item">
                <strong>Measurement Sample</strong>
                <p>30 measured iterations recorded per configuration using high-resolution performance timers.</p>
            </li>
            <li class="methodology-item">
                <strong>Tukey Outlier Fences</strong>
                <p>Outliers identified via Q1 - 1.5&times;IQR and Q3 + 1.5&times;IQR fences. All raw observations are retained in statistical calculations.</p>
            </li>
            <li class="methodology-item">
                <strong>Binary Throughput</strong>
                <p>Throughput calculated using binary megabytes (1 MB = 1,048,576 bytes) divided by mean execution duration.</p>
            </li>
        </ul>
        """

        html_doc = f"""<!DOCTYPE html>
<html lang="en" data-report-version="2.0">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="data-report-version" content="2.0">
    <title>{_escape(title)}</title>
    <style>
{_REPORT_CSS}
    </style>
</head>
<body>
    <div class="container" data-report-version="2.0">
        <header>
            <div class="header-top">
                <div>
                    <h1>{_escape(title)}</h1>
                    <div class="subtitle">Statistical Performance Evaluation &amp; Empirical Benchmark Profile</div>
                </div>
                <div class="badge">Schema 2.0</div>
            </div>
            <div class="metadata-grid">
                <div class="meta-item">
                    <div class="meta-label">Generated UTC</div>
                    <div class="meta-value">{_escape(iso_ts)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Python Version</div>
                    <div class="meta-value">{_escape(py_ver)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Platform / OS</div>
                    <div class="meta-value">{_escape(plat_str)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Schema Version</div>
                    <div class="meta-value">2.0</div>
                </div>
            </div>
        </header>

        <section class="section">
            <h2>Executive Summary</h2>
            {exec_summary_html}
        </section>

        <section class="section">
            <h2>Performance Benchmarks</h2>
            {bench_section_html}
            {charts_section_html}
        </section>

        <section class="section">
            <h2>Experimental Methodology</h2>
            {methodology_html}
        </section>

        <footer>
            Cryptography Testing Lab &bull; V2 Usability &amp; Reporting Layer &bull; Generated offline
        </footer>
    </div>
</body>
</html>"""

        FileHandler.write_text(dest_path, html_doc, encoding="utf-8")
        return dest_path

    @staticmethod
    def build_security_report(security_results: dict, output_path: str | Path | None = None) -> Path:
        """Generate a standalone HTML security evaluation report.

        Consumes SecurityService / SecurityEvaluator results, structures diffusion
        metrics (Avalanche Effect, Key Sensitivity), renders comparative ECB vs CBC
        structural pattern analysis, and persists the self-contained HTML artifact.

        Args:
            security_results: Dictionary containing security evaluation results.
            output_path: Optional destination path. Defaults to
                results/reports/cryptography_report_YYYYMMDD_HHMMSS.html.

        Returns:
            Path to the written HTML report.
        """
        now = _utc_now()
        iso_ts = _iso_timestamp(now)
        file_ts = _file_timestamp(now)

        if output_path is None:
            dest_path = ReportGenerator.DEFAULT_REPORT_DIR / f"cryptography_report_{file_ts}.html"
        else:
            dest_path = Path(output_path)

        title = "Cryptography Testing Lab — Security & Cryptanalysis Report"
        py_ver = platform.python_version()
        plat_str = platform.platform()

        if not security_results or not isinstance(security_results, dict):
            exec_summary_html = """
            <div class="alert-box">
                <strong>Notice:</strong> No security evaluation recorded for this session.
            </div>
            """
            security_section_html = """
            <div class="alert-box">
                <strong>Notice:</strong> No security data recorded.
            </div>
            """
        else:
            # Handle possible nested wrapper (e.g. {"results": {...}})
            if "results" in security_results and isinstance(security_results["results"], dict):
                entries = security_results["results"]
            else:
                entries = security_results

            avalanche_vals = []
            key_sens_vals = []
            has_ecb_leakage = False
            config_cards = []

            for conf_name, conf_data in entries.items():
                if not isinstance(conf_data, dict):
                    continue

                av = conf_data.get("avalanche_effect")
                ks = conf_data.get("key_sensitivity")
                ecb_data = conf_data.get("ecb_weakness")

                if isinstance(av, (int, float)):
                    avalanche_vals.append(float(av))
                if isinstance(ks, (int, float)):
                    key_sens_vals.append(float(ks))
                if ecb_data:
                    has_ecb_leakage = True

                av_str = f"{av:.2f}%" if isinstance(av, (int, float)) else "N/A"
                ks_str = f"{ks:.2f}%" if isinstance(ks, (int, float)) else "N/A"
                av_width = f"{min(max(float(av), 0.0), 100.0):.1f}%" if isinstance(av, (int, float)) else "0%"
                ks_width = f"{min(max(float(ks), 0.0), 100.0):.1f}%" if isinstance(ks, (int, float)) else "0%"

                ecb_comparison_html = ""
                if ecb_data and isinstance(ecb_data, dict):
                    hdr_len = len(ecb_data.get("original_header", b""))
                    px_len = len(ecb_data.get("original_pixel_data", b""))
                    ecb_len = len(ecb_data.get("ecb_ciphertext", b""))
                    cbc_len = len(ecb_data.get("cbc_ciphertext", b""))
                    trailing_len = len(ecb_data.get("bmp_trailing_data", b""))

                    ecb_comparison_html = f"""
                    <div style="margin-top: 1.5rem;">
                        <h4 style="color: var(--text-primary); font-size: 0.95rem; margin-bottom: 0.75rem;">ECB vs. CBC Structural Pattern Comparison (BMP Image)</h4>
                        <div style="overflow-x: auto;">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Attribute / Metric</th>
                                        <th>AES-ECB</th>
                                        <th>AES-CBC</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td>BMP Header Size</td>
                                        <td class="num">{_escape(hdr_len)} bytes</td>
                                        <td class="num">{_escape(hdr_len)} bytes</td>
                                    </tr>
                                    <tr>
                                        <td>Plaintext Pixel Buffer</td>
                                        <td class="num">{_escape(px_len)} bytes</td>
                                        <td class="num">{_escape(px_len)} bytes</td>
                                    </tr>
                                    <tr>
                                        <td>Ciphertext Size (PKCS#7 Padded)</td>
                                        <td class="num">{_escape(ecb_len)} bytes</td>
                                        <td class="num">{_escape(cbc_len)} bytes</td>
                                    </tr>
                                    <tr>
                                        <td>Initialization Vector (IV)</td>
                                        <td>None (Not supported)</td>
                                        <td>16 bytes (Random unique)</td>
                                    </tr>
                                    <tr>
                                        <td>Structural Pattern Leakage</td>
                                        <td><span style="color: var(--accent-red); font-weight: 600;">Observed</span> (Identical blocks yield identical ciphertext)</td>
                                        <td><span style="color: var(--accent-green); font-weight: 600;">Masked</span> (Cipher block chaining diffuses redundancy)</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    """

                config_cards.append(f"""
                <div class="metric-card" style="margin-bottom: 1.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h3 style="font-size: 1.15rem; color: var(--text-primary);">{_escape(conf_name)}</h3>
                        <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border-color: rgba(16, 185, 129, 0.3);">Evaluated</span>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem;">
                        <div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                                <span class="meta-label">Plaintext Avalanche Effect</span>
                                <strong>{_escape(av_str)}</strong>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill" style="width: {_escape(av_width)};"></div>
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Ideal theoretical: 50.0%</div>
                        </div>
                        <div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                                <span class="meta-label">Key Sensitivity</span>
                                <strong>{_escape(ks_str)}</strong>
                            </div>
                            <div class="progress-track">
                                <div class="progress-fill" style="width: {_escape(ks_width)};"></div>
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Ideal theoretical: 50.0%</div>
                        </div>
                    </div>
                    {ecb_comparison_html}
                </div>
                """)

            configs_evaluated = len(entries)

            exec_summary_html = f"""
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">Configurations Evaluated</div>
                    <div class="metric-val">{_escape(configs_evaluated)}</div>
                    <div class="metric-sub">Total distinct security profiles</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">ECB Pattern Leakage</div>
                    <div class="metric-val" style="font-size: 1.25rem; color: {'var(--accent-red)' if has_ecb_leakage else 'var(--text-secondary)'};">
                        {_escape('Identified' if has_ecb_leakage else 'Not Tested')}
                    </div>
                    <div class="metric-sub">{'Block redundancy observed' if has_ecb_leakage else 'No ECB mode tested'}</div>
                </div>
            </div>
            """

            security_section_html = f"""
            {''.join(config_cards)}
            <div class="alert-box">
                <strong>Cryptographic Notice:</strong> AES-CBC provides confidentiality only when used with an unpredictable, unique IV per message. It does NOT provide message authentication or integrity verification.
            </div>
            """

        methodology_html = """
        <ul class="methodology-list">
            <li class="methodology-item">
                <strong>Avalanche Effect</strong>
                <p>Measures the percentage of ciphertext bits that flip when exactly 1 bit of plaintext is inverted (ideal: 50.0%).</p>
            </li>
            <li class="methodology-item">
                <strong>Key Sensitivity</strong>
                <p>Measures the percentage of ciphertext bits that flip when exactly 1 bit of the cryptographic key is inverted (ideal: 50.0%).</p>
            </li>
            <li class="methodology-item">
                <strong>Hamming Distance</strong>
                <p>Exact bit-level differences computed by XORing equal-length byte sequences and counting asserted bits.</p>
            </li>
            <li class="methodology-item">
                <strong>ECB Pattern Analysis</strong>
                <p>Demonstrates structural block leakage in 24-bpp uncompressed BMP image pixel data where identical plaintext blocks produce identical ciphertext blocks.</p>
            </li>
        </ul>
        """

        html_doc = f"""<!DOCTYPE html>
<html lang="en" data-report-version="2.0">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="data-report-version" content="2.0">
    <title>{_escape(title)}</title>
    <style>
{_REPORT_CSS}
    </style>
</head>
<body>
    <div class="container" data-report-version="2.0">
        <header>
            <div class="header-top">
                <div>
                    <h1>{_escape(title)}</h1>
                    <div class="subtitle">Cryptographic Security Evaluation, Diffusion Analysis &amp; Mode Comparison</div>
                </div>
                <div class="badge">Schema 2.0</div>
            </div>
            <div class="metadata-grid">
                <div class="meta-item">
                    <div class="meta-label">Generated UTC</div>
                    <div class="meta-value">{_escape(iso_ts)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Python Version</div>
                    <div class="meta-value">{_escape(py_ver)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Platform / OS</div>
                    <div class="meta-value">{_escape(plat_str)}</div>
                </div>
                <div class="meta-item">
                    <div class="meta-label">Schema Version</div>
                    <div class="meta-value">2.0</div>
                </div>
            </div>
        </header>

        <section class="section">
            <h2>Executive Summary</h2>
            {exec_summary_html}
        </section>

        <section class="section">
            <h2>Security &amp; Cryptanalysis</h2>
            {security_section_html}
        </section>

        <section class="section">
            <h2>Experimental Methodology</h2>
            {methodology_html}
        </section>

        <footer>
            Cryptography Testing Lab &bull; V2 Usability &amp; Reporting Layer &bull; Generated offline
        </footer>
    </div>
</body>
</html>"""

        FileHandler.write_text(dest_path, html_doc, encoding="utf-8")
        return dest_path

    @staticmethod
    def open_in_browser(report_path: str | Path) -> bool:
        """Open the generated HTML report in the default web browser.

        Converts the report path to a file:// URI and invokes webbrowser.open().
        Returns False if the path does not exist or if browser launch fails.
        Never raises an exception to the caller.

        Args:
            report_path: Path to the HTML report file.

        Returns:
            bool: True if the browser was successfully launched, False otherwise.
        """
        try:
            p = Path(report_path)
            if not p.exists() or not p.is_file():
                return False
            uri = p.resolve().as_uri()
            return bool(webbrowser.open(uri))
        except Exception:
            return False
