# TASK 3.4 — GRAPH GENERATOR
# CORRECTED EXPLORE + IMPLEMENTATION PLAN

## 1. Correction Summary
The previous implementation plan incorrectly expanded the scope of Task 3.4 by including Avalanche Effect visualization as a required graph, simply because the upstream `SecurityEvaluator` produced the data. Upon reviewing the authoritative master plan (`what we are solving.txt` and `docs/03_Architecture_Design.md`), it is clear that only 3 performance-based graphs are strictly required for this benchmarking tool. Furthermore, the previous plan incorrectly assumed `GraphGenerator` should delegate PNG persistence to `FileHandler`. The architecture actually dictates that `GraphGenerator` directly handles PNG generation and saving via Matplotlib.

## 2. Authoritative Scope
Based on the foundational project master plan (`what we are solving.txt`) and `docs/03_Architecture_Design.md`, the authoritative scope for Task 3.4 is strictly limited to:
1. Key-size comparison
2. Mode comparison
3. Throughput analysis
4. PNG visualization artifact generation

## 3. Required Graphs
The following three analytical graphs are required to satisfy the project's performance reporting goals:

1. **Key Size Comparison**: To prove that larger keys incur a performance tradeoff.
2. **Mode Comparison**: To compare ECB vs CBC speeds.
3. **Throughput Analysis**: To show data processing speed (MB/s) as payload size scales.

## 4. Explicitly Out-of-Scope Graphs
- **Avalanche Effect Visualization**: Removed from the mandatory Task 3.4 scope. While `SecurityEvaluator` computes these values, they are documented as out-of-scope for `GraphGenerator` visualization in the authoritative master plan. Visualizing security metrics is a potential future extension, but not a blocking requirement for Task 3.4.
- **Memory Usage Visualization**: Out of scope unless explicitly requested in a future phase.

## 5. MetricCollector Data Contract
`GraphGenerator` will consume the summary DataFrame produced by `MetricCollector.get_summary_dataframe()`. It will **not** process raw observations, recalculate statistics, or mutate the input DataFrame. 

Required DataFrame columns:
- `key_size` (int)
- `mode` (str)
- `data_size_bytes` (int)
- `mean_time_ms` or `median_time_ms` (float)
- `throughput_mb_s` (float)

## 6. Key-Size Comparison Specification
- **Purpose**: Show performance impact across AES key sizes.
- **Source DataFrame**: Summary DataFrame.
- **X-Axis**: Key Size (128, 192, 256).
- **Y-Axis**: Time in milliseconds (mean or median).
- **Mode Grouping**: Plotted individually or clustered by mode if multiple modes exist.
- **Ordering**: Ascending numerical order of key sizes (128 -> 192 -> 256).

## 7. Mode Comparison Specification
- **Purpose**: Compare speed between ECB and CBC.
- **Source DataFrame**: Summary DataFrame.
- **X-Axis**: Mode (ECB, CBC).
- **Y-Axis**: Time in milliseconds.
- **Ordering**: Deterministic alphabetical ordering (CBC, ECB).
- **Grouping**: Grouped by Data Size to show how the gap changes with scale.

## 8. Throughput Analysis Specification
- **Purpose**: Data processing speed (scalability).
- **Source DataFrame**: Summary DataFrame.
- **X-Axis**: File/Data Size.
- **Y-Axis**: Throughput (MB/s).
- **Ordering**: Ascending numerical order of data sizes.
- **NaN Handling**: If `throughput_mb_s` is NaN (due to negative or zero time), the Matplotlib line should naturally break or skip the missing node. Do not interpolate or fabricate 0 values.

## 9. PNG / Persistence Boundary
According to `docs/03_Architecture_Design.md`, `graph_generator.py` owns the methods `generate_graph()` and `save_graph()`. Additionally, `docs/04_Methodology.md` explicitly shows `plt.savefig('results/graphs/...', dpi=300)` as part of the visualization process. 
Therefore, `GraphGenerator` **will** directly produce and save the PNG artifacts to the `results/graphs/` directory. `FileHandler` does not manage Matplotlib Figures.

## 10. GraphGenerator API
The proposed minimal API aligned with the architectural specifications:

```python
import pandas as pd

class GraphGenerator:
    """Generates and saves performance visualization PNG artifacts."""
    
    @staticmethod
    def generate_key_size_comparison(summary_df: pd.DataFrame, output_path: str) -> str:
        """Generates key size bar chart and saves it to output_path. Returns the path."""
        pass
        
    @staticmethod
    def generate_mode_comparison(summary_df: pd.DataFrame, output_path: str) -> str:
        """Generates mode comparison bar chart and saves it to output_path. Returns the path."""
        pass
        
    @staticmethod
    def generate_throughput_analysis(summary_df: pd.DataFrame, output_path: str) -> str:
        """Generates throughput line chart and saves it to output_path. Returns the path."""
        pass
```

## 11. Validation Contract
- **Wrong input type**: Raise `TypeError` if input is not a pandas DataFrame.
- **None or Empty DataFrame**: Raise `ValueError`.
- **Missing Columns**: Raise `KeyError` or `ValueError` if the required metrics are missing.
- **Validation Philosophy**: Fail fast if input is structurally invalid. Draw what is available if data subsets (e.g., specific key sizes) are missing.

## 12. Deterministic Ordering
Graphs will explicitly sort the DataFrame before plotting to ensure reproducibility:
- **Key Sizes**: 128, 192, 256.
- **Modes**: Alphabetical (CBC, ECB).
- **Data Sizes**: Ascending numerical order.

## 13. Matplotlib Lifecycle
- `GraphGenerator` creates the Figure.
- `GraphGenerator` sets titles, axes, legends, and styling.
- `GraphGenerator` calls `plt.savefig(output_path, dpi=300)`.
- `GraphGenerator` calls `plt.close()` strictly to free memory and prevent global plot state leakage.
- `plt.show()` must **never** be called to ensure headless test/pipeline compatibility.

## 14. Error Handling
- Invalid DataFrames or missing columns raise early exceptions.
- The component does not swallow exceptions from pandas or matplotlib.
- Missing output directories should be handled securely (e.g., created or checked).

## 15. Test Plan
- **Mock Data**: Create isolated, synthetic `pd.DataFrame` objects matching `MetricCollector` schemas.
- **API Tests**: Verify methods exist and return valid string paths.
- **Artifact Creation**: Verify that a `.png` file is actually created on disk in a temporary directory during testing.
- **Matplotlib State**: Verify that `plt.close()` was called and global state is not contaminated.
- **Validation Tests**: Ensure empty/invalid DataFrames raise the correct exceptions.
- **Headless Safety**: Tests run seamlessly in CI without requiring an active display server (using `Agg` backend).

## 16. File Scope
Files modified:
- `src/analyzers/graph_generator.py`
- `tests/test_graph_generator.py`

Files explicitly protected (NO MODIFICATION):
- `src/analyzers/performance_timer.py`
- `src/analyzers/metric_collector.py`
- `src/analyzers/security_evaluator.py`
- `src/utils/file_handler.py`

## 17. Implementation Sequence
1. Ensure dependencies (`matplotlib`, `pandas`) exist in requirements (do not install now).
2. Set up `graph_generator.py` with standard imports and `matplotlib.use('Agg')` for safety.
3. Write DataFrame validation utilities.
4. Implement `generate_key_size_comparison` + save.
5. Implement `generate_mode_comparison` + save.
6. Implement `generate_throughput_analysis` + save.
7. Write and execute test suite covering successful PNG generation and error states.
8. Verify no frozen components were touched.

## 18. Open Decisions
No blocking decisions remain. The scope is now strictly confined to the authoritative performance graphs and PNG artifact generation.

## 19. Risks
- Matplotlib `Agg` backend must be explicitly defined if running in a pure headless environment without X11/Wayland.
- Directory existence for output paths must be handled gracefully to prevent `FileNotFoundError` during PNG saving.

## 20. Definition of Done
- 3 required analytical methods are implemented.
- Each method successfully writes a formatted PNG graph to disk and returns the file path.
- Tests prove deterministic sorting and proper PNG generation.
- No modifications are made to any other layer of the repository.

## 21. Final Verdict
🟢 PASS — IMPLEMENTATION READY
