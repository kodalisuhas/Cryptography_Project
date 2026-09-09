from src.engines.cipher_factory import CipherFactory
from src.analyzers.performance_timer import PerformanceTimer
from src.analyzers.metric_collector import MetricCollector

class BenchmarkService:
    def __init__(self, factory: CipherFactory = None):
        self.factory = factory or CipherFactory()
        
    def run_performance_suite(self, configs: list[dict], data_payloads: list[bytes]) -> MetricCollector:
        """
        Run performance benchmarks across configurations and payloads.
        Returns the populated MetricCollector.
        """
        collector = MetricCollector()
        
        for config in configs:
            # One configuration -> one fresh cipher instance
            cipher = self.factory.create_cipher(config["algorithm"], config["key_size"], config["mode"])
            
            for payload in data_payloads:
                # Key and IV generation outside the measured function
                key = cipher.generate_key()
                iv = cipher.generate_iv() if config["mode"].upper() == "CBC" else None
                
                # Apply the frozen PerformanceTimer decorator with defaults (30 iterations, 5 warmups)
                @PerformanceTimer.measure_time_with_warmup()
                def _measured_encrypt():
                    cipher.encrypt(payload, key, iv)
                    
                # Execute measured block
                _, stats_dict = _measured_encrypt()
                
                # Format exactly as MetricCollector expects, omitting the optional memory metric
                metric_data = {
                    'algorithm': config["algorithm"],
                    'key_size': config["key_size"],
                    'mode': config["mode"],
                    'data_size_bytes': len(payload),
                    'raw_times_ms': stats_dict['raw_times_ms']
                }
                collector.add_metric(metric_data)
                
        return collector
