import pytest
from src.analyzers.security_evaluator import SecurityEvaluator
from src.core.aes_cipher import AESCipher

def create_valid_bmp_fixture(width=4, height=4, extra_trailing_bytes=0) -> bytes:
    row_bytes = width * 3
    row_stride = ((row_bytes + 3) // 4) * 4
    payload_len = row_stride * abs(height)
    file_size = 54 + payload_len + extra_trailing_bytes
    header = bytearray(54)
    header[0:2] = b'BM'
    header[2:6] = file_size.to_bytes(4, 'little')
    header[10:14] = (54).to_bytes(4, 'little')
    header[14:18] = (40).to_bytes(4, 'little')
    header[18:22] = width.to_bytes(4, 'little', signed=True)
    header[22:26] = height.to_bytes(4, 'little', signed=True)
    header[26:28] = (1).to_bytes(2, 'little')
    header[28:30] = (24).to_bytes(2, 'little')
    header[30:34] = (0).to_bytes(4, 'little')
    header[34:38] = payload_len.to_bytes(4, 'little')
    return bytes(header) + (b'\x00' * payload_len) + (b'\xAA' * extra_trailing_bytes)

class TestHammingDistance:
    def test_identical(self):
        assert SecurityEvaluator.calculate_hamming_distance(b'\x00', b'\x00') == 0
        
    def test_one_bit(self):
        assert SecurityEvaluator.calculate_hamming_distance(b'\x00', b'\x01') == 1
        
    def test_multi_bit(self):
        assert SecurityEvaluator.calculate_hamming_distance(b'\x00', b'\x0F') == 4
        
    def test_completely_different(self):
        assert SecurityEvaluator.calculate_hamming_distance(b'\x00', b'\xFF') == 8
        
    def test_unequal_length(self):
        with pytest.raises(ValueError):
            SecurityEvaluator.calculate_hamming_distance(b'\x00', b'\x00\x00')
            
    def test_invalid_types(self):
        with pytest.raises(ValueError):
            SecurityEvaluator.calculate_hamming_distance("0", "1")
            
    def test_empty_input(self):
        with pytest.raises(ValueError):
            SecurityEvaluator.calculate_hamming_distance(b'', b'')

class TestAvalancheEffect:
    def setup_method(self):
        self.cipher = AESCipher(128, "CBC")
        self.key = b'\x00' * 16
        self.iv = b'\x01' * 16
        self.p1 = b'\x00' * 16
        self.p2 = b'\x01' + b'\x00' * 15
        
    def test_valid_avalanche(self):
        res = SecurityEvaluator.calculate_avalanche_effect(self.p1, self.p2, self.cipher, self.key, self.iv)
        assert isinstance(res, float)
        assert 0.0 <= res <= 100.0
        
    def test_identical_plaintexts(self):
        with pytest.raises(ValueError, match="exactly one bit difference"):
            SecurityEvaluator.calculate_avalanche_effect(self.p1, self.p1, self.cipher, self.key, self.iv)
            
    def test_multi_bit_difference(self):
        p3 = b'\xFF' + b'\x00' * 15
        with pytest.raises(ValueError, match="exactly one bit difference"):
            SecurityEvaluator.calculate_avalanche_effect(self.p1, p3, self.cipher, self.key, self.iv)
            
    def test_empty_plaintext(self):
        with pytest.raises(ValueError):
            SecurityEvaluator.calculate_avalanche_effect(b'', b'', self.cipher, self.key, self.iv)
            
    def test_unequal_length(self):
        with pytest.raises(ValueError):
            SecurityEvaluator.calculate_avalanche_effect(self.p1, self.p1 + b'\x00', self.cipher, self.key, self.iv)
            
    def test_invalid_plaintext_type(self):
        with pytest.raises(ValueError):
            SecurityEvaluator.calculate_avalanche_effect("plain1", "plain2", self.cipher, self.key, self.iv)
            
    def test_missing_iv_cbc(self):
        with pytest.raises(ValueError, match="IV is required"):
            SecurityEvaluator.calculate_avalanche_effect(self.p1, self.p2, self.cipher, self.key)

class TestKeySensitivity:
    def setup_method(self):
        self.cipher = AESCipher(128, "CBC")
        self.p = b'\x00' * 16
        self.iv = b'\x01' * 16
        self.k1 = b'\x00' * 16
        self.k2 = b'\x01' + b'\x00' * 15
        
    def test_valid_sensitivity(self):
        res = SecurityEvaluator.test_key_sensitivity(self.cipher, self.p, self.k1, self.k2, self.iv)
        assert isinstance(res, float)
        assert 0.0 <= res <= 100.0
        
    def test_identical_keys(self):
        with pytest.raises(ValueError, match="exactly one bit difference"):
            SecurityEvaluator.test_key_sensitivity(self.cipher, self.p, self.k1, self.k1, self.iv)
            
    def test_invalid_key_type(self):
        with pytest.raises(ValueError):
            SecurityEvaluator.test_key_sensitivity(self.cipher, self.p, "k1", "k2", self.iv)
            
    def test_missing_iv_cbc(self):
        with pytest.raises(ValueError, match="IV is required"):
            SecurityEvaluator.test_key_sensitivity(self.cipher, self.p, self.k1, self.k2)

class TestECBWeakness:
    def setup_method(self):
        self.key = b'\x00' * 16
        self.iv = b'\x01' * 16
        self.bmp = create_valid_bmp_fixture(4, 4)
        
    def test_valid_bmp(self):
        res = SecurityEvaluator.test_ecb_weakness(self.bmp, self.key, self.iv)
        assert 'original_header' in res
        assert 'original_pixel_data' in res
        assert 'ecb_ciphertext' in res
        assert 'cbc_ciphertext' in res
        assert 'bmp_trailing_data' in res
        
        # 4x4 BMP. Row stride = 12. Payload = 48 bytes.
        # Ciphertext = 64 bytes (due to PKCS#7).
        assert len(res['ecb_ciphertext']) % 16 == 0
        assert len(res['cbc_ciphertext']) % 16 == 0
        assert len(res['ecb_ciphertext']) == 64
        assert len(res['original_header']) == 54
        assert len(res['original_pixel_data']) == 48
        assert len(res['bmp_trailing_data']) == 0

    def test_unaligned_bmp(self):
        # 3x3 BMP with 5 extra trailing bytes
        bmp = create_valid_bmp_fixture(3, 3, extra_trailing_bytes=5)
        res = SecurityEvaluator.test_ecb_weakness(bmp, self.key, self.iv)
        
        # 3x3 BMP. Row bytes = 9. Row stride = 12. Payload = 36 bytes.
        # 36 bytes encrypted with PKCS#7 -> 48 bytes ciphertext.
        assert len(res['original_pixel_data']) == 36
        assert len(res['ecb_ciphertext']) == 48
        assert len(res['cbc_ciphertext']) == 48
        assert len(res['ecb_ciphertext']) % 16 == 0
        assert len(res['cbc_ciphertext']) % 16 == 0
        
        # Ensure actual trailing data is completely separated
        assert len(res['bmp_trailing_data']) == 5
        assert res['bmp_trailing_data'] == b'\xAA' * 5
        
    def test_invalid_image_type(self):
        with pytest.raises(ValueError, match="image_bytes must be bytes"):
            SecurityEvaluator.test_ecb_weakness("not_bytes", self.key, self.iv)

    def test_invalid_key_type(self):
        with pytest.raises(ValueError, match="key must be bytes"):
            SecurityEvaluator.test_ecb_weakness(self.bmp, "not_key", self.iv)

    def test_invalid_iv_type(self):
        with pytest.raises(ValueError, match="iv must be bytes"):
            SecurityEvaluator.test_ecb_weakness(self.bmp, self.key, "not_iv")
            
    def test_invalid_signature(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[0:2] = b'XX'
        with pytest.raises(ValueError, match="b'BM'"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)
            
    def test_too_small(self):
        with pytest.raises(ValueError, match="too small"):
            SecurityEvaluator.test_ecb_weakness(b'BM12', self.key, self.iv)

    def test_declared_file_size_exceeds(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[2:6] = (9999).to_bytes(4, 'little')
        with pytest.raises(ValueError, match="does not match supplied data"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)
            
    def test_invalid_offset(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[0x0A:0x0E] = (999).to_bytes(4, 'little')
        with pytest.raises(ValueError, match="Invalid payload offset"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)

    def test_unsupported_dib(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[0x0E:0x12] = (14).to_bytes(4, 'little')
        with pytest.raises(ValueError, match="Unsupported DIB"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)
            
    def test_invalid_width(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[0x12:0x16] = (0).to_bytes(4, 'little', signed=True)
        with pytest.raises(ValueError, match="Invalid width"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)

    def test_invalid_planes(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[0x1A:0x1C] = (2).to_bytes(2, 'little')
        with pytest.raises(ValueError, match="planes=1"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)
            
    def test_invalid_bpp(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[0x1C:0x1E] = (8).to_bytes(2, 'little')
        with pytest.raises(ValueError, match="24-bit"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)
            
    def test_invalid_compression(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[0x1E:0x22] = (1).to_bytes(4, 'little')
        with pytest.raises(ValueError, match="uncompressed"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)
            
    def test_inconsistent_image_size(self):
        bad_bmp = bytearray(self.bmp)
        bad_bmp[0x22:0x26] = (1).to_bytes(4, 'little') # expecting at least 48
        with pytest.raises(ValueError, match="inconsistent with pixel geometry"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)
            
    def test_inconsistent_pixel_data_size(self):
        bad_bmp = bytearray(self.bmp)
        # Increase height so it expects more data
        bad_bmp[0x16:0x1A] = (99).to_bytes(4, 'little', signed=True)
        # Clear image size field so it skips the first check
        bad_bmp[0x22:0x26] = (0).to_bytes(4, 'little')
        # Also need to fix file size to bypass the file size validation!
        # wait, the original file size was 102. If we just leave it, file size check will fail first.
        # Let's bypass file size check by setting it to the actual len(bad_bmp)
        bad_bmp[2:6] = len(bad_bmp).to_bytes(4, 'little')
        with pytest.raises(ValueError, match="inconsistent with width/height/row stride"):
            SecurityEvaluator.test_ecb_weakness(bytes(bad_bmp), self.key, self.iv)

class TestReportGeneration:
    def test_valid_report(self):
        res = {
            'Avalanche Effect': 50.1,
            'Hamming Distance': 12,
            'ECB Image': b'some binary data'
        }
        report = SecurityEvaluator.generate_test_report(res)
        assert "Security Evaluation Report" in report
        assert "50.10%" in report
        assert "12" in report
        assert "<BINARY DATA: 16 bytes>" in report
        
    def test_invalid_input(self):
        with pytest.raises(ValueError):
            SecurityEvaluator.generate_test_report("not a dict")
