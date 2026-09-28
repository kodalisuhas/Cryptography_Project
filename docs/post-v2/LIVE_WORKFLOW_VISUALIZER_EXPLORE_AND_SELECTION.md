# POST-V2 FEATURE EXPLORATION & SELECTION SPECIFICATION (REVISED)
## LIVE CRYPTOGRAPHY WORKFLOW VISUALIZER (OPTION 8)

**Document ID:** POST-V2-VISUALIZER-SELECT-002 (Replaces SELECT-001)
**Status:** PROPOSED — READY FOR INDEPENDENT SELECTION FREEZE
**Date:** 2026-09-28
**Author:** Antigravity Engineering (Presentation Layer & Systems Architecture)
**Target Milestone:** Live Cryptography Workflow Visualizer Selection Freeze
**Target Integration Point:** V2 Interactive Menu (`src/cli_v2/menu_v2.py`) Option 8; Exit shifts to Option 9
**Implementation Authorization:** **NOT AUTHORIZED** *(Exploration & Selection Phase Only; zero production code modified)*

---

## 1. Executive Summary & Core Architectural Invariants

The Cryptography Testing Lab has successfully built, verified, and frozen:
1. **V1 Core Baseline:** Complete AES implementations (128/192/256 in CBC/ECB), timing decorators, analyzers, and utilities (`v1.0-release`).
2. **V2 Operations Suite:** Single-file operations, batch operations, benchmark suites, security analysis, reporting, and key management (`8449fa1`).
3. **File-Specific Analysis Lab:** Automated microbenchmarking matrix, ciphertext security diffusion analysis, standalone HTML generation (`6ce9fc0`).
4. **V2 Menu Integration & Defect Fixes:** Clean 8-option CLI menu routing and browser dispatch URI resolution (`03fd324`).

The proposed **Live Cryptography Workflow Visualizer** introduces a **strictly decoupled presentation and visualization layer** designed to visually map and demonstrate the actual execution of the frozen cryptographic engines in a modern, browser-based user interface (`http://127.0.0.1:8765`).

### 1.1 Non-Negotiable Invariants & Boundary Rules
1. **Exclusively a Presentation Layer:** The visualizer shall **never** implement, re-implement, or simulate cryptographic logic (NO fake XOR scrambling, NO mock metrics, NO alternate AES algorithms).
2. **No Re-implementation of Frozen Loops:** The visualizer must **not recreate, intercept, or alter frozen timing loops** solely to obtain animation telemetry. If a frozen component does not expose iteration-level events, the visualizer shall display **stage-level progress instead**.
3. **Real Telemetry vs. Presentation Animation:** The UI must strictly distinguish between real backend state transitions and purely decorative animations (e.g. CSS glows or in-flight progress bars). The UI will never claim an animation represents an unobserved internal iteration.
4. **Strict Terminology Discipline:** The visualizer preserves the project's established reporting philosophy. No "ranking", no "#1, #2, #3", and no "Winner/Best" claims. Latency comparisons use descriptive language and the established `"fastest observed in this experiment"` framing.
5. **Zero Additional Dependencies:** Preserves `requirements.txt` immutability. Built entirely with Python standard library `http.server.ThreadingHTTPServer` and self-contained local vanilla HTML5/CSS3/SVG/JavaScript. Zero CDNs, fully air-gapped.
6. **Documentation-Only Metadata:** `explain_data.py` contains static architectural and educational documentation only; it is not a secondary source of cryptographic truth and does not define algorithmic constants.

---

## 2. Telemetry Field Audit: Existing Authoritative Sources vs. Prohibited Metrics

Every piece of data rendered by the visualizer is strictly audited against existing authoritative modules. Any metric not natively produced by the existing codebase is designated **NOT AVAILABLE — DO NOT FABRICATE**.

| Pipeline Domain | Telemetry Field | Authoritative Existing Source | Status / Contract |
| :--- | :--- | :--- | :--- |
| **Single-File** | Input file size & SHA-256 | `FileHandler`, `hashlib.sha256` | Authoritative |
| **Single-File** | Ciphertext size & IV hex | `CipherService.encrypt_data` (`EncryptionResult`) | Authoritative |
| **Single-File** | Wall execution latency (ms) | `time.perf_counter()` boundary matching `MenuV2` | Authoritative |
| **Single-File** | Round-trip verification status | `CipherService.decrypt_data` byte equivalence check | Authoritative |
| **Single-File** | *Ciphertext entropy calculation* | *None in existing single-file engine* | ❌ **NOT AVAILABLE — DO NOT FABRICATE** |
| **Batch** | Discovered files, paths, sizes | `BatchOrchestrator` (`BatchFileResult.source_file`) | Authoritative |
| **Batch** | Per-file processing latency | `BatchFileResult.elapsed_ms` | Authoritative |
| **Batch** | Batch completion status | `BatchFileResult.status` ("SUCCESS", "SKIPPED", "FAILED")| Authoritative |
| **Batch** | Manifest log persistence | `batch_log_*.csv` via `BatchOrchestrator` | Authoritative |
| **Benchmark** | 5 warmups + 30 iterations | `PerformanceTimer.measure_time_with_warmup()` | Authoritative (Stage-Level) |
| **Benchmark** | 30 raw observation timings | `MetricCollector.add_metric` (`raw_times_ms`) | Authoritative (Post-Stage Array) |
| **Benchmark** | Mean, Median, Std Dev, Min, Max | `MetricCollector._summary_data` | Authoritative |
| **Benchmark** | Q1, Q3, IQR, Fences, Outlier Count | `MetricCollector._summary_data` | Authoritative |
| **Benchmark** | Throughput (MB/s) | `MetricCollector._summary_data['throughput_mb_s']` | Authoritative |
| **Security** | Avalanche Effect percentage | `SecurityEvaluator.calculate_avalanche_effect()` | Authoritative |
| **Security** | Key Sensitivity percentage | `SecurityEvaluator.test_key_sensitivity()` | Authoritative |
| **Security** | ECB Weakness analysis dict | `SecurityEvaluator.test_ecb_weakness()` | Authoritative |
| **Security** | *50% Pass/Fail Threshold* | *No threshold defined in SecurityEvaluator* | ❌ **PROHIBITED AS THRESHOLD — Reference Only** |
| **File Lab** | 6 AES configurations | `SUPPORTED_CONFIGURATIONS` in `src.analysis_lab.experiment`| Authoritative |
| **File Lab** | Comparative latencies | `FileAnalysisResult.configurations` | Authoritative |
| **File Lab** | Fastest observed configuration | `FileAnalysisResult.fastest_encryption` / `fastest_decryption`| Authoritative |

---

## 3. Capability Telemetry & Visualization Mapping

### 3.1 Capability 1: Single-File Encryption & Round-Trip Verification
* **Underlying Engines:** `CipherService`, `KeyManager`, `AESCipher`.
* **Telemetry Progression (Stage-Level):**
  1. `STAGE_INPUT`: Preflight inspection (file size, SHA-256).
  2. `STAGE_KEY`: Key selection and IV generation (`os.urandom(16)` for CBC, `None` for ECB).
  3. `STAGE_ENCRYPT`: Real `CipherService.encrypt_data()` execution. Emits real elapsed time, ciphertext size, IV.
  4. `STAGE_VERIFY`: Real `CipherService.decrypt_data()` execution. Emits byte-match confirmation (`PASSED`).
* **UI Representation:** Glowing stages connected by active pulse lines. Final display shows structured card identical in semantics to `MenuV2`.

### 3.2 Capability 2: Standalone Decryption Workflow
* **Underlying Engines:** `CipherService.decrypt_data()`, `PKCS7.unpad()`.
* **Telemetry Progression (Stage-Level):**
  1. `STAGE_INGEST`: Ciphertext byte inspection and sidecar pairing.
  2. `STAGE_DECRYPT`: Real AES decryption execution.
  3. `STAGE_UNPAD`: Verification of valid PKCS#7 padding boundary.
  4. `STAGE_OUTPUT`: Restored plaintext confirmation.

### 3.3 Capability 3: Batch Operations
* **Underlying Engines:** `BatchOrchestrator`.
* **Telemetry Progression:**
  1. `STAGE_PREFLIGHT`: Target directory enumeration and collision planning.
  2. `STAGE_FILE_START`: Emitted per file as `BatchOrchestrator` processes each file sequentially.
  3. `STAGE_FILE_COMPLETE`: Emitted with `source_file`, `status`, `size_bytes`, and `elapsed_ms`.
  4. `STAGE_SUMMARY`: Aggregate statistics (total volume, aggregate throughput MB/s, log CSV path).
* **UI Representation:** Dynamic list of file nodes lighting up as real files complete.

### 3.4 Capability 4: Benchmark Suite
* **Underlying Engines:** `BenchmarkService`, `PerformanceTimer`, `MetricCollector`.
* **Telemetry Progression (Stage-Level):**
  1. `STAGE_CONFIG`: Display selected algorithms, modes, and payload sizes.
  2. `STAGE_WARMUP`: Emits `"Warmup phase active (5 iterations executing in frozen timing loop)..."`.
  3. `STAGE_MEASUREMENT`: Emits `"Measurement phase active (30 iterations executing in frozen timing loop)..."`.
  4. `STAGE_COMPLETE`: Receives `raw_times_ms` (30 floats) and `MetricCollector` summary row.
* **UI Representation:** Clear visual distinction between the in-progress stage and the completed sample distribution. Rendered metrics:
  - 30 raw observation points plotted on a distribution strip.
  - Mean, Median, Std Dev, Min, Max.
  - Tukey Fences ($Q_1$, $Q_3$, Lower Fence, Upper Fence) and highlighted outliers.
  - Throughput (MB/s).

### 3.5 Capability 5: Security & Cryptanalysis
* **Underlying Engines:** `SecurityService`, `SecurityEvaluator`.
* **Telemetry Progression:**
  1. `STAGE_AVALANCHE`: Plaintext 1 vs Plaintext 2 (1-bit mutation). Real `calculate_avalanche_effect()` execution.
     - Telemetry: Real Avalanche percentage (e.g. `49.8%`).
     - Display Text: `"Avalanche Effect: 49.8% | Reference: approximately 50% indicates strong one-bit diffusion."` (No pass/fail claim).
  2. `STAGE_KEY_SENSITIVITY`: Key 1 vs Key 2 (1-bit mutation). Real `test_key_sensitivity()` execution.
     - Telemetry: Real Key Sensitivity percentage.
  3. `STAGE_ECB_WEAKNESS`: Real `test_ecb_weakness()` on 24-bpp BMP payload.
     - Telemetry: Real raw ciphertext buffers for ECB vs CBC comparison.
     - UI: Side-by-side visual demonstration of ECB block structure preservation vs CBC pseudorandom diffusion.

### 3.6 Capability 6: File-Specific Analysis Lab
* **Underlying Engines:** `FileAnalysisRunner`, `PerformanceExperiment`.
* **Telemetry Progression:**
  1. `STAGE_PREFLIGHT`: File validation, streaming SHA-256.
  2. `STAGE_CONFIG_RUN`: Six sequential configuration results (`AES-128/192/256` $\times$ `CBC/ECB`).
     - State per card: `WAITING` $\rightarrow$ `RUNNING` $\rightarrow$ `COMPLETE` (with real mean latency and throughput).
  3. `STAGE_COMPARISON`: Comparative Performance Matrix displaying all 6 configurations.
     - UI Terminology: `"Fastest observed encryption: AES-X-Y (Z.ZZ ms)"`. (Zero ranking or winner terminology).
  4. `STAGE_REPORT`: Saved HTML report path.

### 3.7 "Explain Mode" (Architecture Inspector)
* Interactive panel accessible by clicking any node across all workflow diagrams.
* Backed by `src/visualizer/explain_data.py`:
  - Contains strictly **static documentation strings** referencing authoritative modules.
  - Details: module path, architectural role, cryptographic invariants, timing boundaries (e.g. "PerformanceTimer strictly measures `cipher.encrypt()`, excluding I/O and memory allocation"), and KaTeX mathematical definitions.
  - Explicitly forbidden from defining algorithmic constants or overriding frozen code.

---

## 4. System Architecture & Concurrency Control

```text
run-v2.bat
    │
    ▼
src.cli_v2.main_v2
    │
    ▼
MenuV2.display_main_menu()
    │
    ├── Option 1–7  --> Existing V2 Functionality & Analysis Lab
    │
    ├── Option 8    --> Live Cryptography Workflow Visualizer
    │                        │
    │                        ├── Launches ThreadingHTTPServer (127.0.0.1:8765)
    │                        ├── Opens default browser via webbrowser.open()
    │                        │
    │                        ▼
    │                 Browser Visual UI (HTML5 / CSS3 / SVG / Vanilla JS)
    │                        │
    │                        │ POST /api/run/<mode>
    │                        │ GET  /api/events (SSE)
    │                        ▼
    │           src.visualizer.telemetry_bridge
    │           [Single-Workflow Mutex Lock]
    │                        │
    │     ┌──────────────────┼──────────────────┐
    │     ▼                  ▼                  ▼
    │ CipherService    BenchmarkService   SecurityService
    │ (Single/Batch)     (5+30 Runs)      (Avalanche/Diff)
    │     │                  │                  │
    │     └──────────────────┼──────────────────┘
    │                        ▼
    │                 AES Core Engine
    │              (Frozen V1 Baseline)
    │
    └── Option 9    --> Exit
```

### 4.1 Strict Concurrency Model: Single Active Workflow
To prevent conflicting background executions, resource contention, and confusing demonstrations:
1. `telemetry_bridge` manages a thread-safe mutex (`threading.Lock()`).
2. Only **one active cryptographic workflow** may execute at any given time.
3. If an incoming `POST /api/run/<mode>` request arrives while another workflow is active:
   - Server immediately returns HTTP 409 Conflict: `{"error": "Workflow already in progress", "active_workflow": "<mode>"}`.
   - UI automatically disables execution controls across all modes while a workflow is running.

### 4.2 Server Lifecycle & Threading Model
1. **CLI Main Thread:**
   - Invokes `run_live_workflow_wizard()`.
   - Starts `ThreadingHTTPServer` on a background daemon thread.
   - Attempts `webbrowser.open(server_url)`.
   - Displays clear CLI banner:
     ```text
     ============================================================
               LIVE CRYPTOGRAPHY WORKFLOW SERVER
     ============================================================
       Local Visualizer URL: http://127.0.0.1:8765
       Status: Server running (Single-workflow mode)

       Enter 'q' or press Ctrl+C to stop server and return to menu.
     ============================================================
     ```
   - Enters a clean prompt wait: `raw = input("Visualizer active. Enter 'q' to stop: ").strip().lower()`.
2. **Server Thread (`ThreadingHTTPServer`):**
   - Runs `serve_forever()` as a daemon thread.
   - Handles static file GETs, API POSTs, and SSE streaming connections.
3. **Workflow Worker Thread:**
   - When a workflow is triggered via `POST /api/run/<mode>`, execution occurs on a dedicated worker thread under the mutex lock.
   - Emits SSE events to connected browser client(s).
4. **Clean Shutdown:**
   - Entering `q` or pressing `Ctrl+C` in the CLI (or posting to `/api/shutdown` from browser):
     - Calls `server.shutdown()`.
     - Closes sockets and terminates server thread cleanly.
     - Returns to `MenuV2.display_main_menu()`.

### 4.3 Browser & Server Failure Isolation
1. **Browser Launch Failure:**
   - If `webbrowser.open()` fails (e.g. headless environment or unregistered default browser), the exception is caught silently (`except Exception: pass`).
   - The CLI displays the exact URL (`http://127.0.0.1:8765`) so the user can open it manually.
2. **Port Conflict Recovery:**
   - If default port `8765` is already in use (`OSError: [Errno 98/10048] Address already in use`):
     - Server automatically retries with port `0` (OS-assigned ephemeral port).
     - CLI and browser dispatch automatically use the dynamically assigned port.
3. **Menu Loop Protection:**
   - Server initialization errors (`OSError`, `RuntimeError`) are caught at the menu boundary and routed through `ErrorTranslator.display_error()`.
   - The main menu loop is never crashed.

---

## 5. Package Structure & File Inventory

All visualizer components are isolated in dedicated directories:

```text
src/
└── visualizer/
    ├── __init__.py
    ├── server.py             # ThreadingHTTPServer & REST/SSE RequestHandler
    ├── telemetry_bridge.py   # Mutex-locked adapter invoking real services & yielding SSE
    ├── explain_data.py       # Static architectural documentation for Explain Mode
    └── static/
        ├── index.html        # Single-page UI layout
        ├── visualizer.css    # Cyber/terminal theme, glowing nodes, animations
        └── visualizer.js     # SSE listener, SVG connection renderer, Explain modal
tests/
└── visualizer/
    ├── __init__.py
    ├── test_server.py        # HTTP routing, SSE delivery, port conflict, shutdown
    ├── test_telemetry.py     # Real service invocation, event schema, mutex lock
    └── test_menu_routing.py  # MenuV2 Option 8 dispatch, cancellation, and error handling
```

---

## 6. Menu Integration Specification

The V2 main menu (`src/cli_v2/menu_v2.py`) will expand to 9 options:

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
  7. File-Specific Encryption Analysis
  8. Live Cryptography Workflow
  9. Exit
============================================================
Select an option [1-9]:
```

* **Option 8:** Routes to `self.run_live_workflow_wizard()`.
* **Option 9:** Exit (universal exit tokens: `9`, `exit`, `quit`, `q`, `c`, `cancel`).
* **Prompt:** Updated from `[1-8]` to `[1-9]`.
* **Menu Adapter Boundary:** Catches `KeyboardInterrupt` and `(OSError, ValueError, RuntimeError)`; programming bugs (`TypeError`, `AttributeError`) propagate unmasked.

---

## 7. Governance Checkpoints & Next Steps

1. **Current State:** REVISED SELECTION SPECIFICATION (`POST-V2-VISUALIZER-SELECT-002`).
2. **Authorization Status:** **NO PRODUCTION CODE MODIFICATIONS AUTHORIZED.**
3. **Approval Gate:** Independent Review of `POST-V2-VISUALIZER-SELECT-002`.
4. **Subsequent Roadmap (upon Selection Freeze):**
   - Step 1: Draft Implementation Plan (`POST-V2-VISUALIZER-PLAN-001`).
   - Step 2: Independent Plan Review & Plan Freeze.
   - Step 3: Implementation Authorization.
   - Step 4: Staged Implementation & Unit/Integration Verification.
   - Step 5: Full Regression Testing (973+ tests).
   - Step 6: Final Closure & Two-Commit Staging/Push Strategy.
