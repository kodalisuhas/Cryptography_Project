import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

class GraphGenerator:
    """Constructs Matplotlib visualization artifacts from collected metrics."""
    
    @staticmethod
    def generate_key_size_comparison(summary_df: pd.DataFrame) -> plt.Figure:
        if not isinstance(summary_df, pd.DataFrame):
            raise TypeError("summary_df must be a pandas DataFrame")
        if summary_df.empty:
            raise ValueError("summary_df is empty")
            
        required_cols = ['key_size', 'mode', 'data_size_bytes', 'mean_time_ms']
        for col in required_cols:
            if col not in summary_df.columns:
                raise ValueError(f"Missing required column: {col}")
                
        if summary_df['data_size_bytes'].nunique() > 1:
            raise ValueError("Key-size comparison requires a single benchmark data size. Multiple data_size_bytes found.")
            
        # Validate uniqueness
        if summary_df.duplicated(subset=['key_size', 'mode', 'data_size_bytes']).any():
            raise ValueError("Duplicate configurations found for key_size, mode, and data_size_bytes.")
            
        # We need deterministic modes and key sizes
        modes = sorted(summary_df['mode'].unique().tolist())
        key_sizes = sorted(summary_df['key_size'].unique().tolist())
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bar_width = 0.35
        x = np.arange(len(key_sizes))
        
        for i, mode in enumerate(modes):
            mode_data = summary_df[summary_df['mode'] == mode].sort_values(by='key_size')
            
            y_data = []
            for ks in key_sizes:
                row = mode_data[mode_data['key_size'] == ks]
                if not row.empty:
                    y_data.append(row['mean_time_ms'].values[0])
                else:
                    y_data.append(np.nan)
                    
            offset = bar_width * i - (bar_width * (len(modes) - 1) / 2)
            ax.bar(x + offset, y_data, bar_width, label=mode)
            
        ax.set_xlabel("Key Size")
        ax.set_ylabel("Time (ms)")
        ax.set_title("AES Performance by Key Size")
        ax.set_xticks(x)
        ax.set_xticklabels(key_sizes)
        if len(modes) > 1:
            ax.legend()
            
        return fig

    @staticmethod
    def generate_mode_comparison(summary_df: pd.DataFrame) -> plt.Figure:
        if not isinstance(summary_df, pd.DataFrame):
            raise TypeError("summary_df must be a pandas DataFrame")
        if summary_df.empty:
            raise ValueError("summary_df is empty")
            
        required_cols = ['mode', 'key_size', 'data_size_bytes', 'mean_time_ms']
        for col in required_cols:
            if col not in summary_df.columns:
                raise ValueError(f"Missing required column: {col}")
                
        if summary_df['data_size_bytes'].nunique() > 1:
            raise ValueError("Mode comparison requires a single benchmark data size. Multiple data_size_bytes found.")
            
        # Validate uniqueness
        if summary_df.duplicated(subset=['mode', 'key_size', 'data_size_bytes']).any():
            raise ValueError("Duplicate configurations found for mode, key_size, and data_size_bytes.")
            
        modes = sorted(summary_df['mode'].unique().tolist())
        key_sizes = sorted(summary_df['key_size'].unique().tolist())
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bar_width = 0.35
        x = np.arange(len(modes))
        
        for i, ks in enumerate(key_sizes):
            ks_data = summary_df[summary_df['key_size'] == ks].sort_values(by='mode')
            
            y_data = []
            for mode in modes:
                row = ks_data[ks_data['mode'] == mode]
                if not row.empty:
                    y_data.append(row['mean_time_ms'].values[0])
                else:
                    y_data.append(np.nan)
                    
            offset = bar_width * i - (bar_width * (len(key_sizes) - 1) / 2)
            ax.bar(x + offset, y_data, bar_width, label=f"AES-{ks}")
            
        ax.set_xlabel("Mode")
        ax.set_ylabel("Time (ms)")
        ax.set_title("AES Performance by Mode")
        ax.set_xticks(x)
        ax.set_xticklabels(modes)
        if len(key_sizes) > 1:
            ax.legend()
            
        return fig

    @staticmethod
    def generate_throughput_analysis(summary_df: pd.DataFrame) -> plt.Figure:
        if not isinstance(summary_df, pd.DataFrame):
            raise TypeError("summary_df must be a pandas DataFrame")
        if summary_df.empty:
            raise ValueError("summary_df is empty")
            
        required_cols = ['data_size_bytes', 'throughput_mb_s', 'key_size', 'mode']
        for col in required_cols:
            if col not in summary_df.columns:
                raise ValueError(f"Missing required column: {col}")
                
        if summary_df.duplicated(subset=['data_size_bytes', 'key_size', 'mode']).any():
            raise ValueError("Duplicate configurations found for data_size_bytes, key_size, and mode.")
            
        fig, ax = plt.subplots(figsize=(10, 6))
        
        unique_configs = summary_df[['key_size', 'mode']].drop_duplicates()
        unique_configs = unique_configs.sort_values(by=['key_size', 'mode'])
        
        for _, row in unique_configs.iterrows():
            ks = row['key_size']
            mode = row['mode']
            
            series_data = summary_df[(summary_df['key_size'] == ks) & (summary_df['mode'] == mode)]
            series_data = series_data.sort_values(by='data_size_bytes')
            
            label = f"AES-{ks}-{mode}"
            ax.plot(series_data['data_size_bytes'], series_data['throughput_mb_s'], marker='o', label=label)
            
        ax.set_xlabel("Data Size (bytes)")
        ax.set_ylabel("Throughput (MB/s)")
        ax.set_title("AES Throughput Scaling")
        ax.legend()
        
        return fig
