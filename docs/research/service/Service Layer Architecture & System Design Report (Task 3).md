Research and Architectural Design Report: Service Layer & Application Architecture (Task 3)

1. Executive Summary

This report defines the architectural framework for Task 3 of the Cryptography Testing Lab, a pivotal phase in establishing the system’s service-oriented backbone. As the system transitions from a modular prototype to a high-performance analytical tool, the Service Layer serves as the strategic orchestrator, ensuring scalability and operational security. By strictly decoupling the Cryptographic Engine (Core) from the Presentation Layer (CLI), we provide a maintainable foundation for comparative analysis across AES, RSA, Blowfish, and classical algorithms.

The overarching design goals—modularity, testability, and scientific rigor—are achieved through a layered approach that isolates sensitive cryptographic operations from user-facing logic. This report details the implementation of formal abstractions, factory patterns, and a stateless context management strategy designed to meet both academic engineering standards and professional security requirements.

2. Service Layer & Application Service Fundamentals

The Service Layer is a strategic necessity in this architecture, acting as a buffer that prevents "leaky abstractions" where cryptographic implementation details might bleed into the CLI. Without this layer, the system would become brittle, coupling UI changes directly to core security logic. In this project, the Service Layer functions as a Validation Proxy, ensuring that only scrubbed and validated data payloads reach the sensitive Core Layer.

We distinguish between four primary patterns:

* Service Layer: The broad architectural boundary defining available cryptographic operations.
* Application Service: Orchestrates the flow of data between the Core and Analysis layers.
* Domain Service (Core): Handles internal algorithm logic such as AES padding or RSA key generation.
* Facade: Provides a simplified, high-level interface to complex underlying modules.

Responsibility Allocation

Responsibilities Inside the Layer	Responsibilities Outside the Layer
Orchestrating cipher instantiation via Factories	Raw terminal formatting and UI logic (Presentation)
Performance timing and statistical aggregation	Raw byte manipulation and padding logic (Core)
Multi-iteration benchmark lifecycle management	Persistent storage and physical CSV/PNG I/O (Persistence)
Handoff to Analysis and Persistence layers	Mathematical proof generation (Utility)

We have adopted a "Thick" orchestration approach. The Service Layer is responsible for rigorous validation using the Utility Layer's Validators module, ensuring that invalid configurations (e.g., 127-bit keys) are intercepted before invocation.

3. Layered Boundary & Information Flow Analysis

Strict boundary contracts are enforced to prevent implementation details from contaminating the system's modularity. All data crossing these boundaries must conform to typed enumerations or validated byte-strings.

Boundary Contracts

* Presentation -> Service: The CLI transforms user-supplied strings and flags into typed enumerations and 64-bit compatible numeric types.
* Service -> Core: The Service Layer passes validated parameters (e.g., key_size=256, mode='CBC') to concrete classes like AESCipher.
* Service -> Analysis: The Service Layer triggers the PerformanceTimer without coupling the Core logic to timing mechanisms, utilizing a decorator-based approach for non-intrusive measurement.
* Service -> Persistence: Following operation completion, the Service Layer hands off validated metrics and encrypted payloads to FileHandler and MetricCollector for export.

For valid reporting and reproducibility, metadata—including Python runtime (64-bit), hardware specifications, and high-resolution timestamps—must be captured and forwarded to the Persistence Layer.

4. Cipher Abstraction Design

A formal abstraction layer is critical for a lab environment supporting multiple algorithm types. We have evaluated abc.ABC (nominal subtyping) against typing.Protocol (structural subtyping).

We have selected abc.ABC for Task 3. Unlike Protocols, ABCs allow for code reuse at the interface level. We utilize the CipherInterface base class to provide reusable timing logic and standard parameter validation, ensuring that all concrete implementations (AES, RSA, Blowfish) inherit a uniform execution wrapper.

The CipherInterface Contract

Concrete ciphers must implement the following signatures:

1. encrypt(data: bytes, key: bytes, **kwargs) -> bytes
2. decrypt(data: bytes, key: bytes, **kwargs) -> bytes
3. generate_key() -> bytes
4. get_algorithm_name() -> str
5. get_key_size() -> int
6. get_mode() -> str | None (Nullable for RSA/Classical algorithms)
7. get_metrics() -> dict (Including latency, throughput, and memory stats)

While **kwargs provides flexibility for mode-specific parameters like Initialization Vectors (IVs), the Service Layer acts as a proxy to ensure these arguments are type-checked against the Validators utility.

5. Cipher Factory & Algorithm Construction Design

The CipherFactory centralizes object creation, shielding the CLI from the concrete implementation details of specific libraries. This is the primary mechanism for the system’s extensibility.

Selection and Validation

We utilize a Dictionary Registry over if/elif chains for algorithm selection. This enables new algorithms to be registered at runtime without modifying the factory's core logic. The factory enforces critical security constraints, such as:

* ECB/IV Constraint: Rejecting IV generation if ECB mode is requested.
* Key Size Enforcement: Restricting AES to 128, 192, or 256 bits.
* Payload Constraints: Validating that RSA payloads do not exceed the mathematical limits of the selected key size (max\_size = \frac{key\_size}{8} - 11 bytes).

6. Cryptographic Context & State Management Review

State management in cryptographic systems involves high risk. Following architectural recommendations to prune the Singleton pattern, we have moved to a Stateless Context approach.

Rather than maintaining a global ContextManager instance, the system utilizes a Session-Scoped Object created by the CLI and passed explicitly to the Service Layer. This prevents "Context Leakage"—where sensitive keys or IVs might persist in memory across different benchmark runs—and ensures that the system can be tested in parallel without side effects from a global state. Cryptographic state (keys/IVs) is cleared immediately upon the conclusion of a session.

7. Service ↔ Analysis ↔ Core Benchmark Orchestration Topology

Scientific accuracy in the Testing Lab requires a clean benchmarking topology. We have adopted the following structure: CLI -> Benchmark Service -> Core + Analysis

Benchmark Lifecycle and Rigor

The Benchmark Service owns the execution lifecycle, enforcing the following quantitative requirements for statistical validity:

* Warmup Iterations: 5 to 10 iterations to mitigate "cold-start" interpreter noise and JIT optimization spikes.
* Measurement Iterations: A minimum of N \ge 50 (recommended N=100) iterations per configuration.
* Statistical Filters: Implementation of mean, median, and outlier removal using the Interquartile Range (IQR) method (threshold of 1.5x IQR).

This topology ensures that the measurement logic remains isolated from the Core cryptographic algorithms.

8. CLI Architecture & Presentation Layer Boundaries

The CLI serves as a decoupled consumer of the Service Layer. We utilize the standard library argparse for its stability and schema definition capabilities, mapping user flags to the typed requirements of the Service Layer.

Tech Stack & Dependencies

* Runtime: 64-bit Python 3.11+. (Note: Python 3.13 is currently not officially tested).
* psutil: Required for high-precision process memory metrics.
* Pillow (>=10.0.0): Required for pixel-level encryption in the ECB Penguin visual demo.
* tabulate: For professional-grade terminal reporting.

The argument_parser.py module handles the transformation of CLI strings into bytes and enumerations, ensuring that no raw user input ever reaches the Core layer.

9. Cryptographic Service Layer Security Audit

A security audit of the Service Layer reveals critical enforcement mandates:

* CSPRNG Usage: All key and IV generation must strictly utilize os.urandom() or the secrets module to ensure cryptographic entropy.
* IV Uniqueness: The Service Layer enforces that CBC mode never reuses an IV by mandating a fresh generation per encryption call.
* Exception Safety: The system forbids generic try/except blocks. Cryptographic failures are caught specifically and wrapped in non-sensitive, user-friendly messages to prevent side-channel information leakage.
* Secure Defaults: The system defaults to AES-CBC with 256-bit keys to prevent accidental use of insecure configurations like ECB with small keys.

10. Existing Project Requirements & Scope Traceability

The V1.0 Stability Baseline freezes these interfaces to ensure contract consistency across development.

Responsibility	Classification	Source / Basis
AES (128/192/256) Support	Required	01_Project_Proposal
CSPRNG (os.urandom)	Required	03_Architecture_Design
Benchmarking (N \ge 50)	Required	04_Methodology
Pillow for Visual Demo	Required	05_API_Interface_Spec
ML-based Selection	Optional	Future Scope
HSM Integration	Out of Scope	Project Exclusion

11. Minimal Viable Service Layer Blueprint

To maintain engineering rigor while avoiding bloat, the Task 3 blueprint consists of the following modules:

* src/engines/cipher_interface.py: The ABC defining the algorithm contract and shared timing logic.
* src/engines/cipher_factory.py: Centralized algorithm instantiation and registry.
* src/engines/benchmark_service.py: Orchestrator for multi-iteration execution and statistical aggregation.
* src/utils/validators.py: The primary security proxy for input scrubbing.
* src/analyzers/metric_collector.py: Handler for memory (psutil) and throughput data.

12. Error & Exception Handling Contract

Stability is maintained through a unified, three-class exception hierarchy:

1. CryptographyError: Base for all Core-related failures (e.g., PaddingError, DecryptionError).
2. ValidationError: Raised when the Service Layer proxy detects invalid parameters (e.g., InvalidKeySizeError).
3. FileError: Raised during Persistence Layer operations (e.g., FileNotFoundError).

The system adopts a Fail-Safe state: upon any error, sensitive memory buffers are cleared, and the session returns to the main menu without a process crash.

13. Reproducibility & Session State Management

The "Testing Lab" designation requires absolute reproducibility. Every session captures:

* Environment Metadata: 64-bit Python version, OS kernel version, CPU architecture, and pinned library versions (e.g., cryptography==42.0.0).
* Iteration Logs: Raw timing data for every benchmark run (N \ge 50) to allow for external verification.
* Artifact Linking: A unique Session ID that links CSV metrics, PNG graphs, and encrypted demo images (ECB Penguin) in the results/ directory.

14. Unit & Integration Testing Strategy

We test orchestrators without relying on concrete, high-latency cryptographic operations.

* Mocks/Stubs: We use unittest.mock to simulate CipherInterface behaviors, allowing us to verify the CipherFactory and BenchmarkService logic in isolation.
* Boundary Testing: Verification that the CLI parser correctly transforms strings into the expected byte formats for the Service Layer.
* Proxy Verification: Explicit tests to ensure Validators raises ValidationError for unsupported modes (e.g., GCM) or invalid key sizes before reaching the Core Layer.

15. Open Architectural Decisions & Ambiguities

The following items are submitted for Lead Architect approval:

1. IV Storage: Whether to persist IVs in a dedicated .iv file or append them to the .enc payload during CLI file operations.
2. Outlier Strategy: Final confirmation of the 1.5x IQR threshold for the outlier removal algorithm in benchmark reporting.
3. Memory Monitoring: The performance impact of psutil polling frequency during extremely high-speed classical cipher runs.

16. Proposed Chronological Execution Roadmap

Development follows the implementation order defined in the API Interface Specification:

* Phase 1: Utility Layer: Implement Validators, Padding, and FileHandler (Foundational requirements).
* Phase 2: Core Layer: Finalize concrete AESCipher and RSACipher implementations using CSPRNG.
* Phase 3: Service Layer: Implement the CipherInterface ABC, the CipherFactory, and the BenchmarkService.
* Phase 4: Presentation & Analysis: Hook the Service Layer into the argparse CLI and finalize MetricCollector visualization logic.

The architecture is now validated for Task 3 implementation, ensuring a secure, scientifically rigorous path forward for the Cryptography Testing Lab.
