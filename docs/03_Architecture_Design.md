# Architecture Design: Performance and Security Analysis of AES Encryption

## Why Layered Architecture?

1. **Clear separation of concerns:** Each architectural layer is strictly isolated, handling a single aspect of the system (e.g., interface, cipher execution, performance analysis, utility helpers, or file persistence).
2. **Easier debugging:** Issues within cryptographic logic, input validation, or metric aggregation can be isolated to individual modules without side effects cascading through the pipeline.
3. **Easier testing:** Layers and modules can be independently verified via unit tests and mock interfaces without requiring complete end-to-end runs.
4. **Better maintainability:** Code modifications or internal refactoring within one layer do not break contracts established with other layers.
5. **Easier team collaboration:** Multiple developers can work concurrently on distinct layers (such as core cipher algorithms vs. visualization graphing) without merge conflicts.
6. **Scalable for future algorithms:** Incorporating additional cryptographic schemes (e.g., ChaCha20, 3DES, or post-quantum algorithms) requires adding concrete implementations under the existing factory abstraction without altering user interface logic.

---

## 1. Introduction

This document describes the system architecture, design patterns, and module interactions for the Cryptographic Analysis System. The architecture follows **industry-standard layered design principles** to ensure:
- **Separation of Concerns:** Each layer has a specific responsibility
- **Maintainability:** Easy to modify and extend
- **Testability:** Each module can be tested independently
- **Scalability:** Easy to add new algorithms or features
- **Professional Grade:** Suitable for placement/interview discussion

---

## 2. High-Level Architecture Overview

**Architectural Style: Layered Architecture (N-Tier)**

```
┌──────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                      │
│                   (CLI / User Interface)                     │
│          main.py  |  menu.py  |  argument_parser.py          │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                         │
│             (Orchestration & Business Logic)                 │
│    cipher_factory.py | context_manager.py | cipher_interface │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                          CORE LAYER                          │
│                (Cryptographic Implementations)               │
│ aes_cipher.py | rsa_cipher.py | blowfish_cipher.py | classical│
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        ANALYSIS LAYER                        │
│             (Performance & Security Evaluation)              │
│ performance_timer.py | metric_collector.py | security_eval.  │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        UTILITY LAYER                         │
│              (Helper Functions & Infrastructure)             │
│ file_handler.py | key_generator.py | padding.py | validators │
│ formatters.py   | settings.py      | constants.py            │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                      PERSISTENCE LAYER                       │
│                    (Data Storage & Output)                   │
│   graph_generator.py (matplotlib) | CSV export | File I/O    │
│                        Results Storage                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Layer Details

### 3.1 Presentation Layer
**Purpose:** Handle all user interactions and command-line interface.

| Module | Responsibility | Key Functions |
| :--- | :--- | :--- |
| `main.py` | Entry point | `main()`, argument parsing |
| `menu.py` | Interactive menu | `show_menu()`, `handle_choice()` |
| `argument_parser.py` | CLI arguments | `parse_args()`, `validate_args()` |

**Flow:**
1. User runs `python main.py`
2. Menu displays options: Encrypt, Decrypt, Benchmark, Exit
3. User selects option
4. Input collected and validated
5. Passed to Service Layer

### 3.2 Service Layer (Business Logic)
**Purpose:** Orchestrate operations and provide a unified interface.

| Module | Responsibility | Key Functions |
| :--- | :--- | :--- |
| `cipher_interface.py` | Abstract Base Class | `encrypt()`, `decrypt()`, `get_metrics()` |
| `cipher_factory.py` | Algorithm instantiation | `get_cipher(algorithm, key_size, mode)` |
| `context_manager.py` | State management | `set_context()`, `get_context()` |

**Design Pattern: Factory Pattern**
```
User Request ──► Factory ────────► Cipher Instance
     │              │                     │
     ▼              ▼                     ▼
 Algorithm      Algorithm          Encrypt/Decrypt
Parameters      Selection             Operation
```

**Why Factory Pattern?**
- Decouples client code from concrete classes
- Centralizes object creation
- Easy to add new algorithms
- Single point of modification

### 3.3 Core Layer (Cryptographic Implementations)
**Purpose:** Implement actual cryptographic algorithms.

| Module | Responsibility | Key Functions |
| :--- | :--- | :--- |
| `aes_cipher.py` | AES encryption/decryption | `encrypt()`, `decrypt()`, `generate_key()` |
| `rsa_cipher.py` | RSA encryption/decryption | `generate_keypair()`, `encrypt()`, `decrypt()` |
| `blowfish_cipher.py` | Blowfish encryption/decryption | `encrypt()`, `decrypt()` |
| `classical_ciphers.py` | Caesar, Vigenere, etc. | `caesar_encrypt()`, `vigenere_encrypt()` |

**AES Module Details:**
```python
# Planned Interface
class AESCipher:
    def __init__(self, key_size: int, mode: str):
        self.key_size = key_size  # 128, 192, 256
        self.mode = mode          # 'ECB', 'CBC'
        self.key = None
        self.iv = None
    
    def generate_key(self) -> bytes:
        """Generate random key of specified size"""
        
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt with AES in specified mode"""
        
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt with AES in specified mode"""
        
    def generate_iv(self) -> bytes:
        """Generate random IV (for CBC mode)"""
```

### 3.4 Analysis Layer
**Purpose:** Measure and evaluate performance and security.

| Module | Responsibility | Key Functions |
| :--- | :--- | :--- |
| `performance_timer.py` | Timing decorators | `@timer`, `@measure_time` |
| `metric_collector.py` | Metrics collection | `collect_metrics()`, `export_to_csv()` |
| `security_evaluator.py` | Security analysis | `check_ecb_weakness()`, `avalanche_effect()` |

**Performance Timer Decorator Pattern:**
```python
# Planned Interface
def measure_time(func):
    """Decorator to measure execution time"""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        return result, elapsed_ms
    return wrapper
```

**Metrics Collected:**

| Metric | Unit | Collection Method |
| :--- | :--- | :--- |
| **Encryption Time** | milliseconds | `time.perf_counter()` |
| **Decryption Time** | milliseconds | `time.perf_counter()` |
| **Throughput** | MB/s | Data Size / Time |
| **Memory Usage** | MB | `memory_profiler` (optional) |

### 3.5 Utility Layer
**Purpose:** Provide helper functions and infrastructure support.

| Module | Responsibility | Key Functions |
| :--- | :--- | :--- |
| `file_handler.py` | File operations | `read_file()`, `write_file()`, `chunk_reader()` |
| `key_generator.py` | Key generation | `generate_aes_key()`, `generate_rsa_keypair()` |
| `padding.py` | PKCS#7 padding | `pad()`, `unpad()` |
| `validators.py` | Input validation | `validate_key_size()`, `validate_mode()` |
| `formatters.py` | Data formatting | `to_hex()`, `to_base64()`, `to_binary()` |
| `settings.py` | Configuration | Load settings, constants |
| `constants.py` | Constants | Algorithm names, key sizes, modes |

### 3.6 Persistence Layer
**Purpose:** Save and export results.

| Module | Responsibility | Key Functions |
| :--- | :--- | :--- |
| `graph_generator.py` | Graph creation | `generate_graph()`, `save_graph()` |
| **CSV Export** | Data export | `export_to_csv()` |
| **File I/O** | File operations | Save encrypted files, results |

**Graph Types to Generate:**

| Graph | Purpose | X-axis | Y-axis |
| :--- | :--- | :--- | :--- |
| **Key Size Comparison** | Show performance impact | Key Size (128/192/256) | Time (ms) |
| **Mode Comparison** | ECB vs CBC speed | Mode (ECB/CBC) | Time (ms) |
| **Throughput Analysis** | Data processing speed | File Size (MB) | Throughput (MB/s) |
| **Avalanche Effect** | Security demonstration | Bit Change | Avalanche % |

---

## 4. Data Flow Diagrams

### 4.1 Encryption Flow

```
┌─────────────────────────────────────────┐
│          User Input Plaintext           │
│           Algorithm Key Size            │
│                  Mode                   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│              SERVICE LAYER              │
│          1. Validate Input              │
│          2. Get Cipher from Factory     │
│          3. Pass to Core Layer          │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│               CORE LAYER                │
│       1. Generate Key (if not provided) │
│       2. Generate IV (if CBC mode)      │
│       3. Pad Plaintext (PKCS#7)         │
│       4. Encrypt Data                   │
│       5. Return Ciphertext              │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│             ANALYSIS LAYER              │
│       1. Measure Execution Time         │
│       2. Record Metrics                 │
│       3. Log to CSV                     │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│           PRESENTATION LAYER            │
│       1. Format Output (Hex/Base64)     │
│       2. Display to User                │
│       3. Save to File (if requested)    │
└─────────────────────────────────────────┘
```

### 4.2 Decryption Flow

```
┌─────────────────────────────────────────┐
│         User Input Ciphertext           │
│           Algorithm Key Size            │
│                  Mode                   │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│              SERVICE LAYER              │
│          1. Validate Input              │
│          2. Get Cipher from Factory     │
│          3. Pass to Core Layer          │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│               CORE LAYER                │
│          1. Decrypt Ciphertext          │
│          2. Unpad Plaintext (PKCS#7)    │
│          3. Return Plaintext            │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│             ANALYSIS LAYER              │
│       1. Measure Execution Time         │
│       2. Record Metrics                 │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│           PRESENTATION LAYER            │
│       1. Display Decrypted Text         │
│       2. Save to File (if requested)    │
└─────────────────────────────────────────┘
```

### 4.3 Benchmark/Analysis Flow

```
┌─────────────────────────────────────────┐
│               User Select               │
│             Benchmark Mode              │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│             ANALYSIS LAYER              │
│       1. Load Configuration             │
│       2. Set Test Parameters            │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│            PERFORMANCE LOOP             │
│  For each configuration (key_size x mode)│
│  1. Generate Test Data                  │
│  2. Warmup (avoid cold-start)           │
│  3. Run Encryption N times (N-iter)     │
│  4. Record Times                        │
│  5. Calculate Statistics (mean, median) │
│  6. Store Metrics                       │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│           RESULTS GENERATION            │
│       1. Create DataFrames (pandas)     │
│       2. Export to CSV                  │
│       3. Generate Graphs (matplotlib)   │
│       4. Save Images                    │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│           PRESENTATION LAYER            │
│       1. Display Summary                │
│       2. Show Graph File Paths          │
│       3. Display Statistics (tabulate)  │
└─────────────────────────────────────────┘
```

---

## 5. Design Patterns Used

| Pattern | Where Used | Why |
| :--- | :--- | :--- |
| **Factory Pattern** | `cipher_factory.py` | Create cipher instances dynamically |
| **Abstract Base Class (ABC)** | `cipher_interface.py` | Enforce uniform interface for all ciphers |
| **Decorator Pattern** | `performance_timer.py` | Add timing to functions without modifying them |
| **Strategy Pattern** | `cipher_interface.py` | Swap algorithms at runtime |
| **Singleton Pattern** | `context_manager.py` | Maintain single global state |
| **Observer Pattern** | `metric_collector.py` | Collect and log metrics during operations |

---

## 6. Module Dependencies

```
┌──────────────────────────────────────────────────────────────┐
│                     EXTERNAL DEPENDENCIES                    │
│ cryptography | matplotlib | pandas | numpy | pytest | tabulate│
│                            pyyaml                            │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                        UTILITY LAYER                         │
│ file_handler.py | validators.py | constants.py               │
│ key_generator.py | formatters.py | padding.py | settings.py  │
└──────┬───────────────────────┬────────────────────────┬──────┘
       │                       │                        │
       ▼                       ▼                        ▼
┌──────────────┐       ┌──────────────┐        ┌──────────────┐
│  CORE LAYER  │       │ANALYSIS LAYER│        │SERVICE LAYER │
│aes_cipher.py │       │perf_timer.py │        │cipher_intf.py│
│rsa_cipher.py │       │metric_coll.py│        │cipher_fact.py│
│blowfish.py   │       │sec_eval.py   │        │context_mgr.py│
│classical.py  │       └──────┬───────┘        └──────┬───────┘
└──────┬───────┘              │                       │
       │                      │                       │
       └──────────────────────┼───────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                      │
│             main.py  |  menu.py  |  argument_parser.py       │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. Sequence Diagrams

### 7.1 Encryption Sequence

```
User          CLI            Factory         AESCipher          Timer        FileHandler
 │             │                │                │                │               │
 ├────────────►│                │                │                │               │
 │ 1. Select   │                │                │                │               │
 │ Encrypt Type│                │                │                │               │
 │             ├───────────────►│                │                │               │
 │             │ 2. get_cipher  │                │                │               │
 │             │                ├───────────────►│                │               │
 │             │                │ 3. Create Inst │                │               │
 │             │◄───────────────┤                │                │               │
 │             │ Return Instance│                │                │               │
 │             │                │                │                │               │
 │             ├────────────────────────────────►│                │               │
 │             │ 4. encrypt(plaintext)          │                │               │
 │             │                │                ├───────────────►│               │
 │             │                │                │ 5. Start timer │               │
 │             │                │                │                │               │
 │             │                │                │ 6. pad plaintext               │
 │             │                │                │                │               │
 │             │                │                │ 7. encrypt     │               │
 │             │                │                │                ├──────────────►│
 │             │                │                │                │ 8. Save file  │
 │             │                │                │◄───────────────┤               │
 │             │                │                │ 9. Stop timer  │               │
 │             │◄────────────────────────────────┤                │               │
 │             │ Cipher Text    │                │                │               │
 │◄────────────┤                │                │                │               │
 │ Display res │                │                │                │               │
```

---

## 8. Error Handling Strategy

### 8.1 Exception Hierarchy

```
Exception
   ├── CryptographyError (Base)
   │   ├── InvalidKeyError
   │   │     ├── InvalidKeySizeError
   │   │     └── InvalidKeyFormatError
   │   ├── InvalidModeError
   │   ├── PaddingError
   │   ├── DecryptionError
   │   └── AlgorithmNotSupportedError
   ├── FileError
   │     ├── FileNotFoundError
   │     └── FilePermissionError
   └── ValidationError
         ├── InvalidInputError
         └── ParameterError
```

### 8.2 Error Handling Flow

```
┌─────────────────────────────────────────┐
│               User Input                │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│            1. Validate Input            │
│         - Check algorithm supported     │
│         - Check key size valid          │
│         - Check mode valid              │
│         - Check file exists (if file in)│
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│            2. Try Operation             │
│         - Attempt encryption/decryption │
│         - Catch specific exceptions     │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│            3. Handle Errors             │
│         - Log error with traceback      │
│         - Display user-friendly message │
│         - Suggest fix (if possible)     │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│         4. Return to Menu / Exit        │
│    - On success: Show result            │
│    - On failure: Show error message,    │
│      return to menu                     │
└─────────────────────────────────────────┘
```

---

## 9. Configuration Management

### 9.1 Settings Structure (`src/config/settings.py`)

```python
# Planned Configuration Structure
class Settings:
    # Algorithms
    SUPPORTED_ALGORITHMS = ['AES', 'RSA', 'Blowfish', 'Classical']
    
    # Key sizes
    AES_KEY_SIZES = [128, 192, 256]
    RSA_KEY_SIZES = [1024, 2048, 4096]
    
    # Modes
    SUPPORTED_MODES = ['ECB', 'CBC']
    
    # Default values
    DEFAULT_ALGORITHM = 'AES'
    DEFAULT_KEY_SIZE = 256
    DEFAULT_MODE = 'CBC'
    
    # Benchmark
    BENCHMARK_ITERATIONS = 30
    BENCHMARK_WARMUP_ITERATIONS = 5
    
    # Paths
    DATA_DIR = 'data/'
    RESULTS_DIR = 'results/'
    GRAPHS_DIR = 'results/graphs/'
    CSV_DIR = 'results/csv/'
    LOGS_DIR = 'results/logs/'
    DEMO_OUTPUTS_DIR = 'results/demo_outputs/'
    
    # File formats
    ENCRYPTED_FILE_EXTENSION = '.enc'
    KEY_FILE_EXTENSION = '.key'
    IV_FILE_EXTENSION = '.iv'
```

### 9.2 Constants (`src/config/constants.py`)

```python
# Planned Constants
class Constants:
    BLOCK_SIZE = 16  # AES block size in bytes
    PKCS7_PATTERN = b'\x04\x04\x04\x04'
    MAX_CHUNK_SIZE = 1024 * 1024  # 1MB chunks for large files
    
    # Messages
    SUCCESS_MSG = "✓ Operation completed successfully"
    ERROR_MSG = "✗ Error occurred: "
    INFO_MSG = "ℹ Information: "
    WARNING_MSG = "⚠ Warning: "
```

---

## 10. Performance Considerations

| Aspect | Strategy |
| :--- | :--- |
| **Large Files** | Process in chunks to avoid memory overflow |
| **Repeated Operations** | Cache keys and configurations |
| **Benchmark Accuracy** | Multiple iterations, remove outliers |
| **Cold Start** | Warmup iterations before measuring |
| **Timing Precision** | Use `time.perf_counter()` for microsecond precision |

---

## 11. Security Considerations

| Aspect | Strategy |
| :--- | :--- |
| **Key Management** | Keys stored in memory, never logged |
| **IV Randomness** | Use `os.urandom()` for IV generation |
| **Padding** | Use PKCS#7 standard padding |
| **Input Sanitization** | Validate all inputs before processing |
| **Error Messages** | Generic error messages (no sensitive info) |

---

## 12. Technology Stack Justification

| Component | Choice | Justification |
| :--- | :--- | :--- |
| **Python** | Primary language | Industry standard for cryptography |
| **cryptography** | Crypto library | Battle-tested, FIPS-compliant |
| **matplotlib** | Graph generation | Standard, extensive documentation |
| **pandas** | Data analysis | CSV export, data manipulation |
| **pytest** | Testing | Professional testing framework |
| **Git** | Version control | Industry standard |

---

## 13. Architecture Quality Attributes

| Attribute | How We Achieve It |
| :--- | :--- |
| **Modularity** | Each layer has specific responsibility |
| **Reusability** | Utility functions can be reused |
| **Testability** | Each module can be unit tested |
| **Maintainability** | Clear separation of concerns |
| **Scalability** | Easy to add new algorithms |
| **Performance** | Efficient algorithms, chunked processing |
| **Security** | Industry-standard crypto libraries |
| **Usability** | Simple CLI interface |

---

## 14. Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        LOCAL MACHINE                         │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                   Python Environment (venv)                  │
│  ┌──────────────────┬──────────────────┬──────────────────┐  │
│  │ Application Code │   Dependencies   │  Configuration   │  │
│  └──────────────────┴──────────────────┴──────────────────┘  │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                         File System                          │
│  ┌──────────┬─────────────┬──────────────┬────────────────┐  │
│  │   data   │   results   │   reports    │   benchmarks   │  │
│  └──────────┴─────────────┴──────────────┴────────────────┘  │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                     Git (Version Control)                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Recommendations & Architecture Improvements

The following architectural refinements are structured based on the major review points and critical examination feedback to ensure technical precision, defendability during viva evaluation, and clean code separation:

1. **Reconcile `graph_generator.py` Location in Project Layout**
   - **Explanation:** In the current directory layout, `graph_generator.py` is referenced under Persistence/Analysis but missing from `src/analyzers/`.
   - **Recommendation:** Place `graph_generator.py` explicitly inside `src/analyzers/graph_generator.py` (**Option A**), delegating visual rendering to the analysis pipeline while the persistence layer handles raw file writes.
   - **Benefit:** Maintains a strict separation of concerns between computational visualization logic and physical disk I/O.

2. **Clarify and Re-scope the Persistence Layer**
   - **Explanation:** The current diagram lists generic tasks like `File I/O` and `CSV export` as modules rather than concrete persistence responsibilities.
   - **Recommendation:** Formally define the Persistence Layer as the repository handler responsible for:
     - Saving encrypted and decrypted payloads to disk
     - Writing structured CSV metrics tables
     - Exporting rendered PNG benchmark plots
     - Managing benchmark logs and demo run outputs
   - **Benefit:** Eliminates ambiguity and gives the Persistence Layer a well-defined architectural role.

3. **Adopted Benchmark Iteration Thresholds**
   - **Explanation:** Initial baseline of 5 measured and 2 warmup runs was too low to produce statistically reliable measurements.
   - **Resolution:** Updated the defaults in `config/settings.py` to match the selected experimental methodology:
     - `BENCHMARK_ITERATIONS = 30`
     - `BENCHMARK_WARMUP_ITERATIONS = 5`
   - **Benefit:** Ensures performance data generated by the Analysis Layer is mathematically defensible and academically valid.

4. **Define Timing Boundary for Encryption Pipeline**
   - **Explanation:** In the sequence diagram, `pad plaintext` occurs after starting the timer. Measuring padding alongside cipher computation conflates preprocessing overhead with raw algorithm execution.
   - **Recommendation:** Formally designate that the timer measures the **entire end-to-end encryption pipeline** (Padding + Encryption) because total latency represents real-world user throughput. Document this distinction explicitly in the methodology report.
   - **Benefit:** Clearly justifies benchmark methodology when explaining metrics during project defense.

5. **Prune Unimplemented Design Patterns (Singleton and Observer)**
   - **Explanation:** Claiming patterns like Singleton (for `context_manager.py`) or Observer (for `metric_collector.py`) without full publish/subscribe or strict instance restrictions invites difficult examiner questions.
   - **Recommendation:** Restrict the documented patterns strictly to those actively implemented in the code:
     - Keep: **Factory Pattern**, **Abstract Base Class (ABC)**, **Decorator Pattern**, and **Strategy Pattern**.
     - Remove: **Singleton Pattern** and **Observer Pattern** (unless concrete pub/sub classes are coded).
   - **Benefit:** Prevents viva disqualifications and ensures all declared design patterns can be directly demonstrated in code.

6. **Streamline Exception Hierarchy for Project Scope**
   - **Explanation:** An overly nested 12-exception hierarchy introduces unnecessary code bloat for a laboratory evaluation tool.
   - **Recommendation:** Simplify the active exception hierarchy to three primary core base classes:
     - `CryptographyError` (with subclasses `InvalidKeyError`, `InvalidModeError`, `PaddingError`, `DecryptionError`)
     - `ValidationError` (with `InvalidInputError`)
     - `FileError` (with `FileNotFoundError`)
   - **Benefit:** Retains comprehensive error handling while keeping the implementation clean and maintainable.

7. **Document IV Generation Exclusivity for CBC Mode**
   - **Explanation:** Initializing an Initialization Vector (IV) is only relevant for block chaining modes.
   - **Recommendation:** Explicitly document in the AES module specifications that:
     > *The IV (`Initialization Vector`) is strictly generated and utilized for CBC mode; ECB mode operates without an IV.*
   - **Benefit:** Directly addresses a standard viva examination checkpoint regarding block cipher mode behavior.

8. **Mandate Cryptographically Secure Random Number Generators (CSPRNG)**
   - **Explanation:** Basic random generators produce predictable sequences that invalidate cryptographic benchmarking security.
   - **Recommendation:** Explicitly mandate in the Security Considerations section that all keys and IVs are generated using `os.urandom()` or the `secrets` module.
   - **Benefit:** Complies with NIST and FIPS cryptographic standards.

9. **Incorporate Extensibility into Architecture Quality Attributes**
   - **Explanation:** Demonstrating that new algorithms can be plugged in without modifying existing client code is an essential quality attribute.
   - **Recommendation:** Add `Extensibility` to Section 13:
     - *Attribute:* **Extensibility**
     - *Achievement:* New symmetric/asymmetric algorithms can be integrated by extending `CipherInterface` and updating `CipherFactory` without modifying core presentation or pipeline modules.
   - **Benefit:** Emphasizes software engineering excellence and modularity to examiners.
