# V2 INTENT — Cryptography Testing Lab

**Status:** REVIEWED DRAFT  
**Date:** 2026-09-15  
**Author:** V2 Planning  
**Relationship to V1:** Usability & Guided Workflow Extension (V1 frozen, untouched, independently executable)

---

## 1. Purpose

V1 successfully established a robust, deterministic cryptographic foundation: frozen core layers, high-assurance cipher implementations, disciplined test coverage (434 passing tests), and evidence-based benchmark and security analysis tools. 

However, V1 is primarily a **developer- and technical-oriented tool**. Operating V1 requires memorizing CLI flags, manually copy-pasting hexadecimal keys and IVs across commands, managing paths by hand, and understanding underlying cryptographic primitives.

**V2 exists to make the Cryptography Testing Lab accessible, practical, and intuitive for everyday users, students, and evaluators through guided workflows, automated key handling, resilient batch operations, and human-readable reporting — without modifying, weakening, or replacing V1.**

---

## 2. Target Users & Usability Problem

### 2.1 Target Users

| User Persona | Primary Needs | Primary Interface |
| :--- | :--- | :--- |
| **Developer / Security Engineer** | Direct CLI flags, scriptable execution, exact technical control, raw timing/metrics data. | V1 CLI (`src.cli.main`) |
| **Student / Educator / Evaluator** | Guided step-by-step prompts, visual feedback, educational insights, self-explanatory workflows. | V2 Guided UX |
| **Practical / Non-Technical User** | Folder encryption/decryption, automatic key management, HTML reports, clear error explanations without crypto jargon. | V2 Guided UX & Batch Tools |

### 2.2 Core Friction Points in V1 Solved by V2

1. **Cognitive Load & Flag Memorization:** V1 requires exact CLI arguments (`--mode`, `--key`, `--iv`, `--input-file`, `--output-file`). V2 introduces interactive, step-by-step guided flows.
2. **Manual Key Handling Friction:** V1 requires manual copy-pasting of 32/64-character hex strings. V2 provides automatic key persistence, sidecar `.key` files, and key validation.
3. **Single-File Limitation:** V1 processes one file per command. V2 enables resilient batch processing of entire directories with per-file status accounting.
4. **Raw Terminal Metrics:** V1 outputs text-based benchmark tables and security metrics to the console. V2 introduces formatted, standalone HTML and visual reports that can automatically open in the browser.
5. **Crypto Knowledge Barrier:** V1 expects the user to understand modes (ECB vs. CBC), IV requirements, and padding rules. V2 provides guided selection, safe defaults, in-app explanations, and round-trip verification.

---

## 3. Relationship to V1 & Architecture Isolation

V2 is an **additive usability layer** built strictly on top of V1, not a rewrite or replacement.

```text
┌─────────────────────────────────────────────────────────────┐
│                    V2 Usability Layer                       │
│  Guided Menu UX │ Key Management │ Batch Ops │ HTML Reports │
└──────────────────────────────┬──────────────────────────────┘
                               │ consumes / wraps
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    V1 Foundation (FROZEN)                   │
│  CipherService │ BenchmarkService │ SecurityService │ Utils │
│  AES Core (ECB / CBC) │ MetricCollector │ PerformanceTimer  │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Coexistence and Compatibility Principles

* **V1 Remains Usable & Independent:** V1 direct subcommands (`encrypt`, `decrypt`, `benchmark`, `security`, `menu` via `python -m src.cli.main <command>`) remain 100% operational and unchanged. As in V1, a subcommand is required (`python -m src.cli.main menu` launches the V1 interactive menu); a zero-argument invocation continues to produce an argparse usage error by design.
* **Preservation of Cryptographic Behavior:** V2 consumes V1 services directly or through thin adapters; it must never alter cryptographic mathematics, IV generation semantics, padding logic, or metric measurement accuracy.
* **No Cryptographic Re-implementation:** V2 must not duplicate cipher engines or re-implement encryption algorithms.
* **Strict Behavioral Consistency:** A file encrypted via V2 must be decryptable via V1, and vice versa.

| Dimension | V1 (Technical Foundation) | V2 (Guided Usability Layer) |
| :--- | :--- | :--- |
| **Status** | Frozen (`v1.0-release`, commit `650bc7f`) | Active Planning / New Layer |
| **Primary Invocation** | `python -m src.cli.main [command]` | `python -m src.cli_v2.main_v2` / Launcher |
| **Interaction Model** | CLI flags + linear CLI menu | Guided interactive UX with step-by-step prompts |
| **Key Handling** | Manual hex copy-paste | Automated key sidecars (`.key`), load/save prompts |
| **Processing Scope** | Single file / single string | Single file + resilient batch folder processing |
| **Output Formats** | Terminal stdout + raw PNG/CSV | Rich terminal summaries + standalone HTML reports |
| **Error Handling** | Technical exceptions & exit codes | Human-readable diagnostics with recovery suggestions |

---

## 4. V1 Non-Modification Contract

V2 will **NOT** modify, move, or rename any file in the frozen V1 codebase:

* `src/core/*` (AES cipher implementation, ECB/CBC modes)
* `src/engines/*` (`CipherService`, `BenchmarkService`, `SecurityService`, `CipherFactory`, `CipherInterface`)
* `src/analyzers/*` (`MetricCollector`, `PerformanceTimer`, `SecurityEvaluator`, `GraphGenerator`)
* `src/utils/*` (`padding.py`, `file_handler.py`, formatters, validators)
* `src/cli/*` (V1 CLI entry points, argument parsers, commands, and menu)
* `tests/*` (All existing 434 passing V1 unit and integration tests)
* `requirements.txt` (Zero new third-party dependencies permitted)
* `.gitignore` & existing release artifacts

**Enforcement:** Every V2 development phase and verification checkpoint must verify via `git diff --stat` that all V1 files remain completely unmodified.

---

## 5. V2 Core Scope

The baseline scope for V2 consists of four cohesive functional categories:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                               V2 SCOPE                                 │
├──────────────────┬──────────────────┬──────────────────┬───────────────┤
│    Category A    │    Category B    │    Category C    │  Category D   │
│  Guided Menu UX  │  Key Management  │ Batch Operations │   Reporting   │
└──────────────────┴──────────────────┴──────────────────┴───────────────┘
```

### 5.1 Category A: Guided Menu UX

Provide an intuitive, frictionless terminal user experience that guides users through operations without requiring CLI flag knowledge.

* **A1 — Interactive File Selection:** Browse and select target files from `data/input/` or custom directories without manual path typing.
* **A2 — Automated Output & Key Prompts:** Clear, sequential prompts for saving ciphertexts, initialization vectors (IVs), and keys to sensible default paths.
* **A3 — Round-Trip Verification:** Optional or automatic post-encryption decryption test to immediately assure the user that their data can be restored safely.
* **A4 — Output Directory Navigation:** Convenient action to open the destination output folder in the OS file manager (e.g., Windows Explorer) upon completion.
* **A5 — Post-Operation Summaries:** Clean visual summary cards detailing file sizes, algorithm used, key location, output location, and execution duration.
* **A6 — Human-Readable Error Diagnostics:** Translate technical exceptions (e.g., padding corruptions, file permission errors) into clear, actionable advice.
* **A7 — Contextual In-App Help:** Embedded "How does this work?" explanations for cryptographic concepts (ECB vs CBC, why IVs matter, key safety).

### 5.2 Category B: Key Management

Eliminate the burden and security hazards of manual hex string copy-pasting while keeping key management transparent.

* **B1 — Key & IV File Persistence:** Save generated keys and IVs into designated sidecar files (`.key`, `.iv`) alongside encrypted outputs.
* **B2 — Key File Loading:** Select and load saved `.key` files directly during decryption workflows.
* **B3 — Key Format & Size Validation:** Validate key integrity (hex length, character validity, 128/192/256-bit match) before attempting cryptographic operations.
* **B4 — Plaintext Key Safety Warnings:** Clear, prominent warnings that unencrypted `.key` files on disk are for laboratory/testing use and must be secured.

### 5.3 Category C: Batch Operations

Enable multi-file directory processing with robust error isolation.

* **C1 — Batch Folder Encryption:** Encrypt all matching files within an input directory in a single operation.
* **C2 — Batch Folder Decryption:** Decrypt all matching ciphertexts within an input directory using supplied or associated keys.
* **C3 — Per-File Result Accounting:** Display progress indicators and a structured completion table showing individual file status (Success / Skipped / Failed).
* **C4 — Resilient Error Logging:** Failure on a single corrupted file must not abort the entire batch job; failed items are logged to a dedicated run log (`errors.log` / summary log) while remaining files continue processing.

### 5.4 Category D: Reporting & Analysis

Deliver professional, readable artifacts summarizing benchmark and security evaluation results.

* **D1 — Consolidated Benchmark Reports:** Unified presentation of throughput, memory utilization, and latency across key sizes and modes.
* **D2 — Standalone HTML Report Generation:** Generate self-contained, beautifully styled HTML reports combining summary tables, metrics, and embedded visual graphs.
* **D3 — Comparative Security Visualizations:** Clear side-by-side comparative reporting of ECB pattern leakage vs. CBC diffusion (e.g., bitmap analysis, entropy scores).
* **D4 — Auto-Open in Browser:** Option to automatically launch generated HTML reports in the default web browser upon completion.

---

## 6. Data Safety, Integrity & Error Recovery Principles

V2 must prioritize user confidence, data preservation, and predictable error handling:

1. **Zero Silent Overwrite Policy:** Never overwrite existing plaintext, ciphertext, or key files without explicit user confirmation or a designated conflict resolution policy.
2. **Pre-Operation Validation:** Verify file existence, read/write permissions, and disk space feasibility prior to initiating intensive batch or encryption tasks.
3. **Fault-Tolerant Batch Processing:** An unreadable or corrupt file during a batch run must be recorded as an individual failure without terminating the batch workflow for subsequent files.
4. **Non-Destructive Operations:** Original input files must remain completely untouched during encryption and decryption workflows.
5. **Deterministic Diagnostics:** Error states must provide understandable feedback explaining *what failed*, *why it failed*, and *how to resolve it* (e.g., "Incorrect key or corrupt padding" rather than a raw unhandled stack trace).

---

## 7. V2 Non-Scope & Deferred Features

To maintain disciplined focus and preserve architectural boundaries, the following items are **strictly OUT of scope for V2**:

| Non-Scope Item | Rationale & Classification |
| :--- | :--- |
| **Modifying V1 Core / Engines** | V1 is frozen; V2 is strictly an additive extension layer. |
| **New Third-Party Dependencies** | Zero external dependencies; standard library + existing V1 dependencies only (`matplotlib` already in V1). |
| **Custom Exception Hierarchies** | Maintain frozen architectural contract using Python standard exception types. |
| **Web Server / Web UI / REST API** | V2 is a terminal/CLI application; standalone HTML reports are static output artifacts, not a web server. |
| **Database Backends / ORMs** | File-system-based persistence is sufficient and appropriate for the testing lab. |
| **Multi-User / Authentication / Cloud** | Desktop testing lab context; multi-tenant architecture is out of scope. |
| **Password-Based Encryption (PBKDF2 / Argon2)** | Deferred to Post-V2 / Future roadmap. |
| **Authenticated Encryption (AES-GCM / ChaCha20-Poly1305)** | Deferred to Post-V2 / Future roadmap. |
| **Asymmetric / Other Ciphers (RSA, Blowfish, Classical)** | Placeholders remain frozen in V1; full implementations deferred to Post-V2. |
| **Streaming / Chunked Large-File Encryption** | V1 engine is buffer-based; streaming architecture deferred to future core major revision. |

---

## 8. V2 Success & Verification Criteria

V2 acceptance requires fulfilling all of the following verifiable conditions:

| Success Criterion | Verification Method |
| :--- | :--- |
| **V1 Code Unaltered** | `git diff --stat src/core/ src/engines/ src/analyzers/ src/utils/ src/cli/` returns empty. |
| **V1 Test Suite Baseline** | `python -m pytest tests/` passes 434 tests (with 2 platform-specific skipped). |
| **V1 CLI Fully Functional** | `python -m src.cli.main menu` and direct V1 CLI commands execute without regression. |
| **Zero New Dependencies** | `requirements.txt` remains bit-for-bit identical to V1 release. |
| **Standard Exception Conformance** | V2 codebase uses only standard Python exceptions; no custom base classes introduced. |
| **V2 Test Suite Passing** | Comprehensive unit and integration test coverage for all new V2 modules with 100% pass rate. |
| **Guided Workflow Verification** | End-to-end user walkthrough of single-file encrypt, key save, round-trip verify, and decrypt completes seamlessly. |
| **Batch Workflow Verification** | Folder batch encryption and decryption correctly handles mixed file sets and logs individual errors gracefully. |
| **Key Persistence Verification** | Key file generation, validation, and loading work across both V2 and V1 inter-compatibility checks. |
| **HTML Report Generation** | Generated HTML benchmark/security report renders cleanly in standard modern browsers with valid graphs and tables. |

---

## 9. Illustrative V2 Structure & Entry Points (Provisional)

> *Note: The module structure below represents conceptual intent and is subject to detailed architectural design during Phase 1 (Research) and Phase 3 (Selection).*

### 9.1 Conceptual Module Organization

```text
src/
├── cli/                 # [V1 FROZEN] Technical CLI & commands
├── cli_v2/              # [V2 NEW] Usability & guided interaction layer
│   ├── __init__.py
│   ├── main_v2.py       # V2 entry point router
│   ├── menu_v2.py       # Guided interactive workflow engine
│   ├── commands_v2.py   # Guided operation handlers
│   ├── key_management.py# Key/IV persistence & validation
│   ├── batch_ops.py     # Multi-file directory batch executor
│   ├── file_picker.py   # Interactive file & path helper
│   ├── progress.py      # Terminal progress & status indicators
│   ├── summary.py       # Visual summary card generators
│   ├── errors.py        # Friendly error translations
│   ├── help_text.py     # Contextual educational help system
│   └── report_generator.py # HTML & text report builder
tests/
├── cli_v2/              # [V2 NEW] Dedicated V2 test suite
```

### 9.2 Intended Invocation Methods

1. **Python Module Command:** `python -m src.cli_v2.main_v2` (launches guided interactive UX)
2. **Windows Quick Launcher:** Double-clickable launcher script for non-technical users
3. **Direct V2 Subcommands:** Optional direct parameter execution preserving guided safety features

---

## 10. Engineering & Quality Constraints

| Category | Constraint Specification |
| :--- | :--- |
| **Target Runtime** | Python 3.10+ (tested on Windows 11 & cross-platform) |
| **Dependency Policy** | Zero additional dependencies beyond V1 (`matplotlib` for graphs) |
| **Path Handling** | Strict use of `pathlib.Path` for cross-platform compatibility |
| **Test Isolation** | All file-based tests must use pytest `tmp_path` fixtures |
| **Code Documentation** | Comprehensive Google-style docstrings on all public functions and classes |
| **Static Typing** | Complete type annotations throughout all new V2 modules |
| **Error Handling** | Standard built-in exceptions (`ValueError`, `FileNotFoundError`, `IOError`, `KeyError`) |
| **Git Discipline** | Atomic, well-documented commits with regression verification checkpoints |

---

## 11. V2 Development & Governance Process

V2 development follows the project's disciplined engineering lifecycle:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  Phase 0: Intent (This Document — Scope, Boundaries, Usability Goals)       │
│      ▼                                                                      │
│  Phase 1: Research (UX flows, batch algorithms, static HTML reporting)      │
│      ▼                                                                      │
│  Phase 2: Forensic Audit (Verify V1 baseline & frozen layer isolation)      │
│      ▼                                                                      │
│  Phase 3: Selection (Finalize exact contracts, signatures, schemas)         │
│      ▼                                                                      │
│  Phase 4: Independent Review (Selection validation)                         │
│      ▼                                                                      │
│  Phase 5: Implementation Plan (Task breakdown, test plan, file plan)        │
│      ▼                                                                      │
│  Phase 6: Implementation (Additive build of V2 modules)                     │
│      ▼                                                                      │
│  Phase 7: Testing & Verification (Unit, integration, walkthrough tests)     │
│      ▼                                                                      │
│  Phase 8: Implementation Review & Audit                                      │
│      ▼                                                                      │
│  Phase 9: V2 Final Freeze & Release Tag                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Document Status & Next Steps

* **Current Document Status:** `REVIEWED DRAFT`
* **Authority Level:** Authoritative Baseline for V2 Scope & Intent
* **Next Action:** Submit for user review and approval. Upon approval, proceed to **Phase 1: Research & Forensic Audit**.

---

*End of V2_INTENT.md*
