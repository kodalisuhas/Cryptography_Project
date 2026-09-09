import pytest
import numpy as np
import pandas as pd
from src.analyzers.metric_collector import MetricCollector

def test_a_basic_statistics():
    collector = MetricCollector()
    # 30 deterministic values
    raw_times = [
        1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
        11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0,
        21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0
    ]
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1048576, 'raw_times_ms': raw_times
    })
    
    df = collector.get_summary_dataframe()
    assert len(df) == 1
    
    row = df.iloc[0]
    assert row['count'] == 30
    assert 'count' in df.columns
    assert row['mean_time_ms'] == np.mean(raw_times)
    assert row['median_time_ms'] == np.median(raw_times)
    assert row['std_dev_time_ms'] == np.std(raw_times, ddof=1)
    assert row['min_time_ms'] == 1.0
    assert row['max_time_ms'] == 30.0
    assert row['q1_ms'] == collector._calculate_percentile(raw_times, 25)
    assert row['q3_ms'] == collector._calculate_percentile(raw_times, 75)
    assert row['iqr_ms'] == row['q3_ms'] - row['q1_ms']

def test_b_quartile_convention():
    collector = MetricCollector()
    raw_times = [10.0, 15.0, 20.0, 25.0]
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1048576, 'raw_times_ms': raw_times
    })
    df = collector.get_summary_dataframe()
    row = df.iloc[0]
    
    # Calculate expected linear percentiles
    try:
        expected_q1 = np.percentile(raw_times, 25, method="linear")
        expected_q3 = np.percentile(raw_times, 75, method="linear")
    except TypeError:
        expected_q1 = np.percentile(raw_times, 25, interpolation="linear")
        expected_q3 = np.percentile(raw_times, 75, interpolation="linear")
        
    assert row['q1_ms'] == expected_q1
    assert row['q3_ms'] == expected_q3

def test_c_sample_standard_deviation():
    collector = MetricCollector()
    raw_times = [10.0, 12.0, 14.0]
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1048576, 'raw_times_ms': raw_times
    })
    df = collector.get_summary_dataframe()
    row = df.iloc[0]
    
    expected_sample_std = np.std(raw_times, ddof=1)
    expected_pop_std = np.std(raw_times, ddof=0)
    
    assert row['std_dev_time_ms'] == expected_sample_std
    assert row['std_dev_time_ms'] != expected_pop_std

def test_d_tukey_fences_and_f_outlier_preservation():
    collector = MetricCollector()
    # Base dataset with tight IQR
    raw_times = [10.0]*28 + [1.0, 100.0]  # 28 typical values, 1 low outlier, 1 high outlier
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1048576, 'raw_times_ms': raw_times
    })
    
    # Summary
    df_summary = collector.get_summary_dataframe()
    assert df_summary.iloc[0]['outlier_count'] == 2
    
    # Q1=10, Q3=10, IQR=0. Fences=10.
    # So 1.0 and 100.0 are strictly outside [10, 10].
    
    # F: Preservation
    # Ensure mean includes the 100.0 and 1.0
    expected_mean = sum(raw_times) / 30.0
    assert df_summary.iloc[0]['mean_time_ms'] == expected_mean
    
    df_raw = collector.get_raw_dataframe()
    assert len(df_raw) == 30
    
    outliers = df_raw[df_raw['is_outlier']]
    assert len(outliers) == 2
    assert set(outliers['elapsed_time_ms']) == {1.0, 100.0}

def test_e_fence_boundaries():
    collector = MetricCollector()
    # Create a deterministic dataset.
    # Q1=10, Q3=20 -> IQR=10. LF=-5, UF=35.
    # We include exactly -5.0 and 35.0 so they fall on the fences.
    # Dataset: [-5.0, 10.0, 10.0, 20.0, 20.0, 35.0]
    # For a list of 6 elements: 25th percentile (pos 1.25) -> 10.0, 75th percentile (pos 3.75) -> 20.0
    raw_times = [-5.0, 10.0, 10.0, 20.0, 20.0, 35.0]
    
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1048576, 'raw_times_ms': raw_times
    })
    
    df_sum = collector.get_summary_dataframe()
    row = df_sum.iloc[0]
    # Double check our math was right
    assert row['q1_ms'] == 10.0
    assert row['q3_ms'] == 20.0
    assert row['iqr_ms'] == 10.0
    
    # Check outlier count is 0
    assert row['outlier_count'] == 0
    
    # Check raw observations are not flagged
    df_raw = collector.get_raw_dataframe()
    fence_rows = df_raw[df_raw['elapsed_time_ms'].isin([-5.0, 35.0])]
    assert not any(fence_rows['is_outlier'])

def test_g_raw_observation_count():
    collector = MetricCollector()
    raw_times = [1.0] * 30
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1024, 'raw_times_ms': raw_times
    })
    df = collector.get_raw_dataframe()
    assert len(df) == 30
    assert list(df['iteration_index']) == list(range(30))

def test_h_multiple_configurations():
    collector = MetricCollector()
    raw1 = [1.0] * 30
    raw2 = [2.0] * 30
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1024, 'raw_times_ms': raw1
    })
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 256, 'mode': 'ECB',
        'data_size_bytes': 2048, 'raw_times_ms': raw2
    })
    
    df_sum = collector.get_summary_dataframe()
    assert len(df_sum) == 2
    
    df_raw = collector.get_raw_dataframe()
    assert len(df_raw) == 60
    assert list(df_raw['key_size'].unique()) == [128, 256]

def test_i_throughput():
    collector = MetricCollector()
    # 1 MB data, 1000 ms time -> 1 MB/s
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1048576, 'raw_times_ms': [1000.0] * 30
    })
    df = collector.get_summary_dataframe()
    assert pytest.approx(df.iloc[0]['throughput_mb_s'], 0.001) == 1.0

def test_j_zero_non_positive_throughput():
    collector = MetricCollector()
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1048576, 'raw_times_ms': [0.0] * 30
    })
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1048576, 'raw_times_ms': [-5.0] * 30
    })
    df = collector.get_summary_dataframe()
    assert pd.isna(df.iloc[0]['throughput_mb_s'])
    assert pd.isna(df.iloc[1]['throughput_mb_s'])

def test_k_identical_values():
    collector = MetricCollector()
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1024, 'raw_times_ms': [5.0] * 30
    })
    df = collector.get_summary_dataframe()
    assert df.iloc[0]['iqr_ms'] == 0.0
    assert df.iloc[0]['outlier_count'] == 0

def test_l_missing_invalid_input():
    collector = MetricCollector()
    with pytest.raises(ValueError):
        collector.add_metric({'algorithm': 'AES'})  # Missing fields
        
    with pytest.raises(ValueError):
        collector.add_metric({
            'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
            'data_size_bytes': 1024, 'raw_times_ms': []  # Empty array
        })
        
    with pytest.raises(ValueError):
        collector.add_metric({
            'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
            'data_size_bytes': -1, 'raw_times_ms': [1.0]  # Negative size
        })

def test_m_missing_memory():
    collector = MetricCollector()
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1024, 'raw_times_ms': [1.0]
    })
    df = collector.get_summary_dataframe()
    assert pd.isna(df.iloc[0]['memory_delta_mb'])

def test_n_no_file_io():
    collector = MetricCollector()
    with pytest.raises(NotImplementedError):
        collector.export_to_csv("test.csv")

def test_o_legacy_get_dataframe_compatibility():
    collector = MetricCollector()
    collector.add_metric({
        'algorithm': 'AES', 'key_size': 128, 'mode': 'CBC',
        'data_size_bytes': 1024, 'raw_times_ms': [1.0]
    })
    df1 = collector.get_dataframe()
    df2 = collector.get_summary_dataframe()
    assert df1.equals(df2)
