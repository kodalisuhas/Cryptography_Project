import pytest
from src.engines.cipher_service import CipherService, EncryptionResult
from src.engines.cipher_factory import CipherFactory
from src.engines.cipher_interface import SymmetricCipherInterface

class MockCipher(SymmetricCipherInterface):
    def __init__(self, key_size, mode):
        self.key_size = key_size
        self.mode = mode
        
    def generate_key(self) -> bytes:
        return b"K" * (self.key_size // 8)
        
    def generate_iv(self) -> bytes:
        if self.mode == "ECB":
            raise ValueError("ECB mode does not use IV")
        return b"I" * 16
        
    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        return b"ENC_" + plaintext
        
    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        if ciphertext.startswith(b"ENC_"):
            return ciphertext[4:]
        return ciphertext

class MockCipherFactory(CipherFactory):
    def __init__(self):
        pass
        
    def create_cipher(self, algorithm: str, key_size: int, mode: str) -> SymmetricCipherInterface:
        return MockCipher(key_size, mode.upper())

def test_cipher_service_encrypt_cbc():
    service = CipherService(factory=MockCipherFactory())
    result = service.encrypt_data("AES", 128, "CBC", b"hello", b"K"*16, iv=b"V"*16)
    assert isinstance(result, EncryptionResult)
    assert result.ciphertext == b"ENC_hello"
    assert result.iv == b"V"*16

def test_cipher_service_encrypt_cbc_no_iv():
    service = CipherService(factory=MockCipherFactory())
    result = service.encrypt_data("AES", 128, "CBC", b"hello", b"K"*16)
    assert result.iv == b"I"*16

def test_cipher_service_encrypt_ecb():
    service = CipherService(factory=MockCipherFactory())
    result = service.encrypt_data("AES", 128, "ECB", b"hello", b"K"*16)
    assert result.iv is None

def test_cipher_service_decrypt():
    service = CipherService(factory=MockCipherFactory())
    plaintext = service.decrypt_data("AES", 128, "CBC", b"ENC_hello", b"K"*16, iv=b"V"*16)
    assert plaintext == b"hello"
    
def test_cipher_service_exception_propagation():
    class ExceptionCipher(MockCipher):
        def encrypt(self, plaintext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
            raise ValueError("Propagated Error")
            
    class ExceptionFactory(CipherFactory):
        def create_cipher(self, algorithm: str, key_size: int, mode: str) -> SymmetricCipherInterface:
            return ExceptionCipher(key_size, mode.upper())
            
    service = CipherService(factory=ExceptionFactory())
    with pytest.raises(ValueError, match="Propagated Error"):
        service.encrypt_data("AES", 128, "CBC", b"hello", b"K"*16, b"V"*16)
