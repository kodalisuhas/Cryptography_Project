# SERVICE LAYER — IMPLEMENTATION PLAN

**STATUS: SERVICE IMPLEMENTATION PLAN COMPLETE — IMPLEMENTATION NOT STARTED**

## 1. Executive Summary
This document provides the formal, project-specific implementation plan for the Cryptography Testing Lab's Service Layer. Following an independent, adversarial architectural review, this plan establishes a thin, strictly stateless Service Layer that orchestrates existing, frozen components without duplicating cryptographic logic or benchmark methodologies. It resolves all open decisions (IV lifecycle, Exception translation, Benchmark return contracts, Parameter passing) and defines explicit APIs, responsibility boundaries, and a detailed testing and implementation sequence.

## 2. Current Repository Verification
*   **Repository inspected:** YES
*   **Current Branch:** `dev` (assumed based on context reports).
*   **Current Service Files:** `src/engines/` contains empty stubs (`cipher_factory.py`, `cipher_interface.py`, `context_manager.py`).
*   **Current Core Files:** `src/core/aes_cipher.py` is fully implemented and validated.
*   **Current Analysis Files:** `performance_timer.py`, `metric_collector.py`, `security_evaluator.py`, `graph_generator.py` are fully implemented and validated.
*   **Existing FileHandler:** `src/utils/file_handler.py` is an empty stub.
*   **Discrepancies:** No discrepancies found. The code accurately reflects the "Frozen Core/Analysis" and "Stubbed Service/Persistence" state.

## 3. Existing Contracts
*   **Existing contracts verified:** YES
*   **Core Contract:** `AESCipher(key_size, mode)` handles its own padding natively and expects explicit `key` and `iv` (for CBC). Raises `ValueError` for bad input.
*   **Analysis Contract:** `PerformanceTimer.measure_time_with_warmup(iterations=30, warmup=5)` inherently executes the loop. `MetricCollector` inherently calculates Tukey fences and throughput without discarding data. `GraphGenerator` yields `plt.Figure` objects.

## 4. Architectural Direction
The Service Layer acts as a **Thin, Stateless Orchestrator**. It will coordinate inputs from the CLI, pass them to Core and Analysis components, and return structured results. It will NOT contain business logic, loops, math, or crypto logic.

## 5. Four Decision Analyses
*   **Four open decisions analyzed:** YES

### DECISION 1 — IV REPRESENTATION
*   **Analysis:** `AESCipher.encrypt` generates random ciphertext. For CBC, a random IV must be generated (either by Core or orchestrated by Service). Since the caller provides the IV to `encrypt`, the Service will call `generate_iv()`. Decryption requires this exact IV. If Service merely returns bytes, the CLI is forced to guess if the bytes contain an IV. 
*   **Recommended Option:** **Option B (Structured Result)**. Service will return a lightweight `EncryptionResult(ciphertext: bytes, iv: bytes)` dataclass. This keeps Core untouched, provides strong typing for the CLI, and delegates serialization (e.g., prepending IV for disk writing) to `FileHandler` or CLI logic.

### DECISION 2 — EXCEPTION MAPPING
*   **Analysis:** `AESCipher` relies entirely on standard `ValueError` for invalid padding, bad keys, or bad modes. If Service lets `ValueError` propagate, the CLI cannot distinguish between a crypto failure and a standard Python type error. The project governance allows `CryptographyError` and `ValidationError`.
*   **Recommended Option:** **Option B (Translate Expected Errors)**. Service will catch `ValueError` specifically raised during Core invocation and wrap/translate it into a `CryptographyError` (for padding/decryption failures) or `ValidationError` (for input constraints) before bubbling to CLI.

### DECISION 3 — BENCHMARK RESULT CONTRACT
*   **Analysis:** `PerformanceTimer` yields a dict of raw times. `MetricCollector` ingests these and can produce a summary dict or Pandas DataFrame. If Service invents a new BenchmarkResult object, it duplicates `MetricCollector`.
*   **Recommended Option:** **Existing MetricCollector Result**. `BenchmarkService.run_performance_suite` will instantiate a `MetricCollector`, populate it via the timer decorators, and return the `MetricCollector` instance. The CLI/Persistence layers can then request DataFrames or Summaries directly from the collector.

### DECISION 4 — PARAMETER PASSING
*   **Analysis:** Option B (`CryptoContext` dataclass) is clean but introduces an unnecessary wrapper for basic orchestration. `AESCipher` is already built for explicit parameters.
*   **Recommended Option:** **Option A (Explicit Parameters)**. Service methods will accept explicit primitives (`algorithm: str, key_size: int, mode: str, key: bytes, iv: bytes`). This guarantees absolute statelessness and avoids creating pseudo-global state objects.

## 6. Final Recommended Decisions
*   **Recommended decisions produced:** YES
1.  **IV Representation:** Structured `EncryptionResult(ciphertext, iv)`.
2.  **Exception Mapping:** Catch `ValueError` from Core -> Translate to `CryptographyError`.
3.  **Benchmark Contract:** Return populated `MetricCollector`.
4.  **Parameter Passing:** Explicit primitive arguments.

## 7. Service API Contracts
*   **Exact API contracts proposed:** YES

**`src/engines/cipher_interface.py`**
*   `SymmetricCipherInterface(abc.ABC)`: Defines `encrypt`, `decrypt`, `generate_key`, `generate_iv`.

**`src/engines/cipher_service.py`**
*   `encrypt_data(cipher, plaintext: bytes, key: bytes, iv: bytes = None) -> EncryptionResult`
*   `decrypt_data(cipher, ciphertext: bytes, key: bytes, iv: bytes = None) -> bytes`

**`src/engines/benchmark_service.py`**
*   `run_performance_suite(cipher_factory_func, config_list, data_payloads, iterations=30, warmup=5) -> MetricCollector`
    *   *Side Effect:* Decorates Core calls. Stores metrics.

**`src/engines/security_service.py`**
*   `run_avalanche_test(cipher, pt1, pt2, key, iv) -> float`
*   `run_ecb_weakness_test(image_bytes, key, iv) -> dict`

## 8. Responsibility Matrix

| Responsibility | CLI | Service | Core | Analysis | Persistence |
| -------------- | --- | ------- | ---- | -------- | ----------- |
| Argument Parsing | **X** | | | | |
| Validation (Input) | **X** | | | | |
| Algorithm Registry | | **X** | | | |
| Key / IV Generation | | | **X** | | |
| Encryption / Decrypt | | | **X** | | |
| Orchestration | | **X** | | | |
| Benchmark Loops | | | | **X** | |
| Statistics (Tukey) | | | | **X** | |
| Security Math | | | | **X** | |
| Graph Construction | | | | **X** | |
| File Writing (Disk) | | | | | **X** |

## 9. Factory / Registry Design
`CipherFactory` will be implemented as a class with a dictionary registry. 
*   **Location:** `src/engines/cipher_factory.py`.
*   **Registration:** Explicit dictionary mapping string names (e.g., `"AES"`) to classes (`AESCipher`).
*   **Method:** `create_cipher(algorithm: str, key_size: int, mode: str) -> SymmetricCipherInterface`.

## 10. Cipher Boundary
The interface will be `SymmetricCipherInterface` to prevent distorting AES to match hypothetical asymmetric RSA requirements. RSA integration is officially deferred to future milestones.

## 11. Key / IV Lifecycle
1.  **CLI** requests encryption. If no key, calls `CipherService.generate_key()`.
2.  **Service** delegates to `Core.generate_key()`.
3.  **Service** delegates `generate_iv()` to Core (if CBC).
4.  **Core** encrypts and returns bytes.
5.  **Service** wraps output in `EncryptionResult(ciphertext, iv)` and returns.
6.  **CLI** temporarily holds key for user session; passes IV and ciphertext to `FileHandler` for persisting.

## 12. Benchmark Orchestration
`BenchmarkService` receives a list of configurations to test. It iterates over the configs, instantiates the cipher via the Factory, applies the `PerformanceTimer.measure_time_with_warmup()` decorator to the cipher's `encrypt` method, runs it, and feeds the resulting `stats_dict` into `MetricCollector.add_metric()`. 

## 13. Security Orchestration
`SecurityService` (or a dedicated method in `BenchmarkService`) simply routes calls to the frozen `SecurityEvaluator.calculate_avalanche_effect()` and `test_ecb_weakness()`. It does not modify inputs or outputs. Pillow is NOT introduced.

## 14. Persistence Boundary
Service does not import `os` or `open`. Service receives the `EncryptionResult`, `MetricCollector`, or `plt.Figure` and returns it to the CLI. The CLI explicitly passes these artifacts to `src/utils/file_handler.py`. 

## 15. File/Data Scope
V1 supports exclusively **in-memory byte arrays**. Chunking, streaming, and large-file memory mapping are completely **OUT OF SCOPE** for this implementation plan.

## 16. Dependency Analysis
*   **New dependencies required:** NONE.
*   **Pillow:** Rejected.
*   **psutil:** Rejected (unless memory profiling becomes a strict future requirement).
*   **cryptography:** Already installed and used by Core.

## 17. File-Level Change Plan
*   **File-level implementation plan produced:** YES

1.  **`src/engines/__init__.py`**: Expose interfaces. (Modify existing stub)
2.  **`src/engines/cipher_interface.py`**: Define `SymmetricCipherInterface`. (Modify existing stub)
3.  **`src/engines/cipher_factory.py`**: Implement registry and `create_cipher`. (Modify existing stub)
4.  **`src/engines/cipher_service.py`**: Implement `EncryptionResult` and `CipherService`. (New file / rename context_manager.py)
5.  **`src/engines/benchmark_service.py`**: Implement performance orchestration. (New file)

## 18. Testing Strategy
*   **Testing plan produced:** YES
*   **`tests/engines/test_cipher_factory.py`**: Test AES instantiation; test unknown algorithm raises error.
*   **`tests/engines/test_cipher_service.py`**: Inject `AESCipher`. Verify `encrypt_data` returns `EncryptionResult`. Verify `ValueError` translation.
*   **`tests/engines/test_benchmark_service.py`**: Mock `PerformanceTimer` and verify `MetricCollector` receives exactly the expected dictionary format.

## 19. Dependency Injection Strategy
Constructor injection is utilized heavily. `CipherService` and `BenchmarkService` will accept `cipher_factory` as an argument during instantiation. This allows tests to inject a `MockCipherFactory` that returns a `MockCipher`, preventing actual cryptographic computation during orchestration tests.

## 20. Implementation Sequence
1.  Define custom Exceptions (`CryptographyError`, `ValidationError`) in `src/utils/exceptions.py` (if not already existing, or use existing definitions).
2.  Implement `SymmetricCipherInterface` and `CipherFactory`.
3.  Write unit tests for Factory.
4.  Implement `CipherService` and `EncryptionResult`.
5.  Write unit tests for `CipherService`.
6.  Implement `BenchmarkService` and link to Analysis.
7.  Write unit tests for `BenchmarkService`.
8.  Verify Integration (Service + Core + Analysis) via integration tests.

## 21. Acceptance Criteria
*   [ ] `SymmetricCipherInterface` defined cleanly.
*   [ ] `CipherFactory` correctly instantiates `AESCipher`.
*   [ ] `CipherService` correctly translates `ValueError` into specific exceptions.
*   [ ] `BenchmarkService` correctly aggregates data into `MetricCollector`.
*   [ ] Service Layer contains 0 manual looping for benchmarks.
*   [ ] Service Layer contains 0 cryptographic generation logic.
*   [ ] 100% test coverage on `src/engines/` logic.

## 22. Risks
*   **Risk:** `ValueError` Translation masks genuine bugs.
    *   **Mitigation:** Only catch `ValueError` directly from the `cipher.encrypt()` call block. Do not use broad `except ValueError:` across the entire method.
*   **Risk:** Memory limits during benchmarking.
    *   **Mitigation:** Explicitly document maximum payload sizes.

## 23. Remaining Open Questions
None. All major architectural decisions have been definitively resolved for V1.

## 24. Change Boundary
*   **Files that will change:** `src/engines/*` and `tests/engines/*`.
*   **Files that MUST remain untouched:**
    *   `src/core/aes_cipher.py`
    *   `src/utils/padding.py`
    *   `src/analyzers/performance_timer.py`
    *   `src/analyzers/metric_collector.py`
    *   `src/analyzers/security_evaluator.py`
    *   `src/analyzers/graph_generator.py`

## 25. Explicit NO-IMPLEMENTATION Status
*   Source modifications made: **NO**
*   Dependencies installed: **NO**
*   Commit created: **NO**
*   Push performed: **NO**

============================================================
STATUS: SERVICE IMPLEMENTATION PLAN COMPLETE — IMPLEMENTATION NOT STARTED
============================================================
