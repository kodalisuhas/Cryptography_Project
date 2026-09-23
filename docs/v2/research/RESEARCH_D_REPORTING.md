# V2 RESEARCH D — REPORTING

**Document ID:** V2-RESEARCH-D  
**Status:** DRAFT / CORRECTED — READY FOR INDEPENDENT VERIFICATION  
**Date:** 2026-09-15  
**Author:** V2 Reporting Research Lead  
**Scope Focus:** Category D (Reporting & Analysis) & Cryptographic Laboratory Artifact Generation  
**Target Milestone:** V2 Phase 1 (Research)  
**Authoritative References:** [V2_INTENT.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md) | [RESEARCH_A_MENU_UX.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_A_MENU_UX.md) | [RESEARCH_B_KEY_MANAGEMENT.MD](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_B_KEY_MANAGEMENT.MD) | [RESEARCH_C_BATCH_OPERATIONS.MD](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_C_BATCH_OPERATIONS.MD)

---

> [!NOTE]
> **Research Scope Note:** Candidate workflows, HTML templates, CSS strategies, image embedding pipelines, report metadata schemas, failure recovery policies, and candidate recommendations in this report are research findings and candidate approaches only. They are NOT frozen V2 decisions and may be changed, refined, combined, or rejected during the V2 Project-Specific Selection phase. Implementation details are not being finalized in this document.

---

## 1. Research Objective

This research report investigates the architectural, presentation, cryptographic, filesystem, security, and user-experience aspects of **Category D: Reporting & Analysis** for the V2 usability layer of the Cryptography Testing Lab.

The central research objective is to resolve:

> **How should V2 generate standalone, self-contained, human-readable HTML reports that synthesize benchmark performance metrics, security evaluation results, and graphical visualizations — while strictly preserving the frozen V1 single-file/single-buffer core, adhering to the zero-new-dependency constraint, maintaining cross-platform portability on Windows and POSIX, and ensuring safety against local HTML/XSS injection?**

In V1, analytical output is divided across terminal tables and raw disk artifacts:
* Benchmark performance metrics are displayed on the terminal via `tabulate` and optionally saved as raw CSV files (`benchmark_summary_*.csv` and `benchmark_raw_*.csv`).
* Performance graphs are generated and saved as individual PNG files (`key_size_comparison_*.png`, `mode_comparison_*.png`, `throughput_analysis_*.png`).
* Security evaluations are printed to standard output and optionally saved as a raw JSON file (`security_report_*_*.json`).

Currently, there is no single, unified document that combines statistical metrics, high-resolution figures, experimental methodology, and security diagnostics in a consolidated view.

This report establishes the technical foundation for candidate HTML report generation in V2, exploring:
1. Standard library HTML generation mechanisms and escaping boundaries.
2. In-memory `matplotlib` rendering and base64 Data URI embedding.
3. Content structure for benchmark analysis, security evaluation, and batch operation summaries.
4. CSS styling strategies for portable, responsive, and print-friendly documents.
5. Cross-platform auto-open mechanisms and Windows filesystem realities.

---

## 2. V1 Context and Existing Reporting Artifacts

An audit of the frozen V1 codebase establishes the exact data sources, metric schemas, figure generation pipelines, and persistence mechanisms available for V2 reporting:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          V1 ANALYTICAL PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Benchmark Data Pipeline:                                                   │
│  • BenchmarkService -> MetricCollector -> pd.DataFrame                     │
│  • MetricCollector.get_summary_dataframe() [16 statistical columns]         │
│  • MetricCollector.get_raw_dataframe() [7 iteration-level columns]           │
│  • GraphGenerator.generate_key_size_comparison() -> plt.Figure              │
│  • GraphGenerator.generate_mode_comparison() -> plt.Figure                  │
│  • GraphGenerator.generate_throughput_analysis() -> plt.Figure              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Security Evaluation Pipeline:                                              │
│  • SecurityService -> SecurityEvaluator                                     │
│  • SecurityEvaluator.calculate_avalanche_effect() -> float (%)              │
│  • SecurityEvaluator.test_key_sensitivity() -> float (%)                    │
│  • SecurityEvaluator.test_ecb_weakness() -> dict (header, pixel, ciphertexts)│
│  • SecurityEvaluator.generate_test_report() -> markdown str                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  V1 CLI Persistence Handlers:                                               │
│  • commands._save_benchmark_graphs() -> saves PNGs via FileHandler          │
│  • commands._build_security_report() -> serializes JSON with base64 binary  │
│  • FileHandler.write_text() -> writes UTF-8 text with mkdir parents         │
│  • main.py -> configures matplotlib.use("Agg") (headless rendering)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Repository Evidence and Line References

1. **`src/analyzers/metric_collector.py` ([`MetricCollector`](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/metric_collector.py#L5-L203)):**
   * Stores raw iteration times and calculates statistical aggregates ([lines 67–93](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/metric_collector.py#L67-L93)).
   * **Frozen V1 Benchmark Methodology:** Calculates mean, median, sample standard deviation ($ddof=1$), $Q_1$, $Q_3$, IQR ($Q_3 - Q_1$), Tukey fences ($Q_1 - 1.5 \times \text{IQR}$, $Q_3 + 1.5 \times \text{IQR}$), outlier counts via strict inequality, and throughput in binary megabytes per second ($\text{MB} = 1,048,576\text{ bytes}$) based on raw mean time.
   * Summary schema ([lines 140–146](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/metric_collector.py#L140-L146)): `algorithm`, `key_size`, `mode`, `data_size_bytes`, `count`, `mean_time_ms`, `median_time_ms`, `std_dev_time_ms`, `min_time_ms`, `max_time_ms`, `q1_ms`, `q3_ms`, `iqr_ms`, `outlier_count`, `throughput_mb_s`, `memory_delta_mb`.
   * Enforces persistence separation: `export_to_csv()` explicitly raises `NotImplementedError` ([lines 164–171](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/metric_collector.py#L164-L171)), delegating all file writing to presentation/persistence layers.
2. **`src/analyzers/graph_generator.py` ([`GraphGenerator`](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/graph_generator.py#L5-L147)):**
   * Static methods returning `matplotlib.pyplot.Figure` instances: `generate_key_size_comparison()` ([L9](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/graph_generator.py#L9)), `generate_mode_comparison()` ([L61](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/graph_generator.py#L61)), `generate_throughput_analysis()` ([L112](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/graph_generator.py#L112)).
   * Requires specific summary DataFrame columns and raises `ValueError` if required columns are missing or if multiple data sizes are passed to key-size/mode comparisons.
3. **`src/analyzers/security_evaluator.py` ([`SecurityEvaluator`](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/security_evaluator.py#L1-L165)):**
   * Computes exact Hamming distances ([L7–16](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/security_evaluator.py#L7-L16)), avalanche effect percentage ([L19–45](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/security_evaluator.py#L19-L45)), key sensitivity percentage ([L47–72](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/security_evaluator.py#L47-L72)), and BMP pixel-level ECB vs. CBC structural patterns ([L74–148](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/security_evaluator.py#L74-L148)).
4. **`src/cli/commands.py` ([`commands.py`](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L92-L158)):**
   * `_save_benchmark_graphs()` ([L92–117](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L92-L117)): Implements the frozen Selection §39 rule (filtering to smallest payload size for comparison charts), saves PNG files, and calls `plt.close(fig)`.
   * `_build_security_report()` ([L128–158](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L128-L158)): Encodes binary image fields (`original_header`, `original_pixel_data`, `ecb_ciphertext`, `cbc_ciphertext`, `bmp_trailing_data`) to ASCII base64 for JSON serialization.
5. **`src/cli/main.py` ([`main.py`](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L13)):**
   * Configures Matplotlib with the non-interactive `Agg` backend before CLI imports (`matplotlib.use("Agg")` at [L13](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L13)), supporting headless rendering in the CLI environment.
6. **`src/utils/file_handler.py` ([`FileHandler`](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L41-L105)):**
   * `write_text(path, text, encoding="utf-8")` ([L41–46](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L41-L46)) and `ensure_directory(path)` ([L101–104](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L101-L104)) provide robust filesystem primitives.

---

## 3. V2 Intent Requirements (Category D)

As specified in the authoritative [V2_INTENT.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md) (§5.4), Category D consists of four cohesive functional capabilities:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CATEGORY D: REPORTING SCOPE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  [D1] Consolidated Benchmark Reports                                        │
│       • Unified presentation of throughput, memory utilization, and latency │
│         across key sizes and modes.                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  [D2] Standalone HTML Report Generation                                     │
│       • Generate self-contained, styled HTML reports combining summary      │
│         tables, metrics, and embedded visual graphs.                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  [D3] Comparative Security Visualizations                                   │
│       • Clear side-by-side comparative reporting of ECB pattern leakage vs. │
│         CBC diffusion (e.g., bitmap analysis, entropy scores).              │
├─────────────────────────────────────────────────────────────────────────────┤
│  [D4] Auto-Open in Browser                                                  │
│       • Option to automatically launch generated HTML reports in the        │
│         default web browser upon completion.                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Research Methodology

The research in this report is based on:
1. **Codebase & Artifact Analysis:** Audited metric schemas, graph generation interfaces, and report dictionaries in `MetricCollector`, `GraphGenerator`, `SecurityEvaluator`, and `commands.py`.
2. **Standard Library Templating & Escaping:** Evaluated `string.Template`, `html.escape`, `f-strings`, and standard string concatenation against XSS safety, readability, performance, and maintenance.
3. **In-Memory Matplotlib Pipeline:** Evaluated figure saving to `io.BytesIO()`, base64 encoding to Data URIs, memory lifecycle (`plt.close()`), and rendering quality.
4. **CSS & HTML Semantic Design:** Evaluated CSS layouts (internal `<style>`, CSS reset, responsive flexbox/grid, print media queries) and semantic HTML5 markup (`<header>`, `<main>`, `<section>`, `<figure>`, `<table>`).
5. **Security & Injection Threat Modeling:** Analyzed potential injection vectors (hostile filenames, corrupted metadata, unescaped error messages, unescaped tags) and established sanitization rules.
6. **Industry Patterns Comparison:** Analyzed single-file HTML report architectures from tools like `pytest-html`, `Sphinx`, and `Jupyter/nbconvert`.
7. **Cross-Platform & Windows Filesystem Analysis:** Evaluated UTF-8 encoding enforcement, `file://` URI resolution, Windows path handling, default browser dispatching (`webbrowser.open()`), and headless environment fallbacks.

---

## 5. HTML Generation Findings

### 5.1 Standard Library Templating Options Evaluated

Under the zero-new-dependency constraint of V2, external templating engines such as `Jinja2`, `Mako`, or `Chameleon` are not permitted. The report generator must rely on the Python standard library.

| Approach | Readability & Structure | Dynamic Escaping Safety | Loops & Table Generation | Maintenance Overhead | Dependency Compliance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`string.Template`** | High (clean `$placeholder` tags) | Requires explicit pre-escaping | Not designed for inner loops; requires helper composition | Low (clear document skeleton) | Standard library |
| **`f-strings`** | High (inline Python expressions) | Requires explicit wrapping with `html.escape()` | Practical for row-by-row list comprehensions | Moderate (can become cluttered if deeply nested) | Standard library |
| **Direct String Assembly (`+` / `join`)** | Low (fragmented string parts) | Requires manual per-fragment escaping | Verbose; requires manual buffering | High (error-prone concatenation) | Standard library |
| **Programmatic DOM / ElementTree** | Low (verbose Python AST calls) | Automatic text node escaping | Heavy code footprint for static HTML boilerplate | Very High (unwieldy for complex CSS/HTML) | Standard library |

#### Technical Note on `xml.etree.ElementTree`
`xml.etree.ElementTree` is designed for XML-oriented serialization rather than direct HTML5 authoring. Using it for HTML5 generation introduces subtleties such as XML self-closing tags (`<div />` instead of `<div></div>`, which can break browser rendering), namespace declarations, and differing void-element rules (e.g., `<meta>`, `<img>`, `<br>`). It is evaluated as a potential candidate approach but is not preferred over textual templating.

### 5.2 Templating vs. Escaping Boundary

> [!IMPORTANT]
> `string.Template` is purely a textual substitution mechanism; it does **NOT** perform HTML escaping or sanitization. Furthermore, `Template.substitute()` raises `KeyError` when a placeholder is missing, whereas `Template.safe_substitute()` leaves unreplaced placeholders in place without raising an exception.
> 
> A candidate architecture is to separate trusted template structure from dynamic data escaping:
> 1. All dynamic input variables (filenames, algorithm names, error messages, user strings) pass through `html.escape(str(v), quote=True)` prior to template substitution.
> 2. Trusted structural fragments (e.g., pre-rendered sanitized table rows or base64 Data URIs) are assembled and injected into higher-level template slots.

### 5.3 Candidate Hybrid Generation Model

A hybrid approach provides a clean separation of concerns:
* `string.Template` defines the macro-level document skeleton (`BASE_HTML_TEMPLATE`) with placeholders like `$metadata_section`, `$benchmark_section`, `$security_section`, `$embedded_css`.
* Helper functions using `f-strings` construct micro-level elements (e.g., table `<tr>` rows, progress bars, figure cards), applying `html.escape()` to dynamic values.

```python
# Illustrative candidate pattern (conceptual only)
import html
from string import Template

def render_table_row(label: str, value: float) -> str:
    safe_label = html.escape(label, quote=True)
    safe_val = html.escape(f"{value:.2f}", quote=True)
    return f"<tr><td>{safe_label}</td><td class='num'>{safe_val}</td></tr>"
```

---

## 6. HTML Document Structure Findings

### 6.1 Semantic Markup and Accessibility

To support clean visual presentation, printing, and screen-reader accessibility, candidate HTML reports can utilize HTML5 semantic tags:
* `<header>`: Contains document title, laboratory context, execution timestamp, and environment metadata.
* `<main>`: Houses the primary analytical sections:
  * `<section id="benchmark-analysis">`: Summary statistics tables and performance figures.
  * `<section id="security-evaluation">`: Avalanche effect, key sensitivity, and structural ECB/CBC comparisons.
  * `<section id="methodology-notes">`: Documentation of warmup counts, sample iterations, Tukey outlier fences, and throughput formulas.
* `<figure>` and `<figcaption>`: Wrap embedded charts with clear descriptive captions.
* `<table>`, `<thead>`, `<tbody>`: Structure tabular data with explicit numerical column alignment.
* `<footer>`: Generation timestamp, software version, and confidential laboratory disclaimer.

### 6.2 Concrete Illustrative HTML Skeleton

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cryptography Laboratory Report - $session_id</title>
    <style>
        /* CSS block injected here */
    </style>
</head>
<body>
    <header class="report-header">
        <h1>Cryptography Testing Lab — Analytical Report</h1>
        <div class="metadata-grid">
            $metadata_cards
        </div>
    </header>

    <main>
        <section id="benchmark-section" class="report-section">
            <h2>1. Performance Benchmark Analysis</h2>
            <div class="table-container">
                $benchmark_table
            </div>
            <div class="charts-grid">
                $benchmark_figures
            </div>
        </section>

        <section id="security-section" class="report-section">
            <h2>2. Cryptographic Security Evaluation</h2>
            <div class="security-metrics-grid">
                $security_cards
            </div>
            <div class="comparison-table-container">
                $ecb_cbc_comparison_table
            </div>
        </section>

        <section id="methodology-section" class="report-section">
            <h2>3. Experimental Methodology & Invariants</h2>
            $methodology_notes
        </section>
    </main>

    <footer class="report-footer">
        <p>Generated by Cryptography Testing Lab V2 | Session: $session_id</p>
    </footer>
</body>
</html>
```

#### Template Placeholder and `$` Character Interaction
In `string.Template`, the `$` character signals variable substitution (e.g., `$session_id`, `$$` for literal `$`). In HTML/CSS templates:
* CSS stylesheets frequently use `{}` curly braces (which do not conflict with `string.Template` unless using `${identifier}` syntax).
* If raw text or CSS rules contain literal `$` characters, they require `$$` escaping or block substitution before/after template processing.

---

## 7. CSS Strategy Findings

### 7.1 CSS Delivery Models Evaluated

| Strategy | Single-File Portability | Maintenance & Cleanliness | Print & Offline Fidelity | Dependency Compliance | Selection Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **External Stylesheet (`<link>`)** | Poor (breaks if HTML is moved or emailed) | High (isolated `.css` file) | Poor (requires local CSS file) | Standard library | Not preferred for standalone reports |
| **Internal Stylesheet (`<style>`)** | High (self-contained document) | High (clean CSS block in Python constant) | High (available offline) | Standard library | **Recommended Candidate** |
| **Inline Styles (`style="..."`)** | High (self-contained document) | Poor (repetitive, harder to maintain) | Moderate | Standard library | Not preferred |
| **External CDN Framework** | Poor (fails completely offline) | High | Poor (fails without network) | Fails zero-dep & offline intent | Rejected |

### 7.2 Styling Architecture & Print Support

* **Candidate approach:** Embed CSS directly inside an internal `<style>` block in the HTML document.
  * *Trade-offs:* Embedded CSS improves report self-containment and offline viewing, but increases repeated document payload across multiple generated reports and couples report appearance to the embedded stylesheet.
* **Layout Design:** Modern CSS Grid and Flexbox provide multi-column metric cards and side-by-side figure rendering without heavy frameworks.
* **Typography:** System font stack (`system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`) eliminates external font dependencies.
* **Print Media Query (`@media print`):** Candidate styling can suppress navigation, force clean white backgrounds, avoid breaking table rows across pages (`page-break-inside: avoid;`), and size figures for standard paper widths (A4 / Letter).

---

## 8. Graph Embedding Findings

### 8.1 Comparison of Image Embedding Approaches

| Approach | Portability | Implementation Complexity | Matplotlib Compatibility | Payload Overhead | Selection Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Embedded Base64 Data URI** | High (single file) | Low (in-memory buffer + base64) | Native (`fig.savefig(buf, format='png')`) | $+33\%$ vs raw binary (derived from Base64 4:3 ratio) | **Recommended Candidate** |
| **Linked PNG Files (`<img src="...">`)** | Poor (multi-file directory) | Low (writes PNGs to disk) | Native | $0\%$ | Candidate Alternative |
| **Inline SVG (`<svg>...</svg>`)** | High (single file) | Moderate (SVG XML injection) | Native (`format='svg'`) | Variable (text-based) | Candidate Alternative |
| **External Charting Library (JS/CDN)**| Poor (requires network/JS) | High (reimplements charting logic) | N/A (reimplements charts) | Low | Rejected (zero-dependency) |

### 8.2 Base64 Data URI Pattern

HTML natively supports inline images using the `data:` URI scheme (RFC 2397):
```html
<figure class="chart-card">
    <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA..." alt="Key Size Comparison Chart">
    <figcaption>Figure 1: AES Performance comparison across key sizes (128, 192, 256 bits).</figcaption>
</figure>
```

---

## 9. Matplotlib In-Memory PNG Findings

### 9.1 The In-Memory Rendering Pipeline

V1 configures Matplotlib with the non-interactive `Agg` backend before CLI imports (`matplotlib.use("Agg")` in `src/cli/main.py` [L13](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L13)), supporting headless rendering in the CLI environment.

To embed figures without intermediate disk files, a candidate reporting pipeline is:
1. `GraphGenerator` generates a `plt.Figure` object.
2. Save figure to an in-memory byte buffer: `io.BytesIO()`.
3. Encode bytes to ASCII base64: `base64.b64encode(buf.getvalue()).decode("ascii")`.
4. Construct the Data URI string: `f"data:image/png;base64,{b64_data}"`.
5. Explicitly call `plt.close(fig)` to free figure memory resources.

```python
# Illustrative candidate pipeline (conceptual only)
import io
import base64
import matplotlib.pyplot as plt

def figure_to_base64_uri(fig: plt.Figure, dpi: int = 150) -> str:
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
        buf.seek(0)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    finally:
        buf.close()
        plt.close(fig)  # Prevents figure retention across multiple graphs
```

---

## 10. Benchmark Report Content Findings

### 10.1 MetricCollector Schema and Frozen Methodology

The V1 benchmark engine produces statistical metrics via `MetricCollector.get_summary_dataframe()` ([`metric_collector.py` L140–146](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/metric_collector.py#L140-L146)):

* **Frozen V1 Benchmark Methodology:**
  * 5 unmeasured warmup iterations (to stabilize CPU caches and runtime compilation).
  * 30 measured sample iterations per configuration.
  * Outliers flagged using Tukey fences ($1.5 \times \text{IQR}$) with strict inequalities.
  * Primary statistical metrics (mean, median, standard deviation) retain all 30 observations (outliers are flagged but not discarded).
  * Throughput is calculated using binary megabytes: $\text{MB} = 1,048,576\text{ bytes}$ ($\text{Throughput} = (\text{bytes} / 1048576.0) / (\text{mean\_ms} / 1000.0)$).

### 10.2 Illustrative Benchmark Summary Table Layout

```text
====================================================================================================
Configuration         Payload     Mean (ms)  Median (ms)  Std Dev (ms)  Outliers  Throughput (MB/s)
====================================================================================================
AES-128-CBC          1.00 MB        12.45        12.30          0.45         1              80.32
AES-192-CBC          1.00 MB        14.80        14.65          0.52         0              67.57
AES-256-CBC          1.00 MB        17.10        16.95          0.61         2              58.48
====================================================================================================
(Illustrative layout — not a measured project result)
```

---

## 11. Security Report Content Findings

### 11.1 SecurityEvaluator Output Integration

The V1 security evaluation suite evaluates three core cryptographic metrics ([`security_evaluator.py` L19–148](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/security_evaluator.py#L19-L148)):

1. **Avalanche Effect (Plaintext Diffusion):**
   * Measures the percentage of ciphertext bits that flip when exactly 1 bit of plaintext is inverted.
   * Ideal theoretical value: $50.0\%$.
2. **Key Sensitivity (Key Diffusion):**
   * Measures the percentage of ciphertext bits that flip when exactly 1 bit of the cryptographic key is inverted.
   * Ideal theoretical value: $50.0\%$.
3. **ECB vs. CBC Structural Weakness Demonstration:**
   * Encrypts an uncompressed 24-bpp BMP pixel buffer using ECB and CBC modes.
   * In ECB mode, identical plaintext blocks produce identical ciphertext blocks, preserving visual shapes.
   * In CBC mode, ciphertext chaining eliminates structural block redundancy.

### 11.2 Precision on Cryptographic Properties

> [!WARNING]
> Reports must maintain strict cryptographic precision:
> * AES-CBC provides **confidentiality** and eliminates ECB structural pattern leaks when used with an unpredictable, unique IV.
> * AES-CBC does **NOT** provide data authentication, integrity verification, or tamper resistance.
> * The report must not describe AES-CBC as authenticated encryption.

### 11.3 Illustrative ECB vs. CBC Comparison Table

Under V1 default parameters (`src/cli/argument_parser.py` [lines 270–280](file:///C:/Users/kodal/Cryptography_Project/src/cli/argument_parser.py#L270-L280)), the security suite constructs a 64×64 24-bpp BMP:
* Header: 54 bytes (14-byte file header + 40-byte DIB header).
* Pixel data: $64 \times 3 = 192\text{ bytes/row} \times 64\text{ rows} = 12,288\text{ bytes}$.
* Padded ciphertext: PKCS#7 pads 12,288 bytes to 12,304 bytes ($12,288 + 16$).

```text
====================================================================================================
Metric / Attribute                AES-256-ECB                    AES-256-CBC
====================================================================================================
BMP Header Size                   54 bytes                       54 bytes
Pixel Data Plaintext Size         12,288 bytes                   12,288 bytes
Padded Ciphertext Size            12,304 bytes                   12,304 bytes
Initialization Vector (IV)        None (Not supported)           16 bytes (Random unique)
Structural Pattern Leakage        Observed (Repeated blocks)     Masked (Chaining eliminates patterns)
====================================================================================================
(Derived from V1 default 64x64 24-bpp BMP parameters)
```

---

## 12. ECB / Image Visualization Findings

### 12.1 Numerical Data vs. Pixel Image Rendering

* V1's `SecurityEvaluator.test_ecb_weakness()` returns raw bytes for `original_header`, `original_pixel_data`, `ecb_ciphertext`, `cbc_ciphertext`, and `bmp_trailing_data` ([`security_evaluator.py` L141–147](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/security_evaluator.py#L141-L147)).
* In V1 CLI (`src/cli/commands.py` [L119–158](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L119-L158)), these bytes are base64-encoded and written to JSON.

#### Evaluated Visualization Alternatives
* **Candidate Option A (Direct BMP Data URI):** Combine the 54-byte BMP header with encrypted pixel data and embed as `<img src="data:image/bmp;base64,...">`. Most modern desktop browsers (Edge, Chrome, Firefox) render uncompressed BMP Data URIs natively.
* **Candidate Option B (Matplotlib Pixel Heatmap):** Reshape pixel bytes into a 2D array and render via `matplotlib.pyplot.imshow()`, embedding the resulting figure as a PNG Data URI.
* **Candidate Option C (Numerical Comparison Table):** Display ciphertext byte sizes, block collision counts, and entropy metrics in a structured table without rendering image tags.

*Selection Note:* Choosing between Candidate Option A, B, or C is an **Open Decision (D-OPEN-05)** for the Selection phase.

---

## 13. Combined vs. Separate Reports

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       REPORT PACKAGING MODELS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Model A: Single Combined Report (Candidate Recommendation D-05)            │
│  • Generates a single report.html containing Benchmark + Security sections. │
│  • Advantages: One file to manage/open/share; consolidated laboratory       │
│    profile in one document.                                                 │
│  • Trade-offs: Requires handling partial data if only benchmark or security │
│    suite was executed.                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Model B: Strictly Separate Reports                                         │
│  • Generates benchmark_report.html and security_report.html independently.  │
│  • Advantages: Single-purpose output files.                                 │
│  • Trade-offs: Multiplies report files; user must manage two artifacts.     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Model C: Combined Default with Specialized CLI Options                     │
│  • Defaults to single combined report; provides options for specialized     │
│    sub-reports if requested.                                                │
│  • Advantages: Flexibility across different testing workflows.              │
│  • Trade-offs: Requires additional CLI argument handling.                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

* *Selection Note:* Choosing between Model A, B, or C remains an **Open Decision (D-OPEN-01)**.

---

## 14. Report Metadata Findings

### 14.1 Metadata Classification

To support laboratory reproducibility while maintaining security boundaries, report metadata is classified into three tiers:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          REPORT METADATA TIERS                              │
├───────────────────┬─────────────────────────────────────────────────────────┤
│ Tier              │ Fields & Parameters                                     │
├───────────────────┼─────────────────────────────────────────────────────────┤
│ [Required]        │ • Generation Timestamp (ISO-8601 & Local)               │
│                   │ • Session ID (matching MetricCollector.session_id)      │
│                   │ • Cryptographic Configurations Tested (Algorithm, Modes)│
│                   │ • Report Format Version (e.g., "V2-HTML-1.0")           │
├───────────────────┼─────────────────────────────────────────────────────────┤
│ [Recommended]     │ • Python Runtime Version (sys.version)                  │
│                   │ • Platform / OS Details (platform.platform())           │
│                   │ • Experimental Parameters (Warmups: 5, Samples: 30)     │
│                   │ • Matplotlib Version & Backend (Agg)                    │
├───────────────────┼─────────────────────────────────────────────────────────┤
│ [Optional]        │ • Host Machine Hardware Summary (CPU model, Cores)      │
│                   │ • Total Elapsed Session Time                            │
├───────────────────┼─────────────────────────────────────────────────────────┤
│ [STRICTLY         │ • Raw Encryption Keys / Generated Hex Keys              │
│  PROHIBITED]      │ • Plaintext Data Payloads                               │
│                   │ • Passwords / Passphrases                               │
└───────────────────┴─────────────────────────────────────────────────────────┘
```

---

## 15. Auto-Open Behavior Findings

### 15.1 Browser Launch Mechanisms

* Python's standard library `webbrowser.open(url, new=2)` provides cross-platform URL launching.
* **Path Conversion:** On Windows and POSIX, local file paths can be converted to valid `file://` URIs:
  ```python
  uri = pathlib.Path(report_path).resolve().as_uri()
  success = webbrowser.open(uri)
  ```
* **Failure Modes & Fallbacks:**
  * In headless Linux environments or Windows Server Core without a GUI browser, `webbrowser.open()` may return `False` or fail silently.
  * *Candidate Handling:* If browser launch returns `False` or raises an exception, the CLI displays the absolute file path in the terminal and continues without crashing:
    ```text
    Saved HTML Report: C:\Lab\results\reports\cryptography_report_20260915_153000.html
    (Unable to launch browser automatically; open the file above manually)
    ```

---

## 16. Filename and Directory Strategy

### 16.1 Destination Path & Collision Safety

* **Candidate Output Location:** `results/reports/` (created on demand via `FileHandler.ensure_directory()`).
* **Candidate Filename Strategy:** `cryptography_report_YYYYMMDD_HHMMSS.html`
  * Helps prevent accidental overwrites of prior runs.
  * Uses filesystem-safe characters (`_` instead of `:`).
* **Collision Fallback:** If a report with the same timestamp exists, append an incremental counter (`_1.html`, `_2.html`).

---

## 17. Report Regeneration Findings

### 17.1 Existing V1 Capability vs. Potential V2 Workflows

* **Existing V1 Capability:** V1 saves raw benchmark CSV files (`benchmark_summary_*.csv`, `benchmark_raw_*.csv`) and security JSON files (`security_report_*.json`). V1 does not have a report regeneration command.
* **Potential V2 Regeneration Workflow (Candidate):**
  ```text
  Illustrative future V2 CLI entry point — not implemented:
  python -m src.cli_v2.main_v2 report --from-csv results/benchmarks/summary.csv
  ```
  * *Trade-offs:* Reconstructing HTML reports from saved CSV/JSON requires parsing schemas, reconstructing DataFrames, and re-invoking `GraphGenerator`.
* *Selection Note:* Limiting report generation to active in-memory session data vs. supporting offline regeneration from disk remains an **Open Decision (D-OPEN-06)**.

---

## 18. Report Templating Architecture

### 18.1 Architecture Models Evaluated

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TEMPLATING ARCHITECTURES EVALUATED                      │
├───────────────────┬──────────────┬──────────────────┬───────────────────────┤
│ Architecture Model│ Complexity   │ Zero-Dep Status  │ Safety & Maintainability│
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 1: Monolithic│ Low          │ Full (stdlib)    │ Poor (fragmented      │
│   String Concat   │              │                  │ string concatenation) │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 2: string.  │ Moderate     │ Full (stdlib)    │ High (clean separation│
│   Template +      │              │                  │ of macro skeleton and │
│   Helper Functions│              │                  │ sanitized components) │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 3: External │ Moderate     │ Full (stdlib)    │ Moderate (requires    │
│   HTML Files      │              │                  │ package resource I/O) │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 4: Jinja2   │ Low (in code)│ Fails (Third-    │ High (standard engine │
│   Engine          │              │ party package)   │ but forbidden by zero-│
│                   │              │                  │ dependency rule)      │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 5: Program- │ Very High    │ Full (stdlib)    │ Poor (unwieldy for    │
│   matic AST / DOM │              │                  │ modern HTML5/CSS)     │
└───────────────────┴──────────────┴──────────────────┴───────────────────────┘
```

* *Candidate Recommendation:* Model 2 (`string.Template` + helper functions) provides a practical balance of zero-dependency compliance, code readability, and security.

---

## 19. HTML Escaping and Injection Safety

### 19.1 Threat Model for Local HTML Reports

Even in offline desktop applications, generating HTML from unvalidated inputs introduces local Cross-Site Scripting (XSS) and layout corruption risks:
* Hostile or malformed filenames (e.g., `<script>alert("xss")</script>.txt`).
* Unescaped error messages containing `<` or `&` characters.
* Custom user labels, benchmark payload identifiers, or directory path strings.

### 19.2 Sanitization Rules and Limitations

1. **Text Node and Attribute Escaping:** Apply `html.escape(str(value), quote=True)` to every dynamic string injected into HTML text nodes and attribute values.
2. **Quoted Attribute Values:** Ensure all HTML attributes are strictly quoted (e.g., `class="value"`, `id="value"`).
3. **Data URI Structure:** Ensure Data URIs strictly follow `data:image/png;base64,[A-Za-z0-9+/=]+` without dynamic interpolation of unvalidated parameters.
4. **Security Boundary:** While `html.escape()` reduces the risk of HTML injection/XSS through addressed surfaces, complete safety also requires careful handling of URL schemes and DOM structures.

```python
# Illustrative escaping validation
import html

hostile_input = '<script>alert("xss")</script>'
safe_output = html.escape(hostile_input, quote=True)
# Result: &lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;
```

---

## 20. Report Testing Strategy

### 20.1 Test Coverage Concepts for Category D

```python
# Illustrative test concept — not an existing project test

def test_candidate_report_generation_basic(tmp_path):
    """Verify HTML report is created with valid DOCTYPE and UTF-8 encoding."""
    # 1. Provide mock summary DataFrame and security results.
    # 2. Generate report to tmp_path / "report.html".
    # 3. Assert file exists and starts with <!DOCTYPE html>.
    # 4. Assert <meta charset="UTF-8"> is present.

def test_candidate_report_graph_embedding(tmp_path):
    """Verify matplotlib figures are embedded as base64 Data URIs."""
    # 1. Generate report with benchmark figures.
    # 2. Assert 'data:image/png;base64,' appears in the HTML text.
    # 3. Assert no external .png references are present.

def test_candidate_html_escaping_hostile_input(tmp_path):
    """Verify malicious/special characters in metadata and errors are escaped."""
    # 1. Inject '<script>alert(1)</script>' in algorithm/file label.
    # 2. Generate report.
    # 3. Assert '&lt;script&gt;' exists in HTML and '<script>' does not.

def test_candidate_empty_data_resilience(tmp_path):
    """Verify report generates gracefully when benchmark or security data is empty."""
    # 1. Pass empty DataFrame / empty security dict.
    # 2. Assert report is generated with fallback notice ("No data recorded").
```

---

## 21. Multi-Report Comparison Findings

### 21.1 Multi-Run Analysis

* **Single-Session Multi-Config (Supported in V1):** V1 natively benchmarks multiple key sizes, modes, and payload sizes in a single run; this data is rendered in standard benchmark tables and charts.
* **Historical Multi-Report Comparison (Deferred Candidate):** Parsing multiple previous CSV files to render side-by-side historical regression charts across sessions.
* *Selection Assessment:* Single-session multi-config presentation is included; historical cross-session regression comparison is evaluated and deferred to Post-V2.

---

## 22. Windows-Specific Considerations

1. **UTF-8 Encoding on NTFS:** `FileHandler.write_text()` explicitly enforces `encoding="utf-8"` ([`file_handler.py` L41–46](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L41-L46)), preventing Windows default code page corruption on mathematical symbols ($\Delta$, $\mu$, $\sigma$, $\pm$).
2. **Windows Drive-Letter URIs:** `pathlib.Path.resolve().as_uri()` produces `file:///C:/...` URIs accepted by Edge, Chrome, and Firefox on Windows.
3. **Spaces in Paths:** `as_uri()` URL-encodes spaces (e.g., `C:\Program Files\` -> `file:///C:/Program%20Files/`).
4. **Browser Association Fallback:** If `webbrowser.open()` encounters an unassociated file handler or headless mode, it fails safely without application crash.

---

## 23. Interaction with Reports A, B, and C

* **Report A (Menu UX):** 
  * Menu summary cards can display report generation status.
  * Menu wizards can offer an option to open the HTML report in a browser upon completion.
* **Report B (Key Management):**
  * Report metadata includes key sizes and algorithms tested.
  * **Candidate Security Rule:** Unencrypted `.key` files and raw key hex strings are strictly excluded from HTML reports.
* **Report C (Batch Operations):**
  * Batch summary reports can include aggregate file counts, total bytes, and throughput.
  * *Candidate approach:* To prevent large HTML file sizes, raw batch logs are not embedded in full; the report includes summary tables and references the companion `batch_log_*.csv`.
  * *Trade-off:* Referencing external companion CSVs reduces single-file portability for batch reports, while embedding full logs could produce large HTML documents.

---

## 24. Alternative Output Formats Compared

| Format | Human Readability | Single-File Portability | Embedded Figures | Machine-Readable | Dependency Compliance | Print Fidelity | V2 Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **HTML** | High | High (with embedded Data URIs) | Native Data URI | Moderate | Full (stdlib) | High (with `@media print`) | **Recommended Candidate** |
| **Markdown** | High | Variable (depends on packager) | Renderer-dependent | Moderate | Full (stdlib) | Moderate | Candidate Complement |
| **PDF** | High | High (Single file) | Native | Poor | Fails (Requires third-party libs) | High | Deferred (Post-V2) |
| **JSON** | Poor | High | Base64 strings | High | Full (stdlib) | Poor | Existing V1 Format |
| **CSV** | Moderate | High | None | High | Full (stdlib) | Poor | Existing V1 Format |
| **Console** | High | N/A | Terminal characters only | Poor | Full (stdlib) | Poor | Existing V1 Format |

---

## 25. Industry Comparison

| Tool / Pattern | Observed Industry Pattern | Source / Reference | Advantages | Limitations | Candidate Lesson for V2 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **pytest-html** | Generates standalone single-file HTML reports with inline CSS and base64 embedded assets. | `pytest-html` documentation / source | High portability; zero runtime server; easily shareable. | Large files when many images are embedded. | Demonstrates that single-file HTML with base64 Data URIs is a practical pattern for test reporting. |
| **Sphinx** | Generates multi-file documentation sites with external CSS/JS and linked media. | Sphinx documentation engine | Rich cross-referencing and modular theme support. | Multi-file directory breaks if single HTML is moved. | Confirms that multi-file static sites create distribution friction for simple laboratory reports. |
| **Jupyter nbconvert** | Converts notebooks to standalone HTML with embedded base64 Matplotlib charts. | `nbconvert` HTML exporter documentation | Consolidated presentation of text, tables, and charts in one document. | Uses heavy Jinja2 templating engine. | Validates the in-memory `BytesIO` -> base64 Data URI Matplotlib pipeline. |

---

## 26. Alternative Architectures Evaluated

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURAL MODELS COMPARISON                          │
├───────────────────┬──────────────┬──────────────────┬───────────────────────┤
│ Architecture Model│ Complexity   │ Portability      │ Zero-Dep Compliance   │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 1: Monolithic│ Low          │ High (single     │ Full (stdlib only)    │
│   String Concaten-│              │ file)            │                       │
│   ation           │              │                  │                       │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 2: string.  │ Moderate     │ High (single     │ Full (stdlib only)    │
│   Template +      │              │ file)            │                       │
│   Sanitized Helper│              │                  │                       │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 3: HTML with│ Low          │ Poor (requires   │ Full (stdlib only)    │
│   Linked PNG Files│              │ folder of PNGs)  │                       │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 4: Jinja2   │ Moderate     │ High (single     │ Fails (requires       │
│   Template Engine │              │ file)            │ external package)     │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model 5: Interme- │ High         │ High (single     │ Full (stdlib only)    │
│   diate Data Model│              │ file)            │                       │
│   + HTML Renderer │              │                  │                       │
└───────────────────┴──────────────┴──────────────────┴───────────────────────┘
```

* **Model 1 (Monolithic String Concatenation):** Low complexity, but high maintenance overhead and risk of escaping mistakes.
* **Model 2 (`string.Template` + Helpers):** **Recommended Candidate** — balances zero-dependency compliance, code readability, and escaping security.
* **Model 3 (HTML with Linked PNG Files):** Simple, but reduces portability when sharing reports across directories or systems.
* **Model 4 (Jinja2):** Fails zero-dependency constraint.
* **Model 5 (Intermediate Data Model + HTML Renderer):** Decouples data structures from HTML rendering, but introduces additional abstraction layers.

---

## 27. Failure-Mode Matrix

| Failure Mode | Detection Point | Impact | Candidate Classification | Candidate Recovery / Handling | Logging / Diagnostics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Empty Summary DataFrame** | Report generator entry | No benchmark metrics | Non-fatal | Render section with fallback notice: "No benchmark metrics recorded." | Log warning to console |
| **Empty Security Results** | Report generator entry | No security metrics | Non-fatal | Render section with fallback notice: "No security evaluation recorded." | Log warning to console |
| **Missing DataFrame Column**| Table row iteration | Incomplete table | Non-fatal | Catch `KeyError`; display `N/A` in table cell | Record warning in report footer |
| **Malformed Numeric Metric**| Float formatting | Format exception | Non-fatal | Display raw string or `NaN` gracefully | Record warning in report footer |
| **Matplotlib Rendering Error**| `fig.savefig()` | Missing chart figure | Non-fatal | Render fallback placeholder: `[Graph unavailable: error]` | Log exception to console |
| **BytesIO Buffer Failure** | Buffer write | Memory exception | Fatal / Per-chart | Fallback to text table; close figures immediately | Console error |
| **Base64 Encoding Failure** | `base64.b64encode()` | Corrupt Data URI | Non-fatal | Omit figure; display error placeholder | Log warning |
| **Template Placeholder Error**| `Template.substitute()`| Missing key | Non-fatal | Ensure thorough key population or evaluate `safe_substitute()` | Log template error |
| **Unescaped Hostile Input** | Variable sanitization | XSS / Layout break | Non-fatal (Sanitized) | Enforce `html.escape(quote=True)` on all dynamic strings | Preventative sanitization |
| **Report Directory Creation** | `FileHandler.ensure_dir`| Cannot create folder| Fatal | Prompt user for writable output directory | Console error |
| **File Write Permission** | `FileHandler.write_text`| Report not saved | Fatal | Catch `PermissionError`; display actionable message | Console error |
| **Disk Space Exhausted** | `FileHandler.write_text`| Truncated HTML file | Fatal | Catch `OSError(ENOSPC)`; clean partial file | Console error |
| **Filename Collision** | Filename generation | Overwrite risk | Non-fatal | Append incremental suffix (`_1.html`) | Inform user in console |
| **UTF-8 Encoding Anomaly** | File write boundary | Corrupted characters | Non-fatal | Explicitly pass `encoding="utf-8"` | Enforced by FileHandler |
| **Browser Not Found** | `webbrowser.open()` | Browser does not open| Non-fatal | Display absolute file path in terminal for manual open | Console notice |
| **Invalid file:// URI** | `Path.resolve().as_uri()`| Malformed link | Non-fatal | Fallback to raw local path display | Console notice |
| **Large Report File Size** | Report assembly | High memory / slow | Non-fatal | Evaluate default figure DPI (e.g., 150 DPI) | Inform user if large |
| **User Interruption (Ctrl+C)**| Report generation loop| Partial report write | Cancellation | Clean incomplete temporary files; exit cleanly with `EXIT_SUCCESS` | Console notice |

---

## 28. Candidate Recommendations

The following candidate recommendations synthesize research findings for evaluation during the V2 Selection phase. All recommendations remain non-frozen:

* **RECOMMENDATION D-01 (NOT YET FROZEN):**  
  * *Recommendation:* Adopt a hybrid HTML generation model combining `string.Template` for macro document skeletons and `f-strings` for sanitized micro-level components.  
  * *Rationale:* Adheres to zero-dependency constraints while maintaining clean code separation.  
  * *Trade-off:* Does not provide the declarative power of Jinja2.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-02 (NOT YET FROZEN):**  
  * *Recommendation:* Enforce `html.escape(str(value), quote=True)` on dynamic parameters, filenames, and error messages injected into HTML reports.  
  * *Rationale:* Reduces the risk of HTML injection/XSS through text-node and attribute-value surfaces.  
  * *Trade-off:* Requires disciplined helper function construction.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-03 (NOT YET FROZEN):**  
  * *Recommendation:* Embed CSS styles within an internal `<style>` block in the HTML `<head>` and include print-specific styling (`@media print`).  
  * *Rationale:* Supports self-contained single-file portability and offline printing without external CSS dependencies.  
  * *Trade-off:* Increases HTML template string size.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-04 (NOT YET FROZEN):**  
  * *Recommendation:* Render `matplotlib.pyplot.Figure` instances to in-memory `io.BytesIO()` buffers, encode as base64 PNG Data URIs, and explicitly call `plt.close(fig)` immediately after encoding.  
  * *Rationale:* Eliminates intermediate disk clutter and prevents figure memory leaks.  
  * *Trade-off:* Increases base64 image data size by approximately 33% relative to raw binary PNGs.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-05 (NOT YET FROZEN):**  
  * *Recommendation:* Default to a unified single-document report (`cryptography_report_*.html`) containing both Benchmark and Security sections with adaptive section visibility.  
  * *Rationale:* Reduces file management friction and presents a consolidated laboratory cryptographic profile.  
  * *Trade-off:* Requires handling partial data when only benchmarks or security suites were executed.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-06 (NOT YET FROZEN):**  
  * *Recommendation:* Save generated reports to `results/reports/` using timestamped naming (`cryptography_report_YYYYMMDD_HHMMSS.html`).  
  * *Rationale:* Isolates human-facing reports from raw CSV/JSON data folders and helps prevent accidental overwrites.  
  * *Trade-off:* Requires occasional directory cleanup for long-running test suites.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-07 (NOT YET FROZEN):**  
  * *Recommendation:* Use `pathlib.Path.resolve().as_uri()` and `webbrowser.open(uri)` for browser launching, providing a graceful terminal fallback if the browser is unavailable.  
  * *Rationale:* Supports cross-platform URL dispatch across Windows and POSIX.  
  * *Trade-off:* Behavior depends on system browser associations.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-08 (NOT YET FROZEN):**  
  * *Recommendation:* Render numerical security metrics (avalanche effect, key sensitivity) using semantic HTML and CSS progress bars alongside exact percentages.  
  * *Rationale:* Provides immediate visual feedback without requiring additional graphical charting libraries.  
  * *Trade-off:* Relies on CSS styling for visual bar widths.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-09 (NOT YET FROZEN):**  
  * *Recommendation:* Document experimental methodology (warmup count: 5, sample iterations: 30, Tukey outlier fences, binary MB definition) in a dedicated methodology section.  
  * *Rationale:* Supports scientific clarity, peer review, and reproducibility.  
  * *Trade-off:* Adds textual volume to the report.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-10 (NOT YET FROZEN):**  
  * *Recommendation:* Strictly exclude raw encryption keys, hex key strings, and plaintext payloads from HTML report generation and metadata blocks.  
  * *Rationale:* Protects cryptographic secrets from unintended leakage in shared reports.  
  * *Trade-off:* Debugging requires inspecting error messages rather than raw keys in reports.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-11 (NOT YET FROZEN):**  
  * *Recommendation:* Provide aggregate summary metrics for batch operations rather than embedding raw, multi-thousand-line batch execution logs into HTML reports.  
  * *Rationale:* Helps prevent large HTML reports while pointing users to companion CSV logs.  
  * *Trade-off:* Full per-file batch audit requires inspecting the companion CSV file.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-12 (NOT YET FROZEN):**  
  * *Recommendation:* Evaluate a moderate default DPI (e.g., 150 DPI) for embedded Matplotlib PNG charts to balance visual clarity with HTML file size.  
  * *Rationale:* Keeps report file sizes manageable while maintaining readable text on high-resolution displays.  
  * *Trade-off:* DPI selection is an open topic for Selection.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-13 (NOT YET FROZEN):**  
  * *Recommendation:* Enforce UTF-8 file writing via `FileHandler.write_text(encoding="utf-8")` for generated HTML artifacts.  
  * *Rationale:* Prevents character corruption on Windows systems with non-UTF-8 default code pages.  
  * *Trade-off:* None; standard practice.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION D-14 (NOT YET FROZEN):**  
  * *Recommendation:* Offer browser auto-open as a configurable preference or interactive prompt in guided menu mode rather than forcing browser launch in automated/headless runs.  
  * *Rationale:* Prevents unexpected browser windows during automated test runs.  
  * *Trade-off:* Requires user input or CLI flag evaluation.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

---

## 29. Open Decisions (Deferred to Selection Phase)

The following design choices remain open and will be evaluated and decided during the V2 Selection phase:
1. **Decision D-OPEN-01 (Report Packaging):** Should V2 generate a single combined report by default (Model A) or offer separate benchmark-only / security-only reports (Model B/C)? (See §13).
2. **Decision D-OPEN-02 (Auto-Open Default Behavior):** Should browser auto-open be enabled by default, prompted interactively `(Y/n)`, or controlled via an explicit `--open` flag? (See §15).
3. **Decision D-OPEN-03 (Report Output Directory):** Should reports be saved to `results/reports/`, a user-specified directory, or the general `results/` root? (See §16).
4. **Decision D-OPEN-04 (Graph Resolution & DPI):** What default DPI (e.g., 100, 150, or 200 DPI) should be standardized for base64 embedded figures? (See §9, §28).
5. **Decision D-OPEN-05 (ECB Structural Visualization Style):** Should ECB weakness be displayed as an embedded BMP Data URI (Candidate Option A), a Matplotlib heatmap figure (Candidate Option B), or a numerical comparison table (Candidate Option C)? (See §12.1 for the evaluated visualization alternatives).
6. **Decision D-OPEN-06 (Report Regeneration Scope):** Should V2 support regenerating HTML reports from historical CSV/JSON files, or limit generation to live in-memory session data? (See §17).
7. **Decision D-OPEN-07 (CSS Theme / Style Standardization):** Should the report CSS use a custom minimalist laboratory style, a modern card-based theme, or a classless CSS reset? (See §7).
8. **Decision D-OPEN-08 (Batch Log Inclusion Level):** In batch mode, should the HTML report embed a summary table only, the top failed files, or link to the companion CSV? (See §23).
9. **Decision D-OPEN-09 (Report Retention & Disk Cleanup):** Should V2 provide an automated cleanup option for old HTML reports, or leave file lifecycle management to the user?
10. **Decision D-OPEN-10 (Report Schema Versioning):** Should HTML reports embed a machine-readable JSON metadata block or schema version attribute (`data-report-version="2.0"`)? (See §14).

---

## 30. Deferred Decisions (Explicitly Post-V2)

1. **Direct PDF Report Generation:** Compiling reports directly to PDF requires external binary dependencies (e.g., `WeasyPrint`, `wkhtmltopdf`, `ReportLab`), which is outside the zero-dependency constraint. Users could use browser Print-to-PDF if suitable `@media print` styling is included.
2. **Interactive JavaScript Charting:** Embedding client-side JS libraries (e.g., Chart.js, D3.js, Plotly) is deferred to post-V2 to maintain zero dependencies and strict offline security.
3. **Historical Regression Comparison Engine:** Building a multi-session database to chart performance over time across arbitrary historical runs is deferred.
4. **Server-Hosted Dashboard / Web Service:** Hosting reports on a local web server is outside desktop testing lab scope.

---

## 31. Risks and Trade-offs

1. **HTML File Size (Base64 Expansion):** Base64 encoding increases binary image payload size by approximately 33%. A report containing multiple high-DPI charts and BMP images can reach several megabytes. This trade-off is evaluated against single-file portability.
2. **Template String Maintainability:** Maintaining raw HTML/CSS strings inside Python source files requires modularization to avoid cluttered code blocks.
3. **Browser Compatibility Differences:** While standard HTML5/CSS renders consistently across modern Edge, Chrome, and Firefox, legacy browsers may render flexbox/grid layouts with minor variations.
4. **Console vs. HTML Discrepancies:** If formatting precision or unit rounding differs between terminal tables and HTML reports, users may perceive inconsistencies. Shared formatting helpers mitigate this risk.

---

## 32. Conclusion

Category D (Reporting & Analysis) can be implemented in V2 by layering a zero-dependency HTML generation pipeline over the verified V1 `MetricCollector`, `GraphGenerator`, and `SecurityEvaluator`. By rendering figures to in-memory `io.BytesIO()` buffers, embedding base64 Data URIs, enforcing `html.escape()` boundaries, and applying internal CSS, V2 can deliver standalone, portable, and comprehensive analytical artifacts that elevate the Cryptography Testing Lab while honoring architectural invariants.

---

## 33. Sources and Evidence

### Repository Evidence
* `src/analyzers/metric_collector.py` — Metric collection, statistical formulas, Tukey outlier fences, throughput calculation ([lines 67–146](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/metric_collector.py#L67-L146)).
* `src/analyzers/graph_generator.py` — Matplotlib figure generation for key sizes, modes, and throughput ([lines 9–146](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/graph_generator.py#L9-L146)).
* `src/analyzers/security_evaluator.py` — Avalanche effect, key sensitivity, BMP structural ECB evaluation ([lines 19–148](file:///C:/Users/kodal/Cryptography_Project/src/analyzers/security_evaluator.py#L19-L148)).
* `src/cli/commands.py` — Benchmark graph saving ([lines 92–117](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L92-L117)), security report dictionary builder with base64 binary fields ([lines 128–158](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L128-L158)).
* `src/cli/main.py` — Headless Matplotlib configuration (`matplotlib.use("Agg")` at [line 13](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L13)).
* `src/utils/file_handler.py` — UTF-8 text writing and directory creation primitives ([lines 41–104](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L41-L104)).
* `tests/cli/test_persistence.py` — Persistence and artifact test baseline.
* `docs/v2/V2_INTENT.md` — Category D Requirements (§5.4) and Architectural Invariants (§3).

### Python / Standard Library Documentation
* Python `string.Template` — PEP 292 string substitution.
* Python `html.escape` — HTML entity escaping for XSS prevention.
* Python `base64` — RFC 4648 Base64 data encoding.
* Python `io.BytesIO` — In-memory binary streams.
* Python `webbrowser` — Cross-platform browser controller.
* Python `pathlib` — Object-oriented filesystem paths and `as_uri()` resolution.

### Matplotlib Documentation
* Matplotlib Headless Rendering: `matplotlib.use('Agg')` non-interactive backend.
* Matplotlib `Figure.savefig`: In-memory buffer export and DPI configuration.

### Industry Tools Consulted
* **pytest-html:** Single-file HTML test report generation with embedded CSS and base64 assets.
* **Sphinx:** Static HTML documentation generation patterns.
* **Jupyter / nbconvert:** HTML notebook conversion with embedded base64 Matplotlib outputs.