import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.analyzers.graph_generator import GraphGenerator

@pytest.fixture
def sample_performance_df():
    data = [
        {'key_size': 128, 'mode': 'CBC', 'mean_time_ms': 10.5, 'data_size_bytes': 1024},
        {'key_size': 128, 'mode': 'ECB', 'mean_time_ms': 9.2, 'data_size_bytes': 1024},
        {'key_size': 192, 'mode': 'CBC', 'mean_time_ms': 12.1, 'data_size_bytes': 1024},
        {'key_size': 192, 'mode': 'ECB', 'mean_time_ms': 11.0, 'data_size_bytes': 1024},
        {'key_size': 256, 'mode': 'CBC', 'mean_time_ms': 14.5, 'data_size_bytes': 1024},
        {'key_size': 256, 'mode': 'ECB', 'mean_time_ms': 13.2, 'data_size_bytes': 1024},
    ]
    return pd.DataFrame(data)

@pytest.fixture
def sample_throughput_df():
    data = [
        {'key_size': 128, 'mode': 'CBC', 'mean_time_ms': 5.0, 'data_size_bytes': 1024, 'throughput_mb_s': 50.0},
        {'key_size': 128, 'mode': 'CBC', 'mean_time_ms': 45.0, 'data_size_bytes': 10240, 'throughput_mb_s': 55.0},
        {'key_size': 128, 'mode': 'CBC', 'mean_time_ms': 420.0, 'data_size_bytes': 102400, 'throughput_mb_s': np.nan},
        {'key_size': 128, 'mode': 'ECB', 'mean_time_ms': 4.5, 'data_size_bytes': 1024, 'throughput_mb_s': 52.0},
        {'key_size': 128, 'mode': 'ECB', 'mean_time_ms': 40.0, 'data_size_bytes': 10240, 'throughput_mb_s': 58.0},
    ]
    return pd.DataFrame(data)

class TestGraphGenerator:
    
    # ------------------ Key Size Comparison Tests ------------------
    def test_key_size_comparison_valid_and_artists(self, sample_performance_df):
        df_copy = sample_performance_df.copy()
        fig = GraphGenerator.generate_key_size_comparison(sample_performance_df)
        
        assert isinstance(fig, plt.Figure)
        ax = fig.gca()
        assert ax.get_title() == "AES Performance by Key Size"
        
        # Verify deterministic ordering and content
        x_labels = [t.get_text() for t in ax.get_xticklabels()]
        assert x_labels == ['128', '192', '256']
        
        # There should be two container objects for the two modes (CBC, ECB)
        bars = ax.containers
        assert len(bars) == 2
        
        # Verify legend (modes deterministic/alphabetical)
        legend = ax.get_legend()
        assert legend is not None
        labels = [text.get_text() for text in legend.get_texts()]
        assert labels == ['CBC', 'ECB']
        
        # Verify values plotted for CBC
        cbc_heights = [b.get_height() for b in bars[0]]
        assert cbc_heights == [10.5, 12.1, 14.5]
        
        # Verify values plotted for ECB
        ecb_heights = [b.get_height() for b in bars[1]]
        assert ecb_heights == [9.2, 11.0, 13.2]

        pd.testing.assert_frame_equal(sample_performance_df, df_copy)
        plt.close(fig)

    def test_key_size_multiple_data_sizes_rejected(self, sample_performance_df):
        # Add a row with a different data size
        new_row = pd.DataFrame([{'key_size': 128, 'mode': 'CBC', 'mean_time_ms': 100.0, 'data_size_bytes': 10240}])
        df = pd.concat([sample_performance_df, new_row], ignore_index=True)
        
        with pytest.raises(ValueError, match="Multiple data_size_bytes found"):
            GraphGenerator.generate_key_size_comparison(df)

    def test_key_size_duplicate_coordinates_rejected(self, sample_performance_df):
        # Same data size, duplicate coordinates
        new_row = pd.DataFrame([{'key_size': 128, 'mode': 'CBC', 'mean_time_ms': 11.0, 'data_size_bytes': 1024}])
        df = pd.concat([sample_performance_df, new_row], ignore_index=True)
        
        with pytest.raises(ValueError, match="Duplicate configurations found"):
            GraphGenerator.generate_key_size_comparison(df)

    # ------------------ Mode Comparison Tests ------------------
    def test_mode_comparison_valid_and_artists(self, sample_performance_df):
        df_copy = sample_performance_df.copy()
        fig = GraphGenerator.generate_mode_comparison(sample_performance_df)
        
        assert isinstance(fig, plt.Figure)
        ax = fig.gca()
        assert ax.get_title() == "AES Performance by Mode"
        
        # Modes deterministic
        x_labels = [t.get_text() for t in ax.get_xticklabels()]
        assert x_labels == ['CBC', 'ECB']
        
        # There should be three container objects for key_sizes (128, 192, 256)
        bars = ax.containers
        assert len(bars) == 3
        
        # Verify legend
        legend = ax.get_legend()
        assert legend is not None
        labels = [text.get_text() for text in legend.get_texts()]
        assert labels == ['AES-128', 'AES-192', 'AES-256']
        
        # Verify heights for 128, 192, and 256 mapped to [CBC, ECB]
        ks128_heights = [b.get_height() for b in bars[0]]
        assert ks128_heights == [10.5, 9.2]
        
        ks192_heights = [b.get_height() for b in bars[1]]
        assert ks192_heights == [12.1, 11.0]
        
        ks256_heights = [b.get_height() for b in bars[2]]
        assert ks256_heights == [14.5, 13.2]
        
        pd.testing.assert_frame_equal(sample_performance_df, df_copy)
        plt.close(fig)

    def test_mode_multiple_data_sizes_rejected(self, sample_performance_df):
        new_row = pd.DataFrame([{'key_size': 128, 'mode': 'CBC', 'mean_time_ms': 100.0, 'data_size_bytes': 10240}])
        df = pd.concat([sample_performance_df, new_row], ignore_index=True)
        
        with pytest.raises(ValueError, match="Multiple data_size_bytes found"):
            GraphGenerator.generate_mode_comparison(df)

    def test_mode_duplicate_coordinates_rejected(self, sample_performance_df):
        new_row = pd.DataFrame([{'key_size': 128, 'mode': 'CBC', 'mean_time_ms': 11.0, 'data_size_bytes': 1024}])
        df = pd.concat([sample_performance_df, new_row], ignore_index=True)
        
        with pytest.raises(ValueError, match="Duplicate configurations found"):
            GraphGenerator.generate_mode_comparison(df)

    # ------------------ Throughput Analysis Tests ------------------
    def test_throughput_analysis_valid_and_artists(self, sample_throughput_df):
        df_copy = sample_throughput_df.copy()
        fig = GraphGenerator.generate_throughput_analysis(sample_throughput_df)
        
        assert isinstance(fig, plt.Figure)
        ax = fig.gca()
        assert ax.get_title() == "AES Throughput Scaling"
        
        lines = ax.get_lines()
        # CBC and ECB for 128 bit -> 2 series
        assert len(lines) == 2
        
        # Deterministic series ordering (AES-128-CBC, AES-128-ECB)
        assert lines[0].get_label() == "AES-128-CBC"
        assert lines[1].get_label() == "AES-128-ECB"
        
        # Check ascending data sizes and correct values
        cbc_xdata = lines[0].get_xdata()
        cbc_ydata = lines[0].get_ydata()
        np.testing.assert_array_equal(cbc_xdata, [1024, 10240, 102400])
        
        # Check NaN behavior -> should be natively present in ydata, not zeroed/interpolated
        assert cbc_ydata[0] == 50.0
        assert cbc_ydata[1] == 55.0
        assert np.isnan(cbc_ydata[2])
        
        pd.testing.assert_frame_equal(sample_throughput_df, df_copy)
        plt.close(fig)

    def test_throughput_duplicate_coordinates_rejected(self, sample_throughput_df):
        new_row = pd.DataFrame([{'key_size': 128, 'mode': 'CBC', 'data_size_bytes': 1024, 'throughput_mb_s': 99.0}])
        df = pd.concat([sample_throughput_df, new_row], ignore_index=True)
        
        with pytest.raises(ValueError, match="Duplicate configurations found"):
            GraphGenerator.generate_throughput_analysis(df)

    # ------------------ General Validation Tests ------------------
    def test_invalid_type(self):
        with pytest.raises(TypeError):
            GraphGenerator.generate_key_size_comparison([1, 2, 3])
            
        with pytest.raises(TypeError):
            GraphGenerator.generate_mode_comparison("not a dataframe")
            
        with pytest.raises(TypeError):
            GraphGenerator.generate_throughput_analysis(None)

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        with pytest.raises(ValueError, match="empty"):
            GraphGenerator.generate_key_size_comparison(df)
            
        with pytest.raises(ValueError, match="empty"):
            GraphGenerator.generate_mode_comparison(df)
            
        with pytest.raises(ValueError, match="empty"):
            GraphGenerator.generate_throughput_analysis(df)

    def test_missing_columns_key_size(self):
        df = pd.DataFrame({'mode': ['CBC'], 'mean_time_ms': [10.0], 'data_size_bytes': [1024]})
        with pytest.raises(ValueError, match="Missing required column: key_size"):
            GraphGenerator.generate_key_size_comparison(df)

    def test_missing_columns_mode_comparison(self):
        df = pd.DataFrame({'key_size': [128], 'mean_time_ms': [10.0], 'data_size_bytes': [1024]})
        with pytest.raises(ValueError, match="Missing required column: mode"):
            GraphGenerator.generate_mode_comparison(df)

    def test_missing_columns_throughput(self):
        df = pd.DataFrame({'key_size': [128], 'mode': ['CBC'], 'data_size_bytes': [1024]})
        with pytest.raises(ValueError, match="Missing required column: throughput_mb_s"):
            GraphGenerator.generate_throughput_analysis(df)

    def test_persistence_boundary(self, sample_performance_df, monkeypatch):
        # We want to prove that none of the matplotlib persistence methods are called.
        import matplotlib.pyplot as plt
        
        called = {"savefig": False, "show": False, "close": False}
        
        def mock_savefig(*args, **kwargs):
            called["savefig"] = True
            
        def mock_show(*args, **kwargs):
            called["show"] = True
            
        def mock_close(*args, **kwargs):
            called["close"] = True

        monkeypatch.setattr(plt.Figure, "savefig", mock_savefig)
        monkeypatch.setattr(plt, "savefig", mock_savefig)
        monkeypatch.setattr(plt, "show", mock_show)
        monkeypatch.setattr(plt, "close", mock_close)

        # Generating should not trigger persistence commands
        fig = GraphGenerator.generate_key_size_comparison(sample_performance_df)
        
        assert called["savefig"] is False
        assert called["show"] is False
        assert called["close"] is False

