from src.core.aes_cipher import AESCipher
from src.engines.cipher_interface import SymmetricCipherInterface

class CipherFactory:
    def __init__(self):
        # Dictionary registry
        self._registry = {
            "AES": AESCipher
        }
        
    def create_cipher(self, algorithm: str, key_size: int, mode: str) -> SymmetricCipherInterface:
        """
        Instantiate a registered cipher.
        Raises ValueError if the algorithm is unsupported.
        """
        algo_upper = algorithm.upper()
        if algo_upper not in self._registry:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
            
        cipher_class = self._registry[algo_upper]
        return cipher_class(key_size=key_size, mode=mode.upper())
