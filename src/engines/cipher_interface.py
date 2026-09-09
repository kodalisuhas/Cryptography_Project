import abc

class SymmetricCipherInterface(abc.ABC):
    
    @abc.abstractmethod
    def generate_key(self) -> bytes:
        """Generate a cryptographically secure random key matching the configured size."""
        pass
        
    @abc.abstractmethod
    def generate_iv(self) -> bytes:
        """
        Generate a cryptographically secure random IV matching the block size.
        Returns the required IV bytes. 
        Only applicable to CBC-capable configurations. Core implementations 
        (e.g., AESCipher) will reject IV generation with a ValueError if the mode is ECB.
        """
        pass
        
    @abc.abstractmethod
    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        """Encrypt plaintext. Requires IV for CBC mode, forbids IV for ECB mode."""
        pass
        
    @abc.abstractmethod
    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
        """Decrypt ciphertext. Requires IV for CBC mode, forbids IV for ECB mode."""
        pass
