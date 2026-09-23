# Analysis System — Explore & Implementation Plan

## 1. Current Context
- **Repository**: `C:\Users\kodal\Cryptography_Project`
- **Branch**: `dev`
- **HEAD**: `04fb4fa feat: implement AES core engine`
- **Status**: Task 1.1 (Padding) and Task 1.2 (AES Core) are completed, closed, and frozen. The methodology conflicts have been resolved, locking the benchmarking rules to 5 warmups, 30 measured iterations, Tukey fences for outlier flagging (no deletion), and preservation of raw observations.

## 2. Existing Architecture
The `src/analyzers/` directory exists but currently contains only empty stub files:
- `performance_timer.py`
- `metric_collector.py`
- `security_evaluator.py`s
- `graph_generator.py`

The architecture enforces strict separation: the Business Logic layer (`src/core/`) handles cryptography, the Analysis Layer (`src/analyzers/`) measures performance, and the Persistence Layer handles all file I/O operations (CSVs, PNGs).

## 3. Existing Relevant APIs
- `AESCipher.encrypt` and `AESCipher.decrypt` natively apply PKCS#7 padding and generate the underlying PyCA cipher objects. They are self-contained and validate their inputs.
- `Padding.pad` and `Padding.unpad` operate correctly.
**Constraint**: These APIs must not be altered. The Analysis system must wrap them exactly as they are currently designed.

## 4. Methodology Contract
The system must strictly implement the locked methodology:
- **Warmup iterations**: 5
- **Measured iterations**: 30
- **Raw observations**: Retained and preserved.
- **IQR & Outliers**: Calculated for every benchmark using Tukey fences ($Q_1 - 1.5 \times IQR$ and $Q_3 + 1.5 \times IQR$). Potential outliers are *flagged*, but **deletion is strictly forbidden**.
- **Primary statistics**: Mean, median, standard deviation, min, max, Q1, Q3, and IQR must be calculated from the **raw observations** (including outliers).
- **SD > 10% trigger**: Not used.

## 5. PerformanceTimer Contract
- **Public API**: `@PerformanceTimer.measure_time_with_warmup(iterations=30, warmup=5)`.
  *Justification*: The decorator API is not merely a convention; it is explicitly mandated by `05_API_Interface_Spec.md` and `03_Architecture_Design.md` (Recommendation 5), which formally requires maintaining the **Decorator Pattern**.
- **Timing Boundary**: The timer starts immediately before invoking the decorated target function and stops immediately after it returns. As mandated by `03_Architecture_Design.md` (Recommendation 4), this measures the **entire end-to-end encryption pipeline**.
  - **INCLUDED**: Target function invocation, input validation, PKCS#7 padding/unpadding, `Cipher` object construction (`_build_cipher`), and the cryptographic execution (`encryptor.update` + `finalize`).
  - **EXCLUDED**: Key generation and IV generation (these occur before the timer starts and are passed as arguments to the decorated function).
- **Execution Behavior**: The decorator executes the target function 5 times without recording time (warmup), then 30 times recording the precise elapsed time per iteration.
- **Timing Units & Sub-microsecond Handling**: Time is captured natively using high-resolution timers (`time.perf_counter()`). The raw measured elapsed time must be preserved exactly as observed. Artificial clamping is strictly prohibited. Zero/tiny values must NOT be replaced with epsilon. The default benchmark behavior is ONE target invocation per measured iteration (no batching multiple operations inside one timed iteration). If elapsed time is `<= 0`, throughput must be represented as `NaN` (undefined) to prevent fabricating a value.
- **Return Value**: Yields `(result, stats_dict)` where `stats_dict` contains exactly 30 raw observations to guarantee methodological preservation.

## 6. MetricCollector Contract
- **Accumulation**: Receives raw measurement dictionaries and computes statistical metrics (mean, median, std_dev, Tukey fences).
- **Data Structure**: Converts metrics into a `pandas.DataFrame`.
- **CSV Format**: The authoritative CSV schema expects one row per configuration (e.g., `encryption_time_ms`). This value will represent the `mean` of the 30 raw observations.
- **Throughput Definition**: Throughput is explicitly defined as `(data_size_bytes / 1048576) / (mean_time_ms / 1000)` representing MB/s (Binary Base).

## 7. SecurityEvaluator Contract
- **Avalanche Effect**: Evaluates bit diffusion (`calculate_avalanche_effect`). The 45%–55% range is treated as an empirical expectation, not a hard pass/fail threshold.
- **Hamming Distance**: Pure mathematical XOR bit-counting helper (`calculate_hamming_distance`).
- **ECB Weakness**: Generates the "ECB Penguin" visual artifact (`test_ecb_weakness`).

## 8. GraphGenerator Contract
- **Input**: Consumes statistical results (e.g., `pandas.DataFrame`).
- **Output Types**:
  1. Key Size Comparison (Bar chart)
  2. Mode Comparison (ECB vs CBC)
  3. Throughput Analysis
  4. Avalanche Effect %
- **Coupling**: It only constructs `matplotlib.pyplot` figure objects. It does **not** save figures to disk.

## 9. Persistence Boundary
The Architecture formally defines the Persistence Layer (`src/utils/file_handler.py`) as the repository handler responsible for all file writing (CSV metrics, PNG plots, logs).
Therefore, the strict separation of responsibility is:
- **MetricCollector**: Calculates statistics and constructs the DataFrame. It does **not** write to disk.
- **SecurityEvaluator**: Calculates bit diffusion and generates the ECB demonstration image payload. It does **not** write to disk.
- **GraphGenerator**: Constructs Matplotlib figures and axes. It does **not** save figures to disk.
- **Persistence / FileHandler**: Exclusively owns disk I/O. It receives DataFrames, Image buffers, or Figures from the Analysis Layer and explicitly writes them to the file system.
  - **Summary CSV**: Writes one row per benchmark configuration containing aggregate metrics (key_size, mode, data_size, encryption_time_ms, throughput_mb_s, memory_delta_mb) and statistical fields.
  - **Raw Observations CSV**: Writes one row per measured observation. Retains all 30 measured timing observations for every configuration, including configuration identifiers, iteration number, raw elapsed time, and outlier/IQR classification information from MetricCollector.

## 10. Data Flow
```text
AES Core (aes_cipher.py)
   ↓
Benchmark Configuration (YAML/env)
   ↓
Performance Timer (executes 5 warmup, 30 measured, yields 30 raw times)
   ↓
Raw Measurements
   ↓
Metric Collector (computes Tukey fences, median, IQR, std, flags outliers)
   ↓
Statistical Results (pandas DataFrame)
   ↓
Security Evaluator (Avalanche metrics, ECB visuals)
   ↓
Graph Generator (creates matplotlib figures)
   ↓
Persistence Layer (FileHandler writes CSVs and PNGs)
```

## 11. Data Models / Structures
**Performance Stats Dictionary**:
```python
{
    "raw_times_ms": list[float], # length 30
    "mean": float,
    "median": float,
    "std_dev": float,
    "min": float,
    "max": float,
    "q1": float,
    "q3": float,
    "iqr": float,
    "outliers_flagged": int  # count of times outside Tukey fences
}
```

## 12. Error Handling
- Invalid iteration counts (`iterations < 1`) will raise `ValueError`.
- General analysis benchmarking failures will raise a custom `BenchmarkError` (as recommended in `05_API_Interface_Spec.md`).
- Cryptographic exceptions from `AESCipher` are allowed to propagate naturally.

## 17. DECISIONS LOCKED
1. **Raw Observation Persistence**: The Persistence layer writes two CSVs: a summary CSV (aggregates, statistics) and a raw CSV preserving all 30 observations per configuration with classification flags.
2. **Memory Measurement Contract**:
   - Library: `psutil`
   - Metric: process RSS (Resident Set Size). Described as "process RSS delta" or "benchmark process memory change" (NOT "AES memory").
   - Unit: MB
   - Granularity: Benchmark batch level (NOT per individual iteration).
   - Baseline: process RSS measured immediately before the benchmark batch.
   - Peak: maximum process RSS observed during the benchmark batch.
   - Reported Memory Metric: peak RSS - baseline RSS.
   - Timing Isolation: Memory measurement occurs OUTSIDE the timed encryption/decryption region so `psutil` overhead does not contaminate timings.
3. **Sub-microsecond Timing & Throughput Division**: Time is preserved exactly as observed. If elapsed time is `<= 0`, throughput is recorded as `NaN` (undefined).

## 18. Implementation Risks
- **psutil Dependency**: `psutil` is required for memory measurement but is not currently installed or listed in `requirements.txt`. It must be added during implementation.
- **Pillow Dependency**: `Pillow` is required for the ECB Penguin demo but is not currently installed.
- **Noisy Fast Execution**: Very small benchmark durations (e.g., 1 KB payload) may produce noisy measurements due to OS timer resolution, potentially triggering NaN throughputs.
- **Environment Variance**: Process RSS delta behavior can fluctuate based on environment and OS.

## 19. Implementation Sequence
1. Implement `PerformanceTimer` (isolated core metric generator).
2. Implement `MetricCollector` (statistical processing engine).
3. Implement `SecurityEvaluator` (cryptographic security checks).
4. Implement `GraphGenerator` (visualization).
5. Implement unit tests for all analyzers.

## 13. Testing Strategy
*(Note: Do not implement these tests now; they must be written during the implementation phase.)*
- **`PerformanceTimer`**:
  - Test exactly 5 warmups and 30 measured iterations.
  - Test exactly 30 raw measured observations are retained in output.
  - Test `perf_counter` usage (mocked) and strict timing boundary.
  - Test invalid iteration values raise `ValueError`.
  - Assert that no artificial timing clamp is applied to zero/negative inputs.
- **`MetricCollector`**:
  - Inject predefined arrays to test: mean, median, standard deviation, min, max, Q1, Q3, and IQR.
  - Test Tukey fence outlier classification flags (outliers are NOT silently removed).
  - Test raw observations are correctly retained.
  - Test zero/non-positive elapsed time handling yields `NaN` for throughput.
- **`Memory`**:
  - Test baseline RSS, peak RSS, and delta calculations.
  - Ensure memory measurement happens outside the timed region at the batch granularity level.
- **`SecurityEvaluator`**:
  - Test `calculate_hamming_distance` with known byte strings.
- **`GraphGenerator`**:
  - Verify `matplotlib` figure objects are successfully constructed.
- **`Persistence`**:
  - Verify summary CSV contains one row per configuration.
  - Verify raw CSV retains all 30 observations per configuration.

## 20. Definition of Done
- All analyzer stubs are fully implemented, exactly satisfying their APIs without bypassing architecture boundaries.
- `PerformanceTimer` guarantees 5 warmups and 30 measurements, retaining raw observations.
- `MetricCollector` computes Tukey fences and flags outliers without mutating the raw dataset, receiving data without writing to disk.
- Persistence Layer exclusively handles all CSV and PNG outputs.
- Unit tests verify analytical correctness, adhering strictly to the contract (e.g. without asserting clamped 1e-6 values).
- AES and Padding implementations remain entirely unmodified.

## 21. Final Verdict
🟢 **PASS — IMPLEMENTATION READY**
