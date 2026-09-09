# TASK 3.4 — GRAPH GENERATOR
# FINAL EXPLORE + IMPLEMENTATION PLAN

## 1. Executive Summary
This is the final, corrected implementation plan for `GraphGenerator`. Following an authoritative reconciliation against the master plan and decision documents, the scope of this module is strictly locked to three analytical graphs (Key Size, Mode, and Throughput). Furthermore, a major architectural refinement found in `REPORT 2.MD` explicitly resolves the persistence boundary: `GraphGenerator` constructs Matplotlib Figures in-memory, while `FileHandler` (Persistence Layer) owns all physical disk I/O, including PNG saving.

## 2. Repository State
The repository has AES encryption, performance timing, metric collection, and security evaluation fully implemented and frozen. `MetricCollector` produces structured DataFrames containing aggregated statistics. `GraphGenerator` is currently stubbed/unimplemented. `FileHandler` (Persistence Layer) is also currently a stub.

## 3. Authoritative Documents
This plan relies strictly on the current versions of:
- `docs/04_Methodology.md`
- `what we are solving.txt` (Master Plan)
- `docs/03_Architecture_Design.md`
- `docs/research/analysis/REPORT 2.MD` (Strategic Refinement decisions)
- `docs/05_API_Interface_Spec.md`

## 4. Authoritative Task Scope
Based directly on `what we are solving.txt` and `docs/04_Methodology.md`, the Task 3.4 scope is strictly limited to:
1. **Key-size comparison**
2. **Mode comparison**
3. **Throughput analysis**

The following are **NOT** mandatory Task 3.4 graphs and are explicitly out-of-scope for `GraphGenerator`:
- Avalanche Effect
- Key Sensitivity
- Hamming Distance
- Memory Usage
- ECB Penguin/security visualization

## 5. Frozen Component Contracts
- **`PerformanceTimer`**: Measures time; untouched.
- **`MetricCollector`**: Consumes timings and exports `get_summary_dataframe()` which contains `mean_time_ms`, `throughput_mb_s`, etc.
- **`SecurityEvaluator`**: Security testing; untouched.
- **`AES Cipher`**: Handles cryptography operations; untouched.
`GraphGenerator` will consume the `MetricCollector` DataFrame exactly as exported.

## 6. MetricCollector → GraphGenerator Contract
`GraphGenerator` will consume `MetricCollector.get_summary_dataframe()`. 
It **must not**:
- Calculate mean, median, IQR, or outliers.
- Calculate throughput.
- Mutate the DataFrame.

## 7. Key-Size Comparison Specification
- **Method**: `generate_key_size_comparison(summary_df: pd.DataFrame) -> plt.Figure`
- **Purpose**: Show performance impact across AES key sizes.
- **X-Axis**: Key Size.
- **Y-Axis**: Time in milliseconds (ms).
- **Exact Metric**: `mean_time_ms` (As explicitly demonstrated in `docs/04_Methodology.md` code snippet).
- **Grouping**: Grouped by `mode` (ECB vs CBC). If multiple data sizes exist, data is averaged or selected per mode/key size to prevent duplicate configuration overlaps (or a specific data size must be filtered).
- **Ordering**: Key sizes numerically ascending (128, 192, 256); modes alphabetically.
- **Title**: "AES Performance by Key Size"

## 8. Mode Comparison Specification
- **Method**: `generate_mode_comparison(summary_df: pd.DataFrame) -> plt.Figure`
- **Purpose**: Compare speed between ECB and CBC.
- **X-Axis**: Mode (CBC, ECB).
- **Y-Axis**: Time in milliseconds (ms).
- **Exact Metric**: `mean_time_ms`.
- **Grouping**: Grouped by `key_size` (128, 192, 256). 
- **Ordering**: Modes alphabetically (CBC, ECB); key sizes numerically ascending.
- **Title**: "AES Performance by Mode"

## 9. Throughput Analysis Specification
- **Method**: `generate_throughput_analysis(summary_df: pd.DataFrame) -> plt.Figure`
- **Purpose**: Show data processing speed as payload size scales.
- **X-Axis**: Data Size (bytes).
- **Y-Axis**: Throughput (MB/s).
- **Exact Metric**: `throughput_mb_s`.
- **Series/Grouping**: Distinct lines for each unique `key_size` + `mode` combination (e.g., `AES-128-CBC`).
- **Ordering**: Data sizes numerically ascending on X-axis. Series sorted alphabetically.
- **NaN Behavior**: Points where `throughput_mb_s` is NaN will be natively skipped by Matplotlib without fabricating a 0 value.
- **Title**: "AES Throughput Scaling"

## 10. PNG Artifact Specification
Because `GraphGenerator` does not perform file I/O, it produces a complete, rendered `matplotlib.figure.Figure` object that is ready to be written to disk. 

## 11. GraphGenerator API
```python
import pandas as pd
import matplotlib.pyplot as plt

class GraphGenerator:
    """Constructs Matplotlib visualization artifacts from collected metrics."""
    
    @staticmethod
    def generate_key_size_comparison(summary_df: pd.DataFrame) -> plt.Figure:
        pass
        
    @staticmethod
    def generate_mode_comparison(summary_df: pd.DataFrame) -> plt.Figure:
        pass
        
    @staticmethod
    def generate_throughput_analysis(summary_df: pd.DataFrame) -> plt.Figure:
        pass
```

## 12. Persistence Boundary
**Conflict Resolution**: While older versions of `docs/03_Architecture_Design.md` placed `graph_generator.py` in the Persistence Layer alongside CSV export, `docs/research/analysis/REPORT 2.MD` issues a "Strategic Refinement" explicitly stating: *"In accordance with architectural best practices, graph_generator.py is located within the Analysis Layer. This decouples the visualization logic (rendering) from the Persistence Layer's role of physical disk I/O."*
- **GraphGenerator owns**: Creating the Matplotlib Figure, Axes, labels, plotting, and returning the `Figure` object.
- **FileHandler owns**: Choosing output paths, creating output directories, saving the PNG (via `fig.savefig()`), and handling overwrite behavior. (Integration with FileHandler is a future task).

## 13. Matplotlib Lifecycle
1. **Creation**: Create explicit figure and axes via `fig, ax = plt.subplots()`.
2. **Plotting**: Plot required series.
3. **Styling**: Set labels, titles, and legends.
4. **Return**: Return the `fig` object directly.
5. **Closing Responsibility**: `GraphGenerator` **DOES NOT** call `plt.close()`. The downstream consumer (`FileHandler` or tests) is strictly responsible for closing the figure to free memory after saving it. `plt.show()` must never be called.

## 14. Validation Contract
- **Invalid Type**: Raise `TypeError` if input is not a pandas DataFrame.
- **Empty DataFrame**: Raise `ValueError`.
- **Missing Columns**: Raise `ValueError` if required columns (`key_size`, `mode`, `data_size_bytes`, `mean_time_ms`, `throughput_mb_s`) are missing.
- **Invalid Values**: Ignore or drop NaNs logically for plotting; raise no exception.

## 15. Deterministic Ordering
Graphs will sort input dynamically before plotting:
- Key Sizes: `[128, 192, 256]`
- Modes: `['CBC', 'ECB']` (Alphabetical)
- Data sizes: Ascending numerical sort.
- Legends/Series: Sorted alphabetically by configuration name.

## 16. Input Immutability
`GraphGenerator` **MUST NOT** mutate the caller's DataFrame. Any sorting or aggregation must be performed on a copy (`df.copy()`) or via non-mutating Pandas operations.

## 17. Error Handling
- Exceptions from missing columns or invalid inputs are raised immediately as `ValueError` or `TypeError`.
- Matplotlib plotting exceptions are not swallowed and will propagate up.

## 18. Test Strategy
Tests will verify the `GraphGenerator` logic without invoking a display server:
- Set Matplotlib to a non-interactive backend (`matplotlib.use('Agg')`) in `test_graph_generator.py`.
- Pass synthetic mocked DataFrames corresponding precisely to `MetricCollector` summary schema.
- Assert that methods return `matplotlib.figure.Figure`.
- Assert that the correct number of axes/lines are rendered in the figure.
- Assert validation logic correctly throws `ValueError` and `TypeError`.
- Tests **MUST** call `plt.close(fig)` on the returned figure to prevent memory leakage across tests.
- **Persistence Testing**: Tests will **NOT** test PNG file generation.

## 19. Dependency Audit
- `matplotlib` is listed as a dependency in `02_System_Requirements.md` and `requirements.txt`.
- `pandas` and `numpy` are listed in `requirements.txt`.
- No new installations are necessary.

## 20. File Scope
Files expected to be modified/created:
- `src/analyzers/graph_generator.py`
- `tests/test_graph_generator.py`

Protected files (NO MODIFICATION):
- `src/analyzers/performance_timer.py`
- `src/analyzers/metric_collector.py`
- `src/analyzers/security_evaluator.py`
- `src/utils/file_handler.py`

## 21. Implementation Sequence
1. Set up `tests/test_graph_generator.py` with `matplotlib.use('Agg')` and mocked DataFrames.
2. Setup `src/analyzers/graph_generator.py` class and method stubs.
3. Implement DataFrame validation helper.
4. Implement `generate_key_size_comparison`.
5. Implement `generate_mode_comparison`.
6. Implement `generate_throughput_analysis`.
7. Verify all tests pass and ensure no figures are persisted to disk.

## 22. Risks
- Grouping DataFrames that contain multiple identical configurations (e.g., benchmark run twice) might cause unexpected stacking in bar charts if not aggregated correctly before plotting. GraphGenerator should explicitly handle duplicate rows (e.g., mean of means) or rely on `MetricCollector`'s uniqueness.

## 23. Open Decisions
No blocking decisions remain. The persistence boundary contradiction has been explicitly resolved using `REPORT 2.MD`. The analytical metric is cleanly locked to `mean_time_ms` as instructed by `04_Methodology.md`. 

## 24. Definition of Done
- `GraphGenerator` exposes 3 public analytical methods returning `plt.Figure` objects.
- Tests prove deterministic sorting, structural integrity of figures, and validation.
- No `plt.show()`, `plt.savefig()`, or filesystem writes occur within the module.
- The input DataFrame remains pristine.

## 25. Final Verdict
🟢 PASS — IMPLEMENTATION READY
