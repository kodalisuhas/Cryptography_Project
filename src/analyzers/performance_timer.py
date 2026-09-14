import time
from functools import wraps

class PerformanceTimer:
    """
    Timer for accurately benchmarking cryptographic operations.
    """

    @staticmethod
    def measure_time_with_warmup(iterations: int = 30, warmup: int = 5):
        """
        Decorator with warmup and multiple iterations.
        
        Args:
            iterations (int): Number of measurement iterations
            warmup (int): Number of warmup iterations
            
        Returns:
            Wrapped function that returns (result, stats_dict)
            
        Raises:
            ValueError: If iterations < 1 or warmup < 0.
        """
        if iterations < 1:
            raise ValueError("Iterations must be at least 1")
        if warmup < 0:
            raise ValueError("Warmup iterations cannot be negative")

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Warmup phase
                for _ in range(warmup):
                    func(*args, **kwargs)

                raw_times_ms = []
                final_result = None

                # Measurement phase
                for i in range(iterations):
                    start = time.perf_counter()
                    result = func(*args, **kwargs)
                    end = time.perf_counter()
                    
                    elapsed_ms = (end - start) * 1000.0
                    raw_times_ms.append(elapsed_ms)
                    
                    # Retain the result of the last measured iteration
                    if i == iterations - 1:
                        final_result = result
                
                # In case iterations > 0 but we want to be safe if iterations was 0 (already guarded by ValueError)
                stats_dict = {
                    "raw_times_ms": raw_times_ms
                }
                
                return final_result, stats_dict
            return wrapper
        return decorator

    @staticmethod
    def context_timer():
        """
        Context manager for timing code blocks.
        
        Usage:
            with PerformanceTimer.context_timer() as timer:
                # Code to measure
                result = encrypt(data)
            print(f"Time: {timer.elapsed_ms:.2f} ms")
        """
        class TimerContext:
            def __init__(self):
                self.elapsed_ms = 0.0
                self._start = 0.0

            def __enter__(self):
                self._start = time.perf_counter()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                end = time.perf_counter()
                self.elapsed_ms = (end - self._start) * 1000.0

        return TimerContext()
