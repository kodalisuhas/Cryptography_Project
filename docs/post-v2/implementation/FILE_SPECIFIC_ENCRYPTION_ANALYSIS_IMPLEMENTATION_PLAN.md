# POST-V2 FEATURE IMPLEMENTATION PLAN
## FILE-SPECIFIC ENCRYPTION ANALYSIS LAB

**Document ID:** POST-V2-FEAT-PLAN-002  
**Status:** PROPOSED — REVISED PER INDEPENDENT AUDIT (READY FOR PLAN FREEZE)  
**Date:** 2026-09-27  
**Author:** Antigravity Engineering (Implementation Architecture & Systems Engineering)  
**Target Milestone:** Post-V2 Implementation Plan Freeze  
**Upstream Frozen Selection:** `docs/post-v2/selection/FILE_SPECIFIC_ENCRYPTION_ANALYSIS_SELECTION.md` (`POST-V2-FEAT-SELECT-002`)  
**Implementation Authorization:** **NOT AUTHORIZED** *(Implementation Planning Phase Only; zero production code written)*

---

## Methodological Classification Key

In accordance with strict project governance, every specification in this implementation plan is categorized under the following taxonomy:

- `[FROZEN CONSTRAINT]`: Inviolable baseline boundary, frozen API contract, or immutability rule established in V1/V2 and confirmed in Selection Freeze that cannot be altered under any circumstances.
- `[OBSERVED FACT]`: Verifiable, empirical property discovered through direct source code inspection and verified automated test execution.
- `[IMPLEMENTATION SPECIFICATION]`: The definitive engineering blueprint, module contract, error handling rule, and execution flow designed to realize the frozen Selection specification.
- `[DEFERRED]`: Deliberately postponed capability, metric, or architectural extension reserved for a future release cycle.
- `[OUT OF SCOPE]`: Feature, algorithm, or methodology explicitly excluded from the testing lab.

---

## 1. Executive Summary & Purpose `[IMPLEMENTATION SPECIFICATION]`

This document establishes the authoritative, binding **Implementation Plan** for the post-V2 **File-Specific Encryption Analysis Lab** (`src/analysis_lab/`).

Its purpose is to provide the exact, file-by-file engineering blueprint required to build the feature once implementation is formally approved. It details:
1. The structural architecture of all 8 new source modules and 7 new test modules in `src/analysis_lab/` and `tests/analysis_lab/`.
2. The granular, method-by-method mapping of the frozen exception policy onto existing V1 and V2 APIs, rigorously distinguishing expected operational/cryptographic failures from internal programming defects.
3. The exact contracts for micro-benchmarking isolation, statistical aggregation via two `MetricCollector` instances, ciphertext length derivation, decoupled security analysis, and offline HTML report generation.
4. The 5-stage sequential implementation roadmap, complete with verification gates and non-regression invariants.

---

## 2. Frozen Baseline & Governance Boundaries `[FROZEN CONSTRAINT]`

Before any implementation code is written, the system state and immutability boundaries are formally established:

| Boundary Parameter | Baseline Commit / Location | Governance Invariant |
| :--- | :--- | :--- |
| **V1 Baseline** | `v1.0-release` (`650bc7f`) | `src/core/`, `src/engines/`, `src/analyzers/`, `src/utils/`, `src/cli/` remain 100% bit-for-bit identical (`git diff` must be empty). |
| **V2 Baseline** | `v2.0-release` (`9a4a114`) | Existing files in `src/cli_v2/` remain 100% bit-for-bit identical. |
| **Existing Tests** | `tests/` and `tests/cli_v2/` | All 886 existing test cases (879 pass, 7 skip) remain untouched and must continue to pass with zero regressions. |
| **Dependencies** | `requirements.txt` | Zero new dependencies added. Python standard library + existing project dependencies (`cryptography`, `matplotlib`, `pandas`, `numpy`, `pytest`) only. |
| **New Package Namespace** | `src/analysis_lab/` | All new feature implementation code is isolated strictly in `src/analysis_lab/`. |
| **New Test Namespace** | `tests/analysis_lab/` | All new unit, integration, and regression tests are isolated strictly in `tests/analysis_lab/`. |
| **Configuration Matrix** | Exactly 6 AES configurations | `AES-128-CBC`, `AES-192-CBC`, `AES-256-CBC`, `AES-128-ECB`, `AES-192-ECB`, `AES-256-ECB`. |
| **Timing Contract** | `@PerformanceTimer.measure_time_with_warmup()` | Default zero-argument invocation: 5 unmeasured warmup iterations and 30 measured iterations. |

---

## 3. API-Specific Exception Policy Mapping `[IMPLEMENTATION SPECIFICATION]`

A central requirement of this implementation plan is the precise, method-by-method mapping of the frozen exception policy onto actual existing V1 and V2 APIs.

### 3.1 Core Principle: Defect Visibility vs. Operational Isolation
- **Expected Operational & Cryptographic Exceptions:** Conditions arising from user input files, operating system resource limits, filesystem permissions, or mathematical/cryptographic boundaries (e.g. corrupt padding, invalid block alignment, disk write errors). These must be caught, handled gracefully, and translated into structured user guidance or isolated configuration failure records.
- **Internal Programming Defects:** Bugs in our own implementation code (e.g., passing missing keys or wrong types to `MetricCollector.add_metric()`, invalid attribute access, typos in dictionary lookups, `IndexError`, `TypeError`, `AttributeError`). These must **NEVER** be caught or swallowed in benchmark execution loops. They must propagate immediately to fail tests and expose defects during development.

### 3.2 Granular API Exception Mapping Matrix

| Existing Component / API Call | Invoked In Module | Target Exception Types | Root Cause / Context | Classification | Handling Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `FileHandler.get_file_size(path)` | `runner.py` | `FileNotFoundError` (subclass of `OSError`) | Input path does not exist on disk | Expected File I/O Error | Halt execution; exit code 1; display 3-tier diagnostic via `ErrorTranslator.display_error()`. |
| `FileHandler.get_file_size(path)` | `runner.py` | `PermissionError` (subclass of `OSError`) | Read permission denied on input file | Expected File I/O Error | Halt execution; exit code 1; display 3-tier diagnostic via `ErrorTranslator.display_error()`. |
| `FileHandler.get_file_size(path)` | `runner.py` | `OSError` | Path is directory or invalid path syntax | Expected File I/O Error | Halt execution; exit code 1; display 3-tier diagnostic via `ErrorTranslator.display_error()`. |
| `FileHandler.read_bytes(path)` | `runner.py` | `FileNotFoundError`, `PermissionError`, `OSError` | File deleted, locked, or unreadable between stat and read | Expected File I/O Error | Halt execution; exit code 1; display 3-tier diagnostic via `ErrorTranslator.display_error()`. |
| `CipherFactory.create_cipher(...)` | `experiment.py` | `ValueError` | Unsupported algorithm, invalid key size, or invalid mode | Cryptographic Setup Failure | Caught in per-config loop; mark configuration status as `FAILED`; record error; continue remaining configs. |
| `AESCipher.generate_key()` | `experiment.py` | `OSError` | OS entropy source failure (`os.urandom`) | Cryptographic Setup Failure | Caught in per-config loop; mark configuration status as `FAILED`; record error; continue remaining configs. |
| `AESCipher.generate_iv()` | `experiment.py` | `ValueError` (if called on ECB), `OSError` (entropy failure) | Mode violation or OS entropy exhaustion | Cryptographic Setup Failure | Guarded in code (only called for CBC); any runtime failure marks config `FAILED`; continue remaining configs. |
| `AESCipher.encrypt(payload, key, iv)` (Pre-check) | `experiment.py` | `ValueError` | Encryption failure (bad key/IV length or type) | Cryptographic Setup Failure | Caught in per-config loop; mark configuration status as `FAILED`; record error; continue remaining configs. |
| `AESCipher.decrypt(ciphertext, key, iv)` (Pre-check) | `experiment.py` | `ValueError` | Corrupted ciphertext, bad block size, or PKCS#7 padding failure | Cryptographic Setup Failure | Caught in per-config loop; mark configuration status as `FAILED`; record error; continue remaining configs. |
| Round-trip equality check (`decrypted != payload`) | `experiment.py` | `RuntimeError` | Restored plaintext does not match input bytes | Cryptographic Round-Trip Defect | Explicitly raised by `experiment.py`; caught in per-config loop; mark config `FAILED`; skip timing; continue. |
| `@PerformanceTimer.measure_time_with_warmup()` wrapping `cipher.encrypt()` | `experiment.py` | `ValueError`, `RuntimeError` | AES engine execution failure or cryptographic error during timed loop | Cryptographic Benchmark Failure | Caught in per-config loop; mark configuration status as `FAILED`; record error; continue remaining configs. |
| `@PerformanceTimer.measure_time_with_warmup()` wrapping `cipher.decrypt()` | `experiment.py` | `ValueError`, `RuntimeError` | AES engine execution failure or cryptographic error during timed loop | Cryptographic Benchmark Failure | Caught in per-config loop; mark configuration status as `FAILED`; record error; continue remaining configs. |
| **`MetricCollector.add_metric(metric_data)`** | `experiment.py` | `ValueError` (missing key, non-str algorithm, empty raw_times) | Schema violation in dictionary assembled by `experiment.py` | **INTERNAL PROGRAMMING DEFECT** | **STRICTLY PROHIBITED FROM CATCHING**. If `add_metric` raises `ValueError`, our dict assembly is buggy. Must propagate unhandled! |
| `SecurityEvaluator.calculate_avalanche_effect(...)` | `security_experiment.py` | `ValueError`, `RuntimeError` | Internal cipher execution failure during 1-bit mutation | Security Evaluation Failure | Caught in security runner; mark security status as `FAILED`; record error message; do not fail benchmark. |
| `SecurityEvaluator.test_key_sensitivity(...)` | `security_experiment.py` | `ValueError`, `RuntimeError` | Internal cipher execution failure during 1-bit key mutation | Security Evaluation Failure | Caught in security runner; mark security status as `FAILED`; record error message; do not fail benchmark. |
| `GraphGenerator.generate_all_charts(...)` | `report.py` | `ValueError`, `RuntimeError` | Matplotlib rendering failure or empty metric dataset | Chart Generation Failure (Level A) | Fall back gracefully: emit warning; generate HTML report with complete data tables (replacing chart with notice). |
| HTML document template assembly | `report.py` | `ValueError`, `RuntimeError` | Internal formatting or compilation failure | HTML Assembly Failure (Level B) | Caught in runner; report generation fails; raw summary metrics dumped to stdout/stderr so benchmark data is preserved. |
| `FileHandler.write_text(report_path, html)` | `runner.py` | `PermissionError`, `OSError` | Output disk full or destination directory read-only | Report Persistence Failure (Level C) | Catch in runner; in-memory HTML cannot be written; display 3-tier error via `ErrorTranslator`; dump summary tables to stdout. |
| Internal code logic across all modules | All modules | `AttributeError`, `TypeError`, `KeyError`, `IndexError`, `NameError` | Coding bugs, misspelled attributes, broken indices, syntax bugs | **INTERNAL PROGRAMMING DEFECT** | **STRICTLY PROHIBITED FROM CATCHING**. Blanket `except Exception` or `except BaseException` is banned. |

### 3.3 The Configuration Execution Loop Pattern

The per-configuration benchmark loop in `src/analysis_lab/experiment.py` will implement this precise structure:

```python
for config_spec in self.configurations:
    config_name = f"{config_spec['algorithm']}-{config_spec['key_size']}-{config_spec['mode']}"
    try:
        # Phase 1: Unmeasured Setup
        cipher = self.factory.create_cipher(
            config_spec["algorithm"],
            config_spec["key_size"],
            config_spec["mode"]
        )
        key = cipher.generate_key()
        iv = cipher.generate_iv() if config_spec["mode"] == "CBC" else None

        # Phase 2: Unmeasured Round-Trip Pre-Check
        initial_ciphertext = cipher.encrypt(self.payload, key, iv)
        decrypted_check = cipher.decrypt(initial_ciphertext, key, iv)
        if decrypted_check != self.payload:
            raise RuntimeError(
                "Pre-benchmark round-trip check failed: restored plaintext did not match original input"
            )

        # Phase 3: Ciphertext Derivation (Stateless, exact length delta)
        ciphertext_metrics = CiphertextAnalyzer.analyze(self.payload, initial_ciphertext)

        # Phase 4: Measured Encryption Microbenchmark (5 warmup + 30 measured)
        @PerformanceTimer.measure_time_with_warmup()
        def _timed_encrypt():
            return cipher.encrypt(self.payload, key, iv)

        final_ciphertext, enc_stats = _timed_encrypt()

        # Phase 5: Measured Decryption Microbenchmark (Optional)
        dec_stats = None
        if not self.skip_decryption:
            @PerformanceTimer.measure_time_with_warmup()
            def _timed_decrypt():
                return cipher.decrypt(initial_ciphertext, key, iv)

            final_plaintext, dec_stats = _timed_decrypt()

    except (OSError, ValueError, RuntimeError) as exc:
        # Expected operational or cryptographic failure: isolate and record
        failure_result = ConfigurationResult(
            algorithm=config_spec["algorithm"],
            key_size=config_spec["key_size"],
            mode=config_spec["mode"],
            status="FAILED",
            error_message=str(exc)
        )
        results.append(failure_result)
        continue  # Proceed to remaining configurations

    # Phase 6: Ingest into MetricCollectors (OUTSIDE try/except for expected crypto failures)
    # Any ValueError here is an internal programming defect in our dictionary assembly!
    enc_dict = {
        'algorithm': config_spec["algorithm"],
        'key_size': config_spec["key_size"],
        'mode': config_spec["mode"],
        'data_size_bytes': len(self.payload),
        'raw_times_ms': enc_stats['raw_times_ms']
    }
    self.encryption_collector.add_metric(enc_dict)

    if dec_stats is not None and self.decryption_collector is not None:
        dec_dict = {
            'algorithm': config_spec["algorithm"],
            'key_size': config_spec["key_size"],
            'mode': config_spec["mode"],
            'data_size_bytes': len(self.payload),
            'raw_times_ms': dec_stats['raw_times_ms']
        }
        self.decryption_collector.add_metric(dec_dict)

    # Build successful result object
    results.append(
        self._build_success_result(
            config_spec,
            enc_stats,
            dec_stats,
            ciphertext_metrics
        )
    )
```

---

## 4. Module Architecture & Design Contracts `[IMPLEMENTATION SPECIFICATION]`

All new source code is situated strictly within `src/analysis_lab/`.

```text
src/analysis_lab/
├── __init__.py                # Package initialization and public API exports
├── models.py                  # Immutable dataclasses for metadata and results
├── ciphertext_analyzer.py     # Stateless derivation for padding and expansion
├── experiment.py              # PerformanceExperiment microbenchmarking runner
├── security_experiment.py     # SecurityExperiment runner (Avalanche & Key Sensitivity)
├── report.py                  # FileAnalysisReportGenerator (HTML assembly & Base64 charts)
├── runner.py                  # FileAnalysisRunner (preflight, orchestration, file I/O)
└── cli.py                     # Dedicated CLI entry point (subcommands & guided wizard)
```

### 4.1 `src/analysis_lab/models.py`
Defines strictly typed, immutable data structures (using `@dataclass(frozen=True)`) containing only the selected result and data contracts needed by the experiment, runner, and report. No external serialization framework or speculative helper methods are introduced.

1. `FileMetadata`:
   - `file_name: str`: Base name of target file.
   - `display_path: str`: Working-directory-relative path (or masked relative path).
   - `absolute_path: str | None`: Full absolute path on disk (omitted or masked by default).
   - `file_size_bytes: int`: Exact byte size of the payload.
   - `sha256_hash: str | None`: 64-character lowercase hex digest (or `None` if `--no-hash` active).
   - `is_zero_byte: bool`: Convenience property (`file_size_bytes == 0`).
   - `is_bmp: bool`: True if file starts with valid 54-byte BMP header.

2. `PerformanceMetrics`:
   - `sample_count: int`: Number of measured iterations ($N = 30$).
   - `mean_ms: float`: Sample arithmetic mean latency.
   - `median_ms: float`: Sample median latency.
   - `std_dev_ms: float`: Sample standard deviation ($ddof = 1$).
   - `min_ms: float`: Minimum observed latency.
   - `max_ms: float`: Maximum observed latency.
   - `q1_ms: float`: 25th percentile.
   - `q3_ms: float`: 75th percentile.
   - `iqr_ms: float`: Interquartile range ($Q3 - Q1$).
   - `outlier_count: int`: Count of observations outside Tukey fences ($[Q1 - 1.5 \times IQR, Q3 + 1.5 \times IQR]$).
   - `throughput_mb_s: float | None`: Binary megabytes per second, or `None` if `file_size_bytes == 0`.
   - `raw_times_ms: tuple[float, ...]`: Tuple of the 30 raw execution times.

3. `CiphertextMetrics`:
   - `plaintext_size_bytes: int`: Size of original plaintext payload ($S$).
   - `ciphertext_size_bytes: int`: Size of engine-produced ciphertext ($C$).
   - `padding_overhead_bytes: int`: Exact padding bytes added ($C - S$).
   - `expansion_percentage: float | None`: $((C - S) / S) \times 100$ or `None` if $S = 0$.

4. `SecurityMetrics`:
   - `status: str`: `"SUCCESS"`, `"SKIPPED"`, or `"FAILED"`.
   - `avalanche_effect_pct: float | None`: Observed Plaintext Avalanche Effect percentage.
   - `key_sensitivity_pct: float | None`: Observed Key Sensitivity percentage.
   - `notes: str | None`: Contextual explanations (e.g. why skipped for zero-byte or non-BMP).

5. `ConfigurationResult`:
   - `algorithm: str`: `"AES"`.
   - `key_size: int`: `128`, `192`, or `256`.
   - `mode: str`: `"CBC"` or `"ECB"`.
   - `status: str`: `"SUCCESS"` or `"FAILED"`.
   - `error_message: str | None`: Failure description if status is `"FAILED"`.
   - `encryption_metrics: PerformanceMetrics | None`.
   - `decryption_metrics: PerformanceMetrics | None`.
   - `ciphertext_metrics: CiphertextMetrics | None`.
   - `security_metrics: SecurityMetrics | None`.

6. `FileAnalysisResult`:
   - `file_metadata: FileMetadata`.
   - `configurations: tuple[ConfigurationResult, ...]`.
   - `timestamp_utc: str`: ISO 8601 formatted UTC timestamp.
   - `skip_decryption: bool`: True if decryption benchmarking was skipped.
   - `security_enabled: bool`: True if security diffusion was executed.
   - `fastest_encryption_config: str | None`: E.g. `"AES-128-CBC (0.42 ms)"`.
     - **Partial-Run & Ranking Semantics:**
       - Evaluated strictly across configurations where `status == "SUCCESS"` and `encryption_metrics` is present.
       - Failed configurations (`status == "FAILED"`) are strictly excluded from participation.
       - Ranked strictly by lowest sample mean latency (`encryption_metrics.mean_ms`).
       - If zero configurations succeeded, value is `None`.
   - `fastest_decryption_config: str | None`: E.g. `"AES-128-CBC (0.39 ms)"`.
     - **Partial-Run & Ranking Semantics:**
       - Evaluated strictly across configurations where `status == "SUCCESS"` and `decryption_metrics` is present.
       - Failed configurations (`status == "FAILED"`) are strictly excluded from participation.
       - If decryption benchmarking was skipped (`skip_decryption=True`) or zero configurations succeeded in decryption, value is `None`.
       - Ranked strictly by lowest sample mean latency (`decryption_metrics.mean_ms`).
   - `success_count: int`: Count of successful configurations (`status == "SUCCESS"`).
   - `failure_count: int`: Count of failed configurations (`status == "FAILED"`).

---

### 4.2 `src/analysis_lab/ciphertext_analyzer.py`
Stateless utility for analyzing ciphertext size and padding:

- Method: `CiphertextAnalyzer.analyze(plaintext: bytes, ciphertext: bytes) -> CiphertextMetrics`
- Logic:
  ```python
  plaintext_size = len(plaintext)
  ciphertext_size = len(ciphertext)
  padding_overhead = ciphertext_size - plaintext_size
  expansion_pct = (
      (padding_overhead / plaintext_size) * 100.0
      if plaintext_size > 0 else None
  )
  return CiphertextMetrics(
      plaintext_size_bytes=plaintext_size,
      ciphertext_size_bytes=ciphertext_size,
      padding_overhead_bytes=padding_overhead,
      expansion_percentage=expansion_pct
  )
  ```
- Boundary Guarantees:
  - 0 B input: `ciphertext = 16 B`, `padding = 16 B`, `expansion = None`.
  - 16 B input: `ciphertext = 32 B`, `padding = 16 B`, `expansion = 100.0%`.
  - 15 B input: `ciphertext = 16 B`, `padding = 1 B`, `expansion = 6.67%`.
  - 17 B input: `ciphertext = 32 B`, `padding = 15 B`, `expansion = 88.24%`.

---

### 4.3 `src/analysis_lab/experiment.py`
Microbenchmark execution engine:

- Responsibilities:
  1. Manages unmeasured setup (key generation, IV generation, round-trip check).
  2. Wraps encryption and decryption calls with `@PerformanceTimer.measure_time_with_warmup()`.
  3. Maintains two separate `MetricCollector` instances (`encryption_collector` and `decryption_collector`) to prevent DataFrame schema key collisions.
  4. Calculates `PerformanceMetrics` from raw times, strictly preserving Tukey fences, outlier retention, and binary megabyte throughput formulas.
  5. Enforces zero-byte throughput rule: sets `throughput_mb_s = None` when `len(payload) == 0`.
  6. Implements per-configuration error isolation as defined in Section 3.3.

---

### 4.4 `src/analysis_lab/security_experiment.py`
Decoupled, opt-in security diffusion evaluator:

- Responsibilities:
  1. Invoked only when `security_enabled=True`.
  2. Pre-check: If `len(payload) == 0`, immediately returns `SecurityMetrics(status="SKIPPED", notes="Diffusion metrics require non-empty payload.")`.
  3. Plaintext Avalanche Effect:
     - Clones payload: `mutated = bytearray(payload); mutated[0] ^= 0x01`.
     - Calls frozen `SecurityEvaluator.calculate_avalanche_effect(payload, bytes(mutated), cipher, key, iv)`.
     - Passes `iv=None` for ECB; configuration IV for CBC.
  4. Key Sensitivity:
     - Clones key: `mutated_key = bytearray(key); mutated_key[0] ^= 0x01`.
     - Calls frozen `SecurityEvaluator.test_key_sensitivity(cipher, payload, key, bytes(mutated_key), iv)`.
  5. BMP Structural Pattern Guard:
     - Checks if payload starts with `b'BM'` and has valid BMP headers.
     - Only runs `test_ecb_weakness()` if valid BMP. Otherwise records: `"Structural pattern test is specific to 24-bpp uncompressed BMP images."`
  6. Error Handling: Catches `(ValueError, RuntimeError)`; records `status="FAILED"`.

---

### 4.5 `src/analysis_lab/report.py`
Self-contained HTML report compiler:

- Responsibilities:
  1. Generates static charts via `GraphGenerator` from `encryption_collector` and `decryption_collector`.
  2. Encodes PNG figures as Base64 data URIs (`data:image/png;base64,...`) and embeds them inline.
  3. Builds HTML tables for:
     - Executive Summary Cards (File size, tested configurations, fastest encryption, fastest decryption, failure count).
     - Comparative Configuration Matrix (all 6 configs, ciphertext size, padding overhead, expansion %, enc/dec latency, enc/dec throughput).
     - Detailed Statistical Breakdown (mean, median, std dev, min, max, outliers).
     - Ciphertext and PKCS#7 Padding Profile.
     - Security Diffusion Profile (if enabled) with prominent scientific caveat notice.
  4. Strictly enforces terminology rules:
     - Zero instances of "Winner" or "Best Configuration".
     - Fastest phrased strictly as: `"Fastest observed configuration in this experiment (lowest sample mean latency)"`.
  5. Strictly enforces privacy rules:
     - Renders relative path by default.
     - Masks absolute path as `[OMITTED FOR PRIVACY]` unless `--include-absolute-path` is True.
     - Omits SHA-256 fingerprint if `--no-hash` is True.
     - Sanitizes all dynamic text via `html.escape(quote=True)`.
     - Never writes encryption keys, IVs, or raw payload bytes to HTML.
  6. Multi-Tier Reporting Failure Handling:
     - **Level A (Chart Generation Failure):** If `GraphGenerator` or Matplotlib encounters an exception, chart generation fails gracefully. HTML report compilation continues normally with complete tabular data, embedding a clear notice in place of the chart: `"[Notice: Performance chart rendering was unavailable for this run; refer to tabular metrics below]"`.
     - **Level B (HTML Assembly Failure):** If template assembly fails during HTML compilation, the generator signals failure to `runner.py`, triggering fallback data dumping.

---

### 4.6 `src/analysis_lab/runner.py`
High-level workflow orchestrator:

- Responsibilities:
  1. Preflight File Inspection:
     - Validates existence and read permissions via `FileHandler`.
     - Computes SHA-256 hash (streaming chunks via `hashlib.sha256()`).
     - Inspects file size against 30 MB warning and 100 MB ceiling.
     - Rejects files > 100 MB unless `force=True`.
  2. Orchestrates execution:
     - Ingests file bytes once via `FileHandler.read_bytes()`.
     - Executes `PerformanceExperiment`.
     - Executes `SecurityExperiment` (if requested).
     - Generates HTML report via `FileAnalysisReportGenerator`.
     - Writes report to disk via `FileHandler.write_text()`.
  3. Auto-Open Dispatch:
     - Dispatches `webbrowser.open(report_path.as_uri())` unless `no_open=True`.
  4. Error Handling & Data Preservation Boundaries:
     - **Preflight Failures:** Converts preflight `OSError`, `FileNotFoundError`, `PermissionError` to exit code 1 with 3-tier diagnostics via `ErrorTranslator.display_error()`.
     - **Level B Recovery (HTML Assembly Failure):** If `report.py` fails to assemble HTML, `runner.py` catches the failure and dumps the formatted tabular metrics directly to terminal stdout/stderr so empirical benchmark data is never lost.
     - **Level C Recovery (Disk Persistence Failure):** If `FileHandler.write_text()` raises `OSError` or `PermissionError` (e.g. read-only directory or disk full), `runner.py` catches the exception, displays a 3-tier diagnostic via `ErrorTranslator.display_error(exc, context="Report Persistence")`, and dumps summary tables directly to terminal stdout.

---

### 4.7 `src/analysis_lab/cli.py`
User interface and argument routing:

- Subcommands / Modes:
  1. **Direct Mode:** Triggered when `--input` / `-i` is provided. Parses flags, executes `FileAnalysisRunner.run()`, outputs terminal summary card, and exits with code 0 (success) or 1 (failure).
  2. **Interactive Wizard Mode:** Triggered when launched without arguments (`python -m src.analysis_lab.cli`). Prompts user through:
     - Step 1: File selection (path entry with drag-and-drop whitespace stripping).
     - Step 2: Preflight summary (size, SHA-256, type).
     - Step 3: Scope confirmation (All 6 AES configurations).
     - Step 4: Options (Include decryption? [Y/n], Include security diffusion? [y/N]).
     - Step 5: High-volume confirmation (if file > 30 MB: prompt with calculated cumulative gigabytes).
     - Step 6: Step-by-step console execution indicators.
     - Step 7: Summary card rendering via `Presentation.format_summary_card()`.
     - Step 8: Prompt to open HTML report in default browser.

---

## 5. File Modification & Creation Inventory `[IMPLEMENTATION SPECIFICATION]`

### 5.1 New Files to Create

| File Path | Component | Purpose |
| :--- | :--- | :--- |
| `src/analysis_lab/__init__.py` | Package Init | Package initialization and public API imports |
| `src/analysis_lab/models.py` | Data Models | Strictly-typed dataclasses for file metadata and results |
| `src/analysis_lab/ciphertext_analyzer.py` | Cryptanalysis Leaf | Stateless padding and expansion derivation |
| `src/analysis_lab/experiment.py` | Benchmark Engine | In-memory microbenchmarking with dual `MetricCollector` |
| `src/analysis_lab/security_experiment.py` | Security Engine | Decoupled avalanche and key sensitivity analysis |
| `src/analysis_lab/report.py` | Report Compiler | Self-contained offline HTML generator with Base64 charts |
| `src/analysis_lab/runner.py` | Orchestrator | Preflight validation, workflow coordination, error translation |
| `src/analysis_lab/cli.py` | User Interface | Dedicated CLI router with direct and wizard execution flows |
| `tests/analysis_lab/__init__.py` | Test Package Init | Package initialization for new lab test suite |
| `tests/analysis_lab/test_models.py` | Test Suite | Unit tests for data containers, immutability, and defaults |
| `tests/analysis_lab/test_ciphertext_analyzer.py` | Test Suite | Unit tests for boundary conditions (0B, 15B, 16B, 17B) |
| `tests/analysis_lab/test_experiment.py` | Test Suite | Unit tests for 6 configs, 5/30 contract, and error isolation |
| `tests/analysis_lab/test_security_experiment.py` | Test Suite | Unit tests for avalanche, key sensitivity, and BMP guard |
| `tests/analysis_lab/test_report.py` | Test Suite | Unit tests for HTML assembly, privacy flags, and terminology |
| `tests/analysis_lab/test_runner.py` | Test Suite | Unit tests for preflight checks, size ceiling, and orchestration |
| `tests/analysis_lab/test_cli.py` | Test Suite | Unit tests for CLI parsing, wizard flows, and exit codes |

### 5.2 Files with ZERO Modifications (`[FROZEN CONSTRAINT]`)
- `src/core/*` (100% frozen)
- `src/engines/*` (100% frozen)
- `src/analyzers/*` (100% frozen)
- `src/utils/*` (100% frozen)
- `src/cli/*` (100% frozen)
- `src/cli_v2/*` (100% frozen, including `menu_v2.py`)
- `tests/test_*.py`, `tests/engines/*`, `tests/cli/*`, `tests/utils/*`, `tests/cli_v2/*` (all 886 existing tests frozen)
- `requirements.txt` (100% frozen)

---

## 6. Testing & Quality Assurance Plan `[IMPLEMENTATION SPECIFICATION]`

### 6.1 Planned Test Coverage in `tests/analysis_lab/`

| Test Module | Target Coverage Area | Key Test Scenarios |
| :--- | :--- | :--- |
| `test_models.py` | `src/analysis_lab/models.py` | - Immutability of dataclasses<br>- Default values and optional fields<br>- Result representation and zero-byte property behavior |
| `test_ciphertext_analyzer.py` | `src/analysis_lab/ciphertext_analyzer.py` | - Zero-byte input: 16 B ciphertext, 16 B padding, expansion is None<br>- Block boundary (16 B): 32 B ciphertext, 16 B padding, expansion = 100.0%<br>- Sub-block (15 B): 16 B ciphertext, 1 B padding, expansion = 6.67%<br>- Over-block (17 B): 32 B ciphertext, 15 B padding, expansion = 88.24%<br>- Arbitrary multi-kilobyte binary buffer expansion |
| `test_experiment.py` | `src/analysis_lab/experiment.py` | - All 6 configurations execute against valid payload<br>- Verify `@PerformanceTimer.measure_time_with_warmup()` executed with 5 warmup and 30 measured cycles<br>- Dual collector verification: encryption and decryption collectors hold 6 rows each without key collisions<br>- Error isolation: mocked cipher failure in config #3 allows configs #4–#6 to complete<br>- Round-trip check failure raises `RuntimeError` and records status `FAILED`<br>- Programming defect verification: invalid dict passed to `MetricCollector.add_metric` raises unhandled `ValueError` (not swallowed)<br>- Zero-byte payload: latency measured; throughput is `None` |
| `test_security_experiment.py` | `src/analysis_lab/security_experiment.py` | - 1-bit flip Plaintext Avalanche Effect calculation across 6 configs<br>- 1-bit flip Key Sensitivity calculation across 6 configs<br>- Zero-byte input skipped with descriptive note<br>- Valid BMP header executes `test_ecb_weakness()`<br>- Non-BMP file (text, PDF, raw bytes) bypasses BMP test with note<br>- Exception in `SecurityEvaluator` recorded as `status="FAILED"` |
| `test_report.py` | `src/analysis_lab/report.py` | - HTML assembly produces valid standalone HTML document<br>- Base64 chart data URI correctly embedded<br>- Terminology check: asserts zero occurrences of `"Winner"` and `"Best Configuration"`<br>- "Fastest" label verified to include lowest sample mean latency qualifier<br>- Path privacy: absolute path omitted by default, included when flag set<br>- Hash privacy: SHA-256 omitted when `--no-hash` active<br>- HTML escaping: filenames with `<script>` or `&` properly escaped |
| `test_runner.py` | `src/analysis_lab/runner.py` | - Non-existent file raises `FileNotFoundError`, handled cleanly with exit code 1<br>- File > 100 MB rejected with error message unless `force=True`<br>- File > 30 MB emits warning notice<br>- Partial success: 5 configs pass, 1 fails -> report generated with failure banner<br>- Report written to target destination directory |
| `test_cli.py` | `src/analysis_lab/cli.py` | - Argument parser: `--input`, `--output`, `--skip-decryption`, `--security`, `--no-hash`, `--force`<br>- Direct CLI mode executes end-to-end and returns exit code 0<br>- Invalid arguments return exit code 2<br>- Wizard mode launches interactive prompts |

### 6.2 Acceptance & Non-Regression Invariant
The acceptance requirement is complete behavioral coverage of all specified scenarios and zero regressions across the baseline. Test-count figures are non-binding estimates; the definitive requirement is that all baseline tests and all new lab tests pass:
```bash
pytest
# Acceptance Invariants:
# - All 886 baseline tests pass (879 passed, 7 skipped).
# - All new analysis lab tests pass with zero failures.
# - Overall pytest exit code must be 0.
```

---

## 7. Five-Stage Implementation Roadmap `[IMPLEMENTATION SPECIFICATION]`

Implementation will proceed in 5 sequential stages once formal authorization is granted:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   5-STAGE IMPLEMENTATION ROADMAP                       │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 1: FOUNDATION (Data Models & Ciphertext Analyzer)                │
│ - Create src/analysis_lab/__init__.py and models.py                    │
│ - Create src/analysis_lab/ciphertext_analyzer.py                      │
│ - Create tests/analysis_lab/test_models.py & test_ciphertext_analyzer  │
│ - Verification Gate: Stage 1 tests pass 100%                           │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 2: EXPERIMENTAL ENGINES (Benchmark & Security)                   │
│ - Create src/analysis_lab/experiment.py                                │
│ - Create src/analysis_lab/security_experiment.py                       │
│ - Create tests/analysis_lab/test_experiment.py & test_security_...     │
│ - Verification Gate: 6 configs timed, 2 collectors populated, isolated │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 3: REPORT COMPILER (HTML Assembly & Base64 Charts)               │
│ - Create src/analysis_lab/report.py                                    │
│ - Create tests/analysis_lab/test_report.py                             │
│ - Verification Gate: HTML artifact renders, terminology clean, privacy │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 4: WORKFLOW ORCHESTRATION & CLI (Runner & Interface)             │
│ - Create src/analysis_lab/runner.py                                    │
│ - Create src/analysis_lab/cli.py                                       │
│ - Create tests/analysis_lab/test_runner.py & test_cli.py               │
│ - Verification Gate: Direct CLI and wizard modes execute cleanly       │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 5: SYSTEM VERIFICATION & REGRESSION AUDIT                        │
│ - Execute full repository test suite (existing 886 + new tests)        │
│ - Verify git diff: zero modified files in V1/V2 baselines              │
│ - Execute live manual verification on sample test files                │
│ - Produce Walkthrough Report                                           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Verifiable Acceptance Criteria `[FROZEN CONSTRAINT]` & `[IMPLEMENTATION SPECIFICATION]`

Prior to project sign-off, the following 14 acceptance criteria must be empirically verified:

1. **V1 Immutability:** `git diff v1.0-release..HEAD -- src/core src/engines src/analyzers src/utils src/cli` is completely empty (0 files changed, 0 insertions, 0 deletions).
2. **V2 Source Immutability:** Zero existing files in `src/cli_v2/` are modified.
3. **Existing Test Immutability:** All existing test files in `tests/` and `tests/cli_v2/` remain bit-for-bit identical, and all 879 passing baseline tests continue to pass with zero regressions.
4. **Permitted Location Isolation:** All new feature code is located strictly within `src/analysis_lab/`, and all new tests are located strictly within `tests/analysis_lab/`.
5. **Zero New Dependencies:** `requirements.txt` remains bit-for-bit identical to the release baseline.
6. **Configuration Matrix Coverage:** The experiment attempts all 6 supported configurations (AES 128/192/256 in ECB and CBC) for every valid input. An isolated configuration failure does not abort remaining configurations. A successful full run produces results for all six; a partial run contains explicit per-configuration failure accounting.
7. **PerformanceTimer Contract:** Each measured operation (encryption and decryption) strictly executes the frozen PerformanceTimer contract of 5 warmup and 30 measured iterations via `@PerformanceTimer.measure_time_with_warmup()`.
8. **Decoupled Security Execution:** Security diffusion analysis executes only when explicitly requested, uses only frozen `SecurityEvaluator` methods, and guards against arbitrary non-BMP files.
9. **Two-Collector Schema Integrity:** Encryption and decryption metrics are managed via separate `MetricCollector` instances without schema collisions.
10. **Zero-Byte Accuracy:** 0-byte input files produce 16-byte ciphertexts, measurable latency, and throughput reported as `N/A`.
11. **Standalone HTML Report:** A single-file, self-contained HTML report with embedded Base64 static Matplotlib charts is generated in `results/reports/`.
12. **Privacy Enforcement:** Generated HTML reports omit absolute system paths by default.
13. **Terminology Compliance:** Reports contain zero instances of "Winner" or universal "Best Configuration", and qualify "Fastest" strictly to the observed experiment.
14. **Error Isolation Resilience:** Single configuration failures do not abort remaining configurations or prevent report generation, and programming defects are never swallowed.

---

## 9. Implementation Plan Status

```text
========================================================================
IMPLEMENTATION PLAN STATUS:
PROPOSED — REVISED PER INDEPENDENT AUDIT (READY FOR PLAN FREEZE)

IMPLEMENTATION AUTHORIZATION:
NOT AUTHORIZED (Awaiting Formal Review & Approval of this Plan)
========================================================================
```

**Formal Governance Rule:** No production code or test packages may be created in `src/analysis_lab/` or `tests/analysis_lab/` until this implementation plan is formally approved by the user/reviewer.
