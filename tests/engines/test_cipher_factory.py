import pytest
from src.engines.cipher_factory import CipherFactory
from src.core.aes_cipher import AESCipher

def test_cipher_factory_creates_aes_cipher():
    factory = CipherFactory()
    cipher = factory.create_cipher("AES", 128, "CBC")
    assert isinstance(cipher, AESCipher)
    assert cipher.key_size == 128
    assert cipher.mode == "CBC"

def test_cipher_factory_unknown_algorithm():
    factory = CipherFactory()
    with pytest.raises(ValueError, match="Unsupported algorithm: UNKNOWN"):
        factory.create_cipher("UNKNOWN", 128, "CBC")

def test_cipher_factory_case_insensitive():
    factory = CipherFactory()
    cipher = factory.create_cipher("aes", 128, "cbc")
    assert isinstance(cipher, AESCipher)
    assert cipher.key_size == 128
    assert cipher.mode == "CBC"

def test_cipher_factory_returns_fresh_instance():
    factory = CipherFactory()
    cipher1 = factory.create_cipher("AES", 128, "CBC")
    cipher2 = factory.create_cipher("AES", 128, "CBC")
    assert cipher1 is not cipher2
