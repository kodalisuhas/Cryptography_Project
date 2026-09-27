# POST-V2 FEATURE EXPLORATION & ARCHITECTURAL DESIGN (EXPLORATION FINAL)
## FILE-SPECIFIC ENCRYPTION ANALYSIS LAB

**Document ID:** POST-V2-FEAT-EXPLORE-004 (Exploration FINAL)  
**Status:** EXPLORATION FINAL — READY FOR PROJECT-SPECIFIC SELECTION & METHODOLOGY DECISION  
**Date:** 2026-09-27  
**Author:** Antigravity Engineering (Forensic Architecture & Systems Analysis)  
**Target Milestone:** Post-V2 Additive Feature Initiation  
**Frozen Baselines:** 
- V1 Baseline: `v1.0-release` (`650bc7f80ada2c4c8e61a0c29b96e9b3a65cca0a`)
- V2 Baseline: `v2.0-release` (`9a4a11409919608817a3b8e3b56102d21a3184b3`)
- Main Branch HEAD: `8449fa1` (`release: promote V2.0 release to main`)

---

## Methodological Classification Key

To maintain strict scientific and architectural discipline, every assertion, finding, and proposal in this document is categorized under the following taxonomy:

- `[FROZEN CONSTRAINT]`: Inviolable baseline architectural boundary, frozen API contract, or immutability rule established in V1/V2 that cannot be modified.
- `[OBSERVED FACT]`: Verifiable, empirical property discovered through direct source code inspection and verified test suite execution.
- `[CANDIDATE DESIGN]`: Proposed, well-reasoned architectural approach under active review; not yet frozen.
- `[CANDIDATE ESTIMATE]`: Conceptual or analytical projection (e.g. memory scaling, volume); not an empirical fact or acceptance requirement.
- `[OPEN DECISION]`: Explicitly uncommitted design choice requiring stakeholder direction before selection.

---

## 1. Feature Intent & Problem Statement

### 1.1 Intent `[CANDIDATE DESIGN]`
The **File-Specific Encryption Analysis** feature provides a comparative empirical laboratory capability:
A user provides a single real-world file (e.g. `report.txt`, `data.bin`, `document.pdf`), and the system evaluates all **currently supported encryption configurations** against that exact file under strictly controlled laboratory conditions.

### 1.2 Core Value Proposition `[CANDIDATE DESIGN]`
- **Real-World Payload Behavior:** Replaces synthetic zero-byte arrays ($1\text{ KB}$, $1\text{ MB}$) with real-world user data, exposing actual latency, throughput, ciphertext size, and padding overhead.
- **Empirical Trade-Off Transparency:** Directly juxtaposes AES key sizes (128 vs. 192 vs. 256 bits) and cipher modes (CBC vs. ECB) across both encryption and decryption operations.
- **Strict Methodological Discipline:** Enforces fair comparison by ensuring all configurations execute against the identical in-memory byte sequence under the frozen V1 statistical measurement model.
- **Actionable Reporting:** Emits a self-contained HTML report with embedded comparative charts and statistical tables detailing empirical performance and security observations.

---

## 2. Current V1/V2 Baseline

### 2.1 Git Topology and Tag Verification `[OBSERVED FACT]`
- `v1.0-release` (`650bc7f80ada2c4c8e61a0c29b96e9b3a65cca0a`): Established the frozen core cryptographic primitives, engines, analyzers, utilities, and V1 CLI.
- `v2.0-release` (`9a4a11409919608817a3b8e3b56102d21a3184b3`): Completed the guided usability layer, sidecar key persistence, folder batch operations, and HTML reporting.
- Current `origin/main` commit: `8449fa1` (`release: promote V2.0 release to main`).

### 2.2 Test Suite Verification Baseline `[OBSERVED FACT]`
Execution of the automated test suite under Python 3.13.1 on Windows 11 Enterprise confirms:
- **Full Repository Suite:** 886 collected tests $\rightarrow$ **879 passed, 7 skipped in 113.49s** (100% clean exit code 0).
- **Frozen V1 Suite (`tests/` excluding `tests/cli_v2`):** **434 passed, 2 skipped** (100% parity with V1 release gate).
- **Frozen V2 Suite (`tests/cli_v2`):** **445 passed, 5 skipped** (100% parity with V2 release gate).
- *Skipped Tests:* 7 tests skipped strictly due to non-interactive headless TTY detection and Windows Explorer GUI invocation mocking.

### 2.3 Dependency Baseline `[FROZEN CONSTRAINT]`
`requirements.txt` is frozen and contains zero non-standard runtime dependencies outside of:
`cryptography`, `matplotlib`, `pandas`, `seaborn`, `numpy`, `tabulate`, `pyyaml`, `pytest`.  
Zero new third-party packages or external libraries may be introduced.

---

## 3. Existing Components Reusable

A forensic audit of the V1 and V2 layers indicates substantial reusability. The new feature requires **zero new cryptographic algorithms** and **zero new benchmark math**:

| Existing Component | Source File | Classification | Capability & Behavioral Contract | Reusability Role |
| :--- | :--- | :--- | :--- | :--- |
| `AESCipher` | `src/core/aes_cipher.py` | `[FROZEN CONSTRAINT]` | Deterministic AES-128/192/256 in ECB/CBC modes with PKCS#7 padding | Core cryptographic execution |
| `CipherFactory` | `src/engines/cipher_factory.py` | `[FROZEN CONSTRAINT]` | Registry for cipher creation via `create_cipher(algo, key_size, mode)` | Cipher instantiation |
| `CipherService` | `src/engines/cipher_service.py` | `[FROZEN CONSTRAINT]` | High-level `encrypt_data()` and `decrypt_data()` | In-memory encryption & decryption |
| `PerformanceTimer` | `src/analyzers/performance_timer.py` | `[FROZEN CONSTRAINT]` | Provides `@measure_time_with_warmup(iterations=30, warmup=5)` | High-resolution microbenchmark timing |
| `MetricCollector` | `src/analyzers/metric_collector.py` | `[FROZEN CONSTRAINT]` | Computes mean, median, std_dev, min, max, Q1, Q3, IQR, Tukey fences, binary MB throughput | Statistical aggregation & outlier tracking |
| `GraphGenerator` | `src/analyzers/graph_generator.py` | `[FROZEN CONSTRAINT]` | `generate_key_size_comparison()` and `generate_mode_comparison()` accept single-size DataFrames | Matplotlib figure generation |
| `SecurityEvaluator`| `src/analyzers/security_evaluator.py` | `[FROZEN CONSTRAINT]` | Bitwise Hamming distance, 1-bit flip avalanche effect, key sensitivity | Security diffusion evaluation |
| `FileHandler` | `src/utils/file_handler.py` | `[FROZEN CONSTRAINT]` | Static binary `read_bytes()`, `write_text()`, file size | Non-destructive file I/O |
| `FilePicker` | `src/cli_v2/file_picker.py` | `[FROZEN CONSTRAINT]` | Path quote stripping (`clean_path`), `format_size` | Path resolution and size display |
| `Presentation` | `src/cli_v2/presentation.py` | `[FROZEN CONSTRAINT]` | Summary card formatting, progress bars, browser auto-open | Terminal presentation & browser dispatch |
| `ReportGenerator` | `src/cli_v2/report_generator.py` | `[FROZEN CONSTRAINT]` | Base64 PNG chart conversion (`figure_to_base64`), CSS styling | Styling and visual chart encoding |
| `ErrorTranslator` | `src/cli_v2/error_translator.py` | `[FROZEN CONSTRAINT]` | 3-tier user-friendly diagnostic translations | Failure message formatting |

---

## 4. Current Supported Configuration Matrix

### 4.1 Implementation Reality `[OBSERVED FACT]`
Forensic inspection of `src/core/aes_cipher.py`, `src/engines/cipher_factory.py`, and `src/core/` reveals:
- `blowfish_cipher.py`, `classical_ciphers.py`, and `rsa_cipher.py` are empty placeholder stubs.
- Only the `AES` cipher family is registered in `CipherFactory`.
- The valid AES key sizes are `(128, 192, 256)`.
- The valid AES modes are `("ECB", "CBC")`.

Thus, the **exact initial configuration space** is strictly the 6 supported AES configurations:

| ID | Configuration Name | Algorithm | Key Size (bits) | Mode | IV Required? | Cryptographic Reality Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CFG-1** | `AES-128-CBC` | AES | 128 | CBC | Yes (16 bytes) | CBC — confidentiality only (No AEAD/integrity) |
| **CFG-2** | `AES-192-CBC` | AES | 192 | CBC | Yes (16 bytes) | CBC — confidentiality only (No AEAD/integrity) |
| **CFG-3** | `AES-256-CBC` | AES | 256 | CBC | Yes (16 bytes) | CBC — confidentiality only (No AEAD/integrity) |
| **CFG-4** | `AES-128-ECB` | AES | 128 | ECB | No (`None`) | ECB — pattern leakage (Demonstration only) |
| **CFG-5** | `AES-192-ECB` | AES | 192 | ECB | No (`None`) | ECB — pattern leakage (Demonstration only) |
| **CFG-6** | `AES-256-ECB` | AES | 256 | ECB | No (`None`) | ECB — pattern leakage (Demonstration only) |

*Scope Enforcement `[FROZEN CONSTRAINT]`:* GCM, ChaCha20, RSA, Blowfish, and ECC are **not implemented** in the project and must NOT be referenced as active choices. Neither CBC nor ECB is designated as a "recommended default" in the experiment design.

---

## 5. Architectural Separation of Concerns

### 5.1 Decoupled Architecture Model `[CANDIDATE DESIGN]`
Rather than creating a single monolithic service responsible for file I/O, micro-benchmarks, security analysis, charts, and report generation, the post-V2 architecture enforces a clean separation of concerns:

```text
                             USER FILE
                                 │
                                 ▼
                     [ FileAnalysisRunner ]
                                 │
            ┌────────────────────┼────────────────────┐
            ▼                    ▼                    ▼
   [PerformanceExperiment]  [CiphertextAnalysis] [SecurityExperiment]
            │                    │                  (Candidate/Opt-In)
            ▼                    │                    │
   [ MetricCollector ]           │                    ▼
    (Enc & Dec Collectors)       │            [SecurityEvaluator]
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 ▼
                    [ FileAnalysisResult ]
                      (Unified Data Model)
                                 │
            ┌────────────────────┴────────────────────┐
            ▼                                         ▼
   [ GraphGenerator ]                        [ ReportGenerator ]
    (Embedded Charts)                         (HTML Assembly)
            │                                         │
            └────────────────────┬────────────────────┘
                                 ▼
         [ Self-Contained HTML Report with Static Charts ]
```

### 5.2 Component Responsibilities `[CANDIDATE DESIGN]`
1. **`FileAnalysisRunner`**: High-level workflow controller. Owns file preflight, user interaction, progress tracking, and error isolation.
2. **`PerformanceExperiment`**: Pure in-memory microbenchmark executor. Owns configuration looping, key/IV management, and delegating to frozen `PerformanceTimer` and `MetricCollector`.
3. **`CiphertextAnalysis`**: Ciphertext characteristic extractor. Directly derives ciphertext size, padding overhead, and expansion ratio from produced ciphertexts.
4. **`SecurityExperiment`**: Optional cryptanalytic diffusion evaluator. Strictly decoupled from performance timing; selectively runs `SecurityEvaluator` methods.
5. **`FileAnalysisResult`**: Immutable dataclass encapsulating all results, metadata, metrics, and failure logs.
6. **`FileAnalysisReportGenerator`**: Presentation assembler. Converts `FileAnalysisResult` into a self-contained HTML report with embedded Base64 static charts and statistical tables.

---

## 6. PerformanceTimer Contract & Measurement Model

### 6.1 Reusing the Frozen PerformanceTimer Contract `[FROZEN CONSTRAINT]`
Forensic analysis of `src/analyzers/performance_timer.py` confirms:
```python
class PerformanceTimer:
    @staticmethod
    def measure_time_with_warmup(iterations: int = 30, warmup: int = 5):
        # 1. Runs warmup iterations (unmeasured)
        # 2. Runs iterations using time.perf_counter()
        # 3. Retains final iteration result
        # 4. Returns (final_result, {"raw_times_ms": [...]})
```
- In V1 `BenchmarkService`, the decorator is invoked without arguments: `@PerformanceTimer.measure_time_with_warmup()`.
- **Architectural Resolution:** The new feature **must not redefine or configure custom timing parameters**. It calls `@PerformanceTimer.measure_time_with_warmup()` with its frozen default contract (30 measured iterations, 5 warmup iterations).
- `PerformanceTimer` strictly owns the timing loop, high-resolution timestamps, and raw timing array aggregation.

### 6.2 Measurement Boundary Reconciliation `[CANDIDATE DESIGN]`
A strict, unambiguous boundary exists between measured cryptographic execution and unmeasured system operations:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        MEASUREMENT BOUNDARIES                          │
├───────────────────────────────────┬────────────────────────────────────┤
│       UNMEASURED SETUP & SYSTEM   │     MEASURED IN-MEMORY CRYPTO      │
├───────────────────────────────────┼────────────────────────────────────┤
│ • Disk read of input file (once)  │ • cipher.encrypt(payload, key, iv) │
│ • SHA-256 fingerprint generation  │ • cipher.decrypt(ciphertext, k, iv)│
│ • Key generation via cipher       │ • (Follows actual implementation of│
│ • IV generation via cipher        │ •  AESCipher.encrypt/decrypt.      │
│ • Pre-benchmark round-trip check  │ •  No padding operation is         │
│ • HTML report generation & I/O    │ •  independently added by feature.)│
└───────────────────────────────────┴────────────────────────────────────┘
```

**Explicit Implementation Truth `[FROZEN CONSTRAINT]`:** The measurement boundary follows the actual implementation of `AESCipher.encrypt()` and `AESCipher.decrypt()`. No padding operation is independently added by the new feature.

### 6.3 Decryption Benchmarking Methodology `[CANDIDATE DESIGN]`
Because `BenchmarkService` only benchmarks encryption, decryption benchmarking is explicitly reconciled with the frozen methodology:
1. **Pre-Timing Preparation (Unmeasured Setup):**
   - The cipher instance encrypts the payload once to obtain `ciphertext`.
   - In-memory round-trip verification is validated once:
     ```python
     decrypted_test = cipher.decrypt(ciphertext, key, iv)
     if decrypted_test != payload:
         # Candidate design: If round-trip validation fails, the configuration is
         # marked as failed and excluded from benchmarking.
         # Exact exception/reporting mechanism to be finalized during Selection.
         raise RuntimeError(
             f"Pre-benchmark round-trip check failed for {cipher_name}: "
             f"decrypted plaintext did not match original input."
         )
     ```
     *(Note: Explicit runtime check used; Python assertions are not used as they can be disabled via optimization flags).*
   - `[CANDIDATE DESIGN]` The round-trip check is a new feature-level validation; standard `RuntimeError` or a structured failure result is used subject to selection approval.
2. **Decryption Microbenchmark Execution (Measured):**
   - The exact same immutable `ciphertext`, `key`, and `iv` generated during preparation are supplied to the decryption timing loop.
   - Decryption is timed via `@PerformanceTimer.measure_time_with_warmup()`:
     ```python
     @PerformanceTimer.measure_time_with_warmup()
     def _measure_decrypt():
         return cipher.decrypt(ciphertext, key, iv)
     recovered, dec_stats = _measure_decrypt()
     ```
   - Key generation, ciphertext creation, round-trip assertion, and file I/O are **excluded from the measured timing boundary**.
   - All 35 iterations (5 warmup + 30 measured) decrypt the identical in-memory ciphertext buffer.

---

## 7. MetricCollector Integration & Throughput Semantics

### 7.1 Schema Rigidity & Two-Collector Architecture `[OBSERVED FACT]`
`MetricCollector` has a strictly frozen DataFrame schema:
`['algorithm', 'key_size', 'mode', 'data_size_bytes', 'count', 'mean_time_ms', 'median_time_ms', 'std_dev_time_ms', 'min_time_ms', 'max_time_ms', 'q1_ms', 'q3_ms', 'iqr_ms', 'outlier_count', 'throughput_mb_s', 'memory_delta_mb']`.
- `MetricCollector` has NO `operation` field (`encrypt` vs `decrypt`).
- Passing both encryption and decryption metrics into a single `MetricCollector` would create duplicate `(key_size, mode, data_size_bytes)` keys.
- `GraphGenerator` explicitly rejects duplicate configuration keys with `ValueError("Duplicate configurations found for key_size, mode, and data_size_bytes.")`.
- **Architectural Resolution `[CANDIDATE DESIGN]`:** The experiment maintains **two separate `MetricCollector` instances**:
  1. `encryption_collector = MetricCollector()`
  2. `decryption_collector = MetricCollector()`
- This avoids schema collisions, prevents `GraphGenerator` exceptions, and cleanly isolates statistical properties.

### 7.2 Zero-Byte File Throughput Semantics `[OBSERVED FACT]` & `[CANDIDATE DESIGN]`
Forensic analysis of `MetricCollector.py` (lines 86-93) shows:
```python
if mean <= 0:
    throughput_mb_s = np.nan
else:
    mb_size = data_size_bytes / 1048576.0
    time_s = mean / 1000.0
    throughput_mb_s = mb_size / time_s
```
- For an empty file (`data_size_bytes == 0`), the formula evaluates mathematically to `0.0 / time_s = 0.0 MB/s`.
- However, physically and scientifically, claiming "Throughput: 0.00 MB/s" falsely implies a stalled pipeline or zero transmission capacity.
- In reality, an empty file produces 16 bytes of ciphertext (PKCS#7 padding block) with measurable execution latency reflecting the fixed block cipher transform.
- **Reporting Resolution `[CANDIDATE DESIGN]`:**
  - In presentation tables and HTML reports, when `data_size_bytes == 0`:
    - Latency is reported normally (e.g. `0.021 ms`).
    - Throughput is reported as **`N/A`** (accompanied by an explanatory note: *"Not applicable for zero-byte payload; latency reflects fixed block padding and encryption overhead"*).

---

## 8. Ciphertext Characteristics & Padding Derivation

### 8.1 Reusing Frozen Padding Behavior `[FROZEN CONSTRAINT]`
Rather than re-implementing mathematical PKCS#7 formulas ($16 - (size \pmod{16})$) in the new feature, all ciphertext metrics are derived directly from the behavior of the frozen cryptographic core:

```python
# Realized experimental values from frozen AESCipher:
ciphertext_size_bytes = len(ciphertext)
plaintext_size_bytes = len(payload)
padding_overhead_bytes = ciphertext_size_bytes - plaintext_size_bytes
expansion_percentage = (
    (padding_overhead_bytes / plaintext_size_bytes) * 100.0 
    if plaintext_size_bytes > 0 else float("nan")
)
```
- For a 0-byte file: `ciphertext_size_bytes = 16`, `padding_overhead_bytes = 16`.
- For a 16-byte file: `ciphertext_size_bytes = 32`, `padding_overhead_bytes = 16` (full block of padding).
- For a 15-byte file: `ciphertext_size_bytes = 16`, `padding_overhead_bytes = 1`.
- This ensures 100% fidelity to `src/utils/padding.py` and `src/core/aes_cipher.py` without replicating logic.

---

## 9. Security Analysis Scope & Candidate Methodologies

### 9.1 Boundaries of Frozen `SecurityEvaluator` `[OBSERVED FACT]`
- `calculate_avalanche_effect(p1, p2, cipher, key, iv)` strictly requires `calculate_hamming_distance(p1, p2) == 1`.
- `test_key_sensitivity(cipher, p, k1, k2, iv)` strictly requires `calculate_hamming_distance(k1, k2) == 1`.
- `test_ecb_weakness(image_bytes, key, iv)` strictly requires a valid 24-bit uncompressed BMP image header.
- Empty payloads (`len(p) == 0`) raise `ValueError("Inputs cannot be empty.")`.

### 9.2 Arbitrary File Security Evaluation `[CANDIDATE DESIGN]`
1. **Plaintext Avalanche Effect on User File:**
   - Create $P_1 = \text{payload}$.
   - Create $P_2 = \text{bytearray}(P_1)$; flip 1 bit: $P_2[0] \oplus= 0x01$.
   - Execute `SecurityEvaluator.calculate_avalanche_effect(P_1, bytes(P_2), cipher, key, iv)`.
2. **Key Sensitivity on User File:**
   - Create $K_1 = \text{key}$.
   - Create $K_2 = \text{bytearray}(K_1)$; flip 1 bit: $K_2[0] \oplus= 0x01$.
   - Execute `SecurityEvaluator.test_key_sensitivity(cipher, P_1, K_1, bytes(K_2), iv)`.
3. **Qualification of Results `[CANDIDATE DESIGN]`:**
   - The report must explicitly state: **"Empirical diffusion measurements using the existing SecurityEvaluator, not a complete security assessment of the file or cipher."**
   - The report must not imply that one configuration is more secure based solely on an avalanche percentage.
4. **Empty File Handling:**
   - If `len(payload) == 0`, avalanche and key sensitivity are cleanly bypassed: *"Diffusion metrics require non-empty payload."*
5. **BMP Weakness Guard:**
   - Arbitrary user files (e.g. `report.txt`, `data.bin`) must **never** be passed to `SecurityEvaluator.test_ecb_weakness()`.
   - Only if a file has the valid 54-byte BMP header with signature `b'BM'`, 24 bpp, and uncompressed geometry may `test_ecb_weakness()` be invoked.

### 9.3 Candidate Block Redundancy Analysis `[OPEN DECISION]`
- Proposing an empirical plaintext block redundancy metric ($N_{unique\_16B\_blocks} / N_{total\_16B\_blocks}$) to illustrate ECB pattern vulnerability on non-BMP files is a **new analytical methodology**, not merely presentation.
- **Decision:** Classified as a `CANDIDATE EXPERIMENTAL PROPOSAL`. It will be omitted from the initial core performance baseline and held for independent cryptanalytic review.

---

## 10. Operational Scale & Memory Working Model

### 10.1 Working Set Reasoning `[CANDIDATE ESTIMATE]`
The project's engine is whole-buffer based (`FileHandler.read_bytes`).
- The experiment performs 6 configurations × 2 directions × 35 iterations.
- At any instant in memory:
  - Original payload buffer: $S$ bytes.
  - Active ciphertext buffer: $\approx S + \text{padding}$ bytes.
  - Transient iteration buffer: $\approx S + \text{padding}$ bytes (garbage collected per iteration).
- **Working-Set Reasoning Only:** Peak memory scales roughly linearly with file size in Python; actual peak memory must be measured if memory profiling becomes a formal feature.
- **Execution Duration Statement:** Actual elapsed wall-clock time depends on the hardware, CPU, Python runtime version, file size, padding overhead, and concurrent system conditions. No fixed wall-clock guarantees are made.

### 10.2 File Size Operational Policy `[OPEN DECISION]`
- **Status:** **`CANDIDATE RECOMMENDATION — NOT APPROVED`** *(Requires explicit stakeholder approval before implementation)*.
- Candidate Options:
  - *Option 1:* Configurable operational warning threshold (candidate: 25 MB). Prompts user confirmation indicating expected processing duration.
  - *Option 2:* Configurable operational ceiling (candidate: 100 MB). Prevents out-of-memory errors on buffer-based processing.
- The acceptance criteria must not silently turn these candidate numbers into immutable requirements.

---

## 11. Architectural Location & Version Boundary

### 11.1 The `src/cli_v2/` Contradiction `[OBSERVED FACT]`
- V2 was audited, frozen, tagged `v2.0-release`, and promoted to `main`.
- While adding new files into `src/cli_v2/` technically avoids modifying existing files, it conceptually pollutes the frozen V2 release namespace and blurs version boundaries.

### 11.2 Candidate Location Options `[OPEN DECISION]`
- **Status:** **`CANDIDATE PROPOSAL — OPEN DECISION`** *(Requires formal selection decision before implementation)*.
1. **Option 1: `src/analysis_lab/` (Leading Candidate)**
   - Creates a dedicated top-level package for post-V2 laboratory analysis features.
   - Keeps `src/cli_v2/` 100% frozen (0 files modified, 0 new files).
   - Contains:
     - `src/analysis_lab/service.py` (Orchestration & experiments)
     - `src/analysis_lab/models.py` (Dataclasses)
     - `src/analysis_lab/report.py` (HTML reporting)
     - `src/analysis_lab/cli.py` (CLI entry point)
   - Tests located in `tests/analysis_lab/`.
2. **Option 2: `src/file_analysis/`**
   - Package dedicated specifically to file-specific analysis.
3. **Option 3: `src/post_v2/file_analysis/`**
   - Explicit version-scoped directory.

*Decision:* `src/analysis_lab/` is currently the leading candidate for clean boundary isolation, but remains an `OPEN DECISION` pending the selection stage.

---

## 12. User Interface & Menu Boundary

### 12.1 Menu Isolation Policy `[FROZEN CONSTRAINT]`
- `src/cli_v2/menu_v2.py` is frozen. Modifying it to add a new menu option violates the V2 freeze.
- **Architectural Resolution:** The post-V2 feature will be invoked strictly via a **dedicated CLI entry point**:
  `python -m src.analysis_lab.cli --input <file>` (or interactive runner `python -m src.analysis_lab.cli`).
- Reopening `menu_v2.py` is completely rejected for this milestone. Integration into the main menu is deferred to a future major release.

---

## 13. Reporting Design & Privacy Controls

### 13.1 Privacy Hygiene & Path Masking `[CANDIDATE DESIGN]`
- Absolute filesystem paths (e.g. `C:\Users\Username\...`) expose local system usernames and folder structures.
- **Resolution:** The HTML report will display:
  - **Filename:** `report.txt` (primary display).
  - **Relative Path:** Relative to repository root if within workspace, or sanitized filename only.
  - **Absolute Path:** Masked or strictly opt-in.
  - **File Size:** Formatted in bytes and human-readable KB/MB.

### 13.2 SHA-256 Fingerprint Privacy `[OPEN DECISION]`
- A full SHA-256 hash of the input file creates a persistent cryptographic fingerprint of potentially proprietary or private file content.
- **Resolution:** Inclusion of the full SHA-256 fingerprint is classified as **`CANDIDATE METADATA — CONFIGURABLE / OPTIONAL`** (enabled by default for forensic lab reproducibility, with an option to omit or mask for privacy).

### 13.3 Report Terminology Discipline `[CANDIDATE DESIGN]`
- The report will **never declare a "Winner" or "Best Configuration"**.
- "Fastest" will be strictly qualified as:
  **"Fastest observed configuration in this experiment (lowest sample mean latency)"**
  and will always be accompanied by the exact latency value (e.g. `0.42 ms`).
- Explicit caveats will be included:
  - Small file overhead warning (fixed Python/C timing overhead vs amortized throughput).
  - CBC confidentiality notice (absence of authentication/integrity/AEAD).
  - ECB pattern leakage warning.

---

## 14. Graph Generation Reusability

### 14.1 Reusing Frozen `GraphGenerator` `[OBSERVED FACT]`
`GraphGenerator` in `src/analyzers/graph_generator.py` provides:
- `generate_key_size_comparison(summary_df)`: Requires a single `data_size_bytes`.
- `generate_mode_comparison(summary_df)`: Requires a single `data_size_bytes`.

Because a file-specific analysis evaluates exactly **one file** (one `data_size_bytes`), both methods work **without modification**:
- Pass `encryption_collector.get_summary_dataframe()` $\rightarrow$ Key Size & Mode charts for Encryption.
- Pass `decryption_collector.get_summary_dataframe()` $\rightarrow$ Key Size & Mode charts for Decryption.
- Generated figures are serialized to in-memory Base64 PNGs via `ReportGenerator.figure_to_base64()`, ensuring zero temporary image files on disk.

---

## 15. Key / IV Experimental Reproducibility

### 15.1 Key and IV Strategy `[CANDIDATE DESIGN]`
- **Input Workload:** All 6 configurations evaluate the exact same immutable in-memory byte buffer.
- **Key Generation:**
  - AES-128, AES-192, and AES-256 require 16, 24, and 32-byte keys, respectively.
  - For each configuration, a cryptographically secure random key is generated once outside the timing loop via `cipher.generate_key()`.
- **IV Generation:**
  - For ECB: `iv = None`.
  - For CBC: A 16-byte random IV is generated once outside the timing loop via `cipher.generate_iv()`.
- **Reuse Across Iterations:** That single key and IV are reused across warmup, all 30 encryption iterations, and all 30 decryption iterations of that specific configuration run.
- **Setup vs. Measured Timing Boundary:** Key/IV generation is excluded from the measured timing boundary but is part of experiment setup.
- **Hygiene:** Keys are held in volatile memory only and are never written to disk or embedded in HTML reports.

---

## 16. Future Cipher Extensibility

### 16.1 Realistic Extensibility Principles `[CANDIDATE DESIGN]`
- While `CipherFactory` allows registering new ciphers, the feature **must not claim universal automatic compatibility** for future algorithms.
- Future algorithms have fundamentally different characteristics:
  - Blowfish has an 8-byte block size (AES is 16 bytes).
  - ChaCha20 is a stream cipher (no padding, no block modes).
  - RSA is asymmetric (cannot directly encrypt arbitrary large files without hybrid symmetric encapsulation).
- **Resolution:** The architecture isolates AES-specific assumptions (16-byte blocks, PKCS#7) into configuration adapters, allowing future algorithms to be integrated cleanly with explicit adapter rules.

---

## 17. Failure Handling & Error Isolation

### 17.1 Per-Configuration Resilience `[CANDIDATE DESIGN]`
Reusing the error isolation philosophy proven in V2 Batch Operations:
- Each configuration executes within an isolated `try/except` boundary.
- If a single configuration fails (e.g. system interrupt or memory error), that configuration is logged as `FAILED`, and the error message is translated via `ErrorTranslator`.
- Remaining configurations continue executing to completion.
- The HTML report renders successfully, displaying data for successful configurations and an alert banner for failed ones.

---

## 18. Testing Strategy

### 18.1 Comprehensive Test Suite `[CANDIDATE DESIGN]`
New tests will be added in a dedicated test directory (e.g. `tests/analysis_lab/`):
1. **Deterministic Round-Trip Tests:** Verify `decrypt(encrypt(P)) == P` across all 6 configurations.
2. **Ciphertext Sizing Parity:** Verify ciphertext sizes match `(len(P) // 16 + 1) * 16`.
3. **Edge Case Payloads:**
   - 0-byte file (empty) $\rightarrow$ 16-byte ciphertext, latency measured, throughput reported as `N/A`.
   - 15-byte, 16-byte (boundary), and 17-byte buffers.
   - Raw binary files and multi-byte UTF-8 text files.
4. **Error Isolation Tests:** Mock a cipher failure and verify that other configurations complete and the report renders cleanly.
5. **Privacy Sanitization Tests:** Verify absolute paths and secret keys do not appear in generated HTML.
6. **Regression Invariant `[FROZEN CONSTRAINT]`:** **All existing baseline tests (V1 and V2) must continue to pass with zero regressions.**

---

## 19. Files That Must Remain Frozen & Permitted New Locations

### 19.1 Frozen Files and Directories `[FROZEN CONSTRAINT]`
The following directories and files must experience **zero modifications**:
- `src/core/*` (`aes_cipher.py`, `blowfish_cipher.py`, `classical_ciphers.py`, `rsa_cipher.py`, `__init__.py`)
- `src/engines/*` (`benchmark_service.py`, `cipher_factory.py`, `cipher_interface.py`, `cipher_service.py`, `context_manager.py`, `security_service.py`)
- `src/analyzers/*` (`graph_generator.py`, `metric_collector.py`, `performance_timer.py`, `security_evaluator.py`)
- `src/utils/*` (`file_handler.py`, `padding.py`, `key_generator.py`, `validators.py`, `formatters.py`)
- `src/cli/*` (All V1 CLI modules)
- `src/cli_v2/*` (All existing V2 usability modules, including `menu_v2.py`, `batch_orchestrator.py`, `key_manager.py`, `report_generator.py`, `main_v2.py`)
- `tests/` Existing V1 test files (`test_aes.py`, `test_blowfish.py`, `test_cli.py`, `test_factory.py`, `test_graph_generator.py`, `test_metric_collector.py`, `test_padding.py`, `test_performance.py`, `test_performance_timer.py`, `test_rsa.py`, `test_security_evaluator.py`, `test_utils.py`, `tests/cli/*`, `tests/engines/*`, `tests/utils/*`)
- `tests/cli_v2/*` Existing V2 test files (`test_batch_orchestrator.py`, `test_error_translator.py`, `test_file_picker.py`, `test_interoperability.py`, `test_key_manager.py`, `test_main_v2.py`, `test_menu_v2.py`, `test_navigation.py`, `test_presentation.py`, `test_report_generator.py`)
- `requirements.txt`, `.gitignore`

### 19.2 Permitted New Locations `[CANDIDATE DESIGN]`
To preserve the frozen V1 and V2 baselines, new code and tests will be added **strictly in dedicated new packages**:
- `src/analysis_lab/` (Candidate new package for production feature code)
- `tests/analysis_lab/` (Candidate new package for feature-specific automated tests)

---

## 20. Summary of Open Decisions `[OPEN DECISION]`

| Decision Item | Candidate Options | Classification & Current Status |
| :--- | :--- | :--- |
| **New Package Namespace** | `src/analysis_lab/` vs. `src/file_analysis/` vs. `src/post_v2/` | `CANDIDATE PROPOSAL — OPEN DECISION` (`src/analysis_lab/` leading candidate) |
| **File-Size Operational Threshold** | Warning at 25 MB vs. 50 MB; Hard ceiling at 100 MB vs. 200 MB | `CANDIDATE RECOMMENDATION — NOT APPROVED` (Requires explicit approval before implementation) |
| **Decryption Benchmarking Scope** | Experiment measures both; CLI prompt vs. always run | `CANDIDATE DESIGN — OPEN DECISION` (Engine supports both; UX toggle decided in Selection) |
| **Candidate Security Redundancy Metric** | Include block uniqueness ratio vs. omit until researched | `CANDIDATE EXPERIMENTAL PROPOSAL` (Omitted from core performance scope) |
| **Report Path & Hash Privacy** | Relative path + optional SHA-256 vs. mandatory full hash | `CANDIDATE DESIGN — OPEN DECISION` (Relative path default; SHA-256 configurable) |

---

## 21. Non-Scope `[FROZEN CONSTRAINT]`

The following items are **strictly out of scope**:
- Implementing RSA, Blowfish, Classical ciphers, ChaCha20, or AES-GCM.
- Streaming / chunked encryption for gigabyte-scale files.
- Modifying V1 core or V2 usability modules.
- Modifying `menu_v2.py`.
- Introducing new third-party dependencies in `requirements.txt`.
- Multi-threaded or distributed benchmark execution.

---

## 22. Disciplined 10-Stage Implementation Lifecycle `[CANDIDATE DESIGN]`

```text
Stage 0 — Baseline Freeze & Environment Verification
  - Record git commit, tags, and verify all 879 baseline tests pass cleanly.

Stage 1 — Architecture & Methodology Correction (This Document)
  - Reconcile PerformanceTimer contract, separate concerns, resolve boundaries.

Stage 2 — Core Performance Experiment Engine
  - Implement PerformanceExperiment, key/IV management, and in-memory timing.

Stage 3 — Result Model & Statistical Aggregation
  - Implement FileAnalysisResult, two-collector MetricCollector handling, and padding derivation.

Stage 4 — Candidate Security Analysis & Diffusion Integration
  - Implement optional SecurityExperiment (avalanche, key sensitivity, BMP guard).

Stage 5 — Graph Generation & HTML Report Assembly
  - Implement FileAnalysisReportGenerator reusing GraphGenerator and ReportGenerator CSS.

Stage 6 — User-Facing CLI Interface
  - Implement dedicated standalone CLI runner (e.g. src/analysis_lab/cli.py).

Stage 7 — Comprehensive Test Suite & Edge-Case Verification
  - Unit and integration tests for empty files, boundaries, binary, Unicode, and error isolation.

Stage 8 — Independent Forensic Code Audit
  - Verify zero modifications to V1/V2 files, check diffs, verify privacy escaping.

Stage 9 — Final Baseline Verification & Freeze Report
  - Re-run full test suite ensuring zero regressions on all baseline tests.
```

---

## 23. Acceptance Criteria `[FROZEN CONSTRAINT]` & `[CANDIDATE DESIGN]`

1. **V1 Immutability `[FROZEN CONSTRAINT]`:** `git diff v1.0-release..HEAD -- src/core src/engines src/analyzers src/utils src/cli` is completely empty (0 lines changed).
2. **Existing Test Immutability `[FROZEN CONSTRAINT]`:** All existing V1 and V2 test files in `tests/` and `tests/cli_v2/` remain 100% bit-for-bit unmodified, and all existing baseline tests continue to pass with zero regressions.
3. **Zero Existing V2 Modifications `[FROZEN CONSTRAINT]`:** Zero existing files in `src/cli_v2/` or `tests/cli_v2/` are modified.
4. **Permitted New Additions `[CANDIDATE DESIGN]`:** New feature code and tests are placed strictly in dedicated post-V2 namespaces (e.g. `src/analysis_lab/` and `tests/analysis_lab/`).
5. **Zero New Dependencies `[FROZEN CONSTRAINT]`:** `requirements.txt` remains bit-for-bit identical.
6. **Configuration Parity `[FROZEN CONSTRAINT]`:** All 6 supported configurations (AES 128/192/256 in ECB and CBC) are evaluated against the target file.
7. **PerformanceTimer Contract `[FROZEN CONSTRAINT]`:** Each measured operation (encryption and decryption) uses the frozen PerformanceTimer contract of 5 warmup and 30 measured iterations via `@PerformanceTimer.measure_time_with_warmup()`.
8. **Independent Directional Reporting `[CANDIDATE DESIGN]`:** Encryption and decryption latency and throughput are independently reported; zero-byte payloads report throughput as `N/A`.
9. **Self-Contained Report `[CANDIDATE DESIGN]`:** A single-file, self-contained HTML report with embedded Base64 static charts and statistical tables is generated in `results/reports/`.
10. **Path Privacy `[CANDIDATE DESIGN]`:** Generated reports omit absolute user paths by default.
11. **Zero Premature Coding `[FROZEN CONSTRAINT]`:** No production implementation begins until this design is independently reviewed and approved.
