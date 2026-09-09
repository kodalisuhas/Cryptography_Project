# DEEP RESEARCH REPORT: ANALYSIS SYSTEM

## Task — Analysis System for AES Cryptography Project

---

## 1. EXECUTIVE SUMMARY

The Analysis System is the second major component of the cryptography project, following the successful completion of the AES Core Engine (Task 1.2). Its purpose is to **measure, record, analyze, and visualize** the performance and security properties of the AES implementation.

The project's existing methodology (`docs/04_Methodology.md`) specifies the following key requirements:

| Requirement | Specification |
| :--- | :--- |
| **Encryption Time** | Measured in milliseconds (ms) |
| **Decryption Time** | Measured in milliseconds (ms) |
| **Throughput** | Measured in MB/s |
| **Memory Usage** | Measured in MB |
| **Warmup Iterations** | 2 iterations (unmeasured) |
| **Measured Iterations** | 5 iterations |
| **Outlier Detection** | IQR (Interquartile Range) method |
| **Graph Types** | Key size comparison, ECB vs CBC comparison, Throughput analysis |

**Critical Finding:** The existing project methodology specifies **5 measured iterations**. This is below the statistical minimum of **30 samples** recommended for basic performance comparisons. The project has two options: (a) treat this as a project-defined constraint and document the limitation, or (b) increase the iteration count to 30+ for statistical validity. This is an **Open Decision** that must be made before implementation.

---

## 2. EXISTING PROJECT REQUIREMENTS

Based on `docs/04_Methodology.md` and `docs/05_API_Interface_Spec.md`:

### Required (Explicitly Stated)

| Requirement | Source |
| :--- | :--- |
| Measure encryption time (ms) | `04_Methodology.md` |
| Measure decryption time (ms) | `04_Methodology.md` |
| Measure throughput (MB/s) | `04_Methodology.md` |
| Measure memory usage (MB) | `04_Methodology.md` |
| 2 warmup iterations | `04_Methodology.md` |
| 5 measured iterations | `04_Methodology.md` |
| IQR outlier removal | `04_Methodology.md` |
| Key size comparison graphs | `04_Methodology.md` |
| ECB vs CBC comparison graphs | `04_Methodology.md` |
| Throughput comparison graphs | `04_Methodology.md` |
| CSV export of metrics | `04_Methodology.md` |

### Recommended (Technically Defensible)

| Recommendation | Rationale |
| :--- | :--- |
| Use `time.perf_counter()` for timing | Highest available resolution, monotonic |
| Use `statistics` module for mean/median/std dev | Python standard library |
| Record environment information | Reproducibility |
| Use pandas for DataFrame storage | Efficient data handling |

### Optional / Future Extensions

| Extension | When to Consider |
| :--- | :--- |
| Chunked processing for large files | After basic benchmarking works |
| Memory profiling with `tracemalloc` | If memory becomes a concern |
| Confidence intervals | If statistical rigor is needed |

---

## 3. TIMING METHODOLOGY

### 3.1 Recommended Timer: `time.perf_counter()`

`time.perf_counter()` is the Python standard library's **highest-resolution monotonic timer**. It is:

- **Monotonic**: Cannot go backwards
- **Unaffected by system clock updates**
- **Includes sleep time**
- **System-wide**: Measures wall-clock time

Python's official documentation confirms: *"Return the value (in fractional seconds) of a performance counter, i.e. a clock with the highest available resolution to measure a short duration"*.

**Comparison with alternatives:**

| Function | Use Case | Resolution | Monotonic |
| :--- | :--- | :--- | :--- |
| `time.time()` | Business logs, long durations | Low | ❌ No |
| `time.perf_counter()` | **Code block measurement** | Highest | ✅ Yes |
| `time.process_time()` | CPU time only | High | ✅ Yes |
| `timeit` | **Repeatable micro-benchmarks** | High | ✅ Yes |

### 3.2 `perf_counter()` vs `timeit`

The project should use **`perf_counter()` directly** rather than `timeit` because:

| Aspect | `perf_counter()` | `timeit` |
| :--- | :--- | :--- |
| **Control** | Full control over iterations | Limited control |
| **Integration** | Easy to wrap in decorators | Separate API |
| **Flexibility** | Can measure any code block | Best for short snippets |
| **Overhead** | Minimal (~56 ns per call) | Slightly higher |

**Recommendation:** Use `perf_counter()` with a decorator pattern for flexibility and integration with the existing codebase.

### 3.3 Timing Implementation Pattern

```python
from time import perf_counter
from contextlib import contextmanager

@contextmanager
def timer():
    """Context manager for timing code blocks."""
    start = perf_counter()
    try:
        yield
    finally:
        elapsed = perf_counter() - start
        # Store or return elapsed time
```

This pattern ensures timing occurs even if exceptions are raised.

### 3.4 Warmup and Measurement Protocol

The project methodology specifies:
- **2 warmup iterations**: Discard results, allow CPU cache warmup, JIT optimization
- **5 measured iterations**: Record and analyze

**Academic note:** For statistically reliable results, 5 iterations is minimal. The benchmark community generally recommends at least 30 samples for basic comparisons. This is an **Open Decision** for the project team.

---

## 4. THROUGHPUT METHODOLOGY

### 4.1 Definition

**Throughput = Data Size (MB) / Time (seconds)**

### 4.2 Units

| Unit | Bytes | When to Use |
| :--- | :--- | :--- |
| **MB/s** (Megabytes per second) | 1,000,000 bytes | Industry standard for storage/network |
| **MiB/s** (Mebibytes per second) | 1,048,576 bytes | Memory/computer science contexts |

**Recommendation:** Use **MB/s** (decimal) for consistency with industry benchmarks and project documentation.

### 4.3 Throughput Calculation

```
throughput_mbps = data_size_bytes / (elapsed_seconds * 1_000_000)
```

**Example:**
- Data size: 1,048,576 bytes (1 MiB)
- Encryption time: 0.045 seconds
- Throughput: 1,048,576 / (0.045 × 1,000,000) = **23.3 MB/s**

### 4.4 Per-Iteration vs Aggregate

Two approaches:

| Approach | Method | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Per-iteration** | Calculate throughput for each run | Captures variance | More computation |
| **Aggregate** | Use mean time for all runs | Simpler | Loses variance info |

**Recommendation:** Calculate per-iteration throughput, then report mean, median, and standard deviation.

---

## 5. MEMORY MEASUREMENT METHODOLOGY

### 5.1 Available Approaches

| Tool | What It Measures | Overhead | Platform | Pros | Cons |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`psutil`** | Process RSS (Resident Set Size) | Low | Cross-platform | Simple, fast | Measures entire process, not Python objects |
| **`memory_profiler`** | Line-by-line memory | Medium | Cross-platform | Detailed, decorator support | Overhead, external dependency |
| **`tracemalloc`** | Python allocation tracking | Low | Python 3.4+ | Standard library, accurate | No real-time monitoring |

### 5.2 Approach Comparison

**`psutil`** reports memory usage of the **entire process** including Python objects, native extensions, and system resources.

**`memory_profiler`** uses line-by-line analysis to calculate memory usage of each line of code.

**`tracemalloc`** tracks memory allocations directly from the Python interpreter, resulting in lower reported memory usage.

### 5.3 Recommendation for This Project

| Criteria | Decision |
| :--- | :--- |
| **Primary Tool** | `psutil` |
| **Why** | Simple, cross-platform, low overhead, measures what users care about (total process memory) |
| **Alternative** | `memory_profiler` for detailed line-by-line analysis if needed |
| **Not Recommended** | `tracemalloc` for this use case (too detailed for summary metrics) |

**Important Note:** Different tools report different values for the same code. The project should **document which tool is used** and use it consistently for all measurements.

### 5.4 Memory Measurement Pattern

```python
import psutil
import os

def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # RSS in MB
```

---

## 6. STATISTICAL METHODOLOGY

### 6.1 Required Statistics

From the project methodology (`docs/04_Methodology.md`):

| Statistic | Purpose | How to Calculate |
| :--- | :--- | :--- |
| **Mean** | Average value | `statistics.mean(times)` |
| **Median** | Middle value (robust) | `statistics.median(times)` |
| **Standard Deviation** | Measure of spread | `statistics.stdev(times)` |
| **Min/Max** | Range | `min(times)`, `max(times)` |

### 6.2 Outlier Detection: IQR Method

The project methodology specifies the **IQR (Interquartile Range) method**:

```
Q1 = 25th percentile
Q3 = 75th percentile
IQR = Q3 - Q1
Lower Bound = Q1 - 1.5 × IQR
Upper Bound = Q3 + 1.5 × IQR

Outlier = Value < Lower Bound OR Value > Upper Bound
```

**Implementation:**

```python
import numpy as np

def detect_outliers(times: list) -> list:
    """Return indices of outliers using IQR method."""
    q25, q75 = np.percentile(times, [25, 75])
    iqr = q75 - q25
    lower = q25 - 1.5 * iqr
    upper = q75 + 1.5 * iqr
    return [i for i, t in enumerate(times) if t < lower or t > upper]
```

### 6.3 Filtering Order

**Recommended order:**

1. Collect all 5 measurements
2. Detect outliers using IQR
3. Remove outliers
4. Calculate statistics on remaining data

**Critical Note:** With only 5 samples, IQR outlier detection has limited statistical power. This should be documented as a limitation of the project methodology.

### 6.4 Sample Size Limitation

The benchmark community recommends:

| Confidence Level | Minimum Samples |
| :--- | :--- |
| Basic comparison | **30** |
| Percentile reporting (P95) | 100 |
| Publication-quality | 1,000+ |

**Project Reality:** 5 samples is far below statistical minimums. This is an **Open Decision** — the team must decide whether to:

1. Accept the limitation and document it
2. Increase iterations to 30+ for statistical validity
3. Use a hybrid approach (5 iterations per run, multiple runs)

---

## 7. DATA COLLECTION DESIGN

### 7.1 Required Fields

| Field | Type | Description | Source |
| :--- | :--- | :--- | :--- |
| `algorithm` | str | "AES" | Project requirement |
| `key_size` | int | 128, 192, 256 | Project requirement |
| `mode` | str | "ECB", "CBC" | Project requirement |
| `operation` | str | "encrypt", "decrypt" | Project requirement |
| `data_size_bytes` | int | Plaintext size | Required for throughput |
| `elapsed_time_ms` | float | Execution time | Measured |
| `throughput_mbps` | float | Calculated | Derived |
| `memory_usage_mb` | float | Process memory | Measured |
| `iteration` | int | 1-5 (or more) | Required for statistics |
| `timestamp` | str | ISO format | For reproducibility |

### 7.2 Optional Fields (Recommended)

| Field | Type | Purpose |
| :--- | :--- | :--- |
| `python_version` | str | Reproducibility |
| `cryptography_version` | str | Reproducibility |
| `os` | str | Reproducibility |
| `hardware` | str | Reproducibility |
| `session_id` | str | Group results |

---

## 8. CSV DESIGN

### 8.1 Recommended CSV Structure

```csv
timestamp,session_id,algorithm,key_size,mode,operation,data_size_bytes,iteration,elapsed_time_ms,throughput_mbps,memory_usage_mb,python_version,cryptography_version,os,hardware
2026-09-08T10:30:00,20260908_001,AES,256,CBC,encrypt,1024,1,0.234,4.37,28.5,3.11.0,42.0.0,Windows11,Intel_i7
2026-09-08T10:30:01,20260908_001,AES,256,CBC,encrypt,1024,2,0.228,4.49,28.5,3.11.0,42.0.0,Windows11,Intel_i7
```

### 8.2 Export Implementation

```python
import pandas as pd

def export_to_csv(metrics: list, filepath: str):
    """Export metrics to CSV using pandas."""
    df = pd.DataFrame(metrics)
    df.to_csv(filepath, index=False)
```

### 8.3 Storage Location

Per project structure: `results/csv/metrics_YYYYMMDD.csv`

---

## 9. GRAPH DESIGN

### 9.1 Key Size Comparison

| Aspect | Specification |
| :--- | :--- |
| **Chart Type** | Bar chart (side-by-side) |
| **X-axis** | Key Size (128, 192, 256) |
| **Y-axis** | Encryption Time (ms) |
| **Groups** | ECB vs CBC (side-by-side bars) |
| **Labels** | Include values on bars |
| **Title** | "AES Encryption Time by Key Size and Mode" |

### 9.2 ECB vs CBC Comparison

| Aspect | Specification |
| :--- | :--- |
| **Chart Type** | Bar chart or grouped bar chart |
| **X-axis** | Mode (ECB, CBC) |
| **Y-axis** | Encryption Time (ms) |
| **Groups** | By key size |
| **Title** | "ECB vs CBC Performance Comparison" |

### 9.3 Throughput Analysis

| Aspect | Specification |
| :--- | :--- |
| **Chart Type** | Line chart or bar chart |
| **X-axis** | Data Size (KB/MB) |
| **Y-axis** | Throughput (MB/s) |
| **Lines** | Each key size/mode combination |
| **Title** | "AES Throughput by Data Size" |

### 9.4 Graph Generation Pattern

```python
import matplotlib.pyplot as plt
import pandas as pd

def generate_key_size_comparison(df: pd.DataFrame, output_path: str):
    """Generate key size comparison bar chart."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Group by key_size and mode, calculate mean
    grouped = df.groupby(['key_size', 'mode'])['elapsed_time_ms'].mean().unstack()
    grouped.plot(kind='bar', ax=ax)
    
    ax.set_xlabel('Key Size (bits)')
    ax.set_ylabel('Encryption Time (ms)')
    ax.set_title('AES Encryption Time by Key Size and Mode')
    ax.legend(title='Mode')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
```

---

## 10. SECURITY ANALYSIS METHODOLOGY

### 10.1 ECB Pattern Leakage (ECB Penguin)

**Concept:** ECB mode encrypts identical plaintext blocks to identical ciphertext blocks, revealing patterns.

**Methodology:**
1. Load a test image (from `assets/images/penguin.png`)
2. Encrypt the image using AES-ECB
3. Save the encrypted data as an image
4. Visually compare original vs encrypted

**What to Measure:**
- Visual pattern preservation (qualitative)
- Optional: Quantitative block similarity analysis

**Project Requirement:** This is explicitly mentioned in the project plan as a key demonstration.

### 10.2 Avalanche Effect

**Concept:** Changing 1 bit of input should change ~50% of output bits.

**Methodology:**
1. Encrypt a known plaintext with a known key
2. Flip 1 bit in the plaintext
3. Encrypt the modified plaintext with the same key
4. Calculate Hamming distance between ciphertexts
5. Avalanche % = (Bits Changed / Total Bits) × 100

**Expected Result:** ~50% (±5%)

### 10.3 Key Sensitivity

**Concept:** Changing 1 bit of the key should completely change the output.

**Methodology:**
1. Generate two keys differing by 1 bit
2. Encrypt the same plaintext with both keys
3. Calculate Hamming distance between ciphertexts

**Expected Result:** ~50% (±5%)

---

## 11. ARCHITECTURE / MODULE BOUNDARIES

### 11.1 Layer Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYSIS SYSTEM ARCHITECTURE                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  src/utils/padding.py          ← Utility Layer                 │
│         ↓                                                       │
│  src/core/aes_cipher.py        ← Core Layer                    │
│         ↓                                                       │
│  src/analyzers/                ← Analysis Layer                │
│  ├── performance_timer.py      ← Timing (decorators)           │
│  ├── metric_collector.py       ← Data collection               │
│  ├── security_evaluator.py     ← Security tests                │
│  └── graph_generator.py        ← Visualization                 │
│         ↓                                                       │
│  results/                      ← Persistence Layer             │
│  ├── csv/                      ← Raw data                      │
│  ├── graphs/                   ← Visualizations                │
│  ├── logs/                     ← Execution logs                │
│  └── demo_outputs/             ← Demo outputs                  │
│                                                                 │
│  src/cli/                      ← Presentation Layer (future)   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 11.2 Module Separation

| Module | Responsibility | Depends On |
| :--- | :--- | :--- |
| `performance_timer.py` | Measure execution time | None |
| `metric_collector.py` | Store and export metrics | pandas, `performance_timer.py` |
| `security_evaluator.py` | Security analysis | `aes_cipher.py`, `padding.py` |
| `graph_generator.py` | Create visualizations | matplotlib, pandas |

---

## 12. ERROR HANDLING

| Scenario | Handling |
| :--- | :--- |
| Invalid algorithm configuration | Raise `ValueError` |
| Invalid key size | Raise `ValueError` |
| Invalid mode | Raise `ValueError` |
| Invalid plaintext | Raise `ValueError` |
| Failed encryption/decryption | Re-raise underlying exception |
| Insufficient benchmark data | Raise `ValueError` or use available data with warning |
| Empty dataset | Raise `ValueError` |
| CSV export failure | Raise `OSError` with path information |
| Graph generation failure | Log error, continue |

**Critical Rule:** The analysis layer must **never silently swallow** cryptographic failures. All exceptions from the AES engine should propagate.

---

## 13. REPRODUCIBILITY

### 13.1 What to Record

| Field | Required? | Why |
| :--- | :--- | :--- |
| Python version | ✅ Required | Different Python versions affect performance |
| Cryptography version | ✅ Required | Library versions affect performance |
| Operating System | ✅ Required | OS affects system calls, scheduling |
| Timestamp | ✅ Required | For experiment tracking |
| Key/IV used | 🔴 NOT RECOMMENDED | Security risk (keys are sensitive) |
| Hardware | 🟡 Recommended | CPU affects performance |
| Iteration count | ✅ Required | For statistical context |
| Warmup count | ✅ Required | For statistical context |

### 13.2 Recording Pattern

```python
import sys
import platform
import cryptography

def get_environment_info() -> dict:
    """Collect environment information for reproducibility."""
    return {
        'python_version': sys.version,
        'cryptography_version': cryptography.__version__,
        'os': platform.platform(),
        'hardware': platform.processor() or 'Unknown'
    }
```

---

## 14. TEST REQUIREMENTS

### 14.1 Performance Timer Tests

| Test | Description | Expected |
| :--- | :--- | :--- |
| `test_timer_measures_time` | Timer returns positive value | > 0 |
| `test_timer_units` | Timer returns seconds | Float |
| `test_warmup_behavior` | Warmup runs don't affect results | Correct iteration count |
| `test_invalid_config` | Invalid config raises error | `ValueError` |

### 14.2 Metric Collector Tests

| Test | Description | Expected |
| :--- | :--- | :--- |
| `test_metric_storage` | Metrics stored correctly | DataFrame has rows |
| `test_statistics_calculation` | Mean, median, std dev calculated | Correct values |
| `test_csv_export` | CSV file created | File exists |

### 14.3 Security Evaluator Tests

| Test | Description | Expected |
| :--- | :--- | :--- |
| `test_avalanche_calculation` | Avalanche percentage | ~50% |
| `test_key_sensitivity` | Key change affects output | ~50% |
| `test_ecb_demo` | ECB demo runs without error | Output files created |

### 14.4 Graph Generator Tests

| Test | Description | Expected |
| :--- | :--- | :--- |
| `test_graph_creation` | Graph file created | PNG exists |
| `test_empty_dataset` | Empty dataset handled | Graceful error |
| `test_invalid_dataset` | Invalid dataset handled | Graceful error |

---

## 15. RECOMMENDED ANALYSIS-SYSTEM WORKFLOW

```
┌─────────────────────────────────────────────────────────────────┐
│              ANALYSIS SYSTEM WORKFLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Configure Benchmark                                    │
│  └── Algorithm, key sizes, modes, iterations                   │
│                                                                 │
│  Step 2: Warmup (2 iterations, unmeasured)                     │
│  └── Discard results                                           │
│                                                                 │
│  Step 3: Measure (5+ iterations, recorded)                     │
│  └── For each iteration:                                       │
│      ├── Start timer (perf_counter)                            │
│      ├── Execute operation (encrypt/decrypt)                   │
│      ├── Stop timer                                            │
│      ├── Measure memory (psutil)                               │
│      └── Store metrics                                         │
│                                                                 │
│  Step 4: Calculate Statistics                                  │
│  ├── Mean, median, standard deviation                          │
│  ├── Detect outliers (IQR)                                     │
│  └── Remove outliers, recalculate                              │
│                                                                 │
│  Step 5: Export                                                │
│  ├── CSV to results/csv/                                       │
│  └── Graphs to results/graphs/                                 │
│                                                                 │
│  Step 6: Security Analysis (if requested)                      │
│  ├── Avalanche effect                                          │
│  ├── Key sensitivity                                           │
│  └── ECB Penguin demo                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 16. OPEN DECISIONS / AMBIGUITIES

| # | Decision | Options | Recommendation |
| :--- | :--- | :--- | :--- |
| 1 | **Iteration Count** | 5 (project requirement) vs 30+ (statistical minimum) | **Accept 5 but document limitation** OR **Increase to 30+** |
| 2 | **Memory Measurement** | psutil vs memory_profiler vs tracemalloc | **Use psutil** (simple, cross-platform) |
| 3 | **Statistical Treatment** | IQR outlier removal before or after stats calculation | **Remove outliers first, then calculate stats** |
| 4 | **Graph Types** | Bar charts vs line charts | **Bar charts for categorical comparisons, line charts for continuous data** |
| 5 | **ECB Penguin** | Qualitative vs quantitative analysis | **Qualitative (visual) is sufficient** |
| 6 | **Memory Overhead** | Include/exclude from benchmarks | **Record memory usage separately** (not as part of time measurement) |
| 7 | **CSV Fields** | Which fields to include | **Include all fields listed in Section 7** |
| 8 | **Time Unit** | Milliseconds vs seconds | **Milliseconds** (more readable for short operations) |

---

## 17. FINAL RECOMMENDATION

### Implementation Sequence

| Order | Module | Priority | Dependencies |
| :--- | :--- | :--- | :--- |
| 1 | **Performance Timer** (`performance_timer.py`) | HIGH | None |
| 2 | **Metric Collector** (`metric_collector.py`) | HIGH | Performance Timer |
| 3 | **Security Evaluator** (`security_evaluator.py`) | MEDIUM | AES, Padding |
| 4 | **Graph Generator** (`graph_generator.py`) | MEDIUM | Metric Collector |
| 5 | **Integration Tests** | HIGH | All above |

### Recommended Next Step

1. **Resolve Open Decision #1** (iteration count: 5 vs 30+)
2. **Update API specification** to include Analysis System interfaces
3. **Proceed with Performance Timer implementation**

---

## 18. SOURCES

| Source | Reference | Purpose |
| :--- | :--- | :--- |
| Python `time` module | `docs.python.org/3/library/time.html` | `perf_counter()` documentation |
| Python `timeit` module | `docs.python.org/3/library/timeit.html` | Alternative timing approach |
| `psutil` documentation | `pypi.org/project/psutil/` | Process memory measurement |
| `memory_profiler` | `pypi.org/project/memory-profiler/` | Line-by-line memory profiling |
| `tracemalloc` | Python standard library | Memory allocation tracking |
| Statistical Rigor Guide | GitHub armory | Sample size recommendations |
| NIST SP 800-38A | Block cipher modes | Mode performance context |
| Project Documentation | `docs/04_Methodology.md` | Primary requirements source |

---

**Report Status:** ✅ Complete  
**Ready for:** Team Review & Architectural Decision Making