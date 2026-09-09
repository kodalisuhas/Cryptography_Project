# SERVICE LAYER — PROJECT-SPECIFIC EXPLORE / PLAN

## 1. Executive Summary

This report analyzes two existing Deep Research documents concerning the Service Layer and CLI, comparing their proposals against the explicitly reconstructed and frozen state of the Cryptography Project. The objective is to distill a project-specific architectural plan for the Service Layer that respects existing contracts (Core AES, frozen Analysis methodology) while discarding conflicting or over-engineered research suggestions. 

The analysis concludes that the Service Layer must act as a **Thin Orchestrator** connecting the CLI, Core, Analysis, and Persistence layers. It will utilize a simple Dictionary-based Factory and a strong, explicit Abstract Base Class (ABC) without `**kwargs` or embedded metric logic. All research recommendations proposing methodology alterations (e.g., discarding outliers, N=50 iterations) are explicitly rejected in favor of the frozen project methodology.

## 2. Evidence Sources

1. **PROJECT_CONTEXT_RECONSTRUCTION.md**: Authoritative current state, frozen boundaries, and completed tasks.
2. **Deep Research Report A**: `DEEP RESEARCH REPORT SERVICE LAYER & CLI.md`
3. **Deep Research Report B**: `Service Layer Architecture & System Design Report (Task 3).md`
4. **Project Source Code**: Actual frozen implementations of `src/core/aes_cipher.py`, `src/analyzers/*`, and `src/utils/padding.py`.

## 3. Current Project Constraints

*   **DO NOT modify Core (`aes_cipher.py`)**: Its API and internal logic are frozen.
*   **DO NOT modify Padding (`padding.py`)**: Owned and invoked directly by Core.
*   **DO NOT modify Analysis (`performance_timer.py`, `metric_collector.py`, `security_evaluator.py`, `graph_generator.py`)**: Their statistical boundaries, APIs, and Tukey outlier logics are frozen.
*   **Frozen Benchmark Methodology**: Exactly 5 warmup runs, exactly 30 measured runs, Tukey fences for flagging outliers (never deleting them), and Throughput calculated as Binary MB.

## 4. Existing Core Contract Relevant to Service

The frozen `AESCipher` establishes the following non-negotiable interaction pattern:
*   **Construction**: `AESCipher(key_size, mode)` (Validates algorithm constraints natively).
*   **Execution**: `encrypt(plaintext, key, iv)` and `decrypt(ciphertext, key, iv)`.
*   **Helpers**: `generate_key()` and `generate_iv()`.
*   **Padding Ownership**: `AESCipher` natively invokes `Padding.pad()` and `Padding.unpad()`.
*   **Exceptions**: Raises native `ValueError` for any invalid keys, modes, lengths, IVs, or alignment issues. No custom hierarchy (`InvalidTag`, `InvalidKey`) is exposed.

## 5. Existing Analysis Contract Relevant to Service

The frozen Analysis Layer establishes:
*   `PerformanceTimer.measure_time_with_warmup(iterations=30, warmup=5)` orchestrates the looping natively via decorators.
*   `MetricCollector` stores raw observations and computes summary statistics; Service must not perform statistical math.
*   `GraphGenerator` expects populated pandas DataFrames/MetricCollectors; generates in-memory `plt.Figure` objects (does not persist to disk).
*   `SecurityEvaluator` operates in isolation.

## 6. Research Report A — Extracted Proposals

*   **Architecture**: Thin Orchestration Service (CLI -> Service -> Analysis/Core).
*   **Cipher Interface**: `abc.ABC` with explicit parameters (`encrypt(plaintext, key, iv=None)`).
*   **Factory**: Simple Dictionary Registry.
*   **Context/State**: Rejects ContextManager/Singleton. Proposes purely stateless design where keys/IVs are passed as explicit parameters.
*   **CLI Framework**: Standard library `argparse`. No third-party deps.
*   **Benchmark**: Service orchestrates the flow; Analysis handles measurement.

## 7. Research Report B — Extracted Proposals

*   **Architecture**: Service Layer as a Validation Proxy utilizing `Validators`.
*   **Cipher Interface**: `abc.ABC` with `**kwargs` (`encrypt(data, key, **kwargs)`) and a `get_metrics()` method on the cipher itself.
*   **Factory**: Dictionary Registry enforcing constraints (e.g., ECB/IV rules, RSA payload rules).
*   **Context/State**: Session-Scoped Object created by CLI and passed to Service.
*   **Benchmark**: Separate `Benchmark Service`. Suggests `N >= 50` iterations, IQR outlier removal (discarding).
*   **CLI Framework**: `argparse`, `psutil`, `Pillow`.

## 8. Research Comparison Matrix

| Topic | Research A | Research B | Actual Project Contract | Compatibility | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Cipher Interface** | ABC, explicit params | ABC, `**kwargs`, `get_metrics()` | AES requires explicit `key`, `iv` | Mixed | **ABC, explicit params** |
| **Factory Pattern** | Dictionary Registry | Dictionary Registry | Unspecified | Compatible | **Dictionary Registry** |
| **Context Management** | Stateless (pass params) | Session-Scoped Object | Unspecified | Open | **Session/Context Object (for CLI/Service handoff)** |
| **Service Role** | Thin Orchestrator | Validation Proxy | Unspecified | Mixed | **Orchestrator** |
| **Validation** | Service forwards | Service scrubs | Core natively validates | Conflict | **Core validates crypto; Service orchestrates** |
| **Benchmark Methodology** | N/A | N=50, discard outliers | 30/5 runs, retain outliers | **Incompatible (B)** | **Project Contract Wins** |
| **CLI Framework** | `argparse` | `argparse` + `psutil`/`Pillow` | Unspecified | Compatible | **`argparse`** |

## 9. Core Compatibility Analysis

Based on the actual frozen `AESCipher`:

*   **Question A (Key/IV provision)**: Service MUST provide `key` and `iv` to `encrypt/decrypt`. Core does not store them.
*   **Question B (Key Generation)**: Core implements `generate_key()`. Service orchestrates calling it when users don't provide a key.
*   **Question C (IV Generation)**: Core implements `generate_iv()`. Service orchestrates calling it for CBC mode.
*   **Question D (Session State)**: `AESCipher` is stateless across calls. Service/CLI must maintain the key/IV between an encrypt and a subsequent decrypt if the user is doing a round-trip.
*   **Question E (Independent Calls)**: Yes, `encrypt` and `decrypt` are completely independent.
*   **Question F (Survivability)**: Key, IV, and configuration (key_size, mode, algorithm) must survive between CLI interactions.
*   **Question G (Missing Context)**: Core raises `ValueError`. Service must catch and return a clean error to CLI.

## 10. Service Responsibility Analysis

| Candidate Responsibility | Owner | Justification |
| :--- | :--- | :--- |
| Algorithm selection | SERVICE | Via Factory |
| Cipher construction | SERVICE | Via Factory |
| Key/IV generation | CORE | Implemented in `AESCipher`. Service just invokes. |
| Padding | CORE | Implemented natively in `AESCipher`. Service MUST NOT pad. |
| Context management | SERVICE/CLI | Must hold Key/IV across interactive menu choices. |
| Encrypt/Decrypt orchestration | SERVICE | Maps CLI request to Core execution. |
| Benchmark orchestration | SERVICE | Coordinates Core execution through `PerformanceTimer`. |
| Statistical math / graphs | ANALYSIS | `MetricCollector` and `GraphGenerator` own this. |
| Persistence / File I/O | PERSISTENCE | `FileHandler` owns disk writes. |
| CLI / Menu rendering | CLI | `argparse` and `menu.py` own this. |

## 11. Interface / ABC Analysis

*   **Explicit vs `**kwargs`**: Research A's explicit parameter recommendation (`key: bytes`, `iv: Optional[bytes] = None`) matches the frozen `AESCipher` perfectly. Research B's `**kwargs` reduces type safety and clarity.
*   **`get_metrics()` on Cipher**: Research B suggests putting `get_metrics()` on the interface. This violates the frozen Architecture where Analysis handles metrics independently. Research A correctly identifies this as an anti-pattern.
*   **Decision**: `abc.ABC` with explicit parameters (`encrypt`, `decrypt`, `generate_key`, `get_algorithm_name`).

## 12. Factory Analysis

Both reports agree on a **Dictionary Registry Factory**. This is appropriate, simple, and extensible.
It allows dynamic instantiation of `AESCipher` now, and `RSACipher`/`BlowfishCipher` later without altering the Service orchestration logic. The Factory will handle the instantiation signature `cipher_class(key_size, mode)`.

## 13. Context / State Management Analysis

*   Research A wants a purely stateless Service.
*   Research B wants a Session-Scoped Object.
*   **Reality Check**: `AESCipher` requires the Key and IV to be passed every time. In an interactive CLI (Option 1: Encrypt, Option 2: Decrypt), *something* must hold the Key and IV in memory between menu selections.
*   **Conclusion**: A lightweight `SessionContext` or `CryptoContext` object (or simple dictionary in the CLI) is required to hold the current `algorithm`, `key_size`, `mode`, `key`, and `iv`. The Service itself can remain stateless, simply receiving this context object from the CLI for each operation.

## 14. Validation Boundary Analysis

Research B proposes the Service acts as a "Validation Proxy". However, the frozen `AESCipher` strictly and thoroughly validates `key_size`, `mode`, `key` length/type, and `iv` rules, raising `ValueError`.
*   **Constraint**: We must not duplicate validation logic unnecessarily.
*   **Boundary**: CLI parses strings to types. Service ensures required parameters exist. Core validates cryptographic constraints (e.g., "Is this key exactly 32 bytes?").

## 15. Exception Boundary Analysis

Core raises `ValueError` for bad inputs/padding.
*   **Proposal**: Service should catch `ValueError` from Core and translate it or propagate it cleanly so the CLI can display "Error: Invalid padding" without a stack trace. We will rely on the frozen exception hierarchy (Base `CryptographyError` vs standard `ValueError`). Since Core uses `ValueError`, Service will catch `ValueError`.

## 16. Benchmark / Analysis Integration Analysis

Service must orchestrate the benchmark:
1.  Service receives config from CLI.
2.  Service generates random payloads.
3.  Service wraps the Core encrypt/decrypt calls with `PerformanceTimer.measure_time_with_warmup`.
4.  Service passes timings to `MetricCollector`.
5.  Service passes `MetricCollector` to `GraphGenerator`.
6.  Service passes `plt.Figure` and CSV data to `Persistence` for saving.
Service acts entirely as the conductor.

## 17. Benchmark Methodology Conflict Audit

**Conflict 1:** Research Report B mandates `N >= 50` or `100` iterations.
**Frozen Rule:** Exactly 30 measured, 5 warmup.
**Decision:** REJECT Research B. Project methodology (30/5) wins.

**Conflict 2:** Research Report B mandates Interquartile Range (IQR) outlier removal (discarding).
**Frozen Rule:** Tukey fences flag outliers, but raw observations are NEVER silently deleted. Primary stats use raw data.
**Decision:** REJECT Research B. Project methodology wins.

## 18. Security Analysis

*   **CSPRNG**: Core already uses `os.urandom`.
*   **Key Logging**: Service must never `print()` or log the `key` or `iv`.
*   **IV Reuse**: Service must ensure `generate_iv()` is called for every new encryption operation in CBC mode.
*   **Memory Expsoure**: Keys must exist only in the temporary Context object and be discarded when the CLI session ends.

## 19. Persistence Boundary Analysis

Service handles the business logic flow but MUST NOT write to disk. 
Service receives the in-memory `plt.Figure` from `GraphGenerator` and byte/string data from Core, and passes them to `src/utils/file_handler.py` for actual disk serialization.

## 20. CLI Boundary Analysis

CLI knows: Interactive menus, `argparse` mapping, file path collection, user intent.
Service knows: Which components to call to fulfill that intent.
CLI does NOT directly import `AESCipher` or `MetricCollector`.

## 21. Future Algorithm Compatibility

The chosen explicit ABC (`encrypt(plaintext, key, iv=None)`) works for AES and Blowfish.
For RSA, `iv` is unused (defaults to None). RSA uses KeyPairs (Public/Private). The ABC may need `generate_keypair()` or a flexible `key` typing (`bytes | tuple`) in the future, but `**kwargs` is still overkill. We can address RSA key structures when RSA is implemented.

## 22. Architecture Options

**Option A: Thin Stateless Service (Recommended)**
CLI manages a simple dictionary of current settings (key, iv). It passes these explicitly to `Service.encrypt(cipher, plaintext, key, iv)`. Service calls Core.

**Option B: Stateful Service**
Service holds the `key` and `iv` as instance variables. CLI calls `Service.set_key()`.
*Risk*: Test contamination, state leakage.

**Option C: Context Object Injection**
CLI instantiates a `CryptoContext` dataclass. Passes it to Service.
*Benefit*: Clean type hints, groups related state.

## 23. Recommended Project-Specific Direction

**RECOMMENDED: Option C (Context Object Injection) + Thin Orchestration Service**

1.  **CipherInterface**: Explicit `abc.ABC` matching AES (`encrypt`, `decrypt`, `generate_key`, `generate_iv`, `get_algorithm_name`).
2.  **CipherFactory**: Dictionary registry for dynamic instantiation.
3.  **CryptoContext**: A simple DataClass holding `algorithm`, `key_size`, `mode`, `key`, `iv` to pass safely between CLI and Service.
4.  **CipherService**: Orchestrates standard encryption/decryption, invoking `FileHandler` for persistence.
5.  **BenchmarkService**: Dedicated orchestrator for the performance loops, interacting securely with `PerformanceTimer` and `MetricCollector`.

## 24. Proposed Service Layer Explore / Plan

**Phase 1: Interfaces & Factory**
*   Define `CipherInterface` (ABC).
*   Define `CipherFactory` (Registry).
*   Register `AESCipher` into the Factory.

**Phase 2: Context & Base Service**
*   Define `CryptoContext` dataclass.
*   Define `CipherService` with `process_encryption` and `process_decryption` methods.
*   Enforce Exception boundary (catching Core `ValueError`).

**Phase 3: Benchmark Orchestration**
*   Define `BenchmarkService`.
*   Wire `BenchmarkService` to `PerformanceTimer` (using 30/5 rules).
*   Wire outputs to `MetricCollector` and `GraphGenerator`.

**Phase 4: Persistence Hookup**
*   Specify the `FileHandler` interface needed by the Service Layer.

## 25. Provisional Component Map

```text
src/
├── engines/
│   ├── __init__.py
│   ├── cipher_interface.py    [PROPOSED: ABC definitions]
│   ├── cipher_factory.py      [PROPOSED: Dictionary Registry]
│   ├── context_manager.py     [PROPOSED: CryptoContext dataclass]
│   ├── cipher_service.py      [PROPOSED: Single op orchestration]
│   └── benchmark_service.py   [PROPOSED: Benchmark orchestration]
```

## 26. Future Testing Strategy

*   **Factory**: Test valid/invalid algorithm retrieval.
*   **CipherService**: Mock `AESCipher`. Verify Service correctly passes parameters and catches `ValueError`.
*   **BenchmarkService**: Mock `PerformanceTimer` and `MetricCollector`. Verify 30 iteration loops trigger correctly and outputs are routed to `GraphGenerator`.
*   **Context**: Verify state holds correctly without mutation leakage.

## 27. Risks & Open Questions

### SERVICE LAYER — OPEN QUESTIONS
1. **Asymmetric Keys**: How will the `CryptoContext` handle RSA's Public/Private key pair format natively if it's currently typed for symmetric `bytes`?
2. **File Buffering**: When the CLI provides a 500MB file, should `CipherService` chunk it, or should `FileHandler` feed it as a generator? (Documentation mentions `MAX_CHUNK_SIZE` but Core AES doesn't stream yet).
3. **Persistence Boundary**: Who creates the timestamped directories in `results/`? The CLI, the Service, or the FileHandler?

## 28. Final Recommendation Matrix

| Area | Recommendation | Confidence | Status |
| :--- | :--- | :--- | :--- |
| **Service abstraction** | Thin Orchestrator (CipherService, BenchmarkService) | High | NOT APPROVED |
| **Cipher interface** | `abc.ABC` with explicit parameters | High | NOT APPROVED |
| **Factory** | Dictionary Registry | High | NOT APPROVED |
| **Context/state** | `CryptoContext` DataClass injected from CLI | High | NOT APPROVED |
| **Validation** | Core validates; Service routes | High | NOT APPROVED |
| **Exceptions** | Catch `ValueError` from Core | High | NOT APPROVED |
| **Benchmark orchestration** | Dedicated `BenchmarkService` | High | NOT APPROVED |
| **Analysis integration** | Respect frozen 30/5, Tukey fences, NO deletion | Absolute | NOT APPROVED |
| **Security lifecycle** | Service stores no keys internally; passed via Context | High | NOT APPROVED |
| **CLI boundary** | CLI parses args -> Context -> Service | High | NOT APPROVED |
| **Persistence boundary** | Service passes byte/plt data to `FileHandler` | High | NOT APPROVED |

## 29. Final Verdict

============================================================
SERVICE LAYER — PROJECT-SPECIFIC EXPLORE / PLAN VERDICT
============================================================

Research Reports Compared:
YES

Actual Project Context Verified:
YES

Core Contract Verified:
YES

Analysis Contract Verified:
YES

Research Conflicts Identified:
YES

Frozen Methodology Protected:
YES

Service Responsibilities Identified:
YES

Architecture Options Evaluated:
YES

Project-Specific Recommendation Produced:
YES

Implementation Started:
NO

Implementation Plan Approved:
NO

Specification Approved:
NO

------------------------------------------------------------
RECOMMENDED DIRECTION
------------------------------------------------------------

Option C: A stateless, thin orchestration Service Layer that receives a `CryptoContext` dataclass from the CLI. Includes a distinct `CipherService` for single operations and a `BenchmarkService` for orchestrating the frozen Analysis methodology. Core logic duplication and research-proposed methodology alterations are explicitly rejected.

------------------------------------------------------------
CURRENT STATUS
------------------------------------------------------------

SERVICE LAYER:
RESEARCH + PROJECT-SPECIFIC EXPLORE/PLAN COMPLETE

ARCHITECTURE:
RECOMMENDED — NOT APPROVED

IMPLEMENTATION:
NOT STARTED

------------------------------------------------------------
NEXT STEP
------------------------------------------------------------

INDEPENDENT REVIEW OF THIS EXPLORE / PLAN REPORT

After review and approval:

1. Create Service Layer Implementation Plan
2. Independently review Implementation Plan
3. Create / modify Service Layer Specification
4. Review and approve specification
5. Implement
6. Review
7. Test
8. Freeze
9. Commit
10. Push

============================================================
END OF SERVICE LAYER PROJECT-SPECIFIC EXPLORE / PLAN
============================================================
