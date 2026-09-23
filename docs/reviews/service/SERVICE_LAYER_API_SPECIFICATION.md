# SERVICE LAYER API SPECIFICATION

## 1. SERVICE LAYER RESPONSIBILITY

The Service Layer acts as a thin orchestration bridge between the CLI presentation layer and the frozen Core/Analysis implementations.

### Responsibility Matrix

| Responsibility | CLI | Service Layer | Core | Analysis | Persistence |
| -------------- | --- | ------------- | ---- | -------- | ----------- |
| **Argument Parsing** | **X** (Owns) | | | | |
| **User Output/Presentation** | **X** (Owns) | | | | |
| **Algorithm Registry** | | **X** (Owns) | | | |
| **Orchestration / Delegation** | | **X** (Owns) | | | |
| **Crypto Pre-Validation** | | **X** (Validates params exist) | | | |
| **Crypto Rules & invariants** | | | **X** (Owns) | | |
| **Key & IV Generation** | | | **X** (Owns) | | |
| **Encryption & Decryption** | | | **X** (Owns) | | |
| **Timing & Measurement (5/30)**| | | | **X** (Owns) | |
| **Metrics & Tukey Fences** | | | | **X** (Owns) | |
| **Security Math & Avalanche** | | | | **X** (Owns) | |
| **Graph Construction** | | | | **X** (Owns) | |
| **Disk/File Writing** | | | | | **X** (Owns) |

**Constraints:**
- The Service Layer must NEVER implement cryptographic algorithms, padding, or block mode logic.
- The Service Layer must NEVER implement statistical mathematics or measurement loops.
- The Service Layer must NEVER perform filesystem I/O operations (e.g., `open`, `os.path`).

---

## 2. SYMMETRIC CIPHER INTERFACE

The interface represents the contract for V1 symmetric ciphers. It guarantees that all registered ciphers conform to the frozen capabilities of `AESCipher`.

*   **File:** `src/engines/cipher_interface.py`
*   **Class:** `SymmetricCipherInterface(abc.ABC)`
*   **Purpose:** Abstraction for symmetric block ciphers.

### Methods

```python
import abc

class SymmetricCipherInterface(abc.ABC):
    
    @abc.abstractmethod
    def generate_key(self) -> bytes:
        """Generate a cryptographically secure random key matching the configured size."""
        pass
        
    @abc.abstractmethod
    def generate_iv(self) -> bytes:
        """
        Generate a cryptographically secure random IV matching the block size.
        Returns the required IV bytes. 
        Only applicable to CBC-capable configurations. Core implementations 
        (e.g., AESCipher) will reject IV generation with a ValueError if the mode is ECB.
        """
        pass
        
    @abc.abstractmethod
    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        """Encrypt plaintext. Requires IV for CBC mode, forbids IV for ECB mode."""
        pass
        
    @abc.abstractmethod
    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        """Decrypt ciphertext. Requires IV for CBC mode, forbids IV for ECB mode."""
        pass
```

*   **Invariants:** Subclasses must raise `ValueError` for invalid keys, invalid IVs, missing IVs, or bad padding. Assumes symmetric key behavior.
*   **Future Scope:** Asymmetric algorithms (like RSA) are explicitly deferred and will require a different interface (e.g., `AsymmetricCipherInterface`).

---

## 3. ENCRYPTION RESULT

The structured output returned by encryption operations.

*   **File:** `src/engines/cipher_service.py`
*   **Class:** `EncryptionResult`

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class EncryptionResult:
    ciphertext: bytes
    iv: bytes | None
```

*   **ECB Behavior:** `iv` is strictly `None`.
*   **CBC Behavior:** `iv` is exactly 16 bytes.
*   **Immutability:** `frozen=True` ensures the result cannot be mutated after return.
*   **Lifecycle:** Service constructs and returns it to CLI. CLI is responsible for reading the properties and forwarding them to Persistence (e.g., prepending IV or writing to separate files).

---

## 4. CIPHER FACTORY

A dictionary-based registry for instantiating symmetric ciphers.

*   **File:** `src/engines/cipher_factory.py`
*   **Class:** `CipherFactory`

### Exact API

```python
class CipherFactory:
    def __init__(self):
        # Dictionary registry
        self._registry = {
            "AES": AESCipher
        }
        
    def create_cipher(self, algorithm: str, key_size: int, mode: str) -> SymmetricCipherInterface:
        """
        Instantiate a registered cipher.
        Raises ValueError if the algorithm is unsupported.
        """
        algo_upper = algorithm.upper()
        if algo_upper not in self._registry:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
            
        cipher_class = self._registry[algo_upper]
        return cipher_class(key_size=key_size, mode=mode.upper())
```

*   **Lifecycle:** The Factory is stateless regarding crypto data. `create_cipher` returns a **fresh instance** every time.
*   **Validation:** It verifies the algorithm string exists. `AESCipher` itself verifies whether `key_size` and `mode` are valid for AES.

---

## 5. CIPHER SERVICE

The primary orchestration class for standard encryption/decryption requests.

*   **File:** `src/engines/cipher_service.py`
*   **Class:** `CipherService`

### Exact API

```python
class CipherService:
    def __init__(self, factory: CipherFactory = None):
        self.factory = factory or CipherFactory()
        
    def encrypt_data(self, algorithm: str, key_size: int, mode: str, plaintext: bytes, key: bytes, iv: bytes | None = None) -> EncryptionResult:
        """
        Orchestrate encryption.
        If mode is CBC and iv is None, Core will generate the IV.
        """
        cipher = self.factory.create_cipher(algorithm, key_size, mode)
        
        # If IV is required but missing, generate it via Core.
        if mode.upper() == "CBC" and iv is None:
            iv = cipher.generate_iv()
            
        # Core validates everything (key length, ECB vs CBC constraints).
        ciphertext = cipher.encrypt(plaintext, key, iv)
        return EncryptionResult(ciphertext=ciphertext, iv=iv)

    def decrypt_data(self, algorithm: str, key_size: int, mode: str, ciphertext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        """
        Orchestrate decryption.
        """
        cipher = self.factory.create_cipher(algorithm, key_size, mode)
        return cipher.decrypt(ciphertext, key, iv)
```

*   **Key Lifecycle:** `CipherService` requires an explicit `key: bytes`. The caller is responsible for obtaining/generating the key. `CipherService` does not generate, persist, or implicitly replace a missing key.
*   **IV Lifecycle (Normal Encryption):**
    *   `CipherService` requests a Core-generated IV when CBC encryption is invoked without an IV.
    *   If the caller explicitly supplies an IV, `CipherService` passes it directly to Core.
    *   Core remains authoritative for IV length, validity, and ECB/CBC rules. The Service does NOT independently validate those cryptographic invariants.

---

## 6. EXCEPTION CONTRACT

*   **Contract:** Core `ValueError` and `TypeError` exceptions propagate **natively** through the Service Layer up to the CLI.
*   **Pre-validation:** The Service does NOT duplicate Core validation (e.g., verifying key lengths).
*   **No Translation:** Artificial wrapper exceptions (`CryptographyError`, `ValidationError`) have been **rejected** for V1 to prevent fragile string-parsing of internal Python errors.
*   **Rule:** The Service Layer will NOT catch `ValueError` just to re-raise it.

---

## 7. BENCHMARK CONFIGURATION CONTRACT

A benchmark configuration is defined as a Python dictionary specifying the exact cryptographic parameters.

**Schema:**
```python
{
    "algorithm": str,  # e.g., "AES"
    "key_size": int,   # e.g., 128, 192, 256
    "mode": str        # e.g., "ECB", "CBC"
}
```
*   **Required Fields:** `algorithm`, `key_size`, `mode`.
*   **Validation:** If keys are missing, `BenchmarkService` will raise `KeyError`. Invalid values (e.g., `key_size=999`) will be rejected natively by `AESCipher` during instantiation.
*   **Normalization:** The Service does not normalize values; it passes them exactly as provided to the Factory (which handles case insensitivity).
*   **Duplicates:** Duplicate configurations are executed multiple times. The Service does not deduplicate them.
*   **Mutation:** Configuration dictionaries are read-only and must not be mutated by the Service.

---

## 8. BENCHMARK SERVICE

*   **File:** `src/engines/benchmark_service.py`
*   **Class:** `BenchmarkService`

### Exact API

```python
class BenchmarkService:
    def __init__(self, factory: CipherFactory = None):
        self.factory = factory or CipherFactory()
        
    def run_performance_suite(self, configs: list[dict], data_payloads: list[bytes]) -> MetricCollector:
        """
        Run performance benchmarks across configurations and payloads.
        Returns the populated MetricCollector.
        """
        collector = MetricCollector()
        
        for config in configs:
            # One configuration -> one fresh cipher instance
            cipher = self.factory.create_cipher(config["algorithm"], config["key_size"], config["mode"])
            
            for payload in data_payloads:
                # Key and IV generation outside the measured function
                key = cipher.generate_key()
                iv = cipher.generate_iv() if config["mode"].upper() == "CBC" else None
                
                # Apply the frozen PerformanceTimer decorator with defaults (30 iterations, 5 warmups)
                @PerformanceTimer.measure_time_with_warmup()
                def _measured_encrypt():
                    cipher.encrypt(payload, key, iv)
                    
                # Execute measured block
                _, stats_dict = _measured_encrypt()
                
                # Format exactly as MetricCollector expects, omitting the optional memory metric
                metric_data = {
                    'algorithm': config["algorithm"],
                    'key_size': config["key_size"],
                    'mode': config["mode"],
                    'data_size_bytes': len(payload),
                    'raw_times_ms': stats_dict['raw_times_ms']
                }
                collector.add_metric(metric_data)
                
        return collector
```

*   **Timing Contract:** `BenchmarkService` invokes the frozen `PerformanceTimer` using its established default configuration (`iterations=30, warmup=5`). `BenchmarkService` does not supply, override, or expose warmup/measurement iteration counts.
*   **IV Handling:** Key and IV generation are performed *outside* the measured block to strictly measure encryption execution time.
*   **Memory Metric:** Memory measurement is out of scope for V1. Since `memory_delta_mb` is structurally optional in `MetricCollector`, it is omitted. The Service MUST NOT fabricate `0.0`.
*   **Cipher Lifecycle Rule:** The rule is **one configuration → one cipher instance**. The stateless cipher instance is safely reused across multiple payload iterations, since AES encryption does not modify internal cipher state.

---

## 9. BENCHMARK INPUT / PAYLOAD CONTRACT

*   `data_payloads: list[bytes]` contains raw byte payloads to benchmark.
*   Payloads are read-only (not mutated).
*   For each configuration/payload pair, a fresh random key and fresh IV are generated.
*   Key and IV generation time are EXCLUDED from the performance measurements.

---

## 10. BENCHMARK OUTPUT CONTRACT

*   **Return Type:** Returns the instantiated `MetricCollector`.
*   **Lifecycle:** The object is fully populated. The caller (CLI) may extract `collector.get_summary_dataframe()` to pass to `GraphGenerator`, or `collector.get_summary()` to print statistics.
*   **Why Not DataFrame?** Returning `MetricCollector` allows the CLI to choose whether it wants summary statistics, DataFrames, or raw observations.

---

## 11. SECURITY SERVICE

*   **File:** `src/engines/security_service.py`
*   **Class:** `SecurityService`

### Exact API

```python
class SecurityService:
    def __init__(self, factory: CipherFactory = None):
        self.factory = factory or CipherFactory()
        
    def run_security_suite(
        self, 
        configs: list[dict], 
        plaintext1: bytes, 
        plaintext2: bytes, 
        key1: bytes, 
        key2: bytes, 
        image_bytes: bytes, 
        iv: bytes
    ) -> dict:
        """
        Execute SecurityEvaluator logic over multiple configurations.
        Returns a nested dictionary of exact evaluator results.
        
        Requires the caller to explicitly supply a controlled 16-byte IV 
        for the security experiment suite.
        """
        results = {}
        for config in configs:
            cipher = self.factory.create_cipher(config["algorithm"], config["key_size"], config["mode"])
            
            conf_str = f"{config['algorithm']}-{config['key_size']}-{config['mode']}"
            conf_results = {}
            
            # Avalanche
            # Service propagates ValueError natively if plaintext1 and plaintext2 don't differ by 1 bit.
            av = SecurityEvaluator.calculate_avalanche_effect(plaintext1, plaintext2, cipher, key1, iv)
            conf_results["avalanche_effect"] = av
            
            # Key Sensitivity
            # Service propagates ValueError natively if key1 and key2 don't differ by 1 bit.
            ks = SecurityEvaluator.test_key_sensitivity(cipher, plaintext1, key1, key2, iv)
            conf_results["key_sensitivity"] = ks
                
            # ECB Weakness (Image)
            if config["mode"].upper() == "ECB":
                # ECB encryption itself does not consume the IV.
                # However, the ECB weakness experiment requires the supplied IV 
                # because it constructs a CBC comparison baseline.
                ecb_res = SecurityEvaluator.test_ecb_weakness(image_bytes, key1, iv) 
                conf_results["ecb_weakness"] = ecb_res
                    
            results[conf_str] = conf_results
            
        return results
```

*   **Exceptions:** `SecurityService` MUST NOT catch `ValueError` or `TypeError` to convert them into `*_error` dictionary fields. It natively propagates all `SecurityEvaluator` and `AESCipher` failures up to the CLI.
*   **Avalanche Contract:** The caller provides `plaintext1`, `plaintext2`, `key1`, and `iv`. The contract explicitly requires plaintexts to differ by exactly one bit. The same `key1` and `iv` are passed to both encryptions. `SecurityEvaluator` natively validates this invariant and raises `ValueError` if violated.
*   **Key Sensitivity Contract:** The caller provides `key1`, `key2`, `plaintext1`, and `iv`. The contract explicitly requires keys to differ by exactly one bit. The same `plaintext1` and `iv` are used. `SecurityEvaluator` natively validates this invariant.
*   **Key Contract & Mixed Key Sizes:**
    *   One supplied `key1`/`key2` pair must be compatible with every configuration in a single suite invocation.
    *   Mixed AES key sizes requiring different key lengths are not supported in one V1 invocation. The single pair of keys cannot physically satisfy different length constraints simultaneously without violating the strict one-bit difference experiment. Run separate suite invocations for different key sizes.
    *   **Caller responsibility:** The caller must supply correctly sized controlled keys. The caller is responsible for constructing the required one-bit-difference key pair. SecurityService does NOT automatically pad, truncate, mutate, or generate security keys.
*   **Security IV Lifecycle & Routing Semantics:** 
    *   **Who supplies:** The Caller explicitly passes a required `iv: bytes`.
    *   **Who generates:** The Caller. SecurityService NEVER generates an IV for the security suite.
    *   **Routing:** 
        *   CBC avalanche and key sensitivity → receive the supplied IV.
        *   ECB avalanche and key sensitivity → receive `None`.
        *   ECB weakness experiment → explicitly receives the supplied IV (required for its internal CBC comparison baseline).
*   **ECB Weakness Contract:** The actual `dict` containing headers and ciphertexts from `test_ecb_weakness` is returned directly in the results. It is NOT replaced by "Data generated" or swallowed.

---

## 12. GRAPH GENERATION BOUNDARY

*   `GraphGenerator` is **intentionally outside the Service Layer**.
*   **Flow:** CLI receives `MetricCollector` from `BenchmarkService`. CLI extracts the DataFrame and passes it directly to `GraphGenerator`.
*   This keeps the Service Layer free from Matplotlib logic.

---

## 13. PERSISTENCE BOUNDARY

*   **Service Layer has zero persistence.**
*   All results are returned in memory (`EncryptionResult`, `MetricCollector`, `bytes`, `dict`).
*   The CLI invokes `src/utils/file_handler.py` to write these artifacts to disk.

---

## 14. DEPENDENCY INJECTION

*   **Strategy:** Constructor Dependency Injection.
*   `CipherService`, `BenchmarkService`, and `SecurityService` take an optional `factory: CipherFactory` parameter.
*   This enables the test suite to pass a `MockCipherFactory` that returns a `MockCipher`, preventing heavy crypto computations during orchestration testing.

---

## 15. STATE AND LIFECYCLE

*   **Service instances maintain no request/session/cryptographic state.** They retain only their injected dependencies.
*   A configured cipher instance may be reused within a benchmark configuration when the underlying Core implementation is stateless.
*   No unnecessary thread-safety claims are made, as state isolation is achieved through statelessness rather than explicit thread synchronization.

### Implementation Plan vs. API Specification Reconciliation

The API Specification is the later, authoritative, and more detailed contract derived from rigorous source analysis, overriding outdated conceptual signatures in the Implementation Plan.

| Contract | Implementation Plan | Final API Specification | Source Evidence | Resolution |
| :--- | :--- | :--- | :--- | :--- |
| **SecurityService Signature** | `run_security_suite(configs, pt1, pt2, image)` | `run_security_suite(configs, pt1, pt2, key1, key2, image, iv)` | `SecurityEvaluator` methods require explicit `key1`, `key2`, and `iv`. | **Updated API Spec.** Service cannot generate mathematical mutations internally. Caller supplies inputs. |
| **Security IV Ownership** | Ambiguous/Service-generated | Caller supplies explicit `iv`. | ECB cannot generate CBC IVs natively. `os.urandom` cannot be hardcoded for ECB weakness. | **Updated API Spec.** SecurityService requires explicit caller-controlled IV input because the suite includes CBC comparisons, including the CBC baseline used by the ECB weakness experiment. |
| **Avalanche Inputs** | Conceptually mentioned | Caller explicitly supplies `plaintext1`, `plaintext2`, `key1`, `iv`. | `calculate_avalanche_effect` explicitly requires 1-bit difference. | **Updated API Spec.** Caller supplies 1-bit varied plaintexts; Evaluator validates. |
| **Key-Sensitivity Inputs** | Missing | Caller explicitly supplies `plaintext1`, `key1`, `key2`, `iv`. | `test_key_sensitivity` exists in source and requires 1-bit key difference. | **Updated API Spec.** Caller supplies 1-bit varied keys; Evaluator validates. |
| **Benchmark Timer Defaults** | Implied Service control | `@PerformanceTimer.measure_time_with_warmup()` with frozen defaults. | `performance_timer.py` strictly defaults to 30 measurements and 5 warmups. | **Consistent.** Service invokes the decorator without overriding parameters. |
| **MetricCollector Memory** | Allowed fabrication | `memory_delta_mb` omitted entirely. | `MetricCollector` structurally allows optional memory. | **Updated API Spec.** Service only supplies exact measured data. |
| **Cipher Lifecycle** | Fresh cipher for every operation | One instance per config reused across payloads. | `AESCipher` holds no internal request state. | **Updated API Spec.** Cipher instance reused per config for benchmark efficiency. |
| **Exception Propagation** | Native propagation | Native propagation | `AESCipher` explicitly raises `ValueError` & `TypeError`. | **Consistent.** No translation or string matching is performed. |

---

## 16. SECURITY / CRYPTOGRAPHIC INVARIANTS

*   **Normal Encryption:** `CipherService` requests a Core-generated IV when CBC encryption is invoked without an IV. Core remains authoritative for IV length, validity, and ECB/CBC rules. The Service does not independently validate those cryptographic invariants.
*   **Controlled Security Experiment:** The caller explicitly supplies a controlled IV. `SecurityService` passes it to `SecurityEvaluator`. Neither `SecurityService` nor `SecurityEvaluator` generates an IV.
*   Core strictly uses `os.urandom` to provide cryptographically strong random bytes for generation.
*   The specification acknowledges that `os.urandom` does not mathematically guarantee that two generated IVs will never collide. It provides unpredictability, not absolute uniqueness.

---

## 17. TESTING CONTRACT

Tests required for implementation sign-off:

1.  **`test_cipher_factory.py`**:
    *   Verify `create_cipher("AES", 128, "CBC")` returns `AESCipher`.
    *   Verify `create_cipher("UNKNOWN", 128, "CBC")` raises `ValueError`.
2.  **`test_cipher_service.py`**:
    *   Verify `encrypt_data` with CBC returns `EncryptionResult(ciphertext, iv)`.
    *   Verify `encrypt_data` with ECB returns `EncryptionResult(ciphertext, None)`.
    *   Verify `decrypt_data` correctly unwraps ciphertext to plaintext.
3.  **`test_benchmark_service.py`**:
    *   Inject `MockCipherFactory` and mock `PerformanceTimer`.
    *   Verify `MetricCollector` is correctly populated with configurations.
4.  **`test_security_service.py`**:
    *   Verify integration with `SecurityEvaluator`.

---

## 18. EXACT FILE MAP

| File Path | Action | Description | Dependencies |
| :--- | :--- | :--- | :--- |
| `src/engines/__init__.py` | Modify | Export Services & Factory | None |
| `src/engines/cipher_interface.py` | Create | `SymmetricCipherInterface` | `abc` |
| `src/engines/cipher_factory.py` | Create | `CipherFactory` | `src.core.aes_cipher` |
| `src/engines/cipher_service.py` | Create | `CipherService`, `EncryptionResult` | Factory |
| `src/engines/benchmark_service.py` | Create | `BenchmarkService` | Factory, Timer, Collector |
| `src/engines/security_service.py` | Create | `SecurityService` | Factory, Evaluator |

**FORBIDDEN TO MODIFY:**
*   `src/core/aes_cipher.py`
*   `src/utils/padding.py`
*   `src/analyzers/performance_timer.py`
*   `src/analyzers/metric_collector.py`
*   `src/analyzers/security_evaluator.py`
*   `src/analyzers/graph_generator.py`

---

## 19. IMPLEMENTATION ORDER

1.  Create `cipher_interface.py` and `cipher_factory.py`. Write factory tests.
2.  Create `cipher_service.py` with `EncryptionResult`. Write service tests.
3.  Create `benchmark_service.py`. Write benchmark orchestration tests.
4.  Create `security_service.py`. Write security orchestration tests.
5.  Update `__init__.py`.
6.  Perform integration review verifying frozen files were not touched.

---

## 20. FORBIDDEN BEHAVIOR

*   No filesystem I/O (`open()`, `os.path`).
*   No persistence in Service.
*   No benchmark timing loop (`for _ in range(30)`).
*   No metric calculation in Service.
*   No cryptographic implementation in Service.
*   No exception-message parsing.
*   No `ValueError` translation (must propagate natively).
*   No singleton ContextManager.
*   No global mutable session state.
*   No new dependencies in `requirements.txt`.
*   No RSA/Classical forced into symmetric V1 interface.
*   No streaming/chunking API additions.
*   No Pillow or psutil additions.
*   No changes to frozen Analysis/Core components.
*   No frontend/CLI presentation logic inside Service.

---

## 21. TRACEABILITY MATRIX

| Approved Decision | API Specification Section | Actual Source Evidence | Implementation Impact |
| ----------------- | ------------------------- | ---------------------- | --------------------- |
| Exception propagation | 6. Exception Contract | `AESCipher` & `Padding` exclusively raise `ValueError` / `TypeError`. | Native propagation; no exception parsing. |
| PerformanceTimer 5/30 | 8. Benchmark Service | `PerformanceTimer.measure_time_with_warmup()` provides 30/5 defaults natively. | Service strictly invokes decorator without parameters. |
| MetricCollector structure | 8. Benchmark Service | `MetricCollector` optionally accepts `memory_delta_mb` (defaults to `np.nan`). | No fabrication of `0.0` for memory metrics. |
| SecurityEvaluator avalanche | 11. Security Service | `calculate_avalanche_effect` raises `ValueError` if plaintexts don't differ by 1 bit. | Caller supplies plaintexts; Service propagates `ValueError`. |
| SecurityEvaluator ECB weakness| 11. Security Service | `test_ecb_weakness` returns a `dict` with headers and ciphertexts. | Service returns the exact `dict` directly without `"Data generated"` placeholders. |
| AESCipher IV behavior | 3. Encryption Result & 5. CipherService | `AESCipher._validate_iv` permits `None` for ECB and requires 16 bytes for CBC. | `EncryptionResult` typing (`iv: bytes \| None`); Service delegates validation. |
| AESCipher lifecycle/state | 8. Benchmark Service & 15. Lifecycle | `AESCipher` methods (`encrypt`, `decrypt`) hold no request state. | One instance per config reused across payloads; stateless Service. |
| Persistence boundary | 13. Persistence Boundary | `FileHandler` isolates disk ops entirely. | Service returns in-memory objects (`EncryptionResult`, `MetricCollector`). |
| Factory behavior | 4. Cipher Factory | `AESCipher` is the only V1 symmetric cipher. | Dictionary registry mapping `"AES"` to `AESCipher`. |

---

## 22. OPEN QUESTIONS / BLOCKERS

`No implementation-blocking open questions remain.`

All contracts have been strictly mapped to existing Core implementations.

---

## 23. FINAL SELF-AUDIT

*   **Exception Translation**: Correctly forbidden. `ValueError` propagates.
*   **IV Ownership**: 
    *   *Normal CipherService CBC encryption:* Service requests IV from Core when IV is absent; the resulting IV is returned in EncryptionResult.
    *   *SecurityService controlled experiments:* Caller supplies the IV; SecurityService passes the exact IV to SecurityEvaluator without generating or replacing it.
*   **Benchmark Iteration**: Correctly delegated to `PerformanceTimer` decorator.
*   **Persistence**: Correctly excluded from Service Layer.
*   **Unsupported Algorithms**: RSA deferred.
*   **Dependencies**: Zero new dependencies introduced.

---

## Specification Status

**READY FOR FINAL INDEPENDENT API REVIEW**

*   Files inspected: `aes_cipher.py`, `padding.py`, `performance_timer.py`, `metric_collector.py`, `security_evaluator.py`, `graph_generator.py`
*   Files created/modified: `docs/reviews/service/SERVICE_LAYER_API_SPECIFICATION.md`
*   Frozen files confirmed untouched: YES
*   Contradictions discovered: NONE (All resolved during prior gate review)
*   Unresolved questions: 0
*   Source implementation: NOT STARTED
*   Source files modified: 0
*   Dependencies changed: 0
