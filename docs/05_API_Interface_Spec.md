# API Interface Specification: Performance and Security Analysis of AES Encryption

## Interface Stability Policy

- **Stability Baseline:** All Version 1.0 interfaces defined in this specification are considered frozen and stable contracts across modules.
- **Breaking Changes:** Any structural modifications, parameter changes, or signature updates require prior team consensus, documented issue tracking, and formal updates to this document.
- **Non-Breaking Additions:** Backward-compatible additions (such as optional parameters with default values or helper utilities) may be integrated without revoking current interface signatures.

---

## 1. Introduction

This document defines the **public interfaces** for all modules in the Cryptographic Analysis System. It specifies:
- Function signatures (parameters and return types)
- Class definitions and methods
- Expected behavior and edge cases
- Error handling

> **Purpose:** This serves as a contract between modules. Once defined, each team member can implement their modules independently as long as they follow these interfaces.

---

## 2. Naming Conventions

| Convention | Example | Description / Standard |
| :--- | :--- | :--- |
| **Classes** | `PascalCase` | `AESCipher`, `MetricCollector` |
| **Functions/Methods** | `snake_case` | `encrypt_data()`, `generate_key()` |
| **Constants** | `UPPER_SNAKE_CASE` | `BLOCK_SIZE`, `MAX_CHUNK_SIZE` |
| **Private Methods** | `_leading_underscore` | `_pad_data()`, `_validate_key()` |
| **Type Hints** | Python type hints | `def encrypt(data: bytes) -> bytes:` |

---

## 3. Core Layer Interfaces

### 3.1 `src/core/aes_cipher.py`

**Purpose:** Implement AES encryption and decryption with support for multiple key sizes and modes.  
**Class:** `AESCipher`

```python
class AESCipher:
    """
    AES encryption/decryption implementation.
    Supports 128, 192, and 256-bit keys with ECB and CBC modes.
    """
    
    def __init__(self, key_size: int, mode: str):
        """
        Initialize AES cipher.
        
        Args:
            key_size (int): Key size in bits (128, 192, or 256)
            mode (str): Mode of operation ('ECB' or 'CBC')
            
        Raises:
            ValueError: If key_size or mode is invalid
        """
        pass
    
    def generate_key(self) -> bytes:
        """
        Generate a random key of the specified size.
        
        Returns:
            bytes: Random key of length key_size/8 bytes
            
        Example:
            cipher = AESCipher(256, 'CBC')
            key = cipher.generate_key()  # Returns 32 bytes
        """
        pass
    
    def generate_iv(self) -> bytes:
        """
        Generate a random Initialization Vector (IV) for CBC mode.
        
        Returns:
            bytes: 16-byte random IV
            
        Raises:
            ValueError: If mode is ECB (IV not used)
        """
        pass
    
    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes = None) -> bytes:
        """
        Encrypt plaintext using AES.
        
        Args:
            plaintext (bytes): Data to encrypt
            key (bytes): Encryption key (must match key_size)
            iv (bytes, optional): IV for CBC mode (required for CBC)
            
        Returns:
            bytes: Encrypted ciphertext
            
        Raises:
            ValueError: If key size doesn't match, key is invalid (wrong type or length), IV missing for CBC, etc.
            
        Example:
            cipher = AESCipher(256, 'CBC')
            key = cipher.generate_key()
            iv = cipher.generate_iv()
            encrypted = cipher.encrypt(b"Hello World", key, iv)
        """
        pass
    
    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes = None) -> bytes:
        """
        Decrypt ciphertext using AES.
        
        Args:
            ciphertext (bytes): Data to decrypt
            key (bytes): Encryption key (must match key_size)
            iv (bytes, optional): IV for CBC mode (required for CBC)
            
        Returns:
            bytes: Decrypted plaintext
            
        Raises:
            ValueError: If key size doesn't match, key is invalid (wrong type or length), IV missing for CBC, padding is invalid, etc.
            Note: ECB/CBC mode does not expose InvalidTag (authentication tags are only used by AEAD modes such as GCM, which are not part of Task 1.2).
            
        Example:
            cipher = AESCipher(256, 'CBC')
            decrypted = cipher.decrypt(encrypted, key, iv)
            print(decrypted)  # b"Hello World"
        """
        pass
```

---

### 3.2 `src/core/rsa_cipher.py`

**Purpose:** Implement RSA asymmetric encryption.  
**Class:** `RSACipher`

```python
class RSACipher:
    """
    RSA asymmetric encryption implementation.
    Supports key generation, encryption, and decryption.
    """
    
    def __init__(self, key_size: int):
        """
        Initialize RSA cipher.
        
        Args:
            key_size (int): Key size in bits (1024, 2048, 4096)
            
        Raises:
            ValueError: If key_size is invalid
        """
        pass
    
    def generate_keypair(self) -> tuple:
        """
        Generate RSA public/private key pair.
        
        Returns:
            tuple: (private_key, public_key) as RSA key objects
            
        Example:
            rsa = RSACipher(2048)
            private_key, public_key = rsa.generate_keypair()
        """
        pass
    
    def encrypt(self, plaintext: bytes, public_key) -> bytes:
        """
        Encrypt data using RSA public key.
        
        Args:
            plaintext (bytes): Data to encrypt (limited by key size)
            public_key: RSA public key object
            
        Returns:
            bytes: Encrypted ciphertext
            
        Raises:
            ValueError: If plaintext too large for key size
            cryptography.exceptions.InvalidKey: If public_key is invalid
            
        Note:
            RSA is for small data. Use AES for bulk encryption.
            Max plaintext size = (key_size/8) - 11 bytes
        """
        pass
    
    def decrypt(self, ciphertext: bytes, private_key) -> bytes:
        """
        Decrypt data using RSA private key.
        
        Args:
            ciphertext (bytes): Data to decrypt
            private_key: RSA private key object
            
        Returns:
            bytes: Decrypted plaintext
            
        Raises:
            cryptography.exceptions.InvalidKey: If private_key is invalid
            cryptography.exceptions.InvalidTag: If decryption fails
        """
        pass
```

---

### 3.3 `src/core/blowfish_cipher.py`

**Purpose:** Implement Blowfish encryption.  
**Class:** `BlowfishCipher`

```python
class BlowfishCipher:
    """
    Blowfish symmetric encryption implementation.
    Supports key sizes from 32 to 448 bits.
    """
    
    def __init__(self, key_size: int, mode: str):
        """
        Initialize Blowfish cipher.
        
        Args:
            key_size (int): Key size in bits (32-448, multiples of 8)
            mode (str): Mode of operation ('ECB' or 'CBC')
            
        Raises:
            ValueError: If key_size or mode is invalid
        """
        pass
    
    def generate_key(self) -> bytes:
        """
        Generate a random key of the specified size.
        
        Returns:
            bytes: Random key
            
        Example:
            blowfish = BlowfishCipher(128, 'CBC')
            key = blowfish.generate_key()
        """
        pass
    
    def generate_iv(self) -> bytes:
        """
        Generate a random IV for CBC mode.
        
        Returns:
            bytes: 8-byte random IV (Blowfish block size is 8 bytes)
        """
        pass
    
    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes = None) -> bytes:
        """
        Encrypt data using Blowfish.
        
        Args:
            plaintext (bytes): Data to encrypt
            key (bytes): Encryption key
            iv (bytes, optional): IV for CBC mode
            
        Returns:
            bytes: Encrypted ciphertext
        """
        pass
    
    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes = None) -> bytes:
        """
        Decrypt data using Blowfish.
        
        Args:
            ciphertext (bytes): Data to decrypt
            key (bytes): Encryption key
            iv (bytes, optional): IV for CBC mode
            
        Returns:
            bytes: Decrypted plaintext
        """
        pass
```

---

## 4. Service Layer Interfaces

### 4.1 `src/engines/cipher_interface.py`

**Purpose:** Define abstract base class for all cipher implementations.  
**Abstract Class:** `CipherInterface`

```python
from abc import ABC, abstractmethod

class CipherInterface(ABC):
    """
    Abstract base class for all cipher implementations.
    Ensures uniform interface across all algorithms.
    """
    
    @abstractmethod
    def encrypt(self, data: bytes, key: bytes, **kwargs) -> bytes:
        """
        Encrypt data.
        
        Args:
            data (bytes): Plaintext to encrypt
            key (bytes): Encryption key
            **kwargs: Additional parameters (IV, etc.)
            
        Returns:
            bytes: Encrypted ciphertext
            
        Raises:
            ValueError: If parameters are invalid
        """
        pass
    
    @abstractmethod
    def decrypt(self, data: bytes, key: bytes, **kwargs) -> bytes:
        """
        Decrypt data.
        
        Args:
            data (bytes): Ciphertext to decrypt
            key (bytes): Encryption key
            **kwargs: Additional parameters (IV, etc.)
            
        Returns:
            bytes: Decrypted plaintext
            
        Raises:
            ValueError: If parameters are invalid
        """
        pass
    
    @abstractmethod
    def generate_key(self) -> bytes:
        """
        Generate a random key.
        
        Returns:
            bytes: Generated key
        """
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """
        Get the name of the algorithm.
        
        Returns:
            str: Algorithm name (e.g., "AES", "RSA")
        """
        pass
    
    @abstractmethod
    def get_key_size(self) -> int:
        """
        Get the key size in bits.
        
        Returns:
            int: Key size in bits
        """
        pass
    
    @abstractmethod
    def get_mode(self) -> str:
        """
        Get the mode of operation.
        
        Returns:
            str: Mode (e.g., "ECB", "CBC")
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> dict:
        """
        Get performance metrics for the last operation.
        
        Returns:
            dict: {
                'encryption_time_ms': float,
                'decryption_time_ms': float,
                'throughput_mbps': float,
                'memory_usage_mb': float
            }
        """
        pass
```

---

### 4.2 `src/engines/cipher_factory.py`

**Purpose:** Create cipher instances based on user configuration.  
**Class:** `CipherFactory`

```python
class CipherFactory:
    """
    Factory class for creating cipher instances.
    Implements the Factory Pattern.
    """
    
    SUPPORTED_ALGORITHMS = ['AES', 'RSA', 'Blowfish', 'Classical']
    SUPPORTED_MODES = ['ECB', 'CBC']
    
    @staticmethod
    def get_cipher(algorithm: str, key_size: int, mode: str = None) -> CipherInterface:
        """
        Create and return a cipher instance.
        
        Args:
            algorithm (str): Algorithm name ('AES', 'RSA', 'Blowfish', 'Classical')
            key_size (int): Key size in bits
            mode (str, optional): Mode of operation (required for AES, Blowfish)
            
        Returns:
            CipherInterface: Cipher instance
            
        Raises:
            ValueError: If algorithm, key_size, or mode is invalid
            
        Example:
            cipher = CipherFactory.get_cipher('AES', 256, 'CBC')
            encrypted = cipher.encrypt(b"Hello", key, iv)
        """
        pass
    
    @staticmethod
    def get_supported_algorithms() -> list:
        """
        Get list of supported algorithms.
        
        Returns:
            list: List of algorithm names
        """
        return CipherFactory.SUPPORTED_ALGORITHMS
    
    @staticmethod
    def get_supported_key_sizes(algorithm: str) -> list:
        """
        Get supported key sizes for an algorithm.
        
        Args:
            algorithm (str): Algorithm name
            
        Returns:
            list: List of supported key sizes
            
        Raises:
            ValueError: If algorithm is not supported
            
        Example:
            sizes = CipherFactory.get_supported_key_sizes('AES')
            # Returns: [128, 192, 256]
        """
        pass
    
    @staticmethod
    def get_supported_modes(algorithm: str) -> list:
        """
        Get supported modes for an algorithm.
        
        Args:
            algorithm (str): Algorithm name
            
        Returns:
            list: List of supported modes
            
        Raises:
            ValueError: If algorithm is not supported
        """
        pass
```

---

### 4.3 `src/engines/context_manager.py`

**Purpose:** Manage current encryption context (state).  
**Class:** `ContextManager`

```python
class ContextManager:
    """
    Manages current encryption context.
    Implements Singleton pattern.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize context with default values."""
        self.current_algorithm = 'AES'
        self.current_key_size = 256
        self.current_mode = 'CBC'
        self.current_key = None
        self.current_iv = None
        self._cipher = None
    
    def set_context(self, algorithm: str, key_size: int, mode: str = None):
        """
        Set the current encryption context.
        
        Args:
            algorithm (str): Algorithm name
            key_size (int): Key size in bits
            mode (str, optional): Mode of operation
            
        Raises:
            ValueError: If parameters are invalid
        """
        pass
    
    def get_cipher(self) -> CipherInterface:
        """
        Get the current cipher instance.
        
        Returns:
            CipherInterface: Current cipher instance
            
        Raises:
            RuntimeError: If context not set
        """
        pass
    
    def set_key(self, key: bytes):
        """
        Set the current key.
        
        Args:
            key (bytes): Encryption key
        """
        pass
    
    def set_iv(self, iv: bytes):
        """
        Set the current IV.
        
        Args:
            iv (bytes): Initialization Vector
        """
        pass
    
    def get_context(self) -> dict:
        """
        Get the current context.
        
        Returns:
            dict: {
                'algorithm': str,
                'key_size': int,
                'mode': str,
                'has_key': bool,
                'has_iv': bool
            }
        """
        pass
    
    def reset(self):
        """Reset all context values to defaults."""
        pass
```

---

## 5. Analysis Layer Interfaces

### 5.1 `src/analyzers/performance_timer.py`

**Purpose:** Measure execution time with decorators.  
**Class:** `PerformanceTimer`

```python
class PerformanceTimer:
    """
    Performance timing utilities using decorators.
    """
    
    @staticmethod
    def measure_time(func):
        """
        Decorator to measure function execution time.
        
        Args:
            func: Function to decorate
            
        Returns:
            Wrapped function that returns (result, time_ms)
            
        Example:
            @PerformanceTimer.measure_time
            def encrypt_data(data):
                # ... encryption logic
                return ciphertext
            
            result, time_ms = encrypt_data(data)
            print(f"Time: {time_ms:.2f} ms")
        """
        pass
    
    @staticmethod
    def measure_time_with_warmup(iterations: int = 30, warmup: int = 5):
        """
        Decorator with warmup and multiple iterations.
        
        Args:
            iterations (int): Number of measurement iterations
            warmup (int): Number of warmup iterations
            
        Returns:
            Wrapped function that returns (result, stats_dict)
            
        Example:
            @PerformanceTimer.measure_time_with_warmup(iterations=30)
            def encrypt_data(data):
                return ciphertext
            
            result, stats = encrypt_data(data)
            print(f"Mean: {stats['mean']:.2f} ms")
        """
        pass
    
    @staticmethod
    def context_timer():
        """
        Context manager for timing code blocks.
        
        Usage:
            with PerformanceTimer.context_timer() as timer:
                # Code to measure
                result = encrypt(data)
            print(f"Time: {timer.elapsed_ms:.2f} ms")
        """
        pass
```

---

### 5.2 `src/analyzers/metric_collector.py`

**Purpose:** Collect and export performance metrics.  
**Class:** `MetricCollector`

```python
from datetime import datetime

class MetricCollector:
    """
    Collects and exports performance metrics.
    """
    
    def __init__(self):
        """Initialize metric collector with empty data."""
        self.metrics = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_metric(self, metric_data: dict):
        """
        Add a metric entry.
        
        Args:
            metric_data (dict): {
                'algorithm': str,
                'key_size': int,
                'mode': str,
                'data_size_bytes': int,
                'encryption_time_ms': float,
                'decryption_time_ms': float,
                'throughput_mbps': float,
                'memory_usage_mb': float,
                'timestamp': str
            }
        """
        pass
    
    def add_batch_metrics(self, metrics_list: list):
        """
        Add multiple metric entries.
        
        Args:
            metrics_list (list): List of metric dictionaries
        """
        pass
    
    def get_dataframe(self):
        """
        Get metrics as pandas DataFrame.
        
        Returns:
            pandas.DataFrame: Metrics data
            
        Raises:
            ImportError: If pandas is not installed
        """
        pass
    
    def export_to_csv(self, filepath: str = None):
        """
        Export metrics to CSV file.
        
        Args:
            filepath (str, optional): Output file path
            
        Returns:
            str: Path to the exported file
            
        Example:
            collector = MetricCollector()
            # ... add metrics
            collector.export_to_csv('results/csv/metrics.csv')
        """
        pass
    
    def get_summary(self) -> dict:
        """
        Get summary statistics.
        
        Returns:
            dict: {
                'total_tests': int,
                'algorithms_tested': list,
                'key_sizes_tested': list,
                'modes_tested': list,
                'avg_encryption_time_ms': float,
                'max_throughput_mbps': float,
                'min_memory_usage_mb': float
            }
        """
        pass
    
    def clear(self):
        """Clear all collected metrics."""
        pass
```

---

### 5.3 `src/analyzers/security_evaluator.py`

**Purpose:** Evaluate security properties of encryption.  
**Class:** `SecurityEvaluator`

```python
class SecurityEvaluator:
    """
    Security analysis utilities.
    """
    
    @staticmethod
    def calculate_hamming_distance(data1: bytes, data2: bytes) -> int:
        """
        Calculate Hamming distance (bit difference) between two byte strings.
        
        Args:
            data1 (bytes): First data
            data2 (bytes): Second data
            
        Returns:
            int: Number of differing bits
            
        Raises:
            ValueError: If lengths don't match
            
        Example:
            bits_diff = SecurityEvaluator.calculate_hamming_distance(b'a', b'b')
            # Returns: 2 (0b01100001 vs 0b01100010)
        """
        pass
    
    @staticmethod
    def calculate_avalanche_effect(plaintext1: bytes, plaintext2: bytes, 
                                   cipher, key: bytes, **kwargs) -> float:
        """
        Calculate avalanche effect between two plaintexts.
        
        Args:
            plaintext1 (bytes): Original plaintext
            plaintext2 (bytes): Modified plaintext (1 bit changed)
            cipher: Cipher instance
            key (bytes): Encryption key
            **kwargs: Additional cipher parameters (iv, etc.)
            
        Returns:
            float: Avalanche percentage (0-100)
            
        Example:
            cipher = AESCipher(256, 'CBC')
            key = cipher.generate_key()
            av = SecurityEvaluator.calculate_avalanche_effect(
                b"HelloWorld123456", 
                b"HelloWorld123457",
                cipher, key, iv=iv
            )
            print(f"Avalanche: {av:.1f}%")  # Should be ~50%
        """
        pass
    
    @staticmethod
    def test_ecb_weakness(image_path: str, output_dir: str, key: bytes):
        """
        Demonstrate ECB weakness using image encryption.
        
        Args:
            image_path (str): Path to input image
            output_dir (str): Directory to save encrypted images
            key (bytes): AES key
            
        Returns:
            dict: {
                'ecb_encrypted_path': str,
                'cbc_encrypted_path': str,
                'is_ecb_weak': bool
            }
            
        Example:
            key = AESCipher(256, 'ECB').generate_key()
            result = SecurityEvaluator.test_ecb_weakness(
                'assets/images/penguin.png',
                'results/demo_outputs/',
                key
            )
            # ECB image will show visible pattern
        """
        pass
    
    @staticmethod
    def test_key_sensitivity(cipher, plaintext: bytes, key1: bytes, key2: bytes, 
                            **kwargs) -> float:
        """
        Test sensitivity to key changes.
        
        Args:
            cipher: Cipher instance
            plaintext (bytes): Plaintext to encrypt
            key1 (bytes): Original key
            key2 (bytes): Modified key (1 bit changed)
            **kwargs: Additional parameters (iv, etc.)
            
        Returns:
            float: Percentage of bits changed (~50% expected)
        """
        pass
    
    @staticmethod
    def generate_test_report(results: dict) -> str:
        """
        Generate a formatted security test report.
        
        Args:
            results (dict): Test results
            
        Returns:
            str: Formatted markdown report
        """
        pass
```

---

## 6. Utility Layer Interfaces

### 6.1 `src/utils/file_handler.py`

**Purpose:** Handle file operations for encryption/decryption.  
**Class:** `FileHandler`

```python
class FileHandler:
    """
    File operations for reading/writing encrypted data.
    """
    
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks
    
    @staticmethod
    def read_file(filepath: str, binary: bool = True) -> bytes:
        """
        Read file contents.
        
        Args:
            filepath (str): Path to file
            binary (bool): Read as binary (True) or text (False)
            
        Returns:
            bytes: File contents
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If permission denied
        """
        pass
    
    @staticmethod
    def read_file_chunked(filepath: str, chunk_size: int = CHUNK_SIZE):
        """
        Read large file in chunks.
        
        Args:
            filepath (str): Path to file
            chunk_size (int): Size of each chunk
            
        Yields:
            bytes: File chunks
            
        Raises:
            FileNotFoundError: If file doesn't exist
            
        Example:
            for chunk in FileHandler.read_file_chunked('large_file.dat'):
                process_chunk(chunk)
        """
        pass
    
    @staticmethod
    def write_file(filepath: str, data: bytes, binary: bool = True):
        """
        Write data to file.
        
        Args:
            filepath (str): Path to file
            data (bytes): Data to write
            binary (bool): Write as binary (True) or text (False)
            
        Raises:
            PermissionError: If permission denied
            OSError: If directory doesn't exist
        """
        pass
    
    @staticmethod
    def write_file_chunked(filepath: str, data_generator, binary: bool = True):
        """
        Write data in chunks to handle large files.
        
        Args:
            filepath (str): Path to file
            data_generator: Generator yielding data chunks
            binary (bool): Write as binary (True) or text (False)
        """
        pass
    
    @staticmethod
    def get_file_size(filepath: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            filepath (str): Path to file
            
        Returns:
            int: File size in bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        pass
    
    @staticmethod
    def file_exists(filepath: str) -> bool:
        """
        Check if file exists.
        
        Args:
            filepath (str): Path to file
            
        Returns:
            bool: True if file exists
        """
        pass
    
    @staticmethod
    def ensure_directory(directory: str):
        """
        Ensure directory exists (create if not).
        
        Args:
            directory (str): Directory path
            
        Raises:
            PermissionError: If permission denied
        """
        pass
```

---

### 6.2 `src/utils/key_generator.py`

**Purpose:** Generate cryptographic keys.  
**Class:** `KeyGenerator`

```python
class KeyGenerator:
    """
    Cryptographic key generation utilities.
    """
    
    @staticmethod
    def generate_aes_key(key_size: int) -> bytes:
        """
        Generate a random AES key.
        
        Args:
            key_size (int): Key size in bits (128, 192, 256)
            
        Returns:
            bytes: Random key
            
        Raises:
            ValueError: If key_size is invalid
        """
        pass
    
    @staticmethod
    def generate_rsa_keypair(key_size: int):
        """
        Generate RSA key pair.
        
        Args:
            key_size (int): Key size in bits (1024, 2048, 4096)
            
        Returns:
            tuple: (private_key, public_key)
            
        Raises:
            ValueError: If key_size is invalid
        """
        pass
    
    @staticmethod
    def generate_blowfish_key(key_size: int) -> bytes:
        """
        Generate a random Blowfish key.
        
        Args:
            key_size (int): Key size in bits (32-448, multiples of 8)
            
        Returns:
            bytes: Random key
            
        Raises:
            ValueError: If key_size is invalid
        """
        pass
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes, 
                                 key_length: int, iterations: int = 100000) -> bytes:
        """
        Derive a key from a password using PBKDF2.
        
        Args:
            password (str): User password
            salt (bytes): Salt (16+ bytes recommended)
            key_length (int): Desired key length in bytes
            iterations (int): Number of PBKDF2 iterations
            
        Returns:
            bytes: Derived key
            
        Example:
            salt = os.urandom(16)
            key = KeyGenerator.derive_key_from_password(
                "my_secure_password", salt, 32, 100000
            )
        """
        pass
    
    @staticmethod
    def generate_salt(length: int = 16) -> bytes:
        """
        Generate a random salt.
        
        Args:
            length (int): Salt length in bytes
            
        Returns:
            bytes: Random salt
        """
        pass
    
    @staticmethod
    def key_to_hex(key: bytes) -> str:
        """
        Convert key to hexadecimal string.
        
        Args:
            key (bytes): Binary key
            
        Returns:
            str: Hex string
        """
        pass
    
    @staticmethod
    def key_from_hex(hex_str: str) -> bytes:
        """
        Convert hexadecimal string to key.
        
        Args:
            hex_str (str): Hex string
            
        Returns:
            bytes: Binary key
            
        Raises:
            ValueError: If hex string is invalid
        """
        pass
```

---

### 6.3 `src/utils/padding.py`

**Purpose:** PKCS#7 padding for block ciphers.  
**Class:** `Padding`

```python
class Padding:
    """
    PKCS#7 padding implementation for block ciphers.
    """
    
    @staticmethod
    def pad(data: bytes, block_size: int = 16) -> bytes:
        """
        Apply PKCS#7 padding to data.
        
        Args:
            data (bytes): Data to pad
            block_size (int): Block size in bytes (16 for AES, 8 for Blowfish)
            
        Returns:
            bytes: Padded data
            
        Raises:
            ValueError: If block_size < 1 or block_size > 255
            
        Example:
            >>> Padding.pad(b"Hello", 16)
            b'Hello\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b'
        """
        pass
    
    @staticmethod
     def unpad(data: bytes, block_size: int = 16) -> bytes:
        """
        Remove PKCS#7 padding from data.
        
        Args:
            data (bytes): Padded data
            block_size (int): Block size in bytes (16 for AES, 8 for Blowfish)
            
        Returns:
            bytes: Unpadded data
            
        Raises:
            ValueError: If padding is invalid, data is empty, or padding length > block_size
            
        Example:
            >>> Padding.unpad(b'Hello\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b', 16)
            b'Hello'
        """
        pass
    
    @staticmethod
    def is_padded(data: bytes, block_size: int = 16) -> bool:
        """
       Check if data has valid PKCS#7 padding.
        
        Args:
            data (bytes): Data to check
            block_size (int): Block size in bytes
            
        Returns:
            bool: True if padding is valid, False otherwise
            
        Example:
            >>> Padding.is_padded(b'Hello\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b', 16)
            True
        """
        pass
    
    @staticmethod
    def get_padding_length(data: bytes, block_size: int = 16) -> int:
        """
         Get the padding length from padded data.
        
        Args:
            data (bytes): Padded data
            block_size (int): Block size in bytes
            
        Returns:
            int: Number of padding bytes
            
        Raises:
            ValueError: If padding is invalid
            
        Example:
            >>> Padding.get_padding_length(b'Hello\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b\\x0b', 16)
            11
        """
        pass
```

---

### 6.4 `src/utils/validators.py`

**Purpose:** Validate inputs and parameters.  
**Class:** `Validators`

```python
class Validators:
    """
    Input validation utilities.
    """
    
    @staticmethod
    def validate_key_size(algorithm: str, key_size: int) -> bool:
        """
        Validate if key size is supported for the algorithm.
        
        Args:
            algorithm (str): Algorithm name
            key_size (int): Key size in bits
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If algorithm is not supported
        """
        pass
    
    @staticmethod
    def validate_mode(algorithm: str, mode: str) -> bool:
        """
        Validate if mode is supported for the algorithm.
        
        Args:
            algorithm (str): Algorithm name
            mode (str): Mode of operation
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If algorithm is not supported
        """
        pass
    
    @staticmethod
    def validate_algorithm(algorithm: str) -> bool:
        """
        Validate if algorithm is supported.
        
        Args:
            algorithm (str): Algorithm name
            
        Returns:
            bool: True if supported
        """
        pass
    
    @staticmethod
    def validate_key(key: bytes, expected_size: int) -> bool:
        """
        Validate key size.
        
        Args:
            key (bytes): Encryption key
            expected_size (int): Expected size in bytes
            
        Returns:
            bool: True if valid
        """
        pass
    
    @staticmethod
    def validate_data(data: bytes, max_size: int = None) -> bool:
        """
        Validate data.
        
        Args:
            data (bytes): Data to validate
            max_size (int, optional): Maximum size in bytes
            
        Returns:
            bool: True if valid
        """
        pass
    
    @staticmethod
    def validate_file_path(filepath: str, must_exist: bool = True) -> bool:
        """
        Validate file path.
        
        Args:
            filepath (str): Path to file
            must_exist (bool): Whether file must exist
            
        Returns:
            bool: True if valid
            
        Raises:
            FileNotFoundError: If file doesn't exist and must_exist is True
        """
        pass
    
    @staticmethod
    def get_validation_errors() -> list:
        """
        Get list of validation errors from the last validation.
        
        Returns:
            list: List of error messages
        """
        pass
```

---

### 6.5 `src/utils/formatters.py`

**Purpose:** Format data for display.  
**Class:** `Formatters`

```python
class Formatters:
    """
    Data formatting utilities.
    """
    
    @staticmethod
    def to_hex(data: bytes) -> str:
        """
        Convert bytes to hexadecimal string.
        
        Args:
            data (bytes): Binary data
            
        Returns:
            str: Hex string
            
        Example:
            hex_str = Formatters.to_hex(b"Hello")
            # Returns: "48656c6c6f"
        """
        pass
    
    @staticmethod
    def to_base64(data: bytes) -> str:
        """
        Convert bytes to Base64 string.
        
        Args:
            data (bytes): Binary data
            
        Returns:
            str: Base64 string
            
        Example:
            b64 = Formatters.to_base64(b"Hello")
            # Returns: "SGVsbG8="
        """
        pass
    
    @staticmethod
    def to_binary(data: bytes) -> str:
        """
        Convert bytes to binary string.
        
        Args:
            data (bytes): Binary data
            
        Returns:
            str: Binary string (0s and 1s)
        """
        pass
    
    @staticmethod
    def to_readable_size(size_bytes: int) -> str:
        """
        Convert bytes to human-readable size.
        
        Args:
            size_bytes (int): Size in bytes
            
        Returns:
            str: Human-readable string
            
        Example:
            Formatters.to_readable_size(1024)      # "1.00 KB"
            Formatters.to_readable_size(1048576)   # "1.00 MB"
        """
        pass
    
    @staticmethod
    def format_table(data: list, headers: list) -> str:
        """
        Format data as a table.
        
        Args:
            data (list): List of rows
            headers (list): Column headers
            
        Returns:
            str: Formatted table
            
        Example:
            table = Formatters.format_table(
                [['AES', 256, '0.45ms'], ['RSA', 2048, '12.3ms']],
                ['Algorithm', 'Key Size', 'Time']
            )
        """
        pass
    
    @staticmethod
    def truncate_string(data: str, max_length: int = 50) -> str:
        """
        Truncate string if too long.
        
        Args:
            data (str): String to truncate
            max_length (int): Maximum length
            
        Returns:
            str: Truncated string with '...' if needed
        """
        pass
```

---

## 7. CLI Layer Interfaces

### 7.1 `src/cli/main.py`

**Purpose:** Application entry point.  
**Function:** `main()`

```python
def main():
    """
    Main entry point for the application.
    Parses command-line arguments and starts the appropriate mode.
    
    Usage:
        python main.py --encrypt --algorithm AES --key-size 256 --mode CBC
        python main.py --decrypt --file encrypted.enc
        python main.py --benchmark
        python main.py --menu
        
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    pass

def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    pass

def run_cli_mode(args):
    """
    Run in CLI mode (non-interactive).
    
    Args:
        args: Parsed command-line arguments
    """
    pass

def run_interactive_mode():
    """
    Run in interactive menu mode.
    """
    pass

def run_benchmark_mode(args):
    """
    Run benchmark mode.
    
    Args:
        args: Parsed command-line arguments
    """
    pass
```

---

### 7.2 `src/cli/menu.py`

**Purpose:** Interactive menu system.  
**Class:** `Menu`

```python
class Menu:
    """
    Interactive menu system.
    """
    
    def __init__(self):
        """Initialize menu with options."""
        self.running = True
        self.context = ContextManager()
    
    def display_main_menu(self):
        """
        Display main menu options.
        
        Options:
            1. Encrypt Data
            2. Decrypt Data
            3. Run Benchmark
            4. View Results
            5. Configuration
            6. Exit
        """
        pass
    
    def display_encrypt_menu(self):
        """
        Display encryption options.
        
        Options:
            1. Encrypt Text
            2. Encrypt File
            3. Back to Main Menu
        """
        pass
    
    def display_decrypt_menu(self):
        """
        Display decryption options.
        
        Options:
            1. Decrypt Text
            2. Decrypt File
            3. Back to Main Menu
        """
        pass
    
    def display_benchmark_menu(self):
        """
        Display benchmark options.
        
        Options:
            1. Run Full Benchmark
            2. Compare Key Sizes
            3. Compare Modes
            4. Custom Benchmark
            5. Back to Main Menu
        """
        pass
    
    def get_user_input(self, prompt: str, input_type: type = str) -> any:
        """
        Get and validate user input.
        
        Args:
            prompt (str): User prompt
            input_type (type): Expected input type
            
        Returns:
            any: Validated user input
            
        Example:
            choice = menu.get_user_input("Enter choice: ", int)
            algorithm = menu.get_user_input("Algorithm: ", str)
        """
        pass
    
    def show_result(self, result: dict):
        """
        Display operation result.
        
        Args:
            result (dict): {
                'success': bool,
                'message': str,
                'data': any,
                'metrics': dict
            }
        """
        pass
    
    def run(self):
        """Run the interactive menu loop."""
        pass
```

---

### 7.3 `src/cli/argument_parser.py`

**Purpose:** Parse command-line arguments.  
**Function:** `create_parser()`

```python
def create_parser() -> argparse.ArgumentParser:
    """
    Create argument parser with all options.
    
    Returns:
        argparse.ArgumentParser: Configured parser
        
    Example:
        parser = create_parser()
        args = parser.parse_args()
    """
    pass
```

#### Command-Line Options:

| Argument | Type | Description | Example |
| :--- | :---: | :--- | :--- |
| `--menu` | flag | Run interactive menu | `python main.py --menu` |
| `--encrypt` | flag | Encrypt mode | `python main.py --encrypt` |
| `--decrypt` | flag | Decrypt mode | `python main.py --decrypt` |
| `--benchmark` | flag | Run benchmarks | `python main.py --benchmark` |
| `--algorithm` | str | Algorithm name | `--algorithm AES` |
| `--key-size` | int | Key size in bits | `--key-size 256` |
| `--mode` | str | Mode of operation | `--mode CBC` |
| `--input` | str | Input file path | `--input data.txt` |
| `--output` | str | Output file path | `--output encrypted.enc` |
| `--key` | str | Key file path | `--key key.bin` |
| `--iterations` | int | Benchmark iterations | `--iterations 5` |

---

## 8. Error Handling Interface

**Class:** `CryptographyError`

```python
class CryptographyError(Exception):
    """Base exception for cryptography operations."""
    pass

class InvalidKeyError(CryptographyError):
    """Raised when key is invalid."""
    pass

class InvalidKeySizeError(InvalidKeyError):
    """Raised when key size is invalid."""
    pass

class InvalidModeError(CryptographyError):
    """Raised when mode is invalid."""
    pass

class PaddingError(CryptographyError):
    """Raised when padding is invalid."""
    pass

class DecryptionError(CryptographyError):
    """Raised when decryption fails."""
    pass

class AlgorithmNotSupportedError(CryptographyError):
    """Raised when algorithm is not supported."""
    pass
```

---

## 9. Interface Summary Table

| Module | Class/Function | Purpose |
| :--- | :--- | :--- |
| `aes_cipher.py` | `AESCipher` | AES encryption/decryption |
| `rsa_cipher.py` | `RSACipher` | RSA encryption/decryption |
| `blowfish_cipher.py` | `BlowfishCipher` | Blowfish encryption/decryption |
| `cipher_interface.py` | `CipherInterface` | Abstract base class |
| `cipher_factory.py` | `CipherFactory` | Create cipher instances |
| `context_manager.py` | `ContextManager` | Manage encryption context |
| `performance_timer.py` | `PerformanceTimer` | Measure execution time |
| `metric_collector.py` | `MetricCollector` | Collect/export metrics |
| `security_evaluator.py` | `SecurityEvaluator` | Security analysis |
| `file_handler.py` | `FileHandler` | File operations |
| `key_generator.py` | `KeyGenerator` | Key generation |
| `padding.py` | `Padding` | PKCS#7 padding |
| `validators.py` | `Validators` | Input validation |
| `formatters.py` | `Formatters` | Data formatting |

---

## 10. Interface Dependencies

```
┌──────────────────────────────────────────────────────────────┐
│                    INTERFACE DEPENDENCIES                    │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                  CLI Layer (main.py, menu.py)                │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│              Service Layer (cipher_factory.py)               │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│               Core Layer (aes_cipher.py, etc.)               │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│           Utility Layer (padding.py, key_generator.py)       │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│           Analysis Layer (performance_timer.py, etc.)        │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                       All layers use:                        │
│        - validators.py (input validation)                    │
│        - formatters.py (data formatting)                     │
│        - file_handler.py (file operations)                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 11. Version Compatibility

| Version | Date | Changes |
| :---: | :---: | :--- |
| **v1.0** | January 2026 | Initial interface specification |

---

## Implementation Order

```
┌────────────────────────┐
│   1. Utility Layer     │ (file_handler, key_generator, padding, validators, formatters)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│     2. Core Layer      │ (aes_cipher, rsa_cipher, blowfish_cipher, classical_ciphers)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│    3. Service Layer    │ (cipher_interface, cipher_factory, context_manager)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│   4. Analysis Layer    │ (performance_timer, metric_collector, security_evaluator)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│     5. CLI Layer       │ (argument_parser, menu, main)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  6. System Integration │ (Pipeline end-to-end hookup)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ 7. Unit & System Test  │ (pytest test suite & benchmark validation)
└────────────────────────┘
```

---

## Recommendations & Interface Refinements

1. **Nullable Mode Return in `CipherInterface.get_mode()`**
   - **Explanation:** Asymmetric algorithms (like RSA) and stream/classical ciphers do not operate under block cipher modes (such as ECB or CBC).
   - **Recommendation:** Modify the return type signature from `str` to `str | None` (or `Optional[str]`), allowing non-block ciphers to return `None` gracefully.
   - **Benefit:** Prevents polymorphic exceptions and unifies the cipher contract.

2. **Future-Proof `CipherFactory.get_cipher()` with Variable Keyword Arguments**
   - **Explanation:** Ciphers beyond AES require specific initialization variables (e.g., Caesar shift integers, Vigenère keyword strings, or RSA padding schemes).
   - **Recommendation:** Update the signature to:
     ```python
     @staticmethod
     def get_cipher(algorithm: str, key_size: int | None = None, mode: str | None = None, **kwargs) -> CipherInterface:
     ```
   - **Benefit:** Allows plug-and-play cipher extension without refactoring the factory signature.

3. **Re-evaluate or Scope Down `ContextManager`**
   - **Explanation:** Maintaining a heavyweight global singleton state across CLI interactions introduces unnecessary coupling when state is already naturally routed through `CipherFactory`.
   - **Recommendation:** Keep `ContextManager` strictly scoped to managing active session parameters and active benchmark configurations, or eliminate it in favor of direct state passing through `main.py` and `Menu`.
   - **Benefit:** Reduces architectural bloat and eliminates tricky singleton testing bugs.

4. **Enrich `get_metrics()` Return Payload**
   - **Explanation:** The current dictionary structure only reports numerical latencies and memory usage, omitting test context.
   - **Recommendation:** Include contextual metadata fields: `'algorithm'`, `'key_size'`, `'mode'`, and `'timestamp'` directly inside the dictionary returned by `get_metrics()`.
   - **Benefit:** Simplifies bulk CSV ingestion and DataFrame creation in `MetricCollector`.

5. **Adopted Default Benchmark Iterations in `PerformanceTimer`**
   - **Explanation:** 5 iterations with 2 warmup runs were statistically unstable for sub-millisecond encryption benchmarks.
   - **Resolution:** Configure `PerformanceTimer` defaults to `iterations=30` and `warmup=5` to align with the approved methodology.
   - **Benefit:** Guarantees statistically consistent mean and standard deviation outputs.

6. **Add Session Persistence to `MetricCollector`**
   - **Explanation:** Long benchmark runs run the risk of metric loss if unhandled exceptions occur before CSV export.
   - **Recommendation:** Implement `save_session(filepath)` and `load_session(filepath)` methods within `MetricCollector`.
   - **Benefit:** Facilitates checkpointing, debug inspection, and iterative analysis resumption.

7. **Add Pillow (`Pillow>=10.0.0`) to Requirements for Image Processing**
   - **Explanation:** `SecurityEvaluator.test_ecb_weakness()` performs pixel-level block encryption and image rendering (for the ECB Penguin demo), which requires PIL.
   - **Recommendation:** Add `Pillow>=10.0.0` directly to `requirements.txt` and the System Requirements document.
   - **Benefit:** Prevents missing import crashes when evaluating visual security demos.

8. **Flexible Type Return on `FileHandler.read_file()`**
   - **Explanation:** Reading non-binary files (e.g., plaintext messages or CSV files) yields decoding errors if restricted strictly to raw bytes.
   - **Recommendation:** Update type hint to return `bytes | str`, returning `str` when `binary=False` (decoded as UTF-8) and `bytes` when `binary=True`.
   - **Benefit:** Cleanly supports both raw file encryption and textual payload inspection.

9. **Make `Validators` Pure and Exception-Driven**
   - **Explanation:** Tracking `get_validation_errors()` introduces mutable state to static validation utility methods.
   - **Recommendation:** Remove `get_validation_errors()` and configure validator methods to directly raise specific exceptions (`ValidationError`, `InvalidKeySizeError`, `InvalidModeError`) upon invalid inputs.
   - **Benefit:** Enforces fail-fast behavior across all caller layers.

10. **Add `--config` Flag to Command-Line Options**
    - **Explanation:** CLI users need the ability to supply custom benchmark definitions without manually tweaking code.
    - **Recommendation:** Add `--config <path_to_yaml>` to `create_parser()` options.
    - **Benefit:** Automates headless benchmarking and integration testing pipelines.

11. **Add `BenchmarkError` to Exception Hierarchy**
    - **Explanation:** Distinguishes algorithmic cryptographic failures from benchmark setup, timeout, or plot generation issues.
    - **Recommendation:** Declare `class BenchmarkError(Exception): pass` in `src/exceptions/`.
    - **Benefit:** Enables precise exception handling between cryptographic runtime errors and operational benchmarking errors.
