# SERVICE LAYER — IMPLEMENTATION PLAN REVIEWED & CORRECTED

**STATUS: SERVICE IMPLEMENTATION PLAN CORRECTED — IMPLEMENTATION NOT STARTED**

## 1. Executive Summary
This document is the independently corrected and rigorously verified Implementation Plan for the Cryptography Testing Lab's Service Layer. It acts as a formal architectural gate before specification and implementation. This review identifies contradictions in the previous plan, corrects API contracts against the frozen Core/Analysis repositories, removes unsupported claims, and strictly defines a thin, stateless orchestration layer.

## 2. Repository Verification
*   **Repository inspected:** YES
*   **Actual Core contracts verified:** YES (`src/core/aes_cipher.py` checked).
*   **Actual Analysis contracts verified:** YES (`performance_timer.py`, `metric_collector.py`, `security_evaluator.py`, `graph_generator.py` checked).
*   **Actual Service state verified:** YES (Only empty stubs exist in `src/engines/`).
*   **Actual exception system verified:** YES (`src/utils/exceptions.py` does NOT exist yet. Project governance mentions `CryptographyError` and `ValidationError`, but they must be formally introduced).

## 3. Findings & Correction Classification

| Issue | Evidence | Impact | Classification | Correction |
| :--- | :--- | :--- | :--- | :--- |
| **1. IV Contract** | `AESCipher.encrypt` requires `iv=None` for ECB. | Data types mismatch. | **CRITICAL** | `EncryptionResult` must define `iv: bytes \| None`. |
| **2. Exception Mapping** | `AESCipher` exposes only broad `ValueError`. | String matching is forbidden. | **CRITICAL** | Service must propagate `ValueError` unchanged. Artificial translation without string matching is unsafe. |
| **3. API/Factory Ambiguity** | Plan had mixed explicit params and injected cipher instances. | Architectural confusion. | **MAJOR** | CLI passes primitive strings -> Service -> Service uses Factory -> Core. Service API expects primitives. |
| **4. Benchmark Loop Exposer** | Plan proposed passing `iterations/warmup` via Service API. | Violates frozen 5/30 methodology. | **CRITICAL** | Remove `iterations` and `warmup` from Service API. Delegate entirely to `PerformanceTimer` defaults. |
| **5. File Brokerage** | Plan made Service the broker to `FileHandler`. | Mixes IO with Crypto orchestration. | **MAJOR** | CLI coordinates Service and `FileHandler`. Service returns results to CLI. |
| **6. Arbitrary Limits** | Plan warned of "documenting max payload size". | No such limit exists in V1. | **MINOR** | Removed. V1 uses in-memory payloads. |
| **7. SecurityService** | Mentioned in API but not file plan. | Inconsistent file changes. | **MAJOR** | Formalize `SecurityService` class uniformly across the plan. |

## 4. Corrected Architecture & Decision Boundaries

### Corrected IV Contract (Decision 1)
*   **Finding:** AES requires IV for CBC, but forbids it for ECB.
*   **Decision:** The Service layer will return a structured `EncryptionResult` dataclass.
*   **Contract:** 
    ```python
    @dataclass(frozen=True)
    class EncryptionResult:
        ciphertext: bytes
        iv: bytes | None
    ```
*   **Lifecycle:** CLI requests encryption. Service calls `Core.generate_iv()` if mode is CBC. Core encrypts. Service packages `(ciphertext, iv)` and returns to CLI. CLI hands off to `FileHandler` for persisting.

### Corrected Exception Contract (Decision 2)
*   **Finding:** Core (`AESCipher` and `Padding`) exclusively uses standard `ValueError` (and occasionally `TypeError`) for all validation and cryptographic failures (e.g., bad key, bad mode, invalid padding). Because they all share the same exception class, the Service Layer cannot safely distinguish between a crypto failure and a validation failure without resorting to fragile string-matching on the error message.
*   **Decision:** **Option A — Propagate ValueError**. The Service Layer will NOT catch and artificially translate `ValueError` into `CryptographyError` or `ValidationError`. The public error contract of the Core layer (`ValueError`) will safely propagate to the CLI.
*   **Contract:** Service methods will allow `ValueError` and `TypeError` to propagate natively. We will NOT implement `exceptions.py` or new exception hierarchies in this milestone, as the repository provides no stable mechanism to classify them.

### Corrected Factory / Service Boundary (Decision 3)
*   **Decision:** Model A. The CLI knows strings. The Service orchestrates objects.
*   **Flow:** `CLI(algorithm="AES")` -> `CipherService.encrypt_data("AES", 128, ...)` -> `CipherFactory.create_cipher("AES", 128, ...)` -> `AESCipher.encrypt(...)`.

### Corrected Symmetric Interface (Decision 4)
*   **Decision:** `SymmetricCipherInterface` acts as the structural typing definition for V1.
*   **Contract:** Defines `encrypt`, `decrypt`, `generate_key`, `generate_iv`. We explicitly defer asymmetric interfaces (RSA) to future work.

### Corrected Benchmark Contract (Decision 5)
*   **Finding:** The 5/30 loop is frozen.
*   **Decision:** `BenchmarkService` iterates over *configurations*, NOT execution timing loops. It applies the `@PerformanceTimer.measure_time_with_warmup()` decorator (using default frozen parameters) to the core execution function. It feeds the `stats_dict` into a locally instantiated `MetricCollector`. It returns the populated `MetricCollector` to the CLI.

### Corrected Security Contract (Decision 6)
*   **Decision:** `SecurityService` will formally exist to orchestrate security math. It iterates over configurations and calls the frozen `SecurityEvaluator` methods, aggregating the returned dictionaries/floats into a standardized report structure.

### Corrected Persistence Boundary (Decision 7)
*   **Finding:** Orchestrating `FileHandler` inside `CipherService` violates Separation of Concerns.
*   **Decision:** Model B. Service returns `EncryptionResult` or `MetricCollector` or `dict`. The CLI receives this in memory. The CLI then delegates to `FileHandler` to write to disk. **Service performs ZERO filesystem I/O.**

## 5. Responsibility Matrix (Corrected)

| Responsibility | CLI | Service | Core | Analysis | Persistence |
| -------------- | --- | ------- | ---- | -------- | ----------- |
| Argument Parsing | **X** | | | | |
| Primitive Validation | **X** | | | | |
| Crypto Validation | | | **X** | | |
| Exception Translation | | | | | |
| Algorithm Registry | | **X** | | | |
| Key / IV Generation | | | **X** | | |
| Encryption / Decrypt | | | **X** | | |
| Service Orchestration| | **X** | | | |
| Benchmark Config Iter | | **X** | | | |
| Timing (5 / 30 loop) | | | | **X** | |
| Statistics (Tukey) | | | | **X** | |
| Security Math | | | | **X** | |
| Graph Construction | | | | **X** | |
| Error Presentation | **X** | | | | |
| File Writing (Disk) | **X** (Delegates)| | | | **X** (Executes) |

## 6. Service API Contracts

**`src/engines/cipher_interface.py`**
*   `SymmetricCipherInterface(abc.ABC)`

**`src/engines/cipher_service.py`**
*   `__init__(self, factory: CipherFactory)`
*   `encrypt_data(self, algorithm: str, key_size: int, mode: str, plaintext: bytes, key: bytes, iv: bytes | None = None) -> EncryptionResult`
*   `decrypt_data(self, algorithm: str, key_size: int, mode: str, ciphertext: bytes, key: bytes, iv: bytes | None = None) -> bytes`

**`src/engines/benchmark_service.py`**
*   `__init__(self, factory: CipherFactory)`
*   `run_performance_suite(self, configs: list[dict], data_payloads: list[bytes]) -> MetricCollector`
    *   *Constraint:* Must use `PerformanceTimer.measure_time_with_warmup()` with default frozen iterations.

**`src/engines/security_service.py`**
*   `__init__(self, factory: CipherFactory)`
*   `run_security_suite(self, configs: list[dict], plaintext1: bytes, plaintext2: bytes, image_bytes: bytes) -> dict`

## 7. File-Level Change Plan & Consistency Audit

| Component | API | Planned File | Test File | Impl. Sequence | Consistent? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Interface** | `SymmetricCipherInterface` | `src/engines/cipher_interface.py` | N/A | 1 | YES |
| **Factory** | `CipherFactory` | `src/engines/cipher_factory.py` | `tests/engines/test_cipher_factory.py` | 2 | YES |
| **CipherService** | `encrypt_data`, `decrypt_data` | `src/engines/cipher_service.py` | `tests/engines/test_cipher_service.py` | 3 | YES |
| **Benchmark** | `run_performance_suite` | `src/engines/benchmark_service.py` | `tests/engines/test_benchmark_service.py`| 4 | YES |
| **Security** | `run_security_suite` | `src/engines/security_service.py` | `tests/engines/test_security_service.py` | 5 | YES |

## 8. Testing Plan
*   **Behavioral Constraints:**
    *   `CipherFactory`: Verify unknown algorithm string raises `ValueError`.
    *   `CipherService`: Inject `MockCipherFactory`. Verify `EncryptionResult` is well-formed (IV is None for ECB, 16 bytes for CBC). Verify `ValueError` is allowed to propagate natively.
    *   `BenchmarkService`: Inject `MockCipherFactory` and mock `PerformanceTimer`. Verify `MetricCollector` contains the correct number of iteration configurations without the Service manually looping 30 times. Verify throughput isn't accidentally recalculated.
    *   `SecurityService`: Inject `MockCipherFactory`. Verify accurate routing to `SecurityEvaluator` methods.
*   **Integration constraints:** Ensure `CipherService` combined with the actual `AESCipher` successfully encrypts and decrypts a byte string.

## 9. Dependency Injection Strategy
We use simple Constructor Injection. `CipherService`, `BenchmarkService`, and `SecurityService` take an instance of `CipherFactory` in their `__init__`. This completely decouples orchestration from concrete cryptography implementations during testing, without requiring complex DI frameworks.

## 10. Implementation Sequence
1.  **Planning Phase** (Current Gate)
2.  **Implementation**: Define `SymmetricCipherInterface`.
3.  **Implementation**: Implement `CipherFactory`.
4.  **Implementation**: Implement `CipherService` and `EncryptionResult`.
5.  **Implementation**: Implement `BenchmarkService`.
6.  **Implementation**: Implement `SecurityService`.
7.  **Unit Tests**: Write behavioral unit tests for all engines.
8.  **Integration**: Run integration tests combining Service and Core.

## 11. Frozen Component Protection
The following files **MUST NOT BE MODIFIED** during implementation:
*   `src/core/aes_cipher.py`
*   `src/utils/padding.py`
*   `src/analyzers/performance_timer.py`
*   `src/analyzers/metric_collector.py`
*   `src/analyzers/security_evaluator.py`
*   `src/analyzers/graph_generator.py`

*If integration proves a frozen file has a bug, it must be escalated as an APPROVAL-REQUIRED ARCHITECTURAL EXCEPTION.*

## 12. Scope Boundaries
V1 scope strictly EXCLUDES:
*   Asymmetric / Classical ciphers
*   Streaming / chunking encryption
*   Pillow / psutil / external dependencies
*   CLI / FileHandler logic inside the Service Layer

## 13. Acceptance Criteria
*   [ ] `EncryptionResult` handles both ECB (None) and CBC (bytes) IVs correctly.
*   [ ] Service must not catch and translate `ValueError`. All Core `ValueErrors` must propagate natively to preserve cryptographic failure specificity.
*   [ ] 0 loops for `iterations` or `warmup` exist in the Service Layer codebase.
*   [ ] 0 dependencies are added to `requirements.txt`.
*   [ ] 0 frozen files are modified.
*   [ ] 0 occurrences of `open()` or `os.write()` exist in the Service Layer.

## 14. Remaining Open Questions
*   **RESOLVED**: IV Contract (`EncryptionResult`).
*   **RESOLVED**: Exception Mapping (`ValueError` propagation).
*   **RESOLVED**: Factory / Service Orchestration Direction (Model A).
*   **RESOLVED**: Persistence Boundary (CLI coordinates).
*   **FUTURE**: Asymmetric cipher interfaces and large-file memory mapping.

## 15. Final Recommendation
The architecture has been rigorously corrected and decoupled. The Service Layer is now definitively configured as a stateless orchestration bridge that respects frozen Core and Analysis implementations without duplicating their responsibilities.

============================================================
FINAL STATUS
============================================================

*   Repository inspected: YES
*   AESCipher ValueError sources inspected: YES
*   Existing exception system inspected: YES
*   Exception classification mechanism verified: YES
*   Error-message parsing required: NO
*   Exception mapping contract corrected: YES
*   Acceptance criteria corrected: YES
*   Frozen architecture preserved: YES

*   Source modifications made: NO
*   Dependencies installed: NO
*   Implementation started: NO
*   Commit created: NO
*   Push performed: NO

**FINAL VERDICT:**
**APPROVE FOR SPECIFICATION**
============================================================
