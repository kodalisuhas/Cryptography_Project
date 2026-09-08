# Methodology: Performance and Security Analysis of AES Encryption

## Threats to Validity

| Threat | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Background Processes** | Timing noise and CPU cycle preemption | Close unnecessary applications; conduct isolated benchmark runs |
| **Different CPUs / Hardware** | Discrepancies in absolute runtime metrics across machines | Report normalized comparisons, throughput ratios, and document exact hardware specs |
| **Python Interpreter Overhead** | Minor timing inaccuracies and interpreter runtime variance | Utilize `time.perf_counter()` for nanosecond precision; run warmup rounds |
| **OS Scheduling & Interrupts** | Non-deterministic latency spikes from kernel thread preemption | Execute high iteration counts ($N \ge 50$) and analyze median/mean values |

---

## 1. Introduction

This document describes the **methodology** for measuring, analyzing, and evaluating cryptographic performance and security. It explains:
- How we measure encryption/decryption time
- How we calculate throughput
- How we analyze security properties
- How we ensure accurate and reproducible results
- How we handle different data sizes and configurations

> **Core Philosophy:** *"If you can't measure it, you can't improve it."* – All decisions about encryption configurations should be backed by data.

---

## 2. Performance Measurement Methodology

### 2.1 Encryption/Decryption Time Measurement

**Tool Used:** `time.perf_counter()` (Python's most precise timer)

#### Why `perf_counter()`?
- Highest available precision (microsecond/nanosecond level)
- Monotonic (only moves forward, unaffected by system clock changes)
- Platform-independent (works on Windows, macOS, Linux)
- Specifically designed for performance measurement

#### Measurement Process:

```
┌──────────────────────────────────────────────────────────────┐
│                     MEASUREMENT PROCESS                      │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┐
  1. Warmup Phase (2 iterations)                                
  - Runs encryption/decryption without measurement             
  - Ensures CPU cache is warm                                  
  - Avoids cold-start inaccuracies                             
└ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┘
                               │
                               ▼
┌ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┐
  2. Measurement Phase (5 iterations)                          
  For each iteration:                                          
  a. start = time.perf_counter()                               
  b. Execute operation (encrypt/decrypt)                       
  c. end = time.perf_counter()                                 
  d. elapsed = (end - start) * 1000    # Convert to ms         
  e. Store elapsed time                                        
└ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┘
                               │
                               ▼
┌ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┐
  3. Statistics Calculation                                    
  - Mean (average) time                                        
  - Median time (less affected by outliers)                    
  - Standard deviation (measure of consistency)                
  - Min/Max times                                              
└ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┘
                               │
                               ▼
┌ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┐
  4. Outlier Removal (Optional)                                
  - Remove times > 2 standard deviations from mean             
  - Ensures OS interrupts don't skew results                   
└ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┘
```

#### Code Pattern (Conceptual):
```python
def measure_time(func):
    """Decorator to measure execution time with warmup"""
    def wrapper(*args, **kwargs):
        # Warmup
        for _ in range(WARMUP_ITERATIONS):
            func(*args, **kwargs)
        
        # Actual measurement
        times = []
        for _ in range(BENCHMARK_ITERATIONS):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            elapsed_ms = (end - start) * 1000
            times.append(elapsed_ms)
        
        # Calculate statistics
        return {
            'result': result,
            'times': times,
            'mean': statistics.mean(times),
            'median': statistics.median(times),
            'stddev': statistics.stdev(times) if len(times) > 1 else 0
        }
    return wrapper
```

---

### 2.2 Throughput Measurement

**Definition:** Amount of data processed per unit time

#### Formula:
$$\text{Throughput (MB/s)} = \frac{\text{Data Size (MB)}}{\text{Time (seconds)}}$$

#### Process:
1. **Data Generation:**
   - Generate random data of specific sizes (1KB, 10KB, 100KB, 1MB, 10MB)
   - Ensures consistent data across tests
2. **Encryption Time Measurement:**
   - Measure time to encrypt entire data
   - Record in seconds (not milliseconds)
3. **Throughput Calculation:**
   ```text
   throughput = data_size_mb / time_seconds
   ```
4. **Repeat for Different Configurations:**
   - AES-128, AES-192, AES-256
   - ECB mode, CBC mode
   - Different data sizes

#### Example:
```text
Data Size: 10 MB
Encryption Time: 0.85 seconds
Throughput = 10 / 0.85 = 11.76 MB/s
```

---

### 2.3 Memory Usage Measurement

**Tool Used:** `memory_profiler` library (optional) or `psutil`  
**Alternative:** Track via Python's memory management

#### Method 1: Using `memory_profiler`
```python
from memory_profiler import memory_usage

def measure_memory(func):
    def wrapper(*args, **kwargs):
        mem_usage = memory_usage((func, args, kwargs), interval=0.01)
        return {
            'result': func(*args, **kwargs),
            'max_memory_mb': max(mem_usage),
            'min_memory_mb': min(mem_usage),
            'avg_memory_mb': sum(mem_usage) / len(mem_usage)
        }
    return wrapper
```

#### Method 2: Manual Tracking
```python
import psutil
import os

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # MB
```

#### What We Measure:
- **Peak Memory Usage:** Maximum RAM during operation
- **Average Memory Usage:** Average over operation duration
- **Memory Increase:** Memory increase from before to after operation

---

### 2.4 Data Size Variations

To show real-world impact, we test with different data sizes:

| Data Size | Use Case | Number of Tests |
| :--- | :--- | :--- |
| **1 KB** | Small text messages, passwords | 10 iterations |
| **10 KB** | Short documents | 10 iterations |
| **100 KB** | Emails, small images | 5 iterations |
| **1 MB** | Photos, PDFs | 5 iterations |
| **10 MB** | Audio files, documents | 3 iterations |
| **100 MB** | Videos, large datasets | 1 iteration (time-consuming) |

#### Why Multiple Sizes?
- Encryption overhead is more noticeable for small data
- Throughput is more relevant for large data
- Shows performance characteristics across use cases

---

## 3. Security Analysis Methodology

### 3.1 ECB vs CBC Visual Demonstration (ECB Penguin)

**Purpose:** Visually demonstrate why ECB mode is insecure for image/data with repeating patterns.

#### Method:
1. **Prepare Test Image:**
   - Use a standard test image (e.g., `penguin.png` or `logo.png`)
   - Image should have uniform color regions (sky, water, etc.)
   - Size: 512x512 pixels or similar
2. **Encrypt Image in ECB Mode:**
   - Read image pixel data
   - Encrypt each block independently (ECB)
   - Write encrypted pixel data as an image
3. **Encrypt Same Image in CBC Mode:**
   - Same process, but with CBC mode
4. **Compare Results:**
   - **ECB Encrypted Image:** Shows visible patterns (penguin outline remains visible)
   - **CBC Encrypted Image:** Completely random/noise

#### Why This Works:

```
                          Original Image
                                │
                                ▼
┌ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┐
  ECB MODE                                                                        
                                                                                  
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            
  │   Block 1    │          │   Block 2    │          │   Block 3    │            
  │  (blue sky)  │          │  (blue sky)  │          │  (blue sky)  │            
  └──────┬───────┘          └──────┬───────┘          └──────┬───────┘            
         │                         │                         │                    
         ▼                         ▼                         ▼                    
      Encrypt                   Encrypt                   Encrypt                 
    (same key)                (same key)                (same key)                
         │                         │                         │                    
         ▼                         ▼                         ▼                    
  ┌──────────────┐          ┌──────────────┐          ┌──────────────┐            
  │   Cipher A   │          │   Cipher A   │          │   Cipher A   │ ◄── IDENTICAL!
  └──────────────┘          └──────────────┘          └──────────────┘            
                                                                                  
  Result: Pattern remains visible!                                                
└ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -┘
```

#### Visual Result Expected:

| Image | Result |
| :--- | :--- |
| **Original** | Clear recognizable image |
| **ECB Encrypted** | Messy but outline visible (penguin shape) |
| **CBC Encrypted** | Complete static noise |

---

### 3.2 Avalanche Effect Demonstration

**Definition:** A good cipher should change ~50% of output bits when 1 bit of input/key changes.

#### Method:
1. **Encrypt a Known Plaintext:**
   ```text
   Plaintext: "HelloWorld123456" (16 bytes)
   Key: "0123456789ABCDEF0123456789ABCDEF"
   Output: Ciphertext_original
   ```
2. **Change 1 Bit of Plaintext:**
   ```text
   Plaintext: "HelloWorld123457" (changed last byte from 0x36 to 0x37)
   Key: Same
   Output: Ciphertext_modified
   ```
3. **Calculate Bit Difference:**
   ```text
   Hamming Distance = XOR(Ciphertext_original, Ciphertext_modified)
   Bits_Changed = Count set bits in Hamming Distance
   Avalanche % = (Bits_Changed / Total_Bits) * 100
   ```
4. **Repeat for Multiple Tests:**
   - 10 different plaintexts
   - 10 different keys
   - Different bit positions

#### Expected Result:

| Metric | Expected Value | Acceptable Range |
| :--- | :--- | :--- |
| **Avalanche Effect** | ~50% | 45% - 55% |
| **Bit Change Distribution** | Uniform | No bias toward specific bits |
| **Key Sensitivity** | ~50% | 45% - 55% |

#### Code Pattern (Conceptual):
```python
def calculate_avalanche(plaintext1, plaintext2, key):
    """Calculate avalanche effect between two plaintexts"""
    cipher = AESCipher(key)
    c1 = cipher.encrypt(plaintext1)
    c2 = cipher.encrypt(plaintext2)
    
    # Calculate Hamming distance
    xor_result = bytes(a ^ b for a, b in zip(c1, c2))
    bits_changed = bin(int.from_bytes(xor_result, 'big')).count('1')
    total_bits = len(c1) * 8
    avalanche_percent = (bits_changed / total_bits) * 100
    
    return avalanche_percent
```

---

### 3.3 Key Sensitivity Test

**Purpose:** Demonstrate that changing 1 bit of the key completely changes the output.

#### Method:
1. **Generate Key:**
   ```text
   Key_original = "0123456789ABCDEF0123456789ABCDEF"
   ```
2. **Change 1 Bit in Key:**
   ```text
   Key_modified = "1123456789ABCDEF0123456789ABCDEF"  # Changed first byte
   ```
3. **Encrypt Same Plaintext:**
   ```text
   Plaintext: "HelloWorld123456"
   Ciphertext1 = AES_Encrypt(Plaintext, Key_original)
   Ciphertext2 = AES_Encrypt(Plaintext, Key_modified)
   ```
4. **Calculate Difference:**
   - Hamming distance between Ciphertext1 and Ciphertext2
   - Should be ~50%

---

## 4. Benchmarking Methodology

### 4.1 Test Environment Standardization

To ensure reproducible results:

| Factor | Control Method |
| :--- | :--- |
| **CPU Frequency** | Disable power-saving modes |
| **Background Processes** | Close unnecessary applications |
| **CPU Core Affinity** | Pin process to specific CPU core |
| **RAM** | Ensure sufficient free RAM |
| **Disk I/O** | Use in-memory operations for timing |

---

### 4.2 Benchmark Configuration

Parameters Configurable via `benchmark_config.yaml`:

```yaml
# Benchmark Configuration
benchmark:
  iterations: 5                    # Number of test iterations
  warmup_iterations: 2             # Warmup iterations
  data_sizes:
    - 1024                        # 1 KB
    - 10240                       # 10 KB
    - 102400                      # 100 KB
    - 1048576                     # 1 MB
    - 10485760                    # 10 MB
  
  algorithms:
    - AES
    - RSA
    - Blowfish
    - Classical
  
  key_sizes:
    AES: [128, 192, 256]
    RSA: [1024, 2048, 4096]
  
  modes:
    - ECB
    - CBC
  
  output:
    csv: "results/csv/benchmark_results.csv"
    graphs: "results/graphs/"
```

---

### 4.3 Test Execution Process

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

## 5. Statistical Analysis

### 5.1 Confidence Intervals

For each measurement, we calculate 95% confidence intervals:
$$\text{Confidence Interval} = \text{Mean} \pm \left(1.96 \times \frac{\text{StdDev}}{\sqrt{n}}\right)$$

**Interpretation:** We are 95% confident that the true mean falls within this range.

### 5.2 Outlier Detection

We use **IQR (Interquartile Range)** method to identify outliers:
$$\begin{aligned}
Q_1 &= \text{25th percentile} \\
Q_3 &= \text{75th percentile} \\
\text{IQR} &= Q_3 - Q_1 \\
\text{Lower Bound} &= Q_1 - 1.5 \times \text{IQR} \\
\text{Upper Bound} &= Q_3 + 1.5 \times \text{IQR}
\end{aligned}$$

$$\text{Outlier} = \text{Value} < \text{Lower Bound} \quad \text{OR} \quad \text{Value} > \text{Upper Bound}$$

**Why Remove Outliers?**
- System interrupts (antivirus scans, OS updates) can skew results
- Ensures measurements reflect cryptographic performance, not system noise

---

## 6. Data Collection and Storage

### 6.1 Data Collected

| Data Type | Description | Format |
| :--- | :--- | :---: |
| **Configuration** | Algorithm, key size, mode | JSON |
| **Performance Metrics** | Time, throughput, memory | CSV |
| **Security Metrics** | Avalanche %, ECB weaknesses | CSV |
| **Environment Info** | Python version, OS, hardware | JSON |

### 6.2 CSV Structure

```csv
timestamp,algorithm,key_size,mode,data_size_bytes,encryption_time_ms,decryption_time_ms,throughput_mbps,memory_usage_mb,avalanche_percent
2026-01-15 10:30:00,AES,128,ECB,1024,0.234,0.198,4.28,12.5,50.2
2026-01-15 10:30:05,AES,128,CBC,1024,0.345,0.289,2.97,15.2,51.3
2026-01-15 10:30:10,AES,256,CBC,1048576,45.678,42.345,22.96,28.4,49.8
```

---

## 7. Graph Generation Methodology

### 7.1 Graph Types and Configurations

| Graph | Data Source | Purpose |
| :--- | :--- | :--- |
| **Key Size Comparison** | Encryption time by key size | Show performance trade-off |
| **Mode Comparison** | ECB vs CBC bar chart | Show mode performance difference |
| **Throughput Analysis** | Throughput vs data size | Show scalability |
| **Avalanche Effect** | Bit change percentages | Prove security property |

### 7.2 Graph Generation Process

```python
# Conceptual process
def generate_key_size_comparison(data):
    """Generate bar chart comparing key sizes"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Data preparation
    key_sizes = [128, 192, 256]
    times = [data['128']['mean'], data['192']['mean'], data['256']['mean']]
    
    # Plot
    bars = ax.bar(key_sizes, times)
    
    # Labels
    ax.set_xlabel('Key Size (bits)')
    ax.set_ylabel('Encryption Time (ms)')
    ax.set_title('AES Encryption Time by Key Size')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f} ms', ha='center', va='bottom')
    
    # Save
    plt.savefig('results/graphs/key_size_comparison.png', dpi=300)
```

---

## 8. Reproducibility Checklist

For any experiment, ensure:
- Same Python version (3.10+)
- Same library versions (`requirements.txt` locked)
- Same system specs documented
- Same data used for comparisons
- Multiple iterations ($\ge 5$)
- Warmup performed ($\ge 2$ iterations)
- Confidence intervals calculated
- Outliers removed (IQR method)
- Environment noise minimized (close other apps)
- Results saved (CSV + graphs + logs)

---

## 9. Validation Methodology

### 9.1 Correctness Validation

| Test | Method | Expected Result |
| :--- | :--- | :--- |
| **Encryption/Decryption** | Encrypt then decrypt | Returns original text |
| **Key Size** | Test all supported sizes | Works without errors |
| **Mode Support** | Test ECB and CBC | Both work correctly |
| **File Handling** | Encrypt/decrypt files | Preserves file contents |

### 9.2 Performance Validation

| Metric | Method | What We Verify |
| :--- | :--- | :--- |
| **Time** | Multiple iterations | Consistent timing |
| **Throughput** | Vary data size | Linear scaling |
| **Memory** | Monitor during operation | No memory leaks |

### 9.3 Security Validation

| Check | Method | Expected |
| :--- | :--- | :--- |
| **Avalanche Effect** | Bit change test | ~50% change |
| **ECB Weakness** | Image encryption | Pattern visible |
| **CBC Strength** | Image encryption | No pattern visible |

---

## 10. Handling Limitations

| Limitation | Mitigation |
| :--- | :--- |
| **System Noise** | Multiple iterations, outlier removal |
| **Hardware Differences** | Document hardware specs, relative comparisons |
| **Library Bugs** | Use stable, well-tested libraries |
| **Time Constraints** | Prioritize most important tests |
| **Memory Constraints** | Process large files in chunks |

---

## 11. Reporting Format

Performance results will be presented as:
- **Tables** (using `tabulate` library)
- **Graphs** (using `matplotlib`)
- **CSV Export** (for further analysis)
- **Markdown Report** (for final submission)

---

## Recommendations & Methodology Refinements

1. **Increase Benchmark and Warmup Iterations**
   - **Explanation:** Using 2 warmup runs and 5 measurement iterations is statistically insufficient to filter out thread scheduling preemption and CPU cache misses.
   - **Recommendation:** Increase to **warmup_iterations: 5–10** and **iterations: 50–100** for production benchmarking.
   - **Benefit:** Produces statistically reliable standard deviations and prevents erratic results during evaluation.

2. **Standardize on `psutil` for Memory Profiling**
   - **Explanation:** Maintaining two memory profiling libraries (`memory_profiler` and `psutil`) creates unnecessary installation complexity and platform inconsistencies.
   - **Recommendation:** Standardize exclusively on `psutil` for process memory polling (`Process.memory_info().rss`), marking `memory_profiler` as optional.
   - **Benefit:** Reduces dependency bloat and provides lightweight, cross-platform RAM metrics.

3. **Pragmatic Scope for Advanced Statistical Filters**
   - **Explanation:** Promising 95% Confidence Intervals and IQR Outlier Detection invites examiners to demand code demonstrations.
   - **Recommendation:** If not explicitly implemented in Python code, move Confidence Interval and IQR calculation into a "Future Enhancements" section and focus core reporting on Mean, Median, and Standard Deviation.
   - **Benefit:** Safeguards against viva challenges while maintaining scientific rigor.

4. **Add Avalanche Effect Variance Disclaimer**
   - **Explanation:** Perfect 50% bit flip distribution is theoretical; real pseudo-random output fluctuates across single runs.
   - **Recommendation:** Document that due to cryptographic randomness, an exact 50.00% avalanche effect is not guaranteed in any single run, and an empirical range of **45% to 55%** confirms strong diffusion.
   - **Benefit:** Clarifies expectations during live demonstrations and evaluations.

5. **Restructure Large Payload Benchmark Matrix**
   - **Explanation:** Running 100 MB single-shot tests on low-RAM evaluation machines can trigger memory paging or freezing.
   - **Recommendation:** Adjust data size categorization:
     - 1 KB (Unit Tests)
     - 10 KB (Small Documents)
     - 100 KB (Medium Documents)
     - 1 MB (Images/PDFs)
     - 10 MB (Large Files)
     - 50 MB (3 iterations, Stress Test)
     - 100 MB (Optional Benchmark)
   - **Benefit:** Ensures fast, reproducible test suites across all team hardware configurations.

6. **Differentiate Bulk Asymmetric Benchmarking Scope**
   - **Explanation:** Grouping RSA together with AES under identical large-payload benchmarks contradicts asymmetric cipher fundamentals.
   - **Recommendation:** Formally document that RSA benchmarking is strictly confined to small payloads (e.g., $\le$ 256 bytes) and key generation speed, noting that RSA is mathematically designed for key encapsulation, not bulk stream encryption.
   - **Benefit:** Preempts fundamental viva criticism regarding asymmetric cipher utilization.

7. **Explicit Binary Base Unit Definition for Throughput**
   - **Explanation:** Discrepancies between decimal ($10^6$) and binary ($2^{20}$) megabytes introduce throughput calculation variances.
   - **Recommendation:** Explicitly state in the formula that $1\text{ MB} = 1{,}048{,}576\text{ bytes}$ ($1024 \times 1024$).
   - **Benefit:** Prevents math reconciliation discrepancies in benchmark CSV exports.

8. **Expand Reporting Deliverables**
   - **Explanation:** Final evaluations require diverse reporting artifacts.
   - **Recommendation:** Expand reporting deliverables to explicitly include PNG graph figures, CSV raw metrics, dynamic CLI summary tables, and a unified final report.
   - **Benefit:** Satisfies submission criteria across documentation, visualization, and raw data requirements.

9. **Refine Core Philosophy Statement**
   - **Explanation:** The current philosophy statement phrasing can be enhanced for formal academic presentation.
   - **Recommendation:** Rephrase as: *"All conclusions regarding encryption performance and security trade-offs should be supported by empirical measurements."*
   - **Benefit:** Elevates the academic tone of the methodology document.
