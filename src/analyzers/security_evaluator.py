class SecurityEvaluator:
    """
    Evaluates cryptographic security properties.
    """

    @staticmethod
    def calculate_hamming_distance(data1: bytes, data2: bytes) -> int:
        """Count bit differences between equal-length byte sequences."""
        if not isinstance(data1, (bytes, bytearray)) or not isinstance(data2, (bytes, bytearray)):
            raise ValueError("Inputs must be bytes or bytearray.")
        if not data1 or not data2:
            raise ValueError("Inputs cannot be empty.")
        if len(data1) != len(data2):
            raise ValueError("Inputs must have equal length.")
            
        return sum(bin(b1 ^ b2).count('1') for b1, b2 in zip(data1, data2))

    @staticmethod
    def calculate_avalanche_effect(plaintext1: bytes, plaintext2: bytes, cipher, key: bytes, iv: bytes = None) -> float:
        """Run plaintext diffusion experiment."""
        if not isinstance(plaintext1, (bytes, bytearray)) or not isinstance(plaintext2, (bytes, bytearray)):
            raise ValueError("Plaintexts must be bytes or bytearray.")
        if not plaintext1 or not plaintext2:
            raise ValueError("Plaintexts cannot be empty.")
        if len(plaintext1) != len(plaintext2):
            raise ValueError("Plaintexts must have equal length.")
            
        if not isinstance(key, (bytes, bytearray)):
            raise ValueError("key must be bytes or bytearray.")
            
        diff = SecurityEvaluator.calculate_hamming_distance(plaintext1, plaintext2)
        if diff != 1:
            raise ValueError("Avalanche experiment requires exactly one bit difference in plaintexts.")

        if cipher.mode == "CBC" and iv is None:
            raise ValueError("IV is required for CBC mode.")

        c1 = cipher.encrypt(plaintext1, key, iv)
        c2 = cipher.encrypt(plaintext2, key, iv)

        if len(c1) != len(c2):
            raise ValueError("Ciphertext lengths do not match.")
        
        return (SecurityEvaluator.calculate_hamming_distance(c1, c2) / (len(c1) * 8)) * 100.0

    @staticmethod
    def test_key_sensitivity(cipher, plaintext: bytes, key1: bytes, key2: bytes, iv: bytes = None) -> float:
        """Run key diffusion experiment."""
        if not isinstance(plaintext, (bytes, bytearray)):
            raise ValueError("Plaintext must be bytes or bytearray.")
        if not plaintext:
            raise ValueError("Plaintext cannot be empty.")
        if not isinstance(key1, (bytes, bytearray)) or not isinstance(key2, (bytes, bytearray)):
            raise ValueError("Keys must be bytes or bytearray.")
        if len(key1) != len(key2):
            raise ValueError("Keys must have equal length.")
            
        diff = SecurityEvaluator.calculate_hamming_distance(key1, key2)
        if diff != 1:
            raise ValueError("Key sensitivity experiment requires exactly one bit difference in keys.")
            
        if cipher.mode == "CBC" and iv is None:
            raise ValueError("IV is required for CBC mode.")
            
        c1 = cipher.encrypt(plaintext, key1, iv)
        c2 = cipher.encrypt(plaintext, key2, iv)
        
        if len(c1) != len(c2):
            raise ValueError("Ciphertext lengths do not match.")
            
        return (SecurityEvaluator.calculate_hamming_distance(c1, c2) / (len(c1) * 8)) * 100.0

    @staticmethod
    def test_ecb_weakness(image_bytes: bytes, key: bytes, iv: bytes) -> dict:
        """Demonstrate ECB structural patterns."""
        if not isinstance(image_bytes, (bytes, bytearray)):
            raise ValueError("image_bytes must be bytes or bytearray.")
        if not isinstance(key, (bytes, bytearray)):
            raise ValueError("key must be bytes or bytearray.")
        if not isinstance(iv, (bytes, bytearray)):
            raise ValueError("iv must be bytes or bytearray.")
            
        if len(image_bytes) < 54:
            raise ValueError("Invalid BMP data: too small.")
        if image_bytes[0:2] != b'BM':
            raise ValueError("Invalid BMP signature: must be b'BM'.")
            
        file_size_field = int.from_bytes(image_bytes[0x02:0x06], byteorder='little')
        if file_size_field != len(image_bytes):
            raise ValueError("Declared file size does not match supplied data.")
            
        offset = int.from_bytes(image_bytes[0x0A:0x0E], byteorder='little')
        if offset > len(image_bytes) or offset < 14:
            raise ValueError("Invalid payload offset.")
            
        dib_header_size = int.from_bytes(image_bytes[0x0E:0x12], byteorder='little')
        if dib_header_size not in (40, 108, 124):
            raise ValueError("Unsupported DIB header size.")
            
        width = int.from_bytes(image_bytes[0x12:0x16], byteorder='little', signed=True)
        height = int.from_bytes(image_bytes[0x16:0x1A], byteorder='little', signed=True)
        if width <= 0 or height == 0:
            raise ValueError("Invalid width or height.")
            
        planes = int.from_bytes(image_bytes[0x1A:0x1C], byteorder='little')
        if planes != 1:
            raise ValueError("Only planes=1 is supported.")
            
        bpp = int.from_bytes(image_bytes[0x1C:0x1E], byteorder='little')
        if bpp != 24:
            raise ValueError("Only 24-bit uncompressed BMP is supported.")
            
        comp = int.from_bytes(image_bytes[0x1E:0x22], byteorder='little')
        if comp != 0:
            raise ValueError("Only uncompressed BMP is supported.")
            
        row_bytes = width * 3
        row_stride = ((row_bytes + 3) // 4) * 4
        expected_pixel_bytes = row_stride * abs(height)
        
        image_size_field = int.from_bytes(image_bytes[0x22:0x26], byteorder='little')
        if image_size_field != 0 and image_size_field < expected_pixel_bytes:
            raise ValueError("Declared image size is inconsistent with pixel geometry.")

        header = image_bytes[:offset]
        payload = image_bytes[offset:]
        
        if len(payload) < expected_pixel_bytes:
            raise ValueError("Pixel data size is inconsistent with width/height/row stride.")
            
        pixel_data = payload[:expected_pixel_bytes]
        bmp_trailing_data = payload[expected_pixel_bytes:]
        
        from src.core.aes_cipher import AESCipher
        ecb_cipher = AESCipher(key_size=len(key) * 8, mode="ECB")
        cbc_cipher = AESCipher(key_size=len(key) * 8, mode="CBC")
        
        ecb_ciphertext = ecb_cipher.encrypt(pixel_data, key)
        cbc_ciphertext = cbc_cipher.encrypt(pixel_data, key, iv)
        
        return {
            'original_header': bytes(header),
            'original_pixel_data': bytes(pixel_data),
            'ecb_ciphertext': bytes(ecb_ciphertext),
            'cbc_ciphertext': bytes(cbc_ciphertext),
            'bmp_trailing_data': bytes(bmp_trailing_data)
        }

    @staticmethod
    def generate_test_report(results: dict) -> str:
        """Format numerical security results into a structured markdown report."""
        if not isinstance(results, dict):
            raise ValueError("Results must be a dictionary.")
            
        lines = ["# Security Evaluation Report\n"]
        for k, v in results.items():
            if isinstance(v, (bytes, bytearray)):
                lines.append(f"- **{k}**: <BINARY DATA: {len(v)} bytes>")
            elif isinstance(v, float):
                lines.append(f"- **{k}**: {v:.2f}%")
            else:
                lines.append(f"- **{k}**: {v}")
                
        return "\n".join(lines)
