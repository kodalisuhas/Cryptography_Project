# PROJECT CONTEXT RECONSTRUCTION

## 1. Executive Summary

This report provides a complete, evidence-based context reconstruction of the Cryptography Project at the start of a new session. Following a strict forensic analysis of the project repository, architecture, implementation history, and test suite, this document establishes the precise current state. The analysis confirms that the project foundation, Analysis Layer, Padding utilities, and AES Core are successfully implemented, rigorously tested, and officially frozen. The Service, Persistence, and CLI layers remain securely stubbed as planned. This context guarantees zero regressions and readies the project for the next phase: Service Layer Deep Research.

## 2. Project Vision

The project is a **"Cryptography Testing Lab"** designed to empirically evaluate and benchmark cryptographic algorithms (AES, RSA, Blowfish, Classical) across different configurations (key sizes, modes). It prioritizes educational clarity and academic rigor. The goal is to provide measurable performance and security analysis metrics (e.g., encryption time, throughput, avalanche effect) while proving software engineering competency through a modular, layered architecture.

## 3. Working Methodology

The project strictly adheres to a phased, AI-assisted engineering methodology designed to guarantee academic and engineering validity. The workflow enforces absolute discipline:

```text
UNDERSTAND -> EXPLORE -> DEEP RESEARCH -> PROJECT-SPECIFIC SELECTION -> PLAN -> INDEPENDENT REVIEW -> APPROVE -> IMPLEMENT -> REVIEW -> TEST -> FREEZE -> COMMIT -> PUSH
```

No implementation can occur without a prior approved plan, and no plan becomes architecture without a formal review phase.

## 4. Repository Structure

The project directory structure rigorously maps to the layered architecture. Key directories include:

*   `src/`: Contains `core/`, `analyzers/`, `utils/`, `engines/`, and `cli/`.
*   `tests/`: Comprehensive test suites mirroring the `src/` directory.
*   `docs/`: Contains core architecture, methodology, API specifications, implementation plans, and independent review reports.
*   `ai/`: Holds project governance and workflow templates (`CLAUDE.md`, `AI_RULES.md`, `SESSION_TEMPLATE.md`, `REVIEW_CHECKLIST.md`).
*   `results/` and `data/`: Target directories for benchmark inputs and persistence outputs.

## 5. Governance Rules

The project enforces strict governance via `ai/AI_RULES.md` and `ai/CLAUDE.md`:

*   **Absolute Rule:** Implement *only* what is requested; do not modify unrelated modules.
*   **Architectural Compliance:** Strict N-Tier Layered Architecture is mandated. Responsibilities must never overlap between Presentation, Service (Engine), Core, Analysis, Utility, and Persistence layers.
*   **Security Discipline:** Use approved cryptographic libraries (`cryptography`). No hardcoded keys. CSPRNGs (`os.urandom`) must be used.
*   **Review Standard:** Every component must be reviewed against `ai/REVIEW_CHECKLIST.md` for API compliance, architecture, PEP 8, and test coverage before freeze.

## 6. Master Plan / Roadmap

The roadmap execution is meticulously tracked:

*   **COMPLETED:** Project foundation, Architecture design, Methodology definitions, Git workflow setup.
*   **COMPLETED / FROZEN:** Task 1.1 (Padding utility), Task 1.2 (AES Core Engine).
*   **COMPLETED / FROZEN:** Task 2 (Analysis Layer), Task 3.4 (Graph Generator).
*   **PROVISIONAL / NOT STARTED:** Persistence Layer (File I/O).
*   **PROVISIONAL / NOT STARTED:** Service Layer (Cipher Interface, Factory, Context Manager).
*   **PROVISIONAL / NOT STARTED:** Presentation Layer (CLI).
*   **APPROVED / NOT STARTED:** Other Core algorithms (RSA, Blowfish, Classical).

## 7. System Requirements

*   **Functional (Mandatory):** Encrypt/decrypt using AES (128, 192, 256) and modes (ECB, CBC). Benchmark multiple configurations autonomously. Generate comparison graphs.
*   **Performance (Mandatory):** Capture encryption/decryption execution times (ms), throughput (MB/s). Must perform chunking to prevent memory overflow.
*   **Security (Mandatory):** Generate CSPRNG keys and IVs. Execute an empirical Avalanche Effect calculation. Visually demonstrate ECB vulnerabilities (the "ECB Penguin").
*   **Methodology (Mandatory):** Exactly 5 warmup iterations, 30 measurement iterations. Use Tukey fences for outlier flagging (silent removal is forbidden).

## 8. Current Architecture

The established layered architecture defines clear boundaries. Based on physical repository evidence:

*   **Presentation Layer (`src/cli`):** Handles user interactions. (*Currently STUBBED*)
*   **Service Layer (`src/engines`):** Orchestrates logic via Factory and Interface patterns. (*Currently STUBBED*)
*   **Core Layer (`src/core`):** Cryptographic algorithm execution. (*AES IMPLEMENTED; Others STUBBED*)
*   **Analysis Layer (`src/analyzers`):** Performance and security evaluation. (*IMPLEMENTED & FROZEN*)
*   **Utility Layer (`src/utils`):** Helper functions. (*Padding IMPLEMENTED; File Handling STUBBED*)
*   **Persistence Layer:** Orchestrates data storage. (*STUBBED via file_handler.py*)

## 9. Core Layer Reconstruction

The Core layer currently holds the definitive implementation for AES.

| Algorithm | Source Exists | Tests Exist | Implemented | Frozen | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| AES | YES | YES | YES | YES | **FACT - FROZEN** |
| RSA | YES (stub) | YES (stub) | NO | NO | **PROVISIONAL** |
| Blowfish | YES (stub) | YES (stub) | NO | NO | **PROVISIONAL** |
| Classical | YES (stub) | NO | NO | NO | **PROVISIONAL** |

**AES Details (`src/core/aes_cipher.py`):**
Supports 128/192/256-bit keys and ECB/CBC modes. Validates parameters stringently. Employs `os.urandom` for Key and IV generation (IV generation raises `ValueError` for ECB). Padding is natively invoked via `src/utils/padding.py` without duplication. FIPS 197 and SP 800-38A KATs are tested and verified.

## 10. Padding Reconstruction

**Location:** `src/utils/padding.py`
**Contract:** Provides pure Python PKCS#7 implementation supporting block sizes 1-255.
**Status:** **FACT - FROZEN** (Task 1.1).
Exposes `pad()`, `unpad()`, `is_padded()`, and `get_padding_length()`. Integrated successfully into the AES Core module.

## 11. Analysis Layer Reconstruction

The Analysis layer is comprehensively implemented and successfully audited.

*   `performance_timer.py`: Precision timing decorators.
*   `metric_collector.py`: Collects benchmarks, tracks data size, computes Tukey statistics.
*   `security_evaluator.py`: Isolated avalanche effect calculations and ECB weakness reconstruction.
*   `graph_generator.py`: Generates un-persisted Matplotlib visual representations of collected metrics.

**Status:** **FACT - FROZEN**. Confirmed via `docs/reviews/analysis/ANALYSIS_LAYER_FINAL_REVIEW_AND_VERIFICATION.md`.

## 12. Frozen Analysis Methodology

The exact frozen methodology (documented in `ANALYSIS SYSTEM METHODOLOGY DECISION RESOLUTION.md` and `docs/04_Methodology.md`) mandates:

*   **5 Warmup Iterations** (discarded).
*   **30 Measured Iterations** (retained).
*   **Outlier Treatment:** Tukey fences (`Q1/Q3`) calculate outliers for flagging, but outliers are **strictly kept intact** in the raw descriptive pool. No data is silently deleted.
*   **Throughput:** Calculated fundamentally as Binary MB (`1 MB = 1048576 bytes`).

## 13. Persistence Reconstruction

**Location:** `src/utils/file_handler.py`
**Status:** **PROVISIONAL / STUBBED**.
The Persistence Layer is intended to manage File I/O, CSV export, and saving graph figures. Currently, `graph_generator.py` relies on Matplotlib but explicitly refrains from filesystem writing, deferring physical disk serialization to this future layer.

## 14. Utilities Reconstruction

*   `padding.py`: **FACT - FROZEN**. Fully operational PKCS#7.
*   `validators.py`, `formatters.py`, `key_generator.py`: **PROVISIONAL / STUBBED**. Existing as placeholder files pending implementation. Note that `AESCipher` autonomously manages AES Key/IV generation, diminishing the immediate mandate for `key_generator.py`.

## 15. Test Suite Reconstruction

The test suite accurately reflects the repository's partial completion state:

*   **Total Tests:** 226
*   **PASSING:** 226
*   **FAILING:** 0
*   **SKIPPED:** 0
*   **Coverage:** 
    *   `test_aes.py` (123 tests, PASS)
    *   `test_padding.py` (30 tests, PASS)
    *   `test_performance_timer.py` (9 tests, PASS)
    *   `test_metric_collector.py` (14 tests, PASS)
    *   `test_security_evaluator.py` (36 tests, PASS)
    *   `test_graph_generator.py` (14 tests, PASS)

## 16. Implementation History

The implementation sequence followed the roadmap stringently:

1.  **Task 1.1:** PKCS#7 Padding. Explored, Planned, Reviewed, Implemented, Tested, Frozen.
2.  **Task 1.2:** AES Core Engine. Explored, Planned, Spec Corrected, Implemented, Tested, Reviewed, Frozen.
3.  **Task 2/3:** Analysis Layer (`PerformanceTimer`, `MetricCollector`, `SecurityEvaluator`, `GraphGenerator`). Methodology decisions formally resolved, implemented, and fully verified, Frozen.

## 17. Review / Audit History

The project heavily relies on independent, read-only forensic audits prior to component freezing.

*   `TASK_1.1_PADDING_CODE_REVIEW.md`: Verified PKCS#7 behavior and alignment.
*   `TASK_1.2_INDEPENDENT_CODE_REVIEW_REPORT.md`: Validated `AESCipher`, KAT arrays, and API spec compliance.
*   `ANALYSIS_LAYER_FINAL_REVIEW_AND_VERIFICATION.md`: Assessed the 4-module Analysis layer for dependency flow, methodology compliance, API adherence, and immutability. Confirmed fully operational and boundary-compliant.

## 18. Frozen Components

The following components are locked. Any future changes require formal review and re-justification:

*   `src/utils/padding.py`
*   `src/core/aes_cipher.py`
*   `src/analyzers/performance_timer.py`
*   `src/analyzers/metric_collector.py`
*   `src/analyzers/security_evaluator.py`
*   `src/analyzers/graph_generator.py`

## 19. Git / Milestone State

*   **Branch:** `dev`
*   **HEAD:** `050bb77 chore: freeze analysis layer`
*   **Untracked Files:** Numerous exploration and review documents generated dynamically during the Analysis/Task 2-5 phases (`.claude/`, `DECISIONS.md`, `docs/implementation/*`, `docs/research/*`, `docs/reviews/*`).
*   **Working Tree:** Clean of uncommitted tracked changes. No active coding is mid-flight.

## 20. Architecture Consistency Audit

*   **Resolved:** Methodology iteration counts (5/30) and Outlier policies initially contradicted between specs and methodology; resolved successfully via `ANALYSIS SYSTEM METHODOLOGY DECISION RESOLUTION.md`.
*   **Resolved:** API ambiguity regarding padding `block_size` resolved in commit `3fb988e`.
*   **Resolved:** Graph rendering decoupled from persistence. `graph_generator.py` generates in-memory `plt.Figure` objects; `file_handler.py` assumes future responsibility for disk I/O.

## 21. Existing Architectural Decisions

**FACT - DOCUMENTED DECISIONS:**

1.  **AI Workflow:** Adopted via `DECISIONS.md`.
2.  **Exception Hierarchy:** Simplified to `CryptographyError`, `ValidationError`, `FileError`.
3.  **AES Implementation:** `AESCipher` manages its own Key/IV generation internally.
4.  **CSPRNG:** `os.urandom` is strictly required for cryptographic generation.
5.  **Benchmarking:** 5 warmup runs, 30 measured runs. Raw stats must be retained. Outliers are flagged via Tukey Fences, never deleted.
6.  **Padding API:** `is_padded()` is an optional utility; `unpad()` validates autonomously.

## 22. Provisional / Open Decisions

**OPEN/PROVISIONAL CONCEPTS:**

*   **Service Layer Orchestration:** `CipherFactory`, `CipherInterface`, and `ContextManager` exist in documentation and stubs but have not been formally designed or approved for concrete implementation.
*   **Persistence Mechanics:** The exact bridging logic between `FileHandler` and `GraphGenerator` (and CSV exports) requires detailed specification.
*   **CLI Architecture:** The command-line parsing and interactive menu behavior are undefined.
*   **Additional Algorithms:** RSA and Blowfish integration scope requires future task planning.

## 23. Current Project Status

| Area | Status | Evidence |
| :--- | :--- | :--- |
| Project foundation | COMPLETED | `8336ccf2` commit |
| Utilities | IN PROGRESS | `padding.py` (Frozen); others stubbed |
| Padding | FROZEN | `cf21434e` commit; `test_padding.py` passes |
| AES Core | FROZEN | `04fb4fa8` commit; `test_aes.py` passes |
| Other Core algorithms | PROVISIONAL | Stubbed files present |
| Analysis | FROZEN | `050bb77e` commit; 226 total tests passing |
| Persistence | PROVISIONAL | `file_handler.py` stubbed |
| Service | PROVISIONAL | `engines/` stubbed |
| CLI | PROVISIONAL | `cli/` stubbed |
| Integration | NOT STARTED | Dependent on Service/CLI |
| Testing | IN PROGRESS | 226 Integrated Tests passing |

## 24. Verified Current Architecture Diagram

```
CURRENT / VERIFIED Relationships
────────────────────────────────

┌──────────────────────────────────────────────────────────────┐
│                          CORE LAYER                          │
│               [FROZEN] aes_cipher.py (AES)                   │
└──────────────────────────────┬───────────────────────────────┘
                               │ (consumes)
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        UTILITY LAYER                         │
│                 [FROZEN] padding.py (PKCS#7)                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                        ANALYSIS LAYER                        │
│ [FROZEN] performance_timer.py | [FROZEN] metric_collector.py │
│ [FROZEN] security_evaluator.py| [FROZEN] graph_generator.py  │
└──────────────────────────────────────────────────────────────┘

PROPOSED / FUTURE Relationships
───────────────────────────────

┌──────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                      │
│                  [PROVISIONAL] cli/main.py                   │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                         │
│       [PROVISIONAL] cipher_factory.py | cipher_interface.py  │
└──────────────────────────────┬───────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      PERSISTENCE LAYER                       │
│              [PROVISIONAL] utils/file_handler.py             │
└──────────────────────────────────────────────────────────────┘
```

## 25. Important Context for Service Layer Research

To inform the upcoming Service Layer Deep Research, note the following established contracts:

*   **Core APIs:** `AESCipher(key_size, mode)` accepts parameters directly. `encrypt(plaintext, key, iv)` and `decrypt(ciphertext, key, iv)` require keys and IVs to be provided externally by the orchestration layer. The Service Layer is thus responsible for managing Key/IV state.
*   **Padding Ownership:** Managed internally by `AESCipher`. Service layer *must not* attempt to pad inputs manually.
*   **Analysis APIs:** `PerformanceTimer` wraps executions. `MetricCollector` expects structured observation arrays. The Service Layer must orchestrate the pipeline between Core operations and Analysis tracking cleanly.
*   **Exceptions:** `ValueError` is exclusively thrown by Core for validation failures. Service Layer must catch and route these correctly.

## 26. Known Risks / Unresolved Issues

*   **Key State Management:** With `AESCipher` generating keys but relying on the caller to persist them across Encrypt/Decrypt boundaries, the Service Layer design must carefully implement the `ContextManager` to avoid memory leakage or key mismatch errors.
*   **File I/O Memory:** `Constants.MAX_CHUNK_SIZE` exists in documentation but chunked processing is not yet implemented in any layer. The Service or Persistence layer must eventually respect this boundary to prevent Out-Of-Memory (OOM) failures during benchmarking.

## 27. Current Milestone Position

The project is securely positioned between **Milestone 2 (Analysis Engine Complete)** and **Milestone 3 (Service Orchestration & Integration)**.

## 28. Final Context Verdict

============================================================
CRYPTography PROJECT — CONTEXT CONSTRUCTION VERDICT
============================================================

Repository Understanding:
PASS

Project Vision Understanding:
PASS

Requirements Understanding:
PASS

Architecture Understanding:
PASS

Core Understanding:
PASS

Analysis Understanding:
PASS

Persistence Understanding:
PASS

Testing Understanding:
PASS

Implementation History Understanding:
PASS

Review History Understanding:
PASS

Frozen Work Identified:
YES

Existing Decisions Identified:
YES

Contradictions Identified:
YES

Unresolved Questions Identified:
YES

------------------------------------------------------------
CURRENT PROJECT STATE
------------------------------------------------------------

The Cryptography Project has successfully constructed its foundational blocks. The AES Core algorithm and the comprehensive Analysis Layer (Timer, Metrics, Security Evaluation, Graph Generation) are fully implemented, rigorously tested (226 passing tests), and permanently frozen. The Service, Presentation, and Persistence layers are accurately stubbed awaiting the next implementation phase. The project strictly adheres to its documented methodology and architecture.

------------------------------------------------------------
CURRENT MILESTONE
------------------------------------------------------------

Analysis Layer Final Freeze Complete. Ready for Service Layer architectural design.

------------------------------------------------------------
NEXT PLANNED INVESTIGATION
------------------------------------------------------------

SERVICE LAYER DEEP RESEARCH

------------------------------------------------------------
IMPORTANT

No implementation should begin from this report.

The next phase is independent Service Layer research,
followed by project-specific architecture selection,
planning, review, specification, approval, and only then
implementation.

============================================================
END OF CONTEXT CONSTRUCTION
============================================================
