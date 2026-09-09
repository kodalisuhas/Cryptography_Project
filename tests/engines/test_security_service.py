import pytest
import unittest.mock
from src.engines.security_service import SecurityService
from src.engines.cipher_factory import CipherFactory

def flip_bit(b: bytes, index: int) -> bytes:
    mutated = bytearray(b)
    mutated[index // 8] ^= (1 << (index % 8))
    return bytes(mutated)

def test_security_service_integration_aes_128_cbc():
    service = SecurityService(factory=CipherFactory())
    configs = [{"algorithm": "AES", "key_size": 128, "mode": "CBC"}]
    
    pt1 = b"P" * 16
    pt2 = flip_bit(pt1, 0)
    k1 = b"K" * 16
    k2 = flip_bit(k1, 0)
    img = b"BM" + b"\x00" * 52 # dummy bmp
    iv = b"V" * 16
    
    results = service.run_security_suite(configs, pt1, pt2, k1, k2, img, iv)
    assert "AES-128-CBC" in results
    assert isinstance(results["AES-128-CBC"]["avalanche_effect"], float)
    assert isinstance(results["AES-128-CBC"]["key_sensitivity"], float)
    assert "ecb_weakness" not in results["AES-128-CBC"]

def test_security_service_integration_aes_128_ecb():
    service = SecurityService(factory=CipherFactory())
    configs = [{"algorithm": "AES", "key_size": 128, "mode": "ECB"}]
    
    pt1 = b"P" * 16
    pt2 = flip_bit(pt1, 0)
    k1 = b"K" * 16
    k2 = flip_bit(k1, 0)
    
    # Minimal valid BMP for ecb_weakness
    # 54 byte header + 4 bytes of pixel data
    img = bytearray(b"BM" + b"\x00"*56)
    img[0x02:0x06] = (58).to_bytes(4, 'little')
    img[0x0A:0x0E] = (54).to_bytes(4, 'little')
    img[0x0E:0x12] = (40).to_bytes(4, 'little')
    img[0x12:0x16] = (1).to_bytes(4, 'little', signed=True)
    img[0x16:0x1A] = (1).to_bytes(4, 'little', signed=True)
    img[0x1A:0x1C] = (1).to_bytes(2, 'little')
    img[0x1C:0x1E] = (24).to_bytes(2, 'little')
    
    iv = b"V" * 16
    
    results = service.run_security_suite(configs, pt1, pt2, k1, k2, img, iv)
    assert "AES-128-ECB" in results
    assert isinstance(results["AES-128-ECB"]["avalanche_effect"], float)
    assert isinstance(results["AES-128-ECB"]["key_sensitivity"], float)
    assert "ecb_weakness" in results["AES-128-ECB"]
    assert "cbc_ciphertext" in results["AES-128-ECB"]["ecb_weakness"]

def test_security_service_key_size_mismatch_fails():
    service = SecurityService(factory=CipherFactory())
    # 256-bit config, but we pass 16-byte (128-bit) keys
    configs = [{"algorithm": "AES", "key_size": 256, "mode": "CBC"}]
    
    pt1 = b"P" * 16
    pt2 = flip_bit(pt1, 0)
    k1 = b"K" * 16
    k2 = flip_bit(k1, 0)
    img = b"BM" + b"\x00" * 52 
    iv = b"V" * 16
    
    # AESCipher will natively raise ValueError because len(k1) != 32
    with pytest.raises(ValueError, match="key length must be 32 bytes"):
        service.run_security_suite(configs, pt1, pt2, k1, k2, img, iv)

def test_security_service_integration_aes_192_cbc():
    service = SecurityService(factory=CipherFactory())
    configs = [{"algorithm": "AES", "key_size": 192, "mode": "CBC"}]
    
    pt1 = b"P" * 16
    pt2 = flip_bit(pt1, 0)
    k1 = b"K" * 24
    k2 = flip_bit(k1, 0)
    img = b"BM" + b"\x00" * 52 # dummy bmp
    iv = b"V" * 16
    
    results = service.run_security_suite(configs, pt1, pt2, k1, k2, img, iv)
    assert "AES-192-CBC" in results

def test_security_service_integration_aes_256_ecb():
    service = SecurityService(factory=CipherFactory())
    configs = [{"algorithm": "AES", "key_size": 256, "mode": "ECB"}]
    
    pt1 = b"P" * 16
    pt2 = flip_bit(pt1, 0)
    k1 = b"K" * 32
    k2 = flip_bit(k1, 0)
    
    img = bytearray(b"BM" + b"\x00"*56)
    img[0x02:0x06] = (58).to_bytes(4, 'little')
    img[0x0A:0x0E] = (54).to_bytes(4, 'little')
    img[0x0E:0x12] = (40).to_bytes(4, 'little')
    img[0x12:0x16] = (1).to_bytes(4, 'little', signed=True)
    img[0x16:0x1A] = (1).to_bytes(4, 'little', signed=True)
    img[0x1A:0x1C] = (1).to_bytes(2, 'little')
    img[0x1C:0x1E] = (24).to_bytes(2, 'little')
    
    iv = b"V" * 16
    
    results = service.run_security_suite(configs, pt1, pt2, k1, k2, img, iv)
    assert "AES-256-ECB" in results

@unittest.mock.patch('src.engines.security_service.SecurityEvaluator')
def test_security_service_cbc_routing(mock_evaluator):
    mock_evaluator.calculate_avalanche_effect.return_value = 0.5
    mock_evaluator.test_key_sensitivity.return_value = 0.6
    
    service = SecurityService(factory=CipherFactory())
    configs = [{"algorithm": "AES", "key_size": 128, "mode": "CBC"}]
    
    pt1 = b"P" * 16
    pt2 = flip_bit(pt1, 0)
    k1 = b"K" * 16
    k2 = flip_bit(k1, 0)
    img = b"BM" + b"\x00" * 52 
    iv = b"V" * 16
    
    service.run_security_suite(configs, pt1, pt2, k1, k2, img, iv)
    
    # Verify EXACT arguments forwarded to calculate_avalanche_effect
    # calculate_avalanche_effect(plaintext1, plaintext2, cipher, key, iv)
    av_args, av_kwargs = mock_evaluator.calculate_avalanche_effect.call_args
    assert av_args[0] == pt1
    assert av_args[1] == pt2
    # av_args[2] is cipher instance
    assert av_args[3] == k1
    assert av_args[4] == iv  # CBC gets supplied IV
    
    # Verify EXACT arguments forwarded to test_key_sensitivity
    # test_key_sensitivity(cipher, plaintext, key1, key2, iv)
    ks_args, ks_kwargs = mock_evaluator.test_key_sensitivity.call_args
    # ks_args[0] is cipher
    assert ks_args[1] == pt1
    assert ks_args[2] == k1
    assert ks_args[3] == k2
    assert ks_args[4] == iv  # CBC gets supplied IV

@unittest.mock.patch('src.engines.security_service.SecurityEvaluator')
def test_security_service_ecb_routing(mock_evaluator):
    mock_evaluator.calculate_avalanche_effect.return_value = 0.5
    mock_evaluator.test_key_sensitivity.return_value = 0.6
    mock_evaluator.test_ecb_weakness.return_value = {"headers": b"H"}
    
    service = SecurityService(factory=CipherFactory())
    configs = [{"algorithm": "AES", "key_size": 128, "mode": "ECB"}]
    
    pt1 = b"P" * 16
    pt2 = flip_bit(pt1, 0)
    k1 = b"K" * 16
    k2 = flip_bit(k1, 0)
    img = b"BM" + b"\x00" * 52 
    iv = b"V" * 16
    
    service.run_security_suite(configs, pt1, pt2, k1, k2, img, iv)
    
    # Verify avalanche gets None for IV
    av_args, av_kwargs = mock_evaluator.calculate_avalanche_effect.call_args
    assert av_args[4] is None
    
    # Verify key sensitivity gets None for IV
    ks_args, ks_kwargs = mock_evaluator.test_key_sensitivity.call_args
    assert ks_args[4] is None
    
    # Verify ecb_weakness gets the actual supplied IV
    ecb_args, ecb_kwargs = mock_evaluator.test_ecb_weakness.call_args
    assert ecb_args[0] == img
    assert ecb_args[1] == k1
    assert ecb_args[2] == iv
