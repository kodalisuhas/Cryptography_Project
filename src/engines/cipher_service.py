from dataclasses import dataclass
from src.engines.cipher_factory import CipherFactory

@dataclass(frozen=True)
class EncryptionResult:
    ciphertext: bytes
    iv: bytes | None

class CipherService:
    def __init__(self, factory: CipherFactory = None):
        self.factory = factory or CipherFactory()
        
    def encrypt_data(self, algorithm: str, key_size: int, mode: str, plaintext: bytes, key: bytes, iv: bytes | None = None) -> EncryptionResult:
        """
        Orchestrate encryption.
        If mode is CBC and iv is None, Core will generate the IV.
        """
        cipher = self.factory.create_cipher(algorithm, key_size, mode)
        
        # If IV is required but missing, generate it via Core.
        if mode.upper() == "CBC" and iv is None:
            iv = cipher.generate_iv()
            
        # Core validates everything (key length, ECB vs CBC constraints).
        ciphertext = cipher.encrypt(plaintext, key, iv)
        return EncryptionResult(ciphertext=ciphertext, iv=iv)

    def decrypt_data(self, algorithm: str, key_size: int, mode: str, ciphertext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        """
        Orchestrate decryption.
        """
        cipher = self.factory.create_cipher(algorithm, key_size, mode)
        return cipher.decrypt(ciphertext, key, iv)
