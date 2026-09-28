# POST-V2 FEATURE IMPLEMENTATION PLAN: LIVE CRYPTOGRAPHY WORKFLOW VISUALIZER (REVISED)

**Document ID:** POST-V2-VISUALIZER-PLAN-002 (Replaces PLAN-001)
**Status:** PROPOSED — READY FOR INDEPENDENT PLAN AUDIT & FREEZE
**Date:** 2026-09-28
**Author:** Antigravity Engineering (Presentation Layer & Systems Architecture)
**Target Milestone:** Implementation Plan Freeze
**Target Integration Point:** `src/cli_v2/menu_v2.py` Option 8 (`run-v2.bat` compatible; Exit shifts to Option 9)
**Frozen Upstream Base:** `03fd324` (Main branch; V1/V2/Analysis Lab frozen)
**Implementation Authorization:** **NOT AUTHORIZED** *(Planning Phase Only; zero production code modified)*

---

## 1. Executive Summary & Non-Negotiable Invariants

This plan operationalizes the approved `POST-V2-VISUALIZER-SELECT-002` selection specification into an exact, audited, and testable technical architecture.

### Non-Negotiable Engineering Invariants
1. **Exclusively Presentation & Telemetry (No Workflow Re-implementation):** `TelemetryBridge` delegates directly to existing authoritative headless services and runners (`CipherService`, `BatchOrchestrator`, `BenchmarkService`, `SecurityService`, `FileAnalysisRunner`). It must **not** recreate an existing V2 workflow's orchestration, validation, batch loops, key generation strategies, or business logic merely for visualization.
2. **Zero Modification or Re-implementation of Frozen Loops:** Frozen timing loops (`PerformanceTimer.measure_time_with_warmup()`) shall execute uninterrupted. Telemetry is emitted at **stage boundaries**; the visualizer shall never intercept or loop internally to manufacture simulated tick events.
3. **Public API Contract Discipline:** All telemetry data is extracted exclusively via **public methods and attributes** of existing modules. For example, `MetricCollector` data is retrieved via `get_summary_dataframe()` and `get_raw_dataframe()`; private attributes (`_summary_data`, `_raw_data`) are never accessed.
4. **Authoritative Input Generation Conventions:** Workflows requiring synthetic inputs (e.g. Security diffusion 1-bit mutations) strictly reuse existing V2 conventions (`p1`, `p2 = p1 ^ 0x01`, `k1`, `k2 = k1 ^ 0x01`, 24-bpp minimal BMP, fixed IV). No new mutation or payload generators are introduced.
5. **Real Execution Events vs. Presentation Animation:** Real backend state transitions (`STAGE_FILE_COMPLETE`, real latencies, real byte counts) are strictly distinguished in schema and UI from purely aesthetic CSS/SVG animations (glows, pulse lines, loading spinners).
6. **Strict Terminology Discipline:** No "ranking", `#1/#2/#3`, or "Winner/Best" labels. Comparative latencies use descriptive language and the established `"fastest observed in this experiment"` framing.
7. **Zero Additional Dependencies:** 100% Python standard library (`http.server`, `threading`, `queue`, `json`, `webbrowser`, `errno`). Preserves `requirements.txt` immutability.
8. **Air-Gapped & Offline:** Local static assets only (`index.html`, `visualizer.css`, `visualizer.js`). Zero external CDN scripts, stylesheets, or web fonts.
9. **Strict Concurrency & Safe Shutdown:** Single-workflow mutex (`threading.Lock()`). Any concurrent trigger receives HTTP 409 Conflict. Shutdown stops the HTTP server from accepting new requests without aborting an in-flight cryptographic operation.
10. **Explain Mode as Documentation:** `explain_data.py` contains static architectural documentation only; it defines no algorithmic constants or contracts.

---

## 2. Authoritative Backend Service API Contracts

Before any implementation, every backend service entrypoint is audited and locked down:

| Capability | Authoritative Class / Entrypoint | Signature & Visibility | Return Type | Telemetry Extraction Method |
| :--- | :--- | :--- | :--- | :--- |
| **Single Encrypt** | `CipherService.encrypt_data` | `(algorithm, key_size, mode, plaintext, key, iv=None)` [Public] | `EncryptionResult(ciphertext: bytes, iv: bytes \| None)` | Measure wall time around call via `time.perf_counter()` (matching `MenuV2`). Read `res.ciphertext`, `res.iv`. |
| **Single Decrypt** | `CipherService.decrypt_data` | `(algorithm, key_size, mode, ciphertext, key, iv)` [Public] | `bytes` | Measure wall time around call. Verify `decrypted == plaintext`. |
| **Batch Encrypt** | `BatchOrchestrator.run_batch_encrypt` | `(source_dir, dest_dir, algorithm="AES", key_size=256, mode="CBC", shared_key=None, on_conflict="skip", dry_run=False, progress_callback=None)` [Public] | `BatchSummary` | Pass `progress_callback(current, total, filename)` to emit per-file progress events. Read `BatchSummary.results` and aggregate statistics. |
| **Benchmark** | `BenchmarkService.run_performance_suite` | `(configs: list[dict], data_payloads: list[bytes])` [Public] | `MetricCollector` | Call `collector.get_summary_dataframe()` and `collector.get_raw_dataframe()` [Public APIs]. Extract 30 raw observation timings and Tukey metrics. |
| **Security** | `SecurityService.run_security_suite` | `(configs, plaintext1, plaintext2, key1, key2, image_bytes, iv)` [Public] | `dict[str, dict]` | Direct consumption of returned dict: `avalanche_effect` (float), `key_sensitivity` (float), `ecb_weakness` (dict). |
| **File Lab** | `FileAnalysisRunner.run` | `()` [Public] on `FileAnalysisRunner(file_path, no_open=True)` | `tuple[FileAnalysisResult \| None, Path \| None, int]` | Consume `result.configurations`, `result.fastest_encryption_config`, and `result.fastest_decryption_config`. |

---

## 3. Server Architecture & Endpoints (`src/visualizer/server.py`)

### 3.1 Class `VisualizerServer`
- Wraps `http.server.ThreadingHTTPServer(('127.0.0.1', port), VisualizerRequestHandler)`.
- **Targeted Port Fallback:**
  ```python
  import errno
  WSAEADDRINUSE = 10048

  try:
      self.httpd = ThreadingHTTPServer(('127.0.0.1', default_port), VisualizerRequestHandler)
  except OSError as exc:
      is_addr_in_use = (
          exc.errno == errno.EADDRINUSE
          or getattr(exc, "winerror", None) == WSAEADDRINUSE
          or exc.errno == WSAEADDRINUSE
      )
      if is_addr_in_use:
          # Targeted fallback to OS-assigned ephemeral port
          self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), VisualizerRequestHandler)
      else:
          # Unrelated socket error propagates to menu error handler
          raise
  ```
- **Properties:**
  - `port: int` (actual bound port from `self.httpd.server_port`).
  - `server_url: str` (`f"http://127.0.0.1:{self.port}"`).
- **Lifecycle Methods:**
  - `start() -> None`: Starts daemon thread executing `self.httpd.serve_forever()`.
  - `shutdown() -> None`: Invokes `self.httpd.shutdown()`, closes sockets, and joins thread.

### 3.2 Request Handler Routing Table
Implements clean HTTP dispatch via `VisualizerRequestHandler(http.server.BaseHTTPRequestHandler)`:

| Method | Route | Description | Response Content |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves `static/index.html` | `text/html; charset=utf-8` |
| `GET` | `/visualizer.css` | Serves `static/visualizer.css` | `text/css; charset=utf-8` |
| `GET` | `/visualizer.js` | Serves `static/visualizer.js` | `application/javascript; charset=utf-8` |
| `GET` | `/api/status` | Returns server & workflow state | `application/json` (`{"status": "idle"\|"running", "active_workflow": null\|str, "port": int}`) |
| `GET` | `/api/explain` | Returns all node explain docs | `application/json` (dictionary of node documentation from `explain_data.py`) |
| `POST`| `/api/run/<mode>` | Triggers a workflow execution | If idle: HTTP 202 `{"status": "started", "workflow": mode}`<br>If busy: HTTP 409 `{"error": "Workflow already in progress", "active_workflow": ...}` |
| `GET` | `/api/events` | Server-Sent Events (SSE) stream | `text/event-stream; charset=utf-8` |
| `POST`| `/api/shutdown` | Initiates graceful server stop | HTTP 200 `{"status": "shutting_down"}` |

### 3.3 Safe Server Shutdown Semantics
- When `/api/shutdown` is called or CLI enters `q` / Ctrl+C:
  1. `self.httpd.shutdown()` is called. This stops the server from accepting new HTTP connections or SSE subscribers.
  2. Any in-flight cryptographic workflow executing on the worker thread is **allowed to complete normally**. It will release the mutex and exit naturally.
  3. No abort or interrupt signals are injected into running crypto/timing operations.

---

## 4. Telemetry Bridge & Service Delegation (`src/visualizer/telemetry_bridge.py`)

### 4.1 Concurrency & Mutex Model
- Single-workflow mutex: `self._lock = threading.Lock()`.
- Active workflow indicator: `self._active_workflow: str | None = None`.
- Subscriber queues: `self._subscribers: list[queue.Queue]`.
- Trigger flow:
  ```python
  def run_workflow_async(self, mode: str, params: dict | None = None) -> bool:
      if not self._lock.acquire(blocking=False):
          return False  # Triggers HTTP 409 Conflict
      self._active_workflow = mode
      worker = threading.Thread(target=self._execute_wrapper, args=(mode, params), daemon=True)
      worker.start()
      return True
  ```

### 4.2 Exact Delegation by Capability

#### A. Single-File Workflow (`mode="single"`)
- **Parameter Support:** User selects parameters via UI/REST (or defaults):
  - `algorithm`: `"AES"`
  - `key_size`: `128`, `192`, or `256` (default: `256`)
  - `mode`: `"CBC"` or `"ECB"` (default: `"CBC"`)
  - `plaintext`: User string or default demonstration payload
- **Execution:**
  1. `emit("single", "STAGE_INPUT", "ACTIVE", {"size_bytes": len(plaintext), "sha256": sha256_hex})`
  2. Key & IV Generation using frozen `CipherFactory` / `os.urandom(16)`:
     - `emit("single", "STAGE_KEY", "ACTIVE", {"key_size": key_size, "mode": cipher_mode, "iv_hex": iv.hex() if iv else "None (ECB)"})`
  3. Wall-Clock Timed Encryption (matching `MenuV2` convention):
     ```python
     t0 = time.perf_counter()
     res = cipher_service.encrypt_data(algorithm, key_size, cipher_mode, plaintext, key, iv)
     elapsed_ms = (time.perf_counter() - t0) * 1000.0
     ```
  4. `emit("single", "STAGE_ENCRYPT", "COMPLETE", {"elapsed_ms": elapsed_ms, "ciphertext_size": len(res.ciphertext), "iv_hex": res.iv.hex() if res.iv else None})`
  5. Round-Trip Verification:
     ```python
     decrypted = cipher_service.decrypt_data(algorithm, key_size, cipher_mode, res.ciphertext, key, res.iv)
     verified = (decrypted == plaintext)
     ```
  6. `emit("single", "STAGE_VERIFY", "COMPLETE", {"verified": verified, "status": "MATCH_VERIFIED"})`
  7. `emit("single", "STAGE_COMPLETE", "COMPLETE", summary_data)`

#### B. Standalone Decryption Workflow (`mode="decrypt"`)
1. Ingests ciphertext and sidecar IV (if CBC).
2. Calls `cipher_service.decrypt_data(algorithm, key_size, cipher_mode, ciphertext, key, iv)`.
3. Measures wall-clock latency, verifies valid byte output, and emits `STAGE_COMPLETE`.

#### C. Batch Workflow (`mode="batch"`)
1. Uses a designated sandbox directory containing sample test files.
2. Directly delegates to `BatchOrchestrator.run_batch_encrypt()` with a progress callback:
   ```python
   def _on_progress(current: int, total: int, filename: str) -> None:
       self.emit("batch", "STAGE_FILE_PROGRESS", "ACTIVE", {
           "current": current, "total": total, "filename": filename
       })

   summary: BatchSummary = batch_orchestrator.run_batch_encrypt(
       source_dir=sample_dir,
       dest_dir=out_dir,
       progress_callback=_on_progress,
   )
   ```
3. Extracts real outcomes from `summary.results` (`BatchFileResult.elapsed_ms`, `status`) and emits `STAGE_COMPLETE`.

#### D. Benchmark Suite Workflow (`mode="benchmark"`)
1. Emits `STAGE_CONFIG`.
2. Emits `STAGE_WARMUP` with notification: `"Executing 5 warmup cycles in frozen timing loop..."`.
3. Calls frozen `BenchmarkService.run_performance_suite(configs, [payload])`.
4. Extracts metrics strictly via public APIs:
   ```python
   summary_df = collector.get_summary_dataframe()
   raw_df = collector.get_raw_dataframe()
   summary = summary_df.iloc[0].to_dict()
   raw_times = raw_df['elapsed_time_ms'].tolist()  # Exactly 30 floats
   ```
5. Emits `STAGE_COMPLETE` with `raw_times_ms`, `mean_time_ms`, `median_time_ms`, `std_dev_time_ms`, `min_time_ms`, `max_time_ms`, `q1_ms`, `q3_ms`, `iqr_ms`, `outlier_count`, and `throughput_mb_s`.

#### E. Security Suite Workflow (`mode="security"`)
1. Constructs standard inputs matching `src/cli_v2/menu_v2.py:1326-1338`:
   ```python
   p1 = b"CryptographyTestingLabV2KeySafe!"[:16]
   p2 = bytearray(p1); p2[0] ^= 0x01; plaintext2 = bytes(p2)
   k1 = b"\x01\x23\x45\x67\x89\xab\xcd\xef\xfe\xdc\xba\x98\x76\x54\x32\x10\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff"
   k2 = bytearray(k1); k2[0] ^= 0x01; key2 = bytes(k2)
   iv = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0\x0f\xed\xcb\xa9\x87\x65\x43\x21"
   image_bytes = _create_minimal_bmp(16, 16)
   ```
2. Calls `SecurityService.run_security_suite(configs, p1, plaintext2, k1, key2, image_bytes, iv)`.
3. Emits `STAGE_AVALANCHE`, `STAGE_KEY_SENSITIVITY`, and `STAGE_ECB_WEAKNESS` from returned dictionary:
   - Avalanche: `results["AES-256-CBC"]["avalanche_effect"]`
   - Key Sensitivity: `results["AES-256-CBC"]["key_sensitivity"]`
   - Note: Descriptive reference only (`"Approximately 50% indicates strong one-bit diffusion"`); zero pass/fail threshold claims.

#### F. File-Specific Lab Workflow (`mode="file_lab"`)
1. Instantiates `FileAnalysisRunner(file_path=sample_file, no_open=True)`.
2. Calls `runner.run()`, returning `(result, report_path, exit_code)`.
3. Emits `STAGE_COMPLETE` with configuration comparative matrix and `"fastest observed"` configurations.

---

## 5. Explain Mode Specification (`src/visualizer/explain_data.py`)

Static documentation dictionary mapping node identifiers to architectural and educational context:

```python
EXPLAIN_NODES = {
    "node_aes_cipher": {
        "title": "AES Core Engine",
        "module": "src.core.aes.AESCipher",
        "role": "Low-level cryptographic primitive implementing NIST FIPS 197 standard.",
        "invariants": [
            "Fixed block size of strictly 16 bytes (128 bits).",
            "Supported key lengths: 128, 192, and 256 bits.",
            "CBC mode requires a cryptographically secure 16-byte random IV.",
            "ECB mode forbids IV usage and operates on independent 16-byte blocks."
        ],
        "timing_boundary": "PerformanceTimer strictly isolates the core encrypt/decrypt method, excluding I/O and key expansion.",
        "formula": None,
        "freeze_reference": "Frozen in V1.0 release (commit 8449fa1 / 6ce9fc0)."
    },
    "node_metric_collector": {
        "title": "MetricCollector & Statistical Engine",
        "module": "src.analyzers.metric_collector.MetricCollector",
        "role": "Synthesizes raw microbenchmark observations into robust statistical aggregates.",
        "invariants": [
            "Sample size must equal exactly 30 observations.",
            "Warmup iterations (5 loops) are strictly excluded from statistical calculation.",
            "Sample variance uses Bessel's correction (ddof=1)."
        ],
        "timing_boundary": "Operates strictly post-execution on in-memory float arrays.",
        "formula": "IQR = Q3 - Q1; Lower Fence = Q1 - 1.5*IQR; Upper Fence = Q3 + 1.5*IQR",
        "freeze_reference": "Frozen in V1.0 release."
    },
    "node_avalanche": {
        "title": "Avalanche Effect Evaluator",
        "module": "src.analyzers.security_evaluator.SecurityEvaluator",
        "role": "Measures bit diffusion across ciphertexts when exactly 1 bit of plaintext is mutated.",
        "invariants": [
            "Requires exactly 1 bit difference between Plaintext 1 and Plaintext 2.",
            "Plaintext lengths must be strictly identical.",
            "Uses bitwise Hamming Distance over all ciphertext bits."
        ],
        "timing_boundary": "Security evaluation metric; not timing-benchmarked.",
        "formula": "Avalanche (%) = (HammingDistance(C1, C2) / (TotalBytes * 8)) * 100",
        "freeze_reference": "Frozen in V1.0 release."
    },
    # Additional nodes: node_key_manager, node_pkcs7, node_batch_orchestrator, node_file_lab
}
```

---

## 6. Frontend Specification (`static/`)

### 6.1 Layout & Visual Hierarchy (`index.html`)
- **Header:**
  - Branding: `CRYPTOGRAPHY TESTING LAB — LIVE WORKFLOW`
  - Connection indicator: `● CONNECTED (127.0.0.1:8765)` / `● EXECUTING` / `○ OFFLINE`
  - Mode Tabs: `Single File`, `Decrypt`, `Batch`, `Benchmark`, `Security`, `File Lab`
  - Toolbar: `[Explain Mode: ON/OFF]`, `[Shutdown & Return]`
- **Interactive Pipeline Canvas:**
  - Dynamic SVG / Flexbox pipeline showing stage nodes for the active mode.
  - Active nodes glow in neon cyan (`#00f0ff`); completed nodes turn emerald (`#00ff88`).
  - Animated pulse lines connecting nodes during active processing.
  - Clicking any node opens the Explain Mode Drawer.
- **Controls & Telemetry Dashboard:**
  - Parameter controls (Algorithm, Key size, Mode, Payload size).
  - Primary Action Button: `Run Workflow` (disabled with spinner while active).
  - Telemetry Cards: Real-time readouts of latency (ms), throughput (MB/s), IV hex, verification status.
  - Benchmark View: 30-observation distribution strip with mean marker, Tukey fences, and outlier dots.
  - Security View: Bitwise mutation comparison and Avalanche gauge ($\approx 50\%$ reference).
  - File Lab View: 6-card comparative status matrix.
- **Explain Mode Slide-Out Drawer:**
  - Sliding sidebar on right edge showing title, module path, role, invariants, timing boundaries, and formulas.

### 6.2 CSS Design Language (`visualizer.css`)
- **Colors:** Deep obsidian `#0a0c10`, panel surface `#12161f`, borders `#21262d`. Accents: Cyan `#00f0ff`, Magenta `#ff007f`, Emerald `#00ff88`, Amber `#ffb800`.
- **Typography:** System monospaced stack (`Consolas, 'Cascadia Code', 'Courier New', monospace`).
- **Strict Distinction:** Classes `.state-event` (real data changes) vs `.anim-pulse` (presentation motion).

### 6.3 Client Logic (`visualizer.js`)
- Vanilla ES6+.
- `EventSource('/api/events')` connection with auto-reconnect.
- Node state updater based on incoming SSE JSON.
- Modal / Drawer interaction for Explain Mode.
- Fetch calls to `POST /api/run/<mode>`. Handles HTTP 409 by displaying warning toast.

---

## 7. V2 Menu Integration Specification (`src/cli_v2/menu_v2.py`)

### 7.1 Menu Structure Update (9 Options)

```python
# In src/cli_v2/menu_v2.py:
print("============================================================")
print("              CRYPTOGRAPHY TESTING LAB — V2")
print("============================================================")
print("  1. Single-File Operations (Encrypt, Decrypt, Verify)")
print("  2. Batch Operations (Folder Encrypt, Folder Decrypt)")
print("  3. Benchmark & Performance Suite")
print("  4. Security & Cryptanalysis Lab")
print("  5. View & Generate HTML Reports")
print("  6. Help & Documentation")
print("  7. File-Specific Encryption Analysis")
print("  8. Live Cryptography Workflow")
print("  9. Exit")
print("============================================================")
```

- Input prompt: `raw = input("Select an option [1-9]: ").strip()`
- Exit tokens: `token in ("9", "exit", "quit", "q", "c", "cancel")`
- Routing:
  - `raw == "7"` $\rightarrow$ `self.run_file_analysis_wizard()`
  - `raw == "8"` $\rightarrow$ `self.run_live_workflow_wizard()`
  - `raw == "9"` $\rightarrow$ Exit message & return

### 7.2 Method `run_live_workflow_wizard()`
```python
def run_live_workflow_wizard(self) -> None:
    """Launch the Live Cryptography Workflow Visualizer local server and browser."""
    print("\n--- Live Cryptography Workflow Visualizer ---")
    try:
        from src.visualizer.server import VisualizerServer
        server = VisualizerServer()
        server.start()

        url = server.server_url
        print(f"\n[*] Visualizer server active at: {url}")
        print("[*] Launching web browser interface...")

        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass

        print("\n============================================================")
        print(f"  Live Visualizer running at {url}")
        print("  Press Enter or enter 'q' to stop server and return to menu.")
        print("============================================================")

        try:
            input("\nEnter 'q' to return: ")
        except (EOFError, KeyboardInterrupt):
            pass
        finally:
            print("[*] Stopping visualizer server...")
            server.shutdown()
            print("[✓] Visualizer stopped cleanly.")

    except KeyboardInterrupt:
        print("\n[!] Operation cancelled by user.")
    except (OSError, ValueError, RuntimeError) as exc:
        ErrorTranslator.display_error(exc, context="Live Workflow Visualizer", verbose=self._verbose)
```

---

## 8. Verification & Testing Strategy

### 8.1 Unit & Integration Test Suites (`tests/visualizer/`)
1. **`test_server.py`:**
   - Static asset serving (`/`, `/visualizer.css`, `/visualizer.js`) returns 200 with correct MIME types.
   - `/api/status` returns idle state and port number.
   - `/api/explain` returns valid dictionary matching `EXPLAIN_NODES`.
   - Targeted port conflict recovery: `errno.EADDRINUSE` causes automatic fallback to port 0; unrelated `OSError` propagates.
   - Safe shutdown: `/api/shutdown` stops accepting requests while allowing in-flight worker to finish.
2. **`test_telemetry.py`:**
   - SSE client subscription: events emitted via `bridge.emit()` are received by subscriber queue.
   - Mutex concurrency: Triggering workflow while active immediately returns HTTP 409 Conflict.
   - Execution validation across all 6 modes:
     - Single Encrypt: Emits real latency, ciphertext size, IV, and verified=True without altering `CipherService`.
     - Single Decrypt: Emits real elapsed time and plaintext size.
     - Batch: Invokes `BatchOrchestrator.run_batch_encrypt` and emits per-file progress events with real elapsed times.
     - Benchmark: Emits stage-level events (`STAGE_WARMUP`, `STAGE_COMPLETE`) with exactly 30 raw observation timings and Tukey metrics via public `get_summary_dataframe()` and `get_raw_dataframe()`.
     - Security: Uses standard V2 1-bit mutation inputs; emits real Avalanche % and Key Sensitivity % without pass/fail assertions.
     - File Lab: Invokes `FileAnalysisRunner.run()`; emits configuration results with `"fastest observed"` semantics.
3. **`test_menu_routing.py`:**
   - `test_main_menu_exit_options`: Verifies `9`, `exit`, `quit`, `q`, `c`, `cancel` cleanly exit.
   - `test_main_menu_routes_to_live_visualizer`: Selecting `8` invokes `run_live_workflow_wizard()`.
   - `test_run_live_workflow_wizard_lifecycle`: Verifies server start, browser launch, input wait, and server shutdown.
   - `test_run_live_workflow_wizard_error_handling`: Verifies `OSError` routes through `ErrorTranslator.display_error()`.
   - `test_programming_defect_propagates`: Verifies `TypeError` propagates unmasked.

### 8.2 Full Repository Regression Gate
- Run `python -m pytest tests/visualizer/ -v` (100% green).
- Run `python -m pytest tests/cli_v2/test_menu_v2.py -v` (100% green).
- Run full repository suite `python -m pytest`: **0 failed, all relevant tests passing, no regressions**.
- Code hygiene: `git diff --check` with zero whitespace errors.
- Scope audit: Only `src/visualizer/`, `tests/visualizer/`, `src/cli_v2/menu_v2.py`, and `tests/cli_v2/test_menu_v2.py` modified.

---

## 9. Governance Checkpoints & Approval Request

```text
SELECTION FREEZE (Approved)
       ↓
IMPLEMENTATION PLAN (POST-V2-VISUALIZER-PLAN-002)  <-- CURRENT STAGE
       ↓
INDEPENDENT PLAN AUDIT & FREEZE
       ↓
IMPLEMENTATION AUTHORIZATION
       ↓
STAGED IMPLEMENTATION & TEST SUITE
       ↓
FULL REGRESSION & CLOSURE
```

**Implementation Authorization Status:** **NOT AUTHORIZED.**
No production source code has been modified or created during this planning step.
