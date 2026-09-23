# V2 CONSOLIDATED SELECTION

**Document ID:** V2-SELECTION-CONSOLIDATED  
**Status:** DRAFT COMPLETE — PENDING INDEPENDENT VERIFICATION  
**Date:** 2026-09-15  
**Author:** V2 Architecture & Project-Specific Selection Lead  
**Scope Focus:** Consolidated V2 Usability Layer Specification (Categories A, B, C, D)  
**Target Milestone:** V2 Phase 3 (Project-Specific Selection)  
**Authoritative Input Documents:**
- [V2_INTENT.md](file:///c:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md) (Intent & Scope Authority)
- [RESEARCH_A_MENU_UX.md](file:///c:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_A_MENU_UX.md) (Category A Research — Frozen)
- [RESEARCH_B_KEY_MANAGEMENT.MD](file:///c:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_B_KEY_MANAGEMENT.MD) (Category B Research — Frozen)
- [RESEARCH_C_BATCH_OPERATIONS.MD](file:///c:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_C_BATCH_OPERATIONS.MD) (Category C Research — Frozen)
- [RESEARCH_D_REPORTING.md](file:///c:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_D_REPORTING.md) (Category D Research — Frozen)

---

> [!IMPORTANT]
> **V2 Selection Boundary:** This document represents the consolidated, binding specification for the V2 usability layer. It resolves all open research decisions from Phase 1 into frozen implementation contracts. No code implementation has occurred during this phase.

---

## 1. Executive Summary

The V2 Usability Layer extends the Cryptography Testing Lab from a developer-centric CLI tool into an accessible, robust, and guided laboratory environment for students, educators, evaluators, and practitioners.

V1 established a verified AES cryptographic foundation with 434 passing unit/integration tests and zero third-party dependencies. However, V1 requires manual hex string management, single-file invocations, and memorization of command-line flags.

V2 introduces four integrated capability categories without modifying a single line of frozen V1 code:
1. **Category A (Guided Menu UX):** A stateful, task-centric terminal wizard featuring universal step navigation (`b`ack, `c`ancel, `?` help), hybrid file selection, transparent defaults, and actionable error diagnostics.
2. **Category B (Key Management):** Raw-hexadecimal `.key` sidecar persistence and loading, pre-execution format validation, case/whitespace normalization, and laboratory security notices.
3. **Category C (Batch Operations):** Resilient, sequential multi-file folder encryption and decryption with per-file error isolation, non-destructive file handling, skip-existing resumption, and structured CSV logging (`batch_log_*.csv`).
4. **Category D (Reporting & Analysis):** Standalone single-file HTML reports combining statistical benchmark metrics, embedded base64 Matplotlib charts (150 DPI), and comparative security diagnostics (ECB structural leakage vs. CBC diffusion), with browser auto-open integration.

This document consolidates findings across all 53 research recommendations and 35 open decisions, defining the binding architectural contracts for implementation.

---

## 2. V1 Lock Confirmation & Invariants

V1 is formally released and tagged at commit `650bc7f80ada2c4c8e61a0c29b96e9b3a65cca0a` (verified via `git rev-parse v1.0-release^{}`).

### 2.1 Frozen V1 Boundaries
The following components are immutable and must not be modified, refactored, or renamed:
- `src/core/*` — AES cipher engine (`aes_cipher.py`), S-Box transformations, key expansion, and cipher modes (ECB, CBC).
- `src/engines/*` — `CipherService`, `BenchmarkService`, `SecurityService`, `CipherFactory`, and `CipherInterface`.
- `src/analyzers/*` — `MetricCollector`, `PerformanceTimer`, `SecurityEvaluator`, and `GraphGenerator`.
- `src/utils/*` — `file_handler.py`, `padding.py`, formatters, and validators.
- `src/cli/*` — V1 CLI entry point (`src/cli/main.py`), argument parser (`argument_parser.py`), commands (`commands.py`), and menu (`menu.py`).
- `tests/*` — All 434 passing unit and integration tests (2 skipped platform tests).
- `requirements.txt` — Zero new dependencies (standard library + existing `matplotlib`, `numpy`, `pandas`, `tabulate`).

### 2.2 V2 Architectural Relationship
V2 is an **additive orchestration layer** packaged in `src/cli_v2/`. It interacts with V1 exclusively by consuming public service interfaces:
- Calls `CipherService.encrypt_data()` and `CipherService.decrypt_data()`.
- Calls `BenchmarkService.run_benchmark()` and `MetricCollector`.
- Calls `SecurityService.run_security_suite()` and `SecurityEvaluator`.
- Reuses `FileHandler` for low-level I/O.

---

## 3. V2 Authorized Scope

Per [V2_INTENT.md](file:///c:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md) §5, V2 scope is strictly bounded to:

| Category | Intent Scope Items | Selected V2 Capability |
| :--- | :--- | :--- |
| **Category A: Guided Menu UX** | A1–A7 | Task-centric main menu, step-by-step wizard engine, hybrid file picker, summary cards, 3-tier error diagnostics, contextual `?` help, OS Explorer launcher. |
| **Category B: Key Management** | B1–B4 | Raw hex `.key` and `.iv` sidecars, auto-detection prompts, multi-tier key validation, educational plaintext key warnings. |
| **Category C: Batch Operations** | C1–C4 | Flat directory batch encryption/decryption, per-file error isolation, skip-existing overwrite policy, non-destructive processing, `batch_log_*.csv` logging. |
| **Category D: Reporting** | D1–D4 | Consolidated standalone HTML reports (`results/reports/`), base64 embedded Matplotlib graphs (150 DPI), ECB vs CBC visual security analysis, browser auto-open. |

---

## 4. V2 Non-Scope and Deferred Work

The following items are explicitly excluded from V2:

### 4.1 V2 Non-Scope (Excluded by Architecture)
- Modifying or refactoring any V1 source or test file.
- Introducing new third-party dependencies into `requirements.txt`.
- Web servers, Flask/FastAPI backends, REST APIs, or cloud dashboards.
- Multi-user authentication, roles, or database engines (SQLAlchemy, SQLite).
- Custom exception base classes (must use Python standard built-in exceptions).

### 4.2 Deferred Features (Post-V2 Roadmap)
- Password-based key derivation (PBKDF2, Argon2, scrypt).
- Authenticated encryption modes (AES-GCM, ChaCha20-Poly1305).
- Direct PDF report compilation (e.g., WeasyPrint, ReportLab).
- Interactive client-side JavaScript charts (Plotly, Chart.js).
- Streaming/chunked encryption for multi-gigabyte files.
- Asymmetric ciphers (RSA, ECC) and classical cipher implementations.
- Multi-threaded / multi-process batch execution.
- Recursive directory tree mirroring for batch operations.
- Historical benchmark trend database / cross-session regression engine.

---

## 5. Consolidated Research Reconciliation & Architecture Mapping

The four frozen research reports contributed a total of **53 candidate recommendations**, **35 open decisions**, and **16 deferred decisions**.

### 5.1 Input Accounting
- **Report A (Guided Menu UX):** 12 Recommendations (A-01 to A-12), 6 Open Decisions (§22), 4 Deferred Items (§23).
- **Report B (Key Management):** 12 Recommendations (B-01 to B-12), 7 Open Decisions (§25), 4 Deferred Items (§26).
- **Report C (Batch Operations):** 15 Recommendations (C-01 to C-15), 12 Open Decisions (§33), 4 Deferred Items (§34).
- **Report D (Reporting):** 14 Recommendations (D-01 to D-14), 10 Open Decisions (§29), 4 Deferred Items (§30).

### 5.2 Architecture Reconciliation with V2_INTENT

The table below reconciles the conceptual module organization in [V2_INTENT.md](file:///c:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md) §9.1 with the selected concrete module architecture in `src/cli_v2/`:

| V2_INTENT Concept | Selection Disposition | Selected Module | Architectural Justification |
| :--- | :---: | :--- | :--- |
| `main_v2.py` | **PRESERVED** | `src/cli_v2/main_v2.py` | Main CLI entry point and top-level router. |
| `menu_v2.py` | **PRESERVED** | `src/cli_v2/menu_v2.py` | Guided interactive menu and wizard workflow orchestrations. |
| `commands_v2.py` | **MERGED** | `src/cli_v2/menu_v2.py` / `main_v2.py` | CLI dispatch routed directly via `main_v2.py`; interactive wizard workflows orchestrated in `menu_v2.py`; eliminates redundant intermediate command redirection layer. |
| `key_management.py` | **RENAMED** | `src/cli_v2/key_manager.py` | Renamed for naming consistency with project conventions. |
| `batch_ops.py` | **RENAMED** | `src/cli_v2/batch_orchestrator.py` | Renamed to reflect batch execution, error isolation, and logging ownership. |
| `file_picker.py` | **PRESERVED** | `src/cli_v2/file_picker.py` | Directory enumeration and smart path quote-cleaning helper. |
| `progress.py` | **MERGED** | `src/cli_v2/presentation.py` | Merged with summary cards and formatting into unified presentation module. |
| `summary.py` | **MERGED** | `src/cli_v2/presentation.py` | Merged with progress tickers into unified presentation module. |
| `errors.py` | **RENAMED** | `src/cli_v2/error_translator.py` | Renamed to clarify role as 3-tier diagnostic translation layer. |
| `help_text.py` | **MERGED** | `src/cli_v2/navigation.py` | Contextual `?` help handlers integrated directly with step-stack navigation. |
| `report_generator.py` | **PRESERVED** | `src/cli_v2/report_generator.py` | Standalone HTML report compilation and in-memory base64 graph export. |
| *(Extracted)* | **NEW MODULE** | `src/cli_v2/navigation.py` | Extracted generic step-stack engine (`b`ack, `c`ancel, prompt loop) to isolate UI mechanics. |
| *(Windows Launcher)* | **PRESERVED** | `run-v2.bat` | Convenience batch script in project root invoking `main_v2.py` (see §7.2, DSEL-014). |

### 5.3 Conflict Identification & Resolution

#### Conflict 1: V2 Entry Point & Invocation Model
- **Research Input:** Report A proposed both an interactive menu and optional direct CLI subcommands. V1 `src/cli/main.py` requires a subcommand and fails on zero arguments.
- **Intent Boundary:** V2 Intent §3.1 requires V1 CLI to remain untouched; §9.2 authorizes `python -m src.cli_v2.main_v2`.
- **Resolution:** `python -m src.cli_v2.main_v2` is the dedicated V2 entry point. When invoked with no arguments, it **automatically launches the guided interactive menu** (providing a separate UX layer that avoids changing V1). Optional direct V2 subcommands (`encrypt`, `decrypt`, `batch-encrypt`, `batch-decrypt`, `benchmark`, `security`, `report`) are provided for direct execution with V2 defaults. Direct CLI subcommands are non-interactive and execute without prompt. V1 entry point `python -m src.cli.main` remains unchanged.

#### Conflict 2: Key Sidecar Naming & Storage Location
- **Research Input:** Report A suggested `<file>.key` sidecars; Report B analyzed `<output_path>.key` vs `data/keys/`; Report C evaluated per-file vs shared batch keys.
- **Resolution:**
  - **Single-File:** Output ciphertext defaults to `<input_path>.enc`. Key sidecar defaults to `<output_path>.key` (e.g., `sample.txt.enc.key`). IV sidecar defaults to `<output_path>.iv` (e.g., `sample.txt.enc.iv`), maintaining exact symmetry with V1's `.iv` persistence.
  - **Batch Operations:** Default is unique per-file keys (`<output_dir>/<filename>.enc.key`). An opt-in shared batch key mode writes `<output_dir>/batch.key` for the entire batch.

#### Conflict 3: Round-Trip Verification Policy
- **Research Input:** Report A evaluated mandatory automatic verification vs optional prompt vs omitting.
- **Selected Resolution:** The project deliberately selects automatic in-memory round-trip verification for interactive single-file encryption before presenting the summary card, asserting that `decrypt(encrypt(P)) == P`. The project accepts the additional in-memory encryption/decryption work for single-file verification because it provides immediate confirmation that the encrypted result can be restored to the original plaintext. In batch operations, round-trip verification is **omitted by default** to prevent computational overhead across large directory batches, but individual batch outputs remain verifiable via single-file decryption.

#### Conflict 4: Batch Overwrite & Resumption Policy
- **Research Input:** Report C evaluated "Skip Existing", "Force Overwrite", and interactive per-file prompts.
- **Resolution:** The default batch overwrite policy is **Skip Existing** (`--on-conflict skip`). This provides a non-destructive retry/resumption mechanism by skipping existing destination ciphertexts. The guided wizard allows the user to explicitly choose between "Skip Existing" (Default) and "Overwrite All".

#### Conflict 5: Report Packaging & HTML Architecture
- **Research Input:** Report D evaluated separate benchmark/security HTML files vs a single consolidated report.
- **Resolution:** Standardize on a **single consolidated HTML report** (`cryptography_report_YYYYMMDD_HHMMSS.html` in `results/reports/`). Sections for Benchmark Metrics and Security Analysis are rendered adaptively based on available session data. All assets (CSS and Matplotlib graphs) are strictly embedded inline (internal CSS, base64 PNG Data URIs at 150 DPI).

#### Conflict 6: Browser Auto-Open vs Output Directory Explorer
- **Research Input:** Report A explored Explorer launching (A4/A10); Report D explored HTML report browser auto-open (D4/D14).
- **Resolution:** Distinctly separated into two independent contracts:
  - **A4 (Explorer Launcher):** Post-operation menu action to open the output directory in the OS file manager via `os.startfile` (on Windows).
  - **D4 (Browser Auto-Open):** HTML report launch via `webbrowser.open()`, prompted in interactive mode and enabled by default in CLI mode (suppressible via `--no-open`).

---

## 6. Project-Specific Decision Framework

Every project selection follows four governing criteria:
1. **Zero V1 Invalidation:** No changes to V1 source, tests, or math.
2. **Zero New Dependencies:** Strictly use standard library + existing `matplotlib`, `numpy`, `pandas`, `tabulate`.
3. **Data Safety & Non-Destruction:** Input files must never be modified or deleted; overwrites require explicit policy.
4. **Explicit Usability:** Prompts provide recommended defaults, validation at entry point, and clean step navigation.

---

## 7. V2 Architecture & Module Boundaries

V2 components reside entirely within `src/cli_v2/` with zero cross-contamination into `src/cli/` or `src/core/`.

```text
src/
├── cli/                         # Existing V1 source — READ-ONLY FOR V2
├── core/                        # Existing V1 source — READ-ONLY FOR V2
├── engines/                     # Existing V1 source — READ-ONLY FOR V2
├── analyzers/                   # Existing V1 source — READ-ONLY FOR V2
├── utils/                       # Existing V1 source — READ-ONLY FOR V2
│
└── cli_v2/                      # [V2 USABILITY LAYER]
    ├── __init__.py              # Package marker
    ├── main_v2.py               # V2 Entry point router (CLI flags + Menu launch)
    ├── navigation.py            # Step stack engine (Back, Cancel, Help, Validation)
    ├── menu_v2.py               # Task-centric hierarchical menu & wizard flows
    ├── file_picker.py           # Directory enumeration & smart path cleaning
    ├── key_manager.py           # Key & IV persistence, loading, normalization, validation
    ├── batch_orchestrator.py    # Resilient batch execution, error isolation, CSV logging
    ├── report_generator.py      # Consolidated HTML report builder (in-memory base64 PNG)
    ├── presentation.py          # Summary cards, ASCII tables, progress tickers (\r)
    └── error_translator.py      # Three-tier error translation & contextual help
```

### 7.1 Module Responsibilities

| Module | Owns / Primary Responsibility | Does NOT Own |
| :--- | :--- | :--- |
| `main_v2.py` | CLI argument routing, top-level exception catching, zero-arg menu dispatch. | Workflow execution logic. |
| `navigation.py` | Step history stack, prompt looping, `b`/`c`/`?` token interception. | Business domain validation. |
| `menu_v2.py` | Wizard definitions for single-file, batch, benchmark, and security. | Direct file I/O or crypto math. |
| `file_picker.py` | Scanning `data/input/`, listing files, stripping drag-and-drop quotes. | Reading/writing file contents. |
| `key_manager.py` | Saving/loading `.key` sidecars, hex validation, whitespace/BOM normalization. | Cipher execution. |
| `batch_orchestrator.py` | Sequential iteration, per-file try/except isolation, `batch_log_*.csv`. | In-memory cipher algorithms. |
| `report_generator.py` | HTML skeleton, base64 Matplotlib figure export, XSS escaping. | Metric calculation math. |
| `presentation.py` | Formatting summary cards, carriage-return progress, ASCII borders. | State management. |
| `error_translator.py` | Mapping built-in exceptions to 3-tier user guidance. | Catching unhandled exceptions. |

### 7.2 Windows Quick-Launcher Specification (`run-v2.bat`)
Per V2_INTENT §9.2, a convenience launcher `run-v2.bat` is authorized in the project root:
- **Purpose:** Double-clickable shortcut for non-technical Windows users.
- **Contract:** Project-relative script that verifies Python availability on `PATH`, forwards all command-line arguments `%*` directly to `python -m src.cli_v2.main_v2 %*`, and exits cleanly with an informative error message if Python is missing.
- **Constraint:** Contains zero business logic, zero cryptographic logic, and zero path manipulations.

---

## 8. V2 CLI Contract

### 8.1 Entry Point Specification
- **Primary V2 Command:** `python -m src.cli_v2.main_v2`
- **Zero-Argument Behavior:** Launches the V2 Interactive Guided Menu. (V1 `src.cli.main` retains its requirement for subcommands).
- **Subcommand Support (Non-Interactive CLI Execution):**
  ```text
  python -m src.cli_v2.main_v2 [command] [options]
    menu            Launch interactive guided menu (default if no args)
    encrypt         Single-file guided encryption
    decrypt         Single-file guided decryption
    batch-encrypt   Multi-file directory encryption
    batch-decrypt   Multi-file directory decryption
    benchmark       Run performance benchmark suite & generate HTML report
    security        Run security cryptanalysis suite & generate HTML report
    report          Generate consolidated HTML report from metrics
  ```
- **Execution Mode Distinction:**
  1. **Interactive V2 Menu Mode:** Executes via guided wizard steps (`pre-flight discovery` $\to$ `display preview` $\to$ `explicit user confirmation prompt` $\to$ `execute`).
  2. **Direct V2 CLI Mode:** Executes directly and non-interactively for scriptable automation (`pre-flight validation/discovery` $\to$ `display/report planned operation information` $\to$ `execute without interactive confirmation`).
  3. **Dry-Run Simulation Mode (`--dry-run`):** Non-destructive inspection mode (`pre-flight validation/discovery` $\to$ `display planned operations to stdout` $\to$ `exit with zero writes`).

### 8.2 Standard CLI Flags & Shared Semantics
- `--dry-run`: Pre-flight discovery and simulation mode. Scans candidate files, applies exclusions, resolves source/destination paths, evaluates collision status, and displays the planned operations to standard output, but performs zero encryption/decryption writes, creates zero output artifacts (no ciphertext, no plaintext, no `.key`, no `.iv`, no batch CSV log), and does not alter input files.
- `--no-open`: Suppress automatic browser launching for HTML reports.
- `--on-conflict {skip,overwrite}`: Batch file collision policy (default: `skip`, corresponding to interactive "Skip Existing").
- `--shared-key`: In batch encryption, use a single shared key for all files in the batch (saved to `<output_dir>/batch.key`), rather than generating unique per-file keys. In batch decryption, load key from `<source_dir>/batch.key` or prompt.
- `--verbose`: Debugging mode. In normal execution, errors display the clean 3-tier user diagnostic (What, Why, Action). In `--verbose` mode, V2 displays the 3-tier diagnostic followed by the technical Python traceback. Verbose mode never exposes raw keys or plaintext.

---

## 9. V2 Menu and Navigation Contract

### 9.1 Main Menu Hierarchy
The main menu presents 6 task-centric categories using standard ASCII formatting:

```text
============================================================
              CRYPTOGRAPHY TESTING LAB — V2
============================================================
  1. Single-File Operations (Encrypt, Decrypt, Verify)
  2. Batch Operations (Folder Encrypt, Folder Decrypt)
  3. Benchmark & Performance Suite
  4. Security & Cryptanalysis Lab
  5. View & Generate HTML Reports
  6. Help & Documentation
  7. Exit
============================================================
Select an option [1-7]: 
```

### 9.2 Navigation Control Tokens
- **At Wizard Configuration Steps:**
  - `b` or `back`: Return to the previous configuration step, preserving entered parameters.
  - `c` or `cancel`: Abort current wizard immediately, delete any in-flight temporary files, and return to the main menu.
  - `?` or `help`: Print in-place educational explanation and re-prompt.
- **At Main Menu:**
  - `b` or `back`: Not applicable (re-prompts main menu).
  - `c` or `cancel`: Exit the application.
  - `?` or `help`: Display main menu guidance and options overview.
  - Option `7`: Exit cleanly.

---

## 10. Guided Workflow Contracts

### Workflow 1: Single-File Encryption
1. **Step 1 (Input File):** Display available files in `data/input/` with size + custom path prompt.
2. **Step 2 (Algorithm & Mode):** Default to `AES-256-CBC` (Recommended). Option to customize key size (128/192/256) or mode (CBC/ECB).
3. **Step 3 (Key Strategy):** Default to `Generate New Key & Save Sidecar (.key)`. Option to load existing `.key` or paste hex.
4. **Execution & Verify:** Perform in-memory round-trip verification (`encrypt` $\to$ `decrypt` $\to$ assert equal).
5. **Summary Card:** Display input/output paths, sizes, padding delta, full generated key (for laboratory verification), key/iv locations, and execution time.
6. **Next Actions:** [1] Open output folder in Explorer (A4), [2] Test decrypt now, [3] Return to menu.

### Workflow 2: Single-File Decryption
1. **Step 1 (Ciphertext File):** Display files in `data/output/` (or custom path).
2. **Step 2 (Key Acquisition):** Auto-detect matching `.key` sidecar. Prompt `Use detected key '<path>.key'? [Y/n]`. If no sidecar, prompt to select `.key` file or enter hex.
3. **Step 3 (IV Acquisition for CBC):** Auto-detect matching `.iv` sidecar. If missing, prompt for hex IV.
4. **Execution:** Decrypt payload using V1 `CipherService`.
5. **Summary Card:** Display restored file path, byte size, and execution duration.

### Workflow 3: Batch Folder Encryption (Interactive)
1. **Step 1 (Source Directory):** Prompt for source folder (default: `data/input/`).
2. **Step 2 (Configuration):** Select mode (default: AES-256-CBC) and key strategy (default: unique per-file keys, option: shared batch key).
3. **Step 3 (Destination & Conflict):** Destination folder (default: `data/output/`) + Overwrite policy (default: `Skip Existing`).
4. **Step 4 (Pre-flight Preview & Confirmation):** Display discovered file count, excluded files count, collision preview, and target folder. **User must explicitly confirm execution to proceed.**
5. **Execution:** Sequential iteration with `\r` progress ticker. Per-file error isolation.
6. **Completion:** Summary card + Laboratory Security Notice + write `batch_log_YYYYMMDD_HHMMSS.csv`.

### Workflow 4: Batch Folder Decryption (Interactive)
1. **Step 1 (Source Directory):** Prompt for folder containing `.enc` files (default: `data/output/`).
2. **Step 2 (Destination Directory):** Destination folder (default: `data/decrypted/`).
3. **Step 3 (Key Discovery):** Resolve `.key` and `.iv` sidecars per file or use a shared batch key (`batch.key`).
4. **Step 4 (Pre-flight Preview & Confirmation):** Display candidate ciphertext count and destination. **User must explicitly confirm execution to proceed.**
5. **Execution:** Sequential decryption, skipping already decrypted files if conflict policy is `skip`.
6. **Completion:** Structured accounting table + CSV log.

### Workflow 5: Benchmark & Performance Report
1. **Step 1 (Preset Selection):** [1] Quick (128/256-bit, 1KB/1MB), [2] Full Matrix (all key sizes & modes, 1KB to 10MB).
2. **Step 2 (Execution):** 5 warmup iterations, 30 sample iterations per configuration. Collect throughput & Tukey stats.
3. **Step 3 (Report Generation):** Build in-memory Matplotlib charts, assemble HTML report, write to `results/reports/`.
4. **Step 4 (Browser Open):** Prompt `Open HTML report in browser? [Y/n]` (D4).

### Workflow 6: Security & Cryptanalysis Report
1. **Step 1 (Evaluation Scope):** Avalanche effect test (1-bit flip), Key sensitivity test, ECB vs CBC Bitmap analysis.
2. **Step 2 (Execution):** Run V1 `SecurityEvaluator` metrics.
3. **Step 3 (Report Generation):** Generate side-by-side ECB/CBC comparison figure, compile HTML report.
4. **Step 4 (Browser Open):** Launch default browser with generated report (D4).

---

## 11. Key Management Contract

### 11.1 Format & Encoding Specification
- **Extension:** `.key` (mandatory standard sidecar extension).
- **Encoding:** Pure raw hexadecimal string (ASCII/UTF-8), single line, optional trailing newline (`\n` or `\r\n`).
- **No Comment Headers:** Header comments (`# ...`) are excluded from generated files. The `.key` file contains raw hexadecimal key material in a representation suitable for supplying to the V1 `--key` hex input interface, assuming the algorithm/key size and invocation requirements match.
- **Allowed Byte Lengths:** Exactly 16 bytes (32 hex chars), 24 bytes (48 hex chars), or 32 bytes (64 hex chars).

### 11.2 Normalization & Loading Rules
When loading `.key` files:
1. Strip UTF-8 Byte Order Mark (BOM: `\xef\xbb\xbf`) if present.
2. Strip all leading and trailing whitespace (`\r`, `\n`, `\t`, spaces).
3. Validate character set: strictly `[0-9a-fA-F]`.
4. Validate length parity (must be even number of characters).
5. Derive AES key size automatically ($16\text{ bytes} \to 128\text{-bit}$, $24\text{ bytes} \to 192\text{-bit}$, $32\text{ bytes} \to 256\text{-bit}$).

### 11.3 Symmetrical IV Handling
- IV files strictly adhere to V1 conventions: `<ciphertext_path>.iv` containing 32 hex characters (16 bytes).
- Keys and IVs remain separate sidecar files, matching V1's security architecture.

### 11.4 Laboratory Key Visibility & Security Notice
- **Terminal Display:** In single-file interactive encryption, the generated full hex key is displayed in the summary card as a deliberate V2 selection to allow immediate inspection and verification in a laboratory/testing context.
- **Secret Protection:** Key material displayed in the terminal is never written to batch CSV logs, HTML reports, or ordinary diagnostic logs.
- **Educational Notice:** Whenever a `.key` file is created on disk, display this educational notice:
```text
[!] Laboratory Notice: Encryption key saved to '<path>.key'.
    Plaintext key storage is provided for laboratory and testing convenience.
    In production environments, keys must be stored in secure key vaults.
```

---

## 12. Batch Operations Contract

### 12.1 Traversal & Discovery
- **Scope:** Flat directory scan via `pathlib.Path.iterdir()`.
- **Lexical Ordering:** Files are sorted alphabetically by filename before processing for deterministic progress reporting.
- **Exclusion Matrix:** Automatically skip:
  - Sidecar files: `*.key`, `*.iv`, `*.log`, `*.tmp*`
  - Existing ciphertexts during encryption: `*.enc`
  - OS metadata: `.DS_Store`, `Thumbs.db`, `desktop.ini`
  - Hidden dotfiles (e.g., `.*`)

### 12.2 Batch Key Strategies

#### Mode 1: Unique-Per-File Key Mode (Default)
- A fresh random key is generated for each input file.
- Ciphertext is written to `<output_dir>/<filename>.enc`.
- Key sidecar is written to `<output_dir>/<filename>.enc.key`.
- IV sidecar (for CBC) is written to `<output_dir>/<filename>.enc.iv`.
- If an output ciphertext exists and the overwrite policy is `skip`, the file is tallied as `SKIPPED`.

#### Mode 2: Shared-Batch-Key Mode (Opt-in via `--shared-key` or menu)
- A single key is generated or loaded for the entire batch.
- Saved once as `<output_dir>/batch.key`.
- For CBC mode, a **unique random IV** is still generated per file and written to `<output_dir>/<filename>.enc.iv` (preventing IV reuse vulnerabilities).
- Batch decryption in shared-key mode looks for `<source_dir>/batch.key` or prompts the user.

### 12.3 Overwrite, Resumption & Sidecar Consistency Policy
- Default policy: **Skip Existing** (`--on-conflict skip`).
- **Resumption Behavior:** Skipping existing destination ciphertexts provides a non-destructive retry/resumption mechanism for interrupted batches.
- **Sidecar Consistency:** An existing ciphertext does not by itself prove companion `.key`/`.iv` consistency. When skipping an existing file, V2 records it as `SKIPPED`. During batch decryption, if a ciphertext exists but its matching sidecar (`.key` or `.iv`) is missing or corrupt, V2 isolates the error, tallies that specific file as `FAILED` (with diagnostic error reason), and continues batch processing.

### 12.4 Atomic Write & Overwrite Safety Handling
- **Individual Path Atomicity:** `os.replace()` provides atomic replacement semantics for an individual destination path where supported by the platform/filesystem. The ciphertext, `.key`, and `.iv` remain separate artifacts and are not written as one multi-file transaction.
- **Safety during Overwrite:** A failed overwrite operation must not blindly delete or destroy previously existing destination artifacts during preparation failure. When preparing replacement artifacts for an existing file set, newly created temporary/staged artifacts may be cleaned up upon failure, while pre-existing destination artifacts remain intact if preparation fails prior to replacement. Exact staging mechanisms remain an implementation detail for Phase 5.
- **Partial Replacement Failure:** Once individual destination paths begin being replaced via `os.replace()`, the filesystem does not provide a multi-file transaction across `.enc`, `.key`, and `.iv`. If a companion sidecar replacement fails after another artifact is replaced, V2 attempts cleanup of the failed operation's temporary/staged files, marks the file status as `FAILED` in `batch_log_*.csv`, and continues processing remaining batch files.
- **Per-File Error Isolation:** Each file is wrapped in an individual `try-except` block catching `(FileNotFoundError, PermissionError, ValueError, OSError)`.
- A single corrupt or unreadable file is tallied as `FAILED`, logged to the batch CSV, and does **not** abort the remaining batch.
- **Fatal Interruptions:** `KeyboardInterrupt` cleans the active in-flight temporary file, flushes the CSV log, and exits cleanly with exit code `0`.

### 12.5 Batch Logging Specification
Upon batch completion, write `batch_log_YYYYMMDD_HHMMSS.csv` to the output directory:
- **Columns:** `timestamp,source_file,dest_file,status,size_bytes,elapsed_ms,error_message`
- **Secret Protection:** Raw hex keys and plaintexts are **strictly forbidden** from log columns.

---

## 13. Reporting Contract

### 13.1 Standalone HTML Architecture
- **Packaging:** Single HTML artifact (`results/reports/cryptography_report_YYYYMMDD_HHMMSS.html`) with selected CSS and chart assets embedded inline, allowing offline viewing without external report resources.
- **Separation from Batch Logs:** The HTML report is a human-readable visual document for benchmarks and security analyses. Batch operations output separate machine-readable CSV logs (`data/output/batch_log_*.csv`). The HTML report may reference batch summary counts in metadata, but raw CSV logs remain distinct standalone files.
- **Dependencies:** Zero external CDN, JavaScript, or CSS links.
- **Styles:** Internal CSS `<style>` block in `<head>`, including `@media print` rules for clean PDF printing via browser.
- **Asset Embedding:** Matplotlib figures rendered in-memory via `io.BytesIO()`, encoded as base64 PNG Data URIs (`data:image/png;base64,...`), and figures closed immediately via `plt.close(fig)`.
- **Chart DPI:** Standardized at **150 DPI** as an intentional parameter balancing visual readability with Base64 payload size. (Fine-grained rendering options remain Phase 5 implementation details).

### 13.2 Report Content Sections
1. **Header & Metadata:** Test timestamp, platform, Python version, V2 schema version (`data-report-version="2.0"`).
2. **Executive Summary:** High-level metric highlights (peak throughput, fastest configuration, security pass status).
3. **Performance Benchmarks:** Summary tables (throughput MB/s, latency mean $\pm$ std dev, Tukey outlier counts), embedded Matplotlib charts (Key Size Comparison, Mode Comparison, Throughput vs Payload).
4. **Security & Cryptanalysis:** Avalanche effect percentage bar, key sensitivity analysis, and side-by-side ECB pattern leakage vs CBC diffusion bitmap visualization.
5. **Experimental Methodology:** Documenting 5 warmup cycles, 30 sample iterations, $1.5 \times \text{IQR}$ outlier fences, and binary MB ($1,048,576\text{ bytes}$).

### 13.3 XSS Sanitization & Data Safety
- All dynamic strings, filenames, and error messages injected into HTML are strictly sanitized via `html.escape(quote=True)`.
- Raw secret keys and plaintext data are strictly excluded from reports.

### 13.4 Browser Auto-Open Policy (D4) vs Explorer Launcher (A4)
- **D4 (Browser Auto-Open):** In guided menu mode, prompt user `Open report in browser? [Y/n]`. In CLI mode, launch default browser via `webbrowser.open(report_path.resolve().as_uri())` (suppressible via `--no-open`).
- **A4 (Explorer Launcher):** In single-file and batch summary cards, offer an interactive menu action to open the output directory in the OS file manager via `os.startfile` (on Windows).

---

## 14. File Format Contracts

### 14.1 `.key` File Specification
```text
File Name : <ciphertext_name>.key (e.g. sample.txt.enc.key)
Encoding  : UTF-8 / ASCII
Content   : Single raw hexadecimal string (32, 48, or 64 hex characters) + '\n'
Example   : e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

### 14.2 `.iv` File Specification
```text
File Name : <ciphertext_name>.iv (e.g. sample.txt.enc.iv)
Encoding  : UTF-8 / ASCII
Content   : Single raw hexadecimal string (exactly 32 hex characters) + '\n'
Example   : 0123456789abcdef0123456789abcdef
```

### 14.3 `batch_log_*.csv` Specification
All timestamps in CSV logs and report metadata strictly follow UTC ISO-8601 format (`YYYY-MM-DDTHH:MM:SSZ` where `Z` denotes UTC).
```csv
timestamp,source_file,dest_file,status,size_bytes,elapsed_ms,error_message
2026-09-15T19:30:00Z,data/input/doc1.pdf,data/output/doc1.pdf.enc,SUCCESS,1048576,45.2,
2026-09-15T19:30:01Z,data/input/bad.dat,data/output/bad.dat.enc,FAILED,0,0.0,Permission denied
```

---

## 15. Directory and Output Contract

V2 utilizes designated workspace directories with automatic creation via `FileHandler.ensure_directory()`:

| Directory | Purpose | Provenance & Default Behavior |
| :--- | :--- | :--- |
| `data/input/` | Default source folder for single-file and batch inputs. | V2-selected default directory; scanned by file picker; auto-created if missing. (V1 supported arbitrary custom path inputs). |
| `data/output/` | Default destination for encrypted ciphertexts, sidecars, and `batch_log_*.csv`. | V2-selected default directory; auto-created on first write. (V1 supported arbitrary custom path outputs). |
| `data/decrypted/`| Default destination for batch decrypted files. | V2-standardized default directory; auto-created on first write. |
| `results/benchmarks/` | Raw CSV benchmark outputs (`benchmark_summary_*.csv`). | V1-supported / V2-standardized directory for benchmark CSV outputs; auto-created on write. |
| `results/reports/` | Standalone HTML reports (`cryptography_report_*.html`). | V2-specific report directory; auto-created on first write. |

---

## 16. Error Handling & 3-Tier Diagnostics Contract

V2 converts raw technical exceptions into structured, actionable 3-tier user diagnostics while preserving underlying exception types:

```text
[!] Operation Failed: <Short Title>
------------------------------------------------------------
What Failed : Plain-English description of the immediate failure.
Probable Cause : Why it happened (e.g., mismatched key, corrupt padding, file locked).
Action Steps   : Concrete, numbered steps to resolve the issue.
```

### Exception Mapping Table

| Underlying Exception | Failure Scenario | User-Facing Guidance |
| :--- | :--- | :--- |
| `ValueError` (Padding) | Wrong key or corrupt ciphertext. | Check that the matching `.key` and `.iv` files were selected. |
| `ValueError` (Hex format) | Invalid characters or odd length. | Ensure key contains only hex digits (0-9, a-f) and is 32/48/64 chars. |
| `FileNotFoundError` | Missing input or sidecar file. | Verify the file path; check if the companion `.iv` exists for CBC mode. |
| `PermissionError` | OS file lock or read-only destination. | Close applications using the file or select a writable output folder. |

In `--verbose` mode, the technical traceback is appended after the 3-tier diagnostic block.

---

## 17. Security & Data-Safety Contract

1. **Cryptographic Rigor:** AES-CBC is explicitly documented as providing **confidentiality only**, not data authenticity or integrity. ECB is explicitly flagged with educational warnings regarding pattern leakage.
2. **Secret Privacy:** Raw keys, hex strings, and plaintext payloads are strictly excluded from batch execution logs and HTML reports.
3. **Non-Destructive File I/O:** Source input files are opened in read-only binary mode (`rb`) and are never truncated, modified in-place, or deleted.
4. **Memory Residuals:** Python `bytes` are immutable in CPython, meaning memory zeroization cannot be guaranteed at the application level; this is a documented technical limitation and V2 avoids false security claims regarding in-memory erasure.

---

## 18. Testing Requirements

V2 implementation must include comprehensive pytest suites in `tests/cli_v2/` utilizing `tmp_path`, `monkeypatch`, and `capsys`:

1. **Navigation & UX Tests:**
   - Multi-step wizard completion, `Back` step state retention, `Cancel` cleanup, `?` help display.
2. **Key Management Tests:**
   - Valid 128/192/256-bit `.key` saving/loading, case/whitespace/BOM normalization, reject non-hex / odd length / invalid length, V1 round-trip interoperability (supplying V2 `.key` contents to V1 `--key` argument and vice versa).
3. **Batch Operation Tests:**
   - Multi-file directory batch encrypt/decrypt, single corrupt file error isolation, partial sidecar cleanup verification, skip-existing resumption, `--shared-key` mode verification, `batch_log_*.csv` schema validation, `--dry-run` simulation verification (asserting zero writes and zero output files).
4. **Reporting Tests:**
   - Consolidated HTML generation, inline base64 image validity, XSS escaping on hostile filenames, browser launch parameter verification.
5. **V1 Regression Check:**
   - Verify all 434 existing V1 tests continue to pass with zero modifications.

---

## 19. Objective Acceptance Criteria

V2 implementation is complete and acceptable when:
1. `git diff --stat src/core/ src/engines/ src/analyzers/ src/utils/ src/cli/ tests/` returns empty for the frozen V1 paths; no files under the frozen V1 paths are modified.
2. The frozen V1 baseline remains 434 passed / 2 skipped, and all newly added V2 tests in `tests/cli_v2/` pass with zero regressions.
3. `python -m src.cli_v2.main_v2` launches the guided interactive menu cleanly on Python 3.10+ without arguments.
4. Single-file encryption creates valid ciphertext and symmetrical `.key` / `.iv` sidecars.
5. Cryptographic interoperability holds: a file encrypted in V2 can be decrypted via V1 `python -m src.cli.main decrypt` when supplied with the matching key hex, mode, and IV, and vice versa.
6. Batch operations successfully process multi-file folders, isolate individual errors, clean temporary files safely, skip existing files, and write valid CSV logs.
7. Generated HTML reports open in standard web browsers, render all tables and base64 graphs cleanly offline, and contain zero raw secrets.

---

## 20. Consolidated Decision Log (DSEL)

Every genuine project-level decision is formally recorded below:

### Decision DSEL-001 — V2 Entry Point and Invocation Architecture
- **Question:** How should V2 be invoked from the command line, and how does it relate to V1?
- **Options:**
  - A: Modify V1 `src/cli/main.py` to add interactive default.
  - B: Standalone V2 module `python -m src.cli_v2.main_v2` with zero-arg menu launch and optional subcommands.
  - C: Menu-only executable with no CLI flag support.
- **Selected Option:** Option B.
- **Rationale:** Preserves V1 `main.py` with zero changes while providing a separate V2 entry point that launches the guided menu on zero arguments.
- **Rejected Alternatives:** Option A violates V1 Non-Modification Contract. Option C prevents scriptable automation in V2.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-002 — Menu Navigation State Machine
- **Question:** What navigation model should govern terminal wizards?
- **Options:**
  - A: Flat linear loop (like V1 menu).
  - B: Stack-based stateful wizard supporting `b`ack, `c`ancel, and `?` help tokens.
  - C: External curses/urwid TUI framework.
- **Selected Option:** Option B.
- **Rationale:** Delivers high usability and error-recovery without introducing external dependencies.
- **Rejected Alternatives:** Option A repeats V1 friction. Option C introduces heavy third-party dependencies.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-003 — Key Sidecar Format and Encoding
- **Question:** What file format and structure should be used for persisted `.key` files?
- **Options:**
  - A: Raw hexadecimal ASCII string on a single line.
  - B: Hex string with human-readable `# comment` metadata headers.
  - C: Binary byte files (`.bin`).
- **Selected Option:** Option A.
- **Rationale:** The `.key` file contains raw hexadecimal key material in a representation suitable for supplying to the V1 `--key` hex input interface, assuming algorithm and key size match.
- **Rejected Alternatives:** Option B breaks V1's `_parse_hex()` if pasted into CLI. Option C prevents human inspection and manual recovery.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-004 — Symmetrical Key and IV Sidecar Naming and Auto-Discovery
- **Question:** How should sidecars be named and discovered on disk?
- **Options:**
  - A: `<ciphertext_path>.key` and `<ciphertext_path>.iv` in the same directory.
  - B: Separate `data/keys/` directory with random UUID names.
  - C: Single combined `.keyiv` bundle file.
- **Selected Option:** Option A.
- **Rationale:** Mirrors V1's frozen `run_encrypt()` IV persistence (`output_file + ".iv"`) and allows deterministic sidecar auto-discovery.
- **Rejected Alternatives:** Option B causes key/ciphertext desynchronization when moving files. Option C breaks V1's independent IV loader.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-005 — Key Loader Normalization and Pre-Execution Validation
- **Question:** How strictly should the `.key` loader parse text input?
- **Options:**
  - A: Strict byte matching (reject any newline or whitespace).
  - B: Permissive whitespace, BOM stripping, and uppercase normalization before exact hex length validation.
  - C: Auto-padding/truncating arbitrary strings.
- **Selected Option:** Option B.
- **Rationale:** Handles standard text editor artifacts gracefully while strictly enforcing cryptographic length rules.
- **Rejected Alternatives:** Option A causes frustrating failures over invisible newlines. Option C is cryptographically dangerous.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-006 — Single-File In-Memory Round-Trip Verification
- **Question:** Should post-encryption round-trip verification be mandatory, optional, or omitted?
- **Options:**
  - A: Automatic in-memory verification on every single-file encryption.
  - B: Blocking prompt asking the user whether to verify.
  - C: Omitted.
- **Selected Option:** Option A.
- **Rationale:** The project accepts the additional in-memory encryption/decryption work for single-file verification because it provides immediate confirmation that the encrypted result can be restored to the original plaintext.
- **Rejected Alternatives:** Option B adds an unnecessary prompt. Option C misses a key usability confidence booster.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-007 — Flat Directory Traversal, Exclusion Matrix & Lexical Sorting
- **Question:** How should batch directory scanning, sorting, and exclusions be handled?
- **Options:**
  - A: Flat directory scan with lexical sorting and automatic exclusion of `.enc`, `.key`, `.iv`, `.log`, `.tmp*`, and hidden files.
  - B: Recursive scan by default with directory mirroring.
  - C: Unsorted generator iteration.
- **Selected Option:** Option A.
- **Rationale:** Flat directory processing delivers maximum predictability, simpler progress tracking, and zero risk of recursive output pollution within V2 core scope.
- **Rejected Alternatives:** Recursive processing is deferred to Post-V2 roadmap. Unsorted iteration causes non-deterministic progress indicators.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-008 — Batch Overwrite Conflict & Resumption Policy
- **Question:** What overwrite behavior should govern batch operations?
- **Options:**
  - A: Skip Existing by default with `--on-conflict overwrite` override.
  - B: Overwrite all files silently.
  - C: Prompt interactively for every individual file collision.
- **Selected Option:** Option A.
- **Rationale:** Non-destructive default prevents data loss and provides a non-destructive retry/resumption mechanism by skipping existing destination ciphertexts.
- **Rejected Alternatives:** Option B violates Data Safety principles. Option C causes UI lockups during large batch runs.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-009 — Batch Error Isolation, Logging & Partial-Output Cleanup
- **Question:** How should batch operations handle unreadable files and partial sidecar failures?
- **Options:**
  - A: Abort entire batch on first error.
  - B: Isolate errors per-file, clean newly staged temporary files without destroying pre-existing destination artifacts, record failure in `batch_log_*.csv`, and continue batch processing.
  - C: Ignore errors silently without logging.
- **Selected Option:** Option B.
- **Rationale:** Fulfills V2 Intent requirement C4 for resilient, fault-tolerant batch processing while safeguarding pre-existing files during overwrite failures.
- **Rejected Alternatives:** Option A makes batch unusable on mixed folders. Option C prevents auditing failures.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-010 — Standalone Inline-Asset HTML Report Packaging & Content
- **Question:** How should HTML benchmark and security reports be structured and assets embedded?
- **Options:**
  - A: Multi-file bundle with external CSS and linked PNG files.
  - B: Single HTML artifact with selected CSS and chart assets embedded inline (base64 PNG Data URIs at 150 DPI).
  - C: External JavaScript charting framework (Plotly/Chart.js).
- **Selected Option:** Option B.
- **Rationale:** Delivers offline-viewable reports without external dependencies or disk asset clutter. Standardized 150 DPI provides clean visual rendering while keeping base64 size manageable.
- **Rejected Alternatives:** Option A creates file management friction and broken links when moved. Option C introduces external JS dependencies.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-011 — HTML Report Browser Auto-Open Policy (D4)
- **Question:** How should the browser auto-open capability for HTML reports be triggered?
- **Options:**
  - A: Always open browser unconditionally.
  - B: Prompt interactively in menu mode `[Y/n]`; open by default in CLI mode with `--no-open` flag to disable.
  - C: Never open automatically (display path only).
- **Selected Option:** Option B.
- **Rationale:** Balances desktop convenience with headless/automated CI script execution safety.
- **Rejected Alternatives:** Option A disrupts headless test automation. Option C fails to deliver the promised D4 usability feature.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-012 — Output Directory Explorer / OS File Manager Launcher (A4)
- **Question:** How should the output directory navigation action (Intent A4) behave?
- **Options:**
  - A: Automatically launch Windows Explorer after every file/batch operation.
  - B: Offer as an interactive menu action on the post-operation summary card.
  - C: Omitted.
- **Selected Option:** Option B.
- **Rationale:** Gives the user direct control to inspect outputs without disrupting terminal focus automatically.
- **Rejected Alternatives:** Option A steals focus repeatedly during rapid multi-file operations. Option C omits authorized Intent A4.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-013 — Three-Tier Error Translation & Contextual Help Architecture (A6, A7)
- **Question:** How should runtime errors and cryptographic concepts be presented to users?
- **Options:**
  - A: Direct Python exception traceback dumps.
  - B: Dedicated `error_translator.py` mapping standard exceptions to structured 3-tier diagnostics (What, Why, Action) and contextual `?` tooltips.
  - C: Generic one-line error banners.
- **Selected Option:** Option B.
- **Rationale:** Transforms confusing low-level errors into actionable educational guidance without creating custom exception hierarchies.
- **Rejected Alternatives:** Option A overwhelms students with stack traces. Option C lacks actionable recovery steps.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-014 — Windows Quick-Launcher Specification (`run-v2.bat`)
- **Question:** How should the Windows quick launcher (Intent §9.2) be specified?
- **Options:**
  - A: Thin `.bat` script in project root forwarding arguments to `main_v2.py`.
  - B: Compiled `.exe` binary launcher.
  - C: Omitted / Deferred.
- **Selected Option:** Option A.
- **Rationale:** Fulfills V2_INTENT §9.2 desktop launcher requirement using zero dependencies and pure standard Windows batch syntax.
- **Rejected Alternatives:** Option B requires external compilation tools and binary distribution. Option C omits Intent §9.2.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-015 — Directory Workspace Structure & Auto-Creation Policy
- **Question:** How should workspace directories (`data/input/`, `data/output/`, `data/decrypted/`, `results/reports/`) be managed?
- **Options:**
  - A: Automatically ensure/create destination directories on demand via `FileHandler.ensure_directory()`.
  - B: Fail immediately if destination directory does not pre-exist.
  - C: Require user to create directories via OS shell.
- **Selected Option:** Option A.
- **Rationale:** Eliminates setup friction while maintaining deterministic filesystem paths.
- **Rejected Alternatives:** Options B and C introduce unnecessary friction for new users.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-016 — Session Key Caching & In-Memory Key State
- **Question:** Should V2 maintain a global in-memory session key cache across wizard invocations?
- **Options:**
  - A: Retain a global in-memory key cache for the active session.
  - B: Maintain strict stateless execution per wizard run with zero global key caching.
  - C: Write session keys to a temporary hidden file.
- **Selected Option:** Option B.
- **Rationale:** Minimizes secret exposure and prevents state pollution across separate cryptographic operations.
- **Rejected Alternatives:** Option A and C increase secret leakage risks in long-running terminal sessions.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-017 — Interactive Key Display & Laboratory Terminal Visibility
- **Question:** Should full hex key strings be displayed in the terminal during interactive single-file encryption?
- **Options:**
  - A: Display the full generated hex key in the summary card as a deliberate laboratory visibility feature, accompanied by an explicit laboratory notice.
  - B: Mask the key (e.g., `e3b0...b855`).
  - C: Never show the key on screen.
- **Selected Option:** Option A.
- **Rationale:** Deliberate V2 selection for educational and laboratory testing workflows allowing immediate inspection and verification; keys displayed on screen are never written to logs or HTML reports.
- **Rejected Alternatives:** Option B and C hinder manual verification in educational testing workflows.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-018 — Batch Key Strategy & Shared-Key Coordination
- **Question:** How should key generation and distribution be structured in batch operations?
- **Options:**
  - A: Default to unique per-file keys (`<filename>.enc.key`); support opt-in shared batch key (`batch.key` saved to `<output_dir>/batch.key` via `--shared-key` or menu choice, with unique random IV per file in CBC mode).
  - B: Mandatory shared batch key only.
  - C: Mandatory unique keys only.
- **Selected Option:** Option A.
- **Rationale:** Provides minimal cryptographic blast radius by default while offering shared-key convenience when requested (maintaining unique random IVs per file in CBC mode to prevent two-time pad / IV reuse issues).
- **Rejected Alternatives:** Option B increases blast radius if key is compromised. Option C eliminates useful shared-key testing workflows.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

### Decision DSEL-019 — Pre-Flight Dry-Run Preview & Batch Confirmation Semantics
- **Question:** How should dry-run previews and confirmation semantics be structured across interactive menu vs direct CLI execution?
- **Options:**
  - A: Interactive menu workflows require an explicit pre-flight discovery preview and user confirmation step before execution. Direct CLI execution performs pre-flight validation and executes without prompt. The direct CLI exposes `--dry-run` to run discovery and print planned actions without modifying files or creating output artifacts.
  - B: Require interactive confirmation prompts in direct CLI commands.
  - C: Execute batch operations immediately without pre-flight discovery in menu mode.
- **Selected Option:** Option A.
- **Rationale:** Provides complete visibility and user confirmation in interactive workflows, scriptable automation in direct CLI execution, and safe non-destructive simulation via `--dry-run`.
- **Rejected Alternatives:** Option B breaks scriptability for direct CLI commands. Option C risks unintended batch operations in interactive mode.
- **Status:** FROZEN FOR V2 IMPLEMENTATION.

---

## 21. Open-Decision Disposition Matrix

The table below reconciles all **35 research open decisions** across Reports A, B, C, and D into binding project selections:

| Source ID | Report | Topic | Disposition | Final DSEL | Rationale / Reference |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **A-OPEN-01** | A | Menu Depth vs Dynamic Modes | **RESOLVED** | DSEL-002 | 2-level task-centric hierarchy selected (§9.1). |
| **A-OPEN-02** | A | Round-Trip Verification Policy | **RESOLVED** | DSEL-006 | Automatic in-memory verification for single-file, omitted for batch. |
| **A-OPEN-03** | A | Key Sidecar File Extension & Naming | **RESOLVED** | DSEL-004 | Standardized as `<ciphertext_path>.key` (§11.1). |
| **A-OPEN-04** | A | Direct Command Invocation in V2 | **RESOLVED** | DSEL-001 | Standalone V2 entry point with subcommands and zero-arg menu launch (§8.1). |
| **A-OPEN-05** | A | Output Directory Auto-Creation | **RESOLVED** | DSEL-015 | Auto-create output directories on demand via `FileHandler.ensure_directory()` (§15). |
| **A-OPEN-06** | A | Overwrite Confirmation Granularity | **RESOLVED** | DSEL-008 | Global policy (default: Skip Existing) with pre-flight selection (§12.3). |
| **B-OPEN-01** | B | Key File Extension Policy | **RESOLVED** | DSEL-003, DSEL-005 | `.key` is the mandatory standard extension (§11.1). |
| **B-OPEN-02** | B | Key File Header Policy | **RESOLVED** | DSEL-003, DSEL-005 | Pure raw hex text; no `#` comments for V1 `--key` copy-paste suitability (§11.1). |
| **B-OPEN-03** | B | Session Key Caching | **RESOLVED** | DSEL-016 | Stateless per wizard run; no global key memory cache retained (§17). |
| **B-OPEN-04** | B | Auto-Detection Scope | **RESOLVED** | DSEL-004 | Search same directory as ciphertext first, fallback to prompt (§10, Workflow 2). |
| **B-OPEN-05** | B | Interactive Key Display | **RESOLVED** | DSEL-017 | Display full hex key upon generation in summary card for verification (§10, §11.4). |
| **B-OPEN-06** | B | Missing IV Fallback Policy | **RESOLVED** | DSEL-004, DSEL-009 | Prompt interactively for hex IV in single-file; record failure in batch (§10, §12.3). |
| **B-OPEN-07** | B | Security Warning Frequency | **RESOLVED** | DSEL-003 | Non-blocking educational banner on every `.key` file creation (§11.4). |
| **C-OPEN-01** | C | Traversal Mode (Flat vs Recursive) | **RESOLVED** | DSEL-007 | Flat directory traversal only; recursive mode deferred to Post-V2 (§4.2, §12.1). |
| **C-OPEN-02** | C | Output Destination Policy | **RESOLVED** | DSEL-015 | Default to `data/output/` with explicit user override support (§15). |
| **C-OPEN-03** | C | Batch Overwrite Policy Default | **RESOLVED** | DSEL-008 | Default "Skip Existing" with `--on-conflict overwrite` override (§12.3). |
| **C-OPEN-04** | C | Key Strategy Default in Batch | **RESOLVED** | DSEL-018 | Default unique per-file keys; opt-in shared batch key via `--shared-key` (§12.2). |
| **C-OPEN-05** | C | Sidecar Decryption Resolution | **RESOLVED** | DSEL-009 | Skip missing sidecar, tally as `FAILED`, and continue remaining batch (§12.3). |
| **C-OPEN-06** | C | Hidden Files Policy | **RESOLVED** | DSEL-007 | Exclude hidden files automatically in default exclusion matrix (§12.1). |
| **C-OPEN-07** | C | Symlink & Junction Policy | **RESOLVED** | DSEL-007 | Exclude symlinks/junctions in V2 flat traversal to avoid loops (§12.1). |
| **C-OPEN-08** | C | Progress Throttling Rate | **RESOLVED** | DSEL-009 | Rate-throttle `\r` updates (Phase 5 implementation detail: ~50-100ms) (§12.4). |
| **C-OPEN-09** | C | Large-Folder Confirmation | **RESOLVED** | DSEL-019 | Pre-flight discovery preview and confirmation in interactive menu; no artificial numeric threshold (§10, §12). |
| **C-OPEN-10** | C | Partial-Output Cleanup | **RESOLVED** | DSEL-009 | Delete in-flight `.tmp_*` files on failure without destroying existing files (§12.4). |
| **C-OPEN-11** | C | Batch Log Format & Timestamps | **RESOLVED** | DSEL-009 | Standard CSV (`batch_log_*.csv`) with ISO-8601 UTC timestamps (§12.5, §14.3). |
| **C-OPEN-12** | C | Dry-Run Exposure | **RESOLVED** | DSEL-019 | Built into guided wizard preview step and exposed via `--dry-run` flag for CLI (§8.2, §10). |
| **D-OPEN-01** | D | Report Packaging Model | **RESOLVED** | DSEL-010 | Unified single-document HTML report with adaptive section visibility (§13.1). |
| **D-OPEN-02** | D | Auto-Open Default Behavior | **RESOLVED** | DSEL-011 | Prompt in menu mode `[Y/n]`; open by default in CLI with `--no-open` (§13.4). |
| **D-OPEN-03** | D | Report Output Directory | **RESOLVED** | DSEL-010, DSEL-015 | Standardized to `results/reports/` (§15). |
| **D-OPEN-04** | D | Graph Resolution & DPI | **RESOLVED** | DSEL-010 | Standardized to 150 DPI for embedded Matplotlib figures (§13.1). |
| **D-OPEN-05** | D | ECB Visualization Style | **RESOLVED** | DSEL-010 | Side-by-side ECB leakage vs CBC diffusion bitmap comparison figure (§13.2). |
| **D-OPEN-06** | D | Report Regeneration Scope | **RESOLVED** | DSEL-010 | Generate reports from active session metrics; historical re-parsing deferred (§4.2). |
| **D-OPEN-07** | D | CSS Theme / Style Standardization | **RESOLVED** | DSEL-010 | Minimalist laboratory card theme with internal CSS and `@media print` (§13.1). |
| **D-OPEN-08** | D | Batch Log Inclusion Level | **RESOLVED** | DSEL-010 | Embed aggregate batch summary metrics; link to companion CSV log (§13.2). |
| **D-OPEN-09** | D | Report Retention & Disk Cleanup | **RESOLVED** | DSEL-010 | User-managed file lifecycle; automated deletion deferred to Post-V2 (§4.2). |
| **D-OPEN-10** | D | Report Schema Versioning | **RESOLVED** | DSEL-010 | Include `data-report-version="2.0"` and ISO-8601 generation metadata (§13.2). |

---

## 22. Recommendation Disposition Matrix

The table below formally records the disposition of all **53 candidate research recommendations**:

| Research ID | Category | Recommendation Topic | Disposition | Selected Decision / Contract |
| :--- | :---: | :--- | :---: | :--- |
| **A-01** | A | Task-Centric Hierarchical Menu | **APPROVE** | DSEL-002, Menu Contract §9 |
| **A-02** | A | Universal Step Navigation (`Back`/`Cancel`) | **APPROVE** | DSEL-002, Navigation Contract §9.2 |
| **A-03** | A | Safe Defaults with Explicit Visibility | **APPROVE** | Workflow Contract §10 |
| **A-04** | A | Hybrid File Selection (Picker + Custom Path)| **APPROVE** | `file_picker.py` Contract §7 |
| **A-05** | A | Automated Sidecar Key Management | **APPROVE** | DSEL-003, DSEL-004, Key Contract §11 |
| **A-06** | A | Automatic Round-Trip Verification | **MODIFY** | DSEL-006 (Automatic for single-file, omitted for batch) |
| **A-07** | A | Structured Post-Operation Summary Cards | **APPROVE** | Presentation Contract §7, §10 |
| **A-08** | A | Three-Tier Actionable Error Diagnostics | **APPROVE** | DSEL-013, Error Contract §16 |
| **A-09** | A | Contextual In-App Help & Micro-Tooltips | **APPROVE** | DSEL-013, Navigation Contract §9.2 |
| **A-10** | A | Native OS Integration (Explorer/Browser) | **MODIFY** | DSEL-011 (Browser D4), DSEL-012 (Explorer A4) |
| **A-11** | A | Zero-Dependency Progress Feedback (`\r`) | **APPROVE** | Batch Contract §12.4 |
| **A-12** | A | Decoupled Interactive Testing Architecture | **APPROVE** | Testing Contract §18 |
| **B-01** | B | Plain Hexadecimal Text Format | **APPROVE** | DSEL-003, Format Contract §14.1 |
| **B-02** | B | Sidecar Naming Convention (`<output>.key`) | **APPROVE** | DSEL-004, Key Contract §11.1 |
| **B-03** | B | Multi-Tier Pre-Execution Key Validation | **APPROVE** | DSEL-005, Key Contract §11.2 |
| **B-04** | B | Explicit Auto-Detection Confirmation | **APPROVE** | Workflow 2 Contract §10 |
| **B-05** | B | Non-Blocking Laboratory Security Notice | **APPROVE** | Key Contract §11.4 |
| **B-06** | B | Symmetrical Key and IV Separation | **APPROVE** | DSEL-004, Key Contract §11.3 |
| **B-07** | B | Key-Length Based Size Derivation | **APPROVE** | DSEL-005, Key Contract §11.2 |
| **B-08** | B | Permissive Whitespace Normalization on Load | **APPROVE** | DSEL-005, Key Contract §11.2 |
| **B-09** | B | Proactive Key Overwrite Protection | **APPROVE** | Key Contract §11 |
| **B-10** | B | Transparent In-Memory Secret Handling | **APPROVE** | Security Contract §17 |
| **B-11** | B | Standardized Windows File Creation | **APPROVE** | Key Contract §11 |
| **B-12** | B | Decoupled Key Management Test Harness | **APPROVE** | Testing Contract §18 |
| **C-01** | C | Sequential Iteration Engine | **APPROVE** | Batch Contract §12 |
| **C-02** | C | Flat Directory Traversal with Lexical Sort | **APPROVE** | DSEL-007, Batch Contract §12.1 |
| **C-03** | C | Candidate Exclusion Matrix | **APPROVE** | DSEL-007, Batch Contract §12.1 |
| **C-04** | C | Option C Key Strategy (Unique vs Shared) | **APPROVE** | DSEL-018, Batch Contract §12.2 |
| **C-05** | C | Generate Matching Sidecars for Batch | **APPROVE** | DSEL-004, Batch Contract §12.2 |
| **C-06** | C | Skip Existing Default Overwrite Policy | **APPROVE** | DSEL-008, Batch Contract §12.3 |
| **C-07** | C | Per-File Exception Handling & Error Isolation | **APPROVE** | DSEL-009, Batch Contract §12.4 |
| **C-08** | C | Write-and-Replace Atomic Output Strategy | **MODIFY** | DSEL-009, Bounded to single paths (§12.4) |
| **C-09** | C | Single-Line `\r` Progress Indicator | **APPROVE** | Batch Contract §12.4 |
| **C-10** | C | Standardized CSV Batch Logging (`batch_log_*.csv`) | **APPROVE** | DSEL-009, Batch Contract §12.5 |
| **C-11** | C | Security Policy: Exclude Secrets from Logs | **APPROVE** | Batch Contract §12.5, Security §17 |
| **C-12** | C | Consolidated Summary Card on Batch Finish | **APPROVE** | Workflow 3/4 Contract §10 |
| **C-13** | C | Clean Cancellation on `KeyboardInterrupt` | **APPROVE** | Batch Contract §12.4 |
| **C-14** | C | Pre-Flight Dry Run / Preview Step | **APPROVE** | DSEL-019, Workflow 3 Contract §10 |
| **C-15** | C | Strict Non-Destructive Source File Handling| **APPROVE** | Security Contract §17 |
| **D-01** | D | Hybrid Template Engine (`string.Template` + f-strings) | **APPROVE** | DSEL-010, Report Contract §13.1 |
| **D-02** | D | Strict `html.escape(quote=True)` Sanitization | **APPROVE** | Report Contract §13.3 |
| **D-03** | D | Internal CSS with `@media print` | **APPROVE** | DSEL-010, Report Contract §13.1 |
| **D-04** | D | In-Memory Base64 PNG Embedding (`plt.close`)| **APPROVE** | DSEL-010, Report Contract §13.1 |
| **D-05** | D | Unified Single-Document Report Format | **APPROVE** | DSEL-010, Report Contract §13.1 |
| **D-06** | D | Save Reports to `results/reports/` | **APPROVE** | DSEL-015, Directory Contract §15 |
| **D-07** | D | Cross-Platform `as_uri()` Browser Dispatch | **APPROVE** | DSEL-011, Report Contract §13.4 |
| **D-08** | D | CSS Progress Bars for Security Metrics | **APPROVE** | Report Contract §13.2 |
| **D-09** | D | Explicit Methodology Section in Report | **APPROVE** | Report Contract §13.2 |
| **D-10** | D | Exclude Keys and Plaintext from HTML | **APPROVE** | Report Contract §13.3, Security §17 |
| **D-11** | D | Aggregate Batch Summaries in Reports | **APPROVE** | Report Contract §13.2 |
| **D-12** | D | Standardized 150 DPI for Figures | **APPROVE** | DSEL-010, Report Contract §13.1 |
| **D-13** | D | Explicit UTF-8 Encoding on File Writes | **APPROVE** | Report Contract §13.1 |
| **D-14** | D | Configurable Browser Auto-Open Behavior | **APPROVE** | DSEL-011, Report Contract §13.4 |

---

## 23. Traceability Matrix

The matrix below establishes complete end-to-end traceability from V2 Intent requirements through research, selection decisions, and implementation contracts:

```text
V2 Intent Requirement
       │
       ▼
Research Findings & Candidate Proposals (Reports A, B, C, D)
       │
       ▼
Project-Specific Selection Decision (DSEL-001 to DSEL-019)
       │
       ▼
Frozen V2 Implementation Contract (Sections 7–19)
```

| V2 Intent Scope | Research Source | Selection Decision | Target Implementation Contract |
| :--- | :--- | :--- | :--- |
| **A1: File Picker** | Report A §14, A-04 | DSEL-002, DSEL-015 | `src/cli_v2/file_picker.py` |
| **A2: Output Prompts**| Report A §6, A-03, A-05 | DSEL-004, DSEL-015 | `src/cli_v2/menu_v2.py` |
| **A3: Round-Trip Verify**| Report A §12, A-06 | DSEL-006 | `src/cli_v2/menu_v2.py` (Workflow 1) |
| **A4: Explorer Launcher**| Report A §19, A-10 | DSEL-012 | `src/cli_v2/presentation.py` |
| **A5: Summary Cards** | Report A §12, A-07 | DSEL-002, DSEL-017 | `src/cli_v2/presentation.py` |
| **A6: Error Diagnostics**| Report A §9, A-08 | DSEL-013 | `src/cli_v2/error_translator.py` |
| **A7: In-App Help** | Report A §10, A-09 | DSEL-013 | `src/cli_v2/navigation.py` |
| **B1: Key/IV Persistence**| Report B §2, B-01, B-02 | DSEL-003, DSEL-004 | `src/cli_v2/key_manager.py` |
| **B2: Key Loading** | Report B §19, B-04, B-08| DSEL-005, DSEL-016 | `src/cli_v2/key_manager.py` |
| **B3: Key Validation** | Report B §19, B-03, B-07| DSEL-005 | `src/cli_v2/key_manager.py` |
| **B4: Security Notices**| Report B §13, B-05 | DSEL-003, DSEL-017 | `src/cli_v2/presentation.py` |
| **C1: Batch Encrypt** | Report C §4, C-01..C-05| DSEL-007, DSEL-008, DSEL-018 | `src/cli_v2/batch_orchestrator.py` |
| **C2: Batch Decrypt** | Report C §5, C-06..C-08| DSEL-008, DSEL-009, DSEL-018 | `src/cli_v2/batch_orchestrator.py` |
| **C3: Accounting/Status**| Report C §11, C-09, C-12| DSEL-009, DSEL-019 | `src/cli_v2/presentation.py` |
| **C4: Resilient Logging**| Report C §12, C-10, C-11| DSEL-009 | `src/cli_v2/batch_orchestrator.py` |
| **D1: Benchmark Reports**| Report D §4, D-05, D-09 | DSEL-010 | `src/cli_v2/report_generator.py` |
| **D2: Standalone HTML** | Report D §6, D-01..D-04 | DSEL-010 | `src/cli_v2/report_generator.py` |
| **D3: Security Visuals** | Report D §8, D-08, D-12 | DSEL-010 | `src/cli_v2/report_generator.py` |
| **D4: Auto-Open Browser**| Report D §9, D-07, D-14 | DSEL-011 | `src/cli_v2/report_generator.py` |

---

## 24. Final Selection Verdict

```text
DRAFT COMPLETE — PENDING INDEPENDENT VERIFICATION
```
