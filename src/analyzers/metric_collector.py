from datetime import datetime
import numpy as np
import pandas as pd

class MetricCollector:
    """
    Collects and processes performance metrics to compute statistical aggregates,
    identifying outliers and calculating throughput based on raw benchmark data.
    """
    
    def __init__(self):
        self._summary_data = []
        self._raw_data = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _calculate_percentile(self, data, q):
        try:
            return np.percentile(data, q, method='linear')
        except TypeError:
            # Fallback for older numpy versions
            return np.percentile(data, q, interpolation='linear')

    def add_metric(self, metric_data: dict):
        """
        Add a metric entry from raw observations.
        
        Expected dictionary format:
        {
            'algorithm': str,
            'key_size': int,
            'mode': str,
            'data_size_bytes': int,
            'raw_times_ms': list[float],
            'memory_delta_mb': float  # Optional
        }
        """
        required_keys = ['algorithm', 'key_size', 'mode', 'data_size_bytes', 'raw_times_ms']
        for k in required_keys:
            if k not in metric_data:
                raise ValueError(f"Missing required key in metric_data: {k}")

        if not isinstance(metric_data['algorithm'], str):
            raise ValueError("algorithm must be a string")
        if not isinstance(metric_data['key_size'], int):
            raise ValueError("key_size must be an integer")
        if not isinstance(metric_data['mode'], str):
            raise ValueError("mode must be a string")
        if not isinstance(metric_data['data_size_bytes'], int):
            raise ValueError("data_size_bytes must be an integer")
        if not isinstance(metric_data['raw_times_ms'], list):
            raise ValueError("raw_times_ms must be a list")

        if 'memory_delta_mb' in metric_data and metric_data['memory_delta_mb'] is not None:
            if not isinstance(metric_data['memory_delta_mb'], (float, int)):
                raise ValueError("memory_delta_mb must be a float or int")

        data_size_bytes = metric_data['data_size_bytes']
        if data_size_bytes < 0:
            raise ValueError("data_size_bytes cannot be negative")

        raw_times_ms = metric_data['raw_times_ms']
        if not raw_times_ms:
            raise ValueError("raw_times_ms cannot be empty")

        raw_array = np.array(raw_times_ms, dtype=float)
        
        # Calculate strict statistical metrics
        count = len(raw_array)
        mean = np.mean(raw_array)
        median = np.median(raw_array)
        std_dev = np.std(raw_array, ddof=1) if count > 1 else 0.0
        min_val = np.min(raw_array)
        max_val = np.max(raw_array)
        
        q1 = self._calculate_percentile(raw_array, 25)
        q3 = self._calculate_percentile(raw_array, 75)
        iqr = q3 - q1
        
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        
        # Identify outliers (strict inequality)
        outliers_mask = (raw_array < lower_fence) | (raw_array > upper_fence)
        outlier_count = int(np.sum(outliers_mask))
        
        # Calculate throughput
        if mean <= 0:
            throughput_mb_s = np.nan
        else:
            mb_size = data_size_bytes / 1048576.0
            time_s = mean / 1000.0
            throughput_mb_s = mb_size / time_s

        memory_delta_mb = metric_data.get('memory_delta_mb', np.nan)

        # Build summary dictionary
        summary_row = {
            'algorithm': metric_data['algorithm'],
            'key_size': metric_data['key_size'],
            'mode': metric_data['mode'],
            'data_size_bytes': data_size_bytes,
            'count': count,
            'mean_time_ms': mean,
            'median_time_ms': median,
            'std_dev_time_ms': std_dev,
            'min_time_ms': min_val,
            'max_time_ms': max_val,
            'q1_ms': q1,
            'q3_ms': q3,
            'iqr_ms': iqr,
            'outlier_count': outlier_count,
            'throughput_mb_s': throughput_mb_s,
            'memory_delta_mb': memory_delta_mb
        }
        self._summary_data.append(summary_row)
        
        # Build raw rows
        for i, (val, is_outlier) in enumerate(zip(raw_array, outliers_mask)):
            raw_row = {
                'algorithm': metric_data['algorithm'],
                'key_size': metric_data['key_size'],
                'mode': metric_data['mode'],
                'data_size_bytes': data_size_bytes,
                'iteration_index': i,
                'elapsed_time_ms': val,
                'is_outlier': bool(is_outlier)
            }
            self._raw_data.append(raw_row)

    def add_batch_metrics(self, metrics_list: list):
        """Add multiple metric entries."""
        for m in metrics_list:
            self.add_metric(m)

    def get_summary_dataframe(self) -> pd.DataFrame:
        """Return the summary DataFrame containing aggregated statistics."""
        df = pd.DataFrame(self._summary_data)
        if not df.empty:
            # Ensure specific column order if present
            cols = ['algorithm', 'key_size', 'mode', 'data_size_bytes', 'count',
                    'mean_time_ms', 'median_time_ms', 'std_dev_time_ms', 
                    'min_time_ms', 'max_time_ms', 'q1_ms', 'q3_ms', 'iqr_ms', 
                    'outlier_count', 'throughput_mb_s', 'memory_delta_mb']
            # Reindex to ensure all columns exist and are ordered
            df = df.reindex(columns=cols)
        return df

    def get_raw_dataframe(self) -> pd.DataFrame:
        """Return the raw observations DataFrame."""
        df = pd.DataFrame(self._raw_data)
        if not df.empty:
            cols = ['algorithm', 'key_size', 'mode', 'data_size_bytes', 
                    'iteration_index', 'elapsed_time_ms', 'is_outlier']
            df = df.reindex(columns=cols)
        return df

    def get_dataframe(self) -> pd.DataFrame:
        """
        Legacy alias for get_summary_dataframe to maintain API compatibility
        with earlier specifications without violating new boundaries.
        """
        return self.get_summary_dataframe()

    def export_to_csv(self, filepath: str = None):
        """
        Forbidden API call. Persistence layer is exclusively responsible for file I/O.
        """
        raise NotImplementedError(
            "export_to_csv has been deprecated in MetricCollector to enforce architecture boundaries. "
            "Please use FileHandler to export DataFrames generated by get_summary_dataframe or get_raw_dataframe."
        )

    def get_summary(self) -> dict:
        """
        Get high-level summary of all collected metrics.
        """
        df = self.get_summary_dataframe()
        if df.empty:
            return {
                'total_tests': 0,
                'algorithms_tested': [],
                'key_sizes_tested': [],
                'modes_tested': [],
                'avg_encryption_time_ms': 0.0,
                'max_throughput_mbps': 0.0,
                'min_memory_usage_mb': 0.0
            }

        return {
            'total_tests': len(df),
            'algorithms_tested': df['algorithm'].unique().tolist(),
            'key_sizes_tested': df['key_size'].unique().tolist(),
            'modes_tested': df['mode'].unique().tolist(),
            'avg_encryption_time_ms': float(df['mean_time_ms'].mean()),
            'max_throughput_mbps': float(df['throughput_mb_s'].max(skipna=True)) if not df['throughput_mb_s'].isna().all() else 0.0,
            'min_memory_usage_mb': float(df['memory_delta_mb'].min(skipna=True)) if not df['memory_delta_mb'].isna().all() else 0.0
        }

    def clear(self):
        """Clear all collected metrics."""
        self._summary_data = []
        self._raw_data = []
