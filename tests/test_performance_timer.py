import pytest
from unittest.mock import patch, call
from src.analyzers.performance_timer import PerformanceTimer


class TestPerformanceTimer:
    
    def test_default_configuration_and_observation_count(self):
        """Test A, B, F, L: Default config (5 warmup, 30 iterations), raw observation count, return value, no batching."""
        call_count = 0
        
        @PerformanceTimer.measure_time_with_warmup()
        def dummy_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result, stats = dummy_function(10)
        
        assert call_count == 35  # 5 warmup + 30 measured
        assert result == 20
        assert "raw_times_ms" in stats
        assert len(stats["raw_times_ms"]) == 30
        assert all(isinstance(t, float) for t in stats["raw_times_ms"])

    @patch("time.perf_counter")
    def test_perf_counter_and_timing_boundary(self, mock_perf_counter):
        """Test C, D: verify perf_counter is used properly and measures correct boundaries."""
        # 2 calls per iteration (start, end). We have 2 iterations, 1 warmup.
        # warmup doesn't use perf_counter. 
        # Measured: 2 iterations * 2 = 4 calls to perf_counter.
        # We will mock it to return increasing values.
        mock_perf_counter.side_effect = [
            1.0, 1.5,  # iteration 1: diff = 0.5s = 500ms
            2.0, 2.2,  # iteration 2: diff = 0.2s = 200ms
        ]
        
        call_order = []
        
        @PerformanceTimer.measure_time_with_warmup(iterations=2, warmup=1)
        def target_func():
            call_order.append("target_invoked")
            return "ok"
            
        result, stats = target_func()
        
        # 1 warmup + 2 measured
        assert call_order == ["target_invoked", "target_invoked", "target_invoked"]
        assert mock_perf_counter.call_count == 4
        assert stats["raw_times_ms"] == pytest.approx([500.0, 200.0])

    def test_argument_forwarding(self):
        """Test E: positional and keyword arguments are preserved."""
        @PerformanceTimer.measure_time_with_warmup(iterations=1, warmup=0)
        def target_func(a, b, c=None):
            return f"{a}-{b}-{c}"
            
        result, _ = target_func(1, 2, c="hello")
        assert result == "1-2-hello"

    def test_invalid_iterations(self):
        """Test G: Invalid iterations."""
        with pytest.raises(ValueError, match="Iterations must be at least 1"):
            PerformanceTimer.measure_time_with_warmup(iterations=0)
            
        with pytest.raises(ValueError, match="Iterations must be at least 1"):
            PerformanceTimer.measure_time_with_warmup(iterations=-5)

    def test_invalid_warmup(self):
        """Test H: Invalid warmup."""
        with pytest.raises(ValueError, match="Warmup iterations cannot be negative"):
            PerformanceTimer.measure_time_with_warmup(warmup=-1)

    @patch("time.perf_counter")
    def test_zero_elapsed_time(self, mock_perf_counter):
        """Test I: Zero elapsed time."""
        # Both start and end are 1.0, diff = 0.0
        mock_perf_counter.side_effect = [1.0, 1.0]
        
        @PerformanceTimer.measure_time_with_warmup(iterations=1, warmup=0)
        def target_func():
            return "fast"
            
        result, stats = target_func()
        assert stats["raw_times_ms"] == [0.0]

    @patch("time.perf_counter")
    def test_very_small_elapsed_time(self, mock_perf_counter):
        """Test J: Very small elapsed time is not clamped."""
        # diff = 1e-9 seconds = 1e-6 ms
        mock_perf_counter.side_effect = [1.0, 1.0 + 1e-9]
        
        @PerformanceTimer.measure_time_with_warmup(iterations=1, warmup=0)
        def target_func():
            return "tiny"
            
        result, stats = target_func()
        assert stats["raw_times_ms"] == pytest.approx([1e-6])

    def test_target_exception(self):
        """Test K: Exception raised by target propagates."""
        class CustomError(Exception):
            pass
            
        @PerformanceTimer.measure_time_with_warmup(iterations=2, warmup=1)
        def error_func():
            raise CustomError("Intentional failure")
            
        with pytest.raises(CustomError, match="Intentional failure"):
            error_func()
            
    @patch("time.perf_counter")
    def test_context_timer(self, mock_perf_counter):
        mock_perf_counter.side_effect = [1.0, 1.5]
        
        with PerformanceTimer.context_timer() as timer:
            pass
            
        assert timer.elapsed_ms == 500.0
