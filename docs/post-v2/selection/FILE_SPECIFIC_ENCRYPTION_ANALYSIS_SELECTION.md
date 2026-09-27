# POST-V2 FEATURE SELECTION & METHODOLOGY DECISION
## FILE-SPECIFIC ENCRYPTION ANALYSIS LAB

**Document ID:** POST-V2-FEAT-SELECT-002  
**Status:** SELECTION COMPLETE — REVISED PER INDEPENDENT AUDIT (READY FOR SELECTION FREEZE)  
**Date:** 2026-09-27  
**Author:** Antigravity Engineering (Architecture & Methodology Selection)  
**Target Milestone:** Post-V2 Selection Freeze  
**Upstream Exploration Document:** `docs/post-v2/FILE_SPECIFIC_ENCRYPTION_ANALYSIS_EXPLORE_AND_PLAN.md` (`POST-V2-FEAT-EXPLORE-004`)  
**Implementation Authorization:** **NOT AUTHORIZED** *(Selection Phase Only; zero production code written)*

---

## Methodological Classification Key

In accordance with strict project governance, every statement, specification, and boundary in this document is categorized under the following taxonomy:

- `[FROZEN CONSTRAINT]`: Inviolable baseline boundary, frozen API contract, or immutability rule established in V1/V2 that cannot be modified under any circumstances.
- `[OBSERVED FACT]`: Verifiable, empirical property discovered through direct source code inspection and verified automated test execution.
- `[SELECTED DECISION]`: The definitive, project-specific architectural or methodological specification chosen for this feature, resolving all prior candidate proposals.
- `[DEFERRED]`: Deliberately postponed capability, metric, or architectural extension reserved for a future release cycle.
- `[OUT OF SCOPE]`: Feature, algorithm, or methodology explicitly excluded from the testing lab.

---

## 1. Purpose `[SELECTED DECISION]`

This document establishes the authoritative, binding **Project-Specific Selection & Methodology Decision** for the post-V2 **File-Specific Encryption Analysis Lab** feature. 

Its purpose is to:
1. Formally resolve all open decisions, candidate proposals, and architectural trade-offs established in `POST-V2-FEAT-EXPLORE-004`.
2. Freeze the exact cryptographic configuration space, micro-benchmarking timing loop, statistical aggregation rules, ciphertext analysis derivation, security evaluation boundaries, and reporting privacy policies.
3. Define the precise package, module, CLI, and test boundaries that guarantee 100% immutability of the frozen V1 and V2 baselines.
4. Establish the measurable acceptance criteria and traceability matrix required before any implementation planning or coding may be authorized.

---

## 2. Source Inputs `[OBSERVED FACT]`

The specifications in this document are derived directly from a forensic reconciliation of the following authoritative project artifacts:

1. **Exploration Foundation:** `docs/post-v2/FILE_SPECIFIC_ENCRYPTION_ANALYSIS_EXPLORE_AND_PLAN.md` (`POST-V2-FEAT-EXPLORE-004`, Exploration Final).
2. **Frozen V1 Baseline:** `v1.0-release` (`650bc7f80ada2c4c8e61a0c29b96e9b3a65cca0a`)
   - `src/core/aes_cipher.py` (AES core engine, ECB/CBC modes, PKCS#7 padding)
   - `src/engines/cipher_factory.py`, `cipher_service.py`, `benchmark_service.py`, `security_service.py`
   - `src/analyzers/performance_timer.py`, `metric_collector.py`, `security_evaluator.py`, `graph_generator.py`
   - `src/utils/file_handler.py`, `padding.py`
   - `docs/04_Methodology.md`, `docs/05_API_Interface_Spec.md`
3. **Frozen V2 Baseline:** `v2.0-release` (`9a4a11409919608817a3b8e3b56102d21a3184b3`)
   - `src/cli_v2/main_v2.py`, `menu_v2.py`, `batch_orchestrator.py`, `key_manager.py`, `report_generator.py`, `presentation.py`, `error_translator.py`, `file_picker.py`, `navigation.py`
   - `docs/v2/V2_INTENT.md`, `docs/v2/selection/V2_CONSOLIDATED_SELECTION.md`, `docs/v2/implementation/V2_IMPLEMENTATION_PLAN.md`, `docs/v2/V2_FINAL_CLOSURE_REPORT.md`
4. **Verified Runtime Test Suites:**
   - 434 passing V1 automated tests (`tests/test_*.py`, `tests/engines/`, `tests/cli/`, `tests/utils/`)
   - 445 passing V2 automated tests (`tests/cli_v2/`)

---

## 3. Verified Baseline `[OBSERVED FACT]`

Before committing to any architectural selections, the repository baseline was empirically audited and verified:

| Audit Parameter | Target Value | Empirical Observed Reality | Status |
| :--- | :--- | :--- | :--- |
| **V1 Baseline Commit** | `650bc7f80ada2c4c8e61a0c29b96e9b3a65cca0a` | `git rev-parse "v1.0-release^{commit}"` $\rightarrow$ `650bc7f` | **MATCH** |
| **V2 Baseline Commit** | `9a4a11409919608817a3b8e3b56102d21a3184b3` | `git rev-parse "v2.0-release^{commit}"` $\rightarrow$ `9a4a114` | **MATCH** |
| **Active Branch / HEAD** | `main` | `8449fa1c063404ab83cc2e2f0a481e66978cea3a` | **MATCH** |
| **Working Tree State** | Clean (no modified tracked files) | `git status` clean; `git diff --stat` returns 0 files, 0 insertions | **CLEAN** |
| **Automated Test Suite** | 886 collected | **879 passed, 7 skipped in 113.49s** (clean exit code 0) | **PASS** |
| **Runtime Environment** | Windows 11 Enterprise (x86_64) | Python 3.13.1, pytest 9.1.1, cryptography 44.0.0, matplotlib 3.10.0 | **VERIFIED** |

---

## 4. Frozen Constraints `[FROZEN CONSTRAINT]`

The following constraints are immutable across this feature's design and eventual implementation:

1. **V1 Source Immutability:** Zero lines of code in `src/core/`, `src/engines/`, `src/analyzers/`, `src/utils/`, and `src/cli/` may be added, edited, moved, or deleted.
2. **V2 Source Immutability:** Zero lines of code in existing `src/cli_v2/` files may be added, edited, moved, or deleted.
3. **Existing Test Immutability:** All existing test files in `tests/` and `tests/cli_v2/` remain 100% bit-for-bit identical.
4. **Dependency Freezing:** `requirements.txt` remains bit-for-bit identical; no new external or third-party dependencies may be added.
5. **No Cryptographic Duplication:** No AES mathematics, S-boxes, Galois Field operations, PKCS#7 padding routines, or cipher suites may be re-implemented. All cryptography must be delegated to the frozen V1 `AESCipher` / `CipherService`.
6. **No Custom Exception Hierarchies:** Standard Python built-in exception types (`ValueError`, `FileNotFoundError`, `RuntimeError`, `TypeError`) must be used exclusively.
7. **Timing Methodology Invariant:** Microbenchmarks must strictly execute the frozen V1 contract: 5 unmeasured warmup iterations and 30 measured iterations via `@PerformanceTimer.measure_time_with_warmup()`.
8. **Throughput Semantics Invariant:** Throughput calculations must strictly follow the V1 binary megabyte definition ($1\text{ MB} = 1{,}048{,}576\text{ bytes}$).
9. **Outlier Methodology Invariant:** Outliers must strictly be identified via standard Tukey fences ($[Q1 - 1.5 \times IQR, Q3 + 1.5 \times IQR]$) and retained in primary summary statistics.
10. **Zero Premature Implementation:** No production code or test packages may be created until this Selection document receives formal independent approval.

---

## 5. Selected Feature Scope `[SELECTED DECISION]`

The post-V2 **File-Specific Encryption Analysis Lab** is defined as an additive, non-invasive analysis tool with the following bounded scope:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        SELECTED FEATURE SCOPE                          │
├────────────────────────────────────────────────────────────────────────┤
│ 1. SINGLE-FILE EVALUATION                                              │
│    Accepts a single user-specified file from disk.                     │
│    Reads payload into memory once; original file is never modified.   │
│                                                                        │
│ 2. SIX CURRENT AES CONFIGURATIONS                                      │
│    Evaluates all currently implemented AES configurations:             │
│    AES-128-CBC, AES-192-CBC, AES-256-CBC,                              │
│    AES-128-ECB, AES-192-ECB, AES-256-ECB.                              │
│                                                                        │
│ 3. DUAL-DIRECTION BENCHMARKING                                         │
│    Executes microbenchmarks for Encryption AND Decryption under the    │
│    frozen 5 warmup + 30 measured PerformanceTimer contract.            │
│                                                                        │
│ 4. CIPHERTEXT & EXPANSION METRICS                                      │
│    Measures exact ciphertext size, padding overhead bytes, and         │
│    expansion ratio derived directly from engine outputs.               │
│                                                                        │
│ 5. OPTIONAL SECURITY DIFFUSION EXPERIMENTS                             │
│    Opt-in evaluation of 1-bit flip Plaintext Avalanche Effect and      │
│    1-bit flip Key Sensitivity using existing SecurityEvaluator.        │
│                                                                        │
│ 6. STANDALONE HTML EXPERIMENT REPORT                                   │
│    Emits a self-contained HTML artifact with embedded Base64 static   │
│    Matplotlib charts, comparative tables, and privacy masking.         │
│                                                                        │
│ 7. ISOLATED CLI ENTRY POINT                                            │
│    Invoked via a dedicated module router; zero changes to menu_v2.py.  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Selected Configuration Matrix `[SELECTED DECISION]`

Forensic inspection confirms that `CipherFactory` currently registers only AES, supporting key sizes 128, 192, and 256 bits in ECB and CBC modes. The active configuration space is strictly the **6 supported AES configurations**:

| ID | Configuration Name | Algorithm | Key Size (bits) | Mode | IV Required? | Cryptographic Reality Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CFG-1** | `AES-128-CBC` | AES | 128 | CBC | Yes (16 bytes) | `CBC — confidentiality only` |
| **CFG-2** | `AES-192-CBC` | AES | 192 | CBC | Yes (16 bytes) | `CBC — confidentiality only` |
| **CFG-3** | `AES-256-CBC` | AES | 256 | CBC | Yes (16 bytes) | `CBC — confidentiality only` |
| **CFG-4** | `AES-128-ECB` | AES | 128 | ECB | No (`None`) | `ECB — pattern leakage (demonstration only)` |
| **CFG-5** | `AES-192-ECB` | AES | 192 | ECB | No (`None`) | `ECB — pattern leakage (demonstration only)` |
| **CFG-6** | `AES-256-ECB` | AES | 256 | ECB | No (`None`) | `ECB — pattern leakage (demonstration only)` |

### Selection Scope Enforcements `[SELECTED DECISION]`
- Neither CBC nor ECB is designated as a "recommended default" in the benchmark engine.
- AES-CBC is explicitly described in reports as providing **confidentiality only** (no message authentication, integrity, or AEAD).
- AES-ECB is explicitly described as insecure for structured data due to identical block leakage.
- Blowfish, RSA, Classical ciphers, ChaCha20, and AES-GCM are **strictly excluded** from the configuration matrix.

---

## 7. Selected Experimental Methodology `[SELECTED DECISION]`

The laboratory experiment adheres strictly to the following scientific and cryptographic protocol:

### 7.1 Input Workload Protocol
- **Single Read:** The target file is opened in binary mode and read **once** into memory via `FileHandler.read_bytes(path)`.
- **Immutability:** The disk file is closed immediately and never written to, overwritten, or modified.
- **Fairness:** All 6 configurations evaluate the **exact same immutable in-memory `bytes` sequence**.

### 7.2 Cryptographic Setup Protocol (Unmeasured)
- **Key Generation:** For each configuration, a cryptographically secure random key of appropriate length (16, 24, or 32 bytes) is generated once outside the timing loop via `cipher.generate_key()`.
- **IV Generation:**
  - For CBC mode: A 16-byte random IV is generated once outside the timing loop via `cipher.generate_iv()`.
  - For ECB mode: `iv = None`.
- **Ciphertext Preparation:** Before decryption timing begins, the cipher encrypts the payload once in memory to produce `ciphertext`.
- **Round-Trip Pre-Check:** Pre-benchmark round-trip integrity is verified once:
  ```python
  decrypted_check = cipher.decrypt(ciphertext, key, iv)
  if decrypted_check != payload:
      # Handled via failure model (Section 13)
  ```
- **Reuse Across Timing Iterations:** The single key, IV, and prepared ciphertext are reused across all warmup and measured timing iterations of that configuration.
- **Setup Boundary:** All key generation, IV generation, ciphertext preparation, and round-trip verification occur **outside the measured timing boundary**.

### 7.3 Microbenchmark Timing Protocol (Measured)
- **Invocation Contract:** The experiment invokes the frozen decorator `@PerformanceTimer.measure_time_with_warmup()` with default arguments (no custom timing loops).
- **Encryption Timing:**
  ```python
  @PerformanceTimer.measure_time_with_warmup()
  def _timed_encrypt():
      return cipher.encrypt(payload, key, iv)
  final_ciphertext, enc_stats = _timed_encrypt()
  ```
- **Decryption Timing:**
  ```python
  @PerformanceTimer.measure_time_with_warmup()
  def _timed_decrypt():
      return cipher.decrypt(ciphertext, key, iv)
  final_plaintext, dec_stats = _timed_decrypt()
  ```
- **Iteration Invariant:** Exactly 5 unmeasured warmup iterations and 30 measured iterations are executed per operation per configuration.
- **Timing Isolation:** The timed block contains strictly the call to `cipher.encrypt()` or `cipher.decrypt()`. Disk I/O, hash calculation, metric ingestion, and report generation are excluded from the measured timing boundary.

---

## 8. Performance Measurement Model `[SELECTED DECISION]`

### 8.1 Metric Ingestion via Two MetricCollectors
Because the frozen `MetricCollector` DataFrame schema lacks an `operation` column (`encrypt` vs `decrypt`), passing both operations to one collector causes duplicate key collisions in `GraphGenerator`.
- **Selection Decision:** The experiment maintains **two separate `MetricCollector` instances**:
  1. `encryption_collector = MetricCollector()`
  2. `decryption_collector = MetricCollector()`
- Each collector ingests the exact dictionary expected by `MetricCollector.add_metric()`:
  ```python
  metric_data = {
      'algorithm': config["algorithm"],
      'key_size': config["key_size"],
      'mode': config["mode"],
      'data_size_bytes': len(payload),
      'raw_times_ms': stats_dict['raw_times_ms']
  }
  ```

### 8.2 Statistical Aggregation Invariants
Both collectors automatically compute and retain:
- Sample Count ($N = 30$).
- Mean execution time ($\mu$) in milliseconds.
- Median execution time ($M$) in milliseconds.
- Sample standard deviation ($\sigma$, $ddof=1$) in milliseconds.
- Minimum and Maximum execution time in milliseconds.
- Quartiles $Q1$ (25th percentile), $Q3$ (75th percentile), and Interquartile Range ($IQR = Q3 - Q1$).
- Tukey Fences ($[Q1 - 1.5 \times IQR, Q3 + 1.5 \times IQR]$) and outlier count. Outliers are retained in primary statistics.
- Binary Megabyte Throughput ($T$):
  $$T = \frac{\text{data\_size\_bytes} / 1{,}048{,}576}{\mu / 1{,}000} \quad (\text{MB/s})$$

### 8.3 Zero-Byte Payload Semantics
- When input file size is 0 bytes (`data_size_bytes == 0`):
  - Execution latency is measured and reported normally (reflects PKCS#7 block padding and single-block AES transform overhead).
  - Throughput is reported as **`N/A`** across tables and reports, accompanied by the note:
    *"Not applicable for zero-byte payload; latency reflects fixed block padding and encryption overhead."*

---

## 9. Ciphertext Analysis `[SELECTED DECISION]`

All ciphertext and expansion metrics are derived directly from the realized outputs of the frozen cryptographic engine:

```python
plaintext_size_bytes = len(payload)
ciphertext_size_bytes = len(ciphertext)
padding_overhead_bytes = ciphertext_size_bytes - plaintext_size_bytes
expansion_percentage = (
    (padding_overhead_bytes / plaintext_size_bytes) * 100.0 
    if plaintext_size_bytes > 0 else float("nan")
)
```

### Derived Boundary Truths
- **Zero-Byte File (0 B):** `ciphertext_size_bytes = 16`, `padding_overhead_bytes = 16`, `expansion_percentage = N/A`.
- **Block Boundary File (16 B):** `ciphertext_size_bytes = 32`, `padding_overhead_bytes = 16` (full block of padding added per PKCS#7), `expansion_percentage = 100.0%`.
- **Near-Boundary File (15 B):** `ciphertext_size_bytes = 16`, `padding_overhead_bytes = 1`, `expansion_percentage = 6.67%`.
- **Near-Boundary File (17 B):** `ciphertext_size_bytes = 32`, `padding_overhead_bytes = 15`, `expansion_percentage = 88.24%`.

No PKCS#7 mathematical formulas or padding routines are independently re-implemented.

---

## 10. Security Experiment Scope `[SELECTED DECISION]`

Security analysis is treated as an **independent, decoupled, and optional** experiment. It is never entangled with the performance timing loop.

### 10.1 Selected Security Metrics (Opt-in via `--security` or Wizard Prompt)
1. **Plaintext Avalanche Effect:**
   - **Protocol:** $P_1 = \text{payload}$; $P_2 = \text{bytearray}(P_1)$; flip 1 bit: $P_2[0] \oplus= 0x01$.
   - **Execution:** Invokes frozen `SecurityEvaluator.calculate_avalanche_effect(P_1, bytes(P_2), cipher, key, iv)`.
   - **CBC vs. ECB Contract:** ECB receives `iv = None`; CBC receives the configuration's generated IV.
   - **Zero-Byte Rule:** If `len(payload) == 0`, avalanche effect is skipped: *"Diffusion metrics require non-empty payload."*
2. **Key Sensitivity:**
   - **Protocol:** $K_1 = \text{key}$; $K_2 = \text{bytearray}(K_1)$; flip 1 bit: $K_2[0] \oplus= 0x01$.
   - **Execution:** Invokes frozen `SecurityEvaluator.test_key_sensitivity(cipher, P_1, K_1, bytes(K_2), iv)`.
   - **Zero-Byte Rule:** If `len(payload) == 0`, key sensitivity is skipped.
3. **BMP Structural Leakage Guard:**
   - Arbitrary user files (text, binaries, PDF) are **strictly forbidden** from being passed to `SecurityEvaluator.test_ecb_weakness()`.
   - Only if the file possesses a valid 54-byte BMP header (`b'BM'`, 24 bpp, uncompressed) may `test_ecb_weakness()` be executed. For all non-BMP files, structural pattern analysis reports: *"Structural pattern test is specific to 24-bpp uncompressed BMP images."*

### 10.2 Scientific Interpretation Guard
- All security sections in terminal cards and HTML reports must display:
  > *"Notice: These figures represent empirical diffusion measurements under controlled 1-bit mutations using SecurityEvaluator. They do not constitute a comprehensive security audit and cannot be used to declare one cipher configuration universally more secure than another."*
- Prohibits claiming that AES-256 is "more secure" than AES-128 simply due to a minor variance in avalanche percentage.

---

## 11. Architecture Decision `[SELECTED DECISION]`

### 11.1 Package Namespace: `src/analysis_lab/`
To guarantee 100% immutability of the frozen V1 and V2 codebases, the new capability is placed strictly within a **dedicated post-V2 package**:
- **Source Package:** `src/analysis_lab/`
- **Test Package:** `tests/analysis_lab/`
- Zero new files in `src/cli_v2/` or `tests/cli_v2/`.

```text
src/analysis_lab/
├── __init__.py                # Package version and export definitions
├── models.py                  # Immutable dataclasses (FileMetadata, ConfigurationResult, FileAnalysisResult)
├── experiment.py              # PerformanceExperiment (in-memory timing, MetricCollector integration)
├── ciphertext_analyzer.py     # CiphertextAnalyzer (padding and expansion derivation)
├── security_experiment.py     # SecurityExperiment (optional diffusion evaluation)
├── report.py                  # FileAnalysisReportGenerator (HTML assembly, Base64 charts)
├── runner.py                  # FileAnalysisRunner (preflight, orchestration, error isolation)
└── cli.py                     # Dedicated CLI entry point (subcommands & guided wizard)

tests/analysis_lab/
├── __init__.py
├── test_models.py
├── test_experiment.py
├── test_ciphertext_analyzer.py
├── test_security_experiment.py
├── test_report.py
├── test_runner.py
└── test_cli.py
```

### 11.2 Modular Separation of Concerns
Each module has a strict, single responsibility:
- `models.py`: Defines pure data containers; zero business logic.
- `experiment.py`: Pure microbenchmark runner; communicates only with V1 `CipherFactory`, `PerformanceTimer`, and `MetricCollector`.
- `ciphertext_analyzer.py`: Stateless derivation utility.
- `security_experiment.py`: Isolated cryptanalysis runner; communicates only with `SecurityEvaluator`.
- `report.py`: HTML compiler; communicates only with `GraphGenerator` and `FileHandler`.
- `runner.py`: High-level controller; coordinates file reading, preflight checks, experiment execution, and failure logging.
- `cli.py`: User interface router; handles arguments and terminal formatting.

---

## 12. CLI / UX Decision `[SELECTED DECISION]`

### 12.1 Invocation Model
The feature is launched strictly via its dedicated entry point:
```bash
# Non-interactive direct execution:
python -m src.analysis_lab.cli --input data/input/sample.txt [OPTIONS]

# Interactive guided wizard:
python -m src.analysis_lab.cli
```
`src/cli_v2/menu_v2.py` remains 100% frozen and unmodified.

### 12.2 Command-Line Arguments & Options
| Argument / Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--input`, `-i` | Path | None | Path to input file (triggers direct CLI mode). If omitted, launches interactive wizard. |
| `--output`, `-o` | Path | `results/reports/` | Destination path for HTML report. |
| `--skip-decryption` | Flag | `False` | Omit decryption microbenchmarks (run encryption only). |
| `--security` | Flag | `False` | Run optional security diffusion analysis (Avalanche & Key Sensitivity). |
| `--max-size-mb` | Integer | `100` | Operational file-size ceiling in megabytes. |
| `--no-open` | Flag | `False` | Do not automatically launch the HTML report in web browser. |
| `--include-absolute-path`| Flag | `False` | Include absolute file path in report (default: masked for privacy). |
| `--no-hash` | Flag | `False` | Suppress SHA-256 fingerprint in report for privacy. |
| `--force` | Flag | `False` | Override operational size warning/ceiling. |
| `--verbose`, `-v` | Flag | `False` | Display detailed tracebacks on errors. |

### 12.3 Interactive Wizard Flow (When `--input` is omitted)
```text
Step 1: Input File Selection (FilePicker path browse / drag-and-drop clean_path)
Step 2: Preflight Inspection Display (size, type, SHA-256 fingerprint)
Step 3: Configuration Scope Confirmation (All 6 AES configs)
Step 4: Operational Options (Include decryption? [Y/n], Include security analysis? [y/N])
Step 5: Preflight Warning (if file > 30 MB, prompt confirmation with expected volume)
Step 6: Execution Progress Display (step-by-step console indicators)
Step 7: Post-Operation Summary Card (Presentation.format_summary_card)
Step 8: Auto-Open HTML Report Prompt (webbrowser dispatch)
```

---

## 13. Failure Model `[SELECTED DECISION]`

The laboratory implements strict **per-configuration error isolation**:

```text
               CONFIGURATION EXECUTION LOOP
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
         [ CONFIG 1..6 ]           [ UNCAUGHT ]
               │                         │
     ┌─────────┴─────────┐               ▼
     │ try:              │        Catch Expected Failures
     │   - Setup Key/IV  │        (OSError, ValueError, RuntimeError)
     │   - Round-trip    │        Translate via ErrorTranslator
     │   - Timed Encrypt │        Set status = "FAILED"
     │   - Timed Decrypt │        Capture error_message
     │ except (OSError,  │        Log to Result Container
     │         ValueError,│              │
     │         RuntimeError):│           ▼
     └─────────┬─────────┘        Continue Next Config
               ▼                         │
        Record SUCCESS                   │
               │                         │
               └────────────┬────────────┘
                            ▼
              Final Result: 5 SUCCESS, 1 FAILED
              Report Generates with Failure Banner
```

### Specific Failure Rules
1. **Round-Trip Pre-Check Failure:** If `cipher.decrypt(ciphertext, key, iv) != payload`, the configuration is marked as `FAILED` with `error_message = "Pre-benchmark round-trip check failed: restored plaintext did not match original input"`. Timing is not executed. Remaining configurations continue.
2. **Setup / Operational Failure:** If key generation, cipher instantiation, or cryptographic operations raise expected operational or cryptographic exceptions (`OSError`, `ValueError`, `RuntimeError`), the exception is caught, translated via `ErrorTranslator`, and recorded as `FAILED`. Remaining configurations continue.
3. **No Blanket Exception Swallowing:** Catching blanket `Exception` or `BaseException` is strictly prohibited in the configuration execution loop. Unexpected programming defects (such as `AttributeError`, `TypeError`, `KeyError`, `IndexError`, `NameError`) must not be silently disguised as benchmark failures; they must propagate to ensure defect visibility during development and testing.
4. **Report Generation Failure:** If Matplotlib or disk writing fails, the error is displayed via `ErrorTranslator.display_error()`, and raw summary metrics are dumped to terminal stdout so benchmark data is not lost.
5. **Zero Custom Exceptions:** The error model uses standard Python exceptions internally (`RuntimeError`, `ValueError`, `OSError`) and surfaces errors as structured fields on `ConfigurationResult`.

---

## 14. File-Size Operational Policy `[SELECTED DECISION]`

Distinguishing experimental methodology from operational UX safety:

### 14.1 Methodological Rule
The core microbenchmark engine is strictly whole-buffer based. It places zero arbitrary mathematical limits on byte arrays; any payload that can be allocated in RAM will execute.

### 14.2 Operational CLI/UX Safeguards
To protect workstation stability against excessive memory allocation ($~3 \times S$ peak RAM) and massive processing volumes ($\sim 420 \times S$ cumulative AES throughput before accounting for ciphertext padding size differences):
1. **Processing-Volume Qualification:**
   - 6 configurations $\times$ 35 iterations (5 warmup + 30 measured) = 210 encryption cycles of $S$ bytes ($210 \times S$ bytes).
   - 210 decryption cycles of $(S + \text{padding})$ bytes ($210 \times (S + \text{padding})$ bytes, where padding overhead is 1 to 16 bytes).
   - Total cumulative byte volume through AES is $420 \times S + (210 \times \text{padding})$ bytes ($\sim 420 \times S$ bytes before accounting for ciphertext padding size differences).
2. **Operational Warning Threshold (30 MB):**
   - In interactive mode: If file size exceeds 30 MB, display notice:
     *"Notice: File is {size} MB. Evaluating 6 configurations (35 cycles each) will process ~{size * 420 / 1024:.1f} GB through AES (before ciphertext padding differences). Proceed? [y/N]"*.
   - In non-interactive CLI mode: Emits a console warning and proceeds unless `--max-size-mb` is exceeded.
3. **Operational Ceiling (100 MB default):**
   - If file size exceeds 100 MB (or user-defined `--max-size-mb`), execution halts with exit code 1:
     *"Error: File size ({size} MB) exceeds laboratory ceiling (100 MB). The in-memory buffer lab is designed for files up to 100 MB. Use --force to override if system RAM permits."*
4. **Override Flag (`--force`):**
   - Allows users with high-memory workstations to analyze arbitrarily large files without artificial rejection.

---

## 15. Reporting & Privacy Decision `[SELECTED DECISION]`

The report is compiled as a self-contained, offline HTML document saved to `results/reports/file_analysis_<filename>_<timestamp>.html`.

### 15.1 Privacy & Path Masking Rules
- **Filename:** Displayed prominently (e.g. `report.txt`).
- **Relative Path:** Displayed by default (relative to working directory, or sanitized filename only).
- **Absolute Path:** Masked by default (`[OMITTED FOR PRIVACY]`). Only rendered if `--include-absolute-path` is explicitly passed.
- **SHA-256 Fingerprint:** Included by default as a 64-character lowercase hex string as a file-identity and reproducibility fingerprint; suppressed if `--no-hash` is passed.
- **Secret Hygiene:** Keys, IVs, and plaintext payloads are **never written to HTML**.
- **XSS Sanitization:** All dynamic strings, filenames, and paths pass through `html.escape(quote=True)`.

### 15.2 Report Structure & Terminology Discipline
```text
========================================================================
FILE-SPECIFIC ENCRYPTION ANALYSIS REPORT
========================================================================
1. Header & System Metadata
   - Target Filename, Relative Path, File Size, SHA-256 (optional)
   - UTC Timestamp, Python Version, Platform OS, Offline Badge
2. Executive Summary Cards
   - File Size, Tested Configs Count, Fastest Observed Encryption,
     Fastest Observed Decryption, Failure Count
3. Comparative Configuration Matrix
   - Table: Configuration, Ciphertext Size, Padding Added, Expansion %,
            Enc Latency, Enc Throughput, Dec Latency, Dec Throughput
4. Detailed Performance Analysis
   - Encryption Statistical Breakdown (Mean, Median, Std Dev, Min, Max, Outliers)
   - Decryption Statistical Breakdown (Mean, Median, Std Dev, Min, Max, Outliers)
   - Embedded Base64 Static Charts (Key Size Comparison, Mode Comparison)
5. Ciphertext & Padding Profile
   - PKCS#7 Padding overhead analysis and boundary behavior notes
6. Security & Diffusion Profile (Rendered if --security enabled)
   - Plaintext Avalanche Effect % and Key Sensitivity %
   - Cryptographic disclaimer regarding empirical diffusion limits
7. Experimental Methodology
   - 5 Warmup Cycles, 30 Measured Iterations, Tukey Fences (Q1 - 1.5*IQR),
     Binary MB Throughput, In-Memory Timing Boundary
8. Limitations & Scientific Caveats
   - Notice on small-file CPU jitter and non-generalizability
========================================================================
```

### 15.3 Terminology Restrictions
- The word **"Winner"** or **"Best Configuration"** is **strictly forbidden**.
- "Fastest" is strictly phrased as:
  **"Fastest observed configuration in this experiment (lowest sample mean latency)"**
  and must always display the underlying latency value.

---

## 16. Testing Strategy `[SELECTED DECISION]`

Testing is confined entirely to the new test directory `tests/analysis_lab/`. Existing test files remain immutable.

### 16.1 Test Suite Organization
| Test Module | Coverage Area | Key Verification Scenarios |
| :--- | :--- | :--- |
| `test_models.py` | Data structures | Immutability, default fields, serialization |
| `test_ciphertext_analyzer.py` | Padding derivation | 0 B, 15 B, 16 B, 17 B files; expansion calculation |
| `test_experiment.py` | Benchmarking engine | 5 warmup + 30 measured contract; two MetricCollectors; key/IV setup isolation |
| `test_security_experiment.py`| Security diffusion | Avalanche 1-bit flip; key sensitivity 1-bit flip; BMP guard |
| `test_report.py` | HTML compiler | Base64 chart embedding; XSS escaping; path masking; privacy flags |
| `test_runner.py` | Orchestration | Preflight checks; per-configuration failure isolation; size ceilings |
| `test_cli.py` | Interface router | Argument parsing; exit codes (0, 1, 2); direct vs interactive routing |

### 16.2 Behavioral Acceptance Invariants
- **Round-Trip Parity:** `decrypt(encrypt(P)) == P` verified across all 6 configurations.
- **Empty File Parity:** 0-byte file produces 16-byte ciphertext, measured latency, and throughput reported as `N/A`.
- **Block Boundary Parity:** 16-byte file produces 32-byte ciphertext with 16 bytes of padding.
- **Payload Agnosticism:** Raw binary bytes and multi-byte UTF-8 Unicode execute without exceptions.
- **Error Isolation:** A mocked exception in configuration #3 does not halt configurations #4–#6.
- **Regression Zero Defect:** All existing baseline tests continue to pass with zero regressions.

---

## 17. Dependencies & Non-Scope `[FROZEN CONSTRAINT]`

### 17.1 Zero New Dependencies
The feature uses strictly the existing dependencies specified in `requirements.txt`:
- Python standard library (`pathlib`, `time`, `hashlib`, `html`, `io`, `base64`, `argparse`, `dataclasses`, `webbrowser`)
- `cryptography` (for AES execution via frozen `AESCipher`)
- `matplotlib` (for static chart rendering via frozen `GraphGenerator`)
- `pandas` / `numpy` (for statistical aggregation via frozen `MetricCollector`)
- `pytest` (for test suite execution)

### 17.2 Strict Non-Scope Items
- Adding third-party libraries (e.g. `plotly`, `bokeh`, `psutil`, `click`, `rich`).
- Implementing RSA, Blowfish, Classical ciphers, ChaCha20, or AES-GCM.
- Streaming / chunked encryption for multi-gigabyte files.
- Modifying V1 source code or tests.
- Modifying V2 source code (`menu_v2.py`, `batch_orchestrator.py`, etc.) or tests.
- Integrating with the V2 interactive menu.
- Multi-threaded or distributed benchmark execution.

---

## 18. Deferred Items `[DEFERRED]`

The following architectural and cryptanalytic concepts are formally deferred to future milestones:

| Deferred Capability | Reason for Deferral | Future Target Milestone |
| :--- | :--- | :--- |
| **V2 Menu Integration** | Modifying `menu_v2.py` violates the V2 freeze; requires dedicated menu router refactor. | Future Major Release (e.g. V3.0) |
| **Novel ECB Block-Redundancy Metric** | Novel cryptanalytic metric ($N_{unique}/N_{total}$) requires independent peer research and validation. | Future Cryptanalysis Milestone |
| **Streaming / Chunked Encryption** | Buffer-based engine cannot stream; requires redesigning `CipherService` and `AESCipher`. | Future Major Core Revision |
| **Hardware Performance Counters** | Measuring CPU cycles / cache misses requires platform-specific C extensions or dependencies. | Deferred indefinitely |
| **Authenticated Ciphers (GCM / Poly1305)** | Not implemented in V1 core; requires AEAD engine implementation. | Post-V2 Cipher Expansion |

---

## 19. Traceability Matrix `[SELECTED DECISION]`

Every open decision and candidate recommendation from `POST-V2-FEAT-EXPLORE-004` is fully resolved:

| Exploration Item (`EXPLORE-004`) | Selection Decision (`SELECT-002`) | Architectural Rationale & Evidence | Implementation Consequence |
| :--- | :--- | :--- | :--- |
| **Package Namespace** (3 candidates) | **Selected:** `src/analysis_lab/` and `tests/analysis_lab/` | Completely preserves V1 and V2 immutability; avoids namespace collision; clean top-level domain. | Code created exclusively in `src/analysis_lab/`. |
| **File-Size Operational Policy** | **Selected:** 30 MB warning prompt; 100 MB ceiling with `--force` override | Grounded in memory working model ($~3 \times S$) and cumulative volume ($\sim 420 \times S$ before padding differences). Distinguishes UX safety from engine. | `runner.py` checks size in preflight; engine remains unconstrained. |
| **Decryption Scope / UX** | **Selected:** Experiment measures both; CLI defaults to both with `--skip-decryption` flag | Provides complete empirical file analysis while giving CLI users operational control. | `experiment.py` supports both; `cli.py` exposes toggle. |
| **Security Analysis Scope** | **Selected:** Decoupled, opt-in (`--security`); novel block metric **DEFERRED** | Performance is primary; prevents unvetted cryptanalytic claims; strictly uses existing `SecurityEvaluator`. | `security_experiment.py` created as separate runner. |
| **Report Privacy & SHA-256** | **Selected:** Relative path default; absolute masked; SHA-256 default with `--no-hash` flag | Prevents username/path leakage while providing a file-identity and reproducibility fingerprint by default. | `report.py` formats paths and conditionally renders hash. |
| **Round-Trip Failure Mechanism** | **Selected:** Pre-check outside timing; records failure; standard `RuntimeError` internally | Prevents broken ciphertexts in timing loop; avoids custom exception classes; preserves isolation. | `experiment.py` performs explicit check before timing. |
| **PerformanceTimer Timing Contract** | **Selected:** `@PerformanceTimer.measure_time_with_warmup()` with default 5/30 contract | Strictly preserves V1 timing methodology without custom timing loops or parameter overrides. | `experiment.py` calls decorator with zero arguments. |
| **MetricCollector Collision** | **Selected:** Two instances (`encryption_collector`, `decryption_collector`) | Frozen collector lacks `operation` column; avoids schema changes and `GraphGenerator` duplicate errors. | `experiment.py` instantiates and maintains two collectors. |
| **Zero-Byte File Throughput** | **Selected:** Latency measured; throughput reported as `N/A` | Mathematically and physically accurate; avoids claiming 0.0 MB/s transfer capacity. | `report.py` and models render `N/A` for zero-byte throughput. |
| **Padding Overhead Derivation** | **Selected:** Derived via `len(C) - len(P)` from realized ciphertext | Exact parity with `src/utils/padding.py` without replicating mathematical formulas. | `ciphertext_analyzer.py` computes length deltas. |

---

## 20. Acceptance Criteria `[FROZEN CONSTRAINT]` & `[SELECTED DECISION]`

Selection freeze and subsequent implementation acceptance require fulfilling all of the following verifiable conditions:

1. **V1 Immutability:** `git diff v1.0-release..HEAD -- src/core src/engines src/analyzers src/utils src/cli` is completely empty (0 files changed, 0 insertions, 0 deletions).
2. **V2 Source Immutability:** Zero existing files in `src/cli_v2/` are modified.
3. **Existing Test Immutability:** All existing test files in `tests/` and `tests/cli_v2/` remain bit-for-bit identical, and all existing baseline tests continue to pass with zero regressions.
4. **Permitted Location Isolation:** All new feature code is located strictly within `src/analysis_lab/`, and all new tests are located strictly within `tests/analysis_lab/`.
5. **Zero New Dependencies:** `requirements.txt` remains bit-for-bit identical to the release baseline.
6. **Configuration Matrix Coverage:** The experiment attempts all 6 supported configurations (AES 128/192/256 in ECB and CBC) for every valid input. A configuration failure is recorded without preventing remaining configurations from executing. A successful full run produces results for all six; a partial run contains explicit per-configuration failure accounting.
7. **PerformanceTimer Contract:** Each measured operation (encryption and decryption) strictly executes the frozen PerformanceTimer contract of 5 warmup and 30 measured iterations via `@PerformanceTimer.measure_time_with_warmup()`.
8. **Decoupled Security Execution:** Security diffusion analysis executes only when explicitly requested, uses only frozen `SecurityEvaluator` methods, and guards against arbitrary non-BMP files.
9. **Two-Collector Schema Integrity:** Encryption and decryption metrics are managed via separate `MetricCollector` instances without schema collisions.
10. **Zero-Byte Accuracy:** 0-byte input files produce 16-byte ciphertexts, measurable latency, and throughput reported as `N/A`.
11. **Standalone HTML Report:** A single-file, self-contained HTML report with embedded Base64 static Matplotlib charts is generated in `results/reports/`.
12. **Privacy Enforcement:** Generated HTML reports omit absolute system paths by default.
13. **Terminology Compliance:** Reports contain zero instances of "Winner" or universal "Best Configuration", and qualify "Fastest" strictly to the observed experiment.
14. **Error Isolation Resilience:** Single configuration failures do not abort remaining configurations or prevent report generation.

---

## 21. Selection Status & Implementation Authorization

```text
========================================================================
SELECTION STATUS:
REVISED PER INDEPENDENT AUDIT — READY FOR SELECTION FREEZE

IMPLEMENTATION AUTHORIZATION:
NOT AUTHORIZED
========================================================================
```

**Formal Governance Rule:** No production Python code, test files, or packages may be created until this Selection document has been independently audited, corrected if necessary, and formally approved.
