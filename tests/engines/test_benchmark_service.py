import pytest
import unittest.mock
from src.engines.benchmark_service import BenchmarkService
from src.engines.cipher_factory import CipherFactory
from src.engines.cipher_interface import SymmetricCipherInterface

class MockCipher(SymmetricCipherInterface):
    def __init__(self, key_size, mode):
        self.key_size = key_size
        self.mode = mode
        self.encrypt_calls = 0
        
    def generate_key(self) -> bytes:
        return b"K" * (self.key_size // 8)
        
    def generate_iv(self) -> bytes:
        if self.mode == "ECB":
            raise ValueError("ECB mode does not use IV")
        return b"I" * 16
        
    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        self.encrypt_calls += 1
        return b"ENC_" + plaintext
        
    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        return ciphertext

class MockCipherFactory(CipherFactory):
    def __init__(self):
        self.ciphers_created = []
        
    def create_cipher(self, algorithm: str, key_size: int, mode: str) -> SymmetricCipherInterface:
        cipher = MockCipher(key_size, mode.upper())
        self.ciphers_created.append(cipher)
        return cipher

@unittest.mock.patch('src.engines.benchmark_service.PerformanceTimer.measure_time_with_warmup')
def test_benchmark_service_run_suite(mock_decorator):
    # Mocking the PerformanceTimer decorator
    def mock_decorator_impl():
        def decorator(func):
            def wrapper(*args, **kwargs):
                func(*args, **kwargs) # call it once to verify cipher behavior
                return None, {'raw_times_ms': [1.0, 2.0, 3.0]}
            return wrapper
        return decorator
        
    mock_decorator.side_effect = mock_decorator_impl

    factory = MockCipherFactory()
    service = BenchmarkService(factory=factory)
    configs = [
        {"algorithm": "AES", "key_size": 128, "mode": "CBC"},
        {"algorithm": "AES", "key_size": 256, "mode": "ECB"}
    ]
    payloads = [b"hello", b"world"]
    
    collector = service.run_performance_suite(configs, payloads)
    df = collector.get_summary_dataframe()
    
    assert len(df) == 4
    
    # 128 CBC payload 1
    row1 = df.iloc[0]
    assert row1['algorithm'] == 'AES'
    assert row1['key_size'] == 128
    assert row1['mode'] == 'CBC'
    assert row1['data_size_bytes'] == 5
    
    # verify one cipher per config, reused across payloads
    assert len(factory.ciphers_created) == 2
    assert factory.ciphers_created[0].encrypt_calls == 2
    assert factory.ciphers_created[1].encrypt_calls == 2
