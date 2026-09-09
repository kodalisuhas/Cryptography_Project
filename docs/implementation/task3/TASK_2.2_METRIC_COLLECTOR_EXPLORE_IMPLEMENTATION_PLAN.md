# TASK 2.2 — MetricCollector Explore & Implementation Plan

## 1. Current Repository Context
- **Status**: `PerformanceTimer` (Task 2.1) has been implemented and returns exact `raw_times_ms` without clamping or batching.
- **Methodology**: The benchmarking rules strictly require 5 warmups, 30 measurements, preservation of raw observations, calculation of primary statistics from ALL raw observations, and outlier flagging using Tukey fences (no deletion).
- **Target**: `src/analyzers/metric_collector.py` is currently an empty stub.

## 2. Existing Relevant APIs
The `05_API_Interface_Spec.md` currently defines `MetricCollector` with an `add_metric` method that expects pre-calculated scalar values (e.g., `encryption_time_ms`, `throughput_mbps`).
It also defines `get_dataframe()` and `export_to_csv()`.
This existing API conflicts with the newer Analysis Plan which shifts the calculation of statistics (Tukey fences, standard deviation) into `MetricCollector` itself and explicitly forbids `MetricCollector` from performing file I/O (`export_to_csv`).

## 3. MetricCollector Responsibility
`MetricCollector` must act as the pure statistical processing engine.
- **It MUST**: Receive raw benchmark timings, compute aggregate statistics, flag outliers, calculate throughput, and return structured DataFrames (Summary and Raw).
- **It MUST NOT**: Execute benchmarking, write CSV files, generate plots, or calculate cryptographic security metrics (avalanche effect).

## 4. Input Contract
The `add_metric` method must be updated to accept raw observations rather than pre-calculated means.
Proposed input structure:
```python
def add_metric(self, metric_data: dict):
    # metric_data must contain:
    # 'algorithm': str
    # 'key_size': int
    # 'mode': str
    # 'data_size_bytes': int
    # 'raw_times_ms': list[float] (Length exactly 30)
    # 'memory_delta_mb': float (Optional)
```

## 5. Output Contract
Since the system now requires both summary and raw data persistence, the output contract must provide both:
- `get_summary_dataframe() -> pandas.DataFrame`
- `get_raw_dataframe() -> pandas.DataFrame`
*(Note: `get_dataframe()` from the original spec should be aliased to `get_summary_dataframe()` for compatibility if needed).*

## 6. Exact Statistical Formulas/Conventions
- **Count**: `len(raw_times_ms)`
- **Mean**: Arithmetic mean ($\frac{\sum x}{n}$)
- **Median**: 50th percentile (linear interpolation)
- **Standard Deviation**: Sample standard deviation (`numpy.std(..., ddof=1)`)
- **Min / Max**: Absolute minimum and maximum of the 30 raw observations.
- **Q1 / Q3 / IQR**: 25th percentile, 75th percentile (using NumPy's `linear` method/interpolation), and their difference.

## 7. Quartile Convention
- **Locked Decision**: Standardized strictly on **NumPy's `linear` method/interpolation** for calculating the 25th and 75th percentiles.
- **Reasoning**: It is the standard mathematical definition and consistent with pandas' defaults. Other methods (midpoint, lower, higher, nearest) are explicitly forbidden.

## 8. Standard Deviation Convention
- **Locked Decision**: Standardized strictly on **Sample Standard Deviation** (`numpy.std(..., ddof=1)`).
- **Reasoning**: The 30 benchmark measurements represent a sample drawn from the broader population of possible execution times. Population standard deviation (`ddof=0`) must NOT be used for the authoritative metric.

## 9. Tukey Fence Methodology
Using the approved methodology:
1. $Q_1$ and $Q_3$ are calculated.
2. $IQR = Q_3 - Q_1$.
3. $\text{Lower Fence} = Q_1 - 1.5 \times IQR$.
4. $\text{Upper Fence} = Q_3 + 1.5 \times IQR$.

## 10. Outlier Preservation Behavior
- All 30 raw observations are used to calculate the mean, std_dev, and quartiles.
- Any observation $< \text{Lower Fence}$ or $> \text{Upper Fence}$ is flagged.
- The raw dataset is NOT modified or filtered. The summary statistics represent the unfiltered dataset.
- The number of flagged outliers is stored as `outlier_count`.

## 11. Throughput Calculation Responsibility
- **Locked Decision**: `MetricCollector` is responsible for calculating throughput.
- **Reasoning**: `MetricCollector` calculates the authoritative mean benchmark time and has access to `data_size_bytes`.
- **Formula**: `throughput_mb_s = (data_size_bytes / 1048576) / (mean_time_ms / 1000)`
- **Constraints**: 1 MB is strictly defined as 1,048,576 bytes. If `mean_time_ms <= 0`, throughput MUST be explicitly set to `numpy.nan` (do not clamp timing, do not add epsilon, do not fabricate).

## 12. Zero/Non-Positive Timing Behavior
If `mean_time_ms <= 0`, division by zero is mathematically undefined.
- The raw timings will be preserved precisely as observed.
- `throughput_mb_s` will be explicitly set to `numpy.nan`.
- No artificial clamping or epsilon addition will be performed.

## 13. DataFrame Schema
**Summary DataFrame**:
`algorithm`, `key_size`, `mode`, `data_size_bytes`, `mean_time_ms`, `median_time_ms`, `std_dev_time_ms`, `min_time_ms`, `max_time_ms`, `q1_ms`, `q3_ms`, `iqr_ms`, `outlier_count`, `throughput_mb_s`, `memory_delta_mb`.

**Raw Observations DataFrame**:
`algorithm`, `key_size`, `mode`, `data_size_bytes`, `iteration_index`, `elapsed_time_ms`, `is_outlier`.

## 14. Raw Observation Preservation Design
`MetricCollector` will maintain two internal lists of dictionaries:
1. `self._summary_data` (one entry per benchmark configuration).
2. `self._raw_data` (30 entries per benchmark configuration).
These lists will be seamlessly converted into pandas DataFrames when requested.

## 15. Error Handling
- **Missing Keys**: `ValueError` if `metric_data` lacks mandatory fields (e.g., `raw_times_ms`).
- **Empty Raw Times**: `ValueError` if `raw_times_ms` is empty.
- **Negative Data Size**: `ValueError` if `data_size_bytes < 0`.

## 16. Edge Cases Analyzed
- **Exactly identical observations**: $IQR = 0$. No outliers triggered unless strict inequality fails.
- **Zero timing / negative timing**: Allowed mathematically for quartiles/mean, but throughput cleanly resolves to `NaN`.
- **Fewer than 4 observations**: Supported by `numpy` mathematically, but ideally prevented upstream.
- **Missing Memory Data**: Resolves to `NaN` in the summary DataFrame.

## 17. Architecture Boundaries & Legacy API Warning
- **Persistence Boundary**: `MetricCollector` strictly **DOES NOT** write to CSV. Disk I/O is exclusively owned by `FileHandler`.
- **Legacy API Conflict**: The existing `05_API_Interface_Spec.md` contains legacy specifications for `MetricCollector` including scalar pre-calculated metric inputs, `get_dataframe()`, and `export_to_csv()`.
- **Resolution**: Do NOT resolve this conflict by modifying `05_API_Interface_Spec.md` in this task. The implementation phase must explicitly decide how to handle compatibility (e.g., by deprecating `export_to_csv` or bridging the calls) without violating the newly locked Persistence boundary.

## 18. Dependency Requirements
- `numpy` (already installed)
- `pandas` (already installed)
- No new dependencies required.

## 19. Test Strategy
*(Plan Only)*
A. **Basic Statistics**: Inject a known array of 30 floats. Assert exact mean, median, standard deviation (using `ddof=1`), min, max, Q1, Q3 (using NumPy `linear` interpolation), and IQR matches pre-computed values.
B. **Tukey Fences**: Inject an array with 1 high and 1 low outlier. Assert the `outlier_count == 2` and the correct iterations are flagged.
C. **Raw Preservation**: Assert the raw DataFrame contains exactly 30 rows for every configuration added. Assert outliers are NOT removed from the mean.
D. **Throughput**: Assert binary throughput calculation matches exact expected math. Assert `NaN` is produced if mean time is $\le 0$.
E. **DataFrames**: Assert column schemas match exactly.
F. **Edge Cases**: Empty list raises ValueError; identical values produce 0 IQR.

## 20. Implementation Sequence
1. Implement `MetricCollector.add_metric` to accept raw data and compute stats using `numpy`.
2. Implement `get_summary_dataframe` and `get_raw_dataframe`.
3. Address legacy API compatibility without violating architecture boundaries.
4. Implement the test suite.

## 21. DECISIONS LOCKED
1. **Quartile Convention**: Use NumPy's `linear` percentile method/interpolation for Q1 and Q3.
2. **Standard Deviation**: Use Sample Standard Deviation (`numpy.std(..., ddof=1)`).
3. **Throughput Calculation**: `MetricCollector` assumes responsibility for calculating throughput based on authoritative mean benchmark time, resolving to `NaN` if time $\le 0$.

## 22. Risks
- Legacy code attempting to call `export_to_csv` directly on `MetricCollector` will fail unless compatibility logic is implemented.
- Returning `NaN` for throughput on sub-microsecond encryption runs may disrupt naive graph generation code later if not properly handled.

## 23. Definition of Done
- `MetricCollector` fully calculates requested statistics from raw arrays using locked NumPy conventions (`linear` quartiles, `ddof=1` sample SD).
- It handles throughput and mathematical edge cases deterministically.
- Two distinct pandas DataFrames (summary and raw) can be generated.
- No files are written. Legacy API calls must be resolved within strict architecture boundaries.
- Tests verify all mathematical outputs and outlier preservation behaviors.

## 24. Final Verdict
🟢 **PASS — IMPLEMENTATION READY**
