"""PKCS#7 padding implementation for block ciphers."""

class Padding:
    """
    PKCS#7 padding implementation for block ciphers.
    """

    @staticmethod
    def _validate_parameters(data: bytes, block_size: int) -> None:
        """
        Validate block_size and data types.
        
        Args:
            data: Payload to validate
            block_size: Block size integer
            
        Raises:
            TypeError: If types are incorrect
            ValueError: If block size is out of valid range
        """
        if not isinstance(block_size, int) or isinstance(block_size, bool):
            raise TypeError("block_size must be an integer")
        if block_size < 1 or block_size > 255:
            raise ValueError(f"block_size must be between 1 and 255, got {block_size}")
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("data must be bytes or bytearray")

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
            TypeError: If data is not bytes or block_size is not int
            
        Example:
            >>> Padding.pad(b"Hello", 16)
            b'Hello\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b'
        """
        Padding._validate_parameters(data, block_size)
        
        padding_len = block_size - (len(data) % block_size)
        padding_bytes = bytes([padding_len] * padding_len)
        return bytes(data) + padding_bytes

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
            TypeError: If data is not bytes or block_size is not int
            
        Example:
            >>> Padding.unpad(b'Hello\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b', 16)
            b'Hello'
        """
        padding_length = Padding.get_padding_length(data, block_size)
        return bytes(data[:-padding_length])

    @staticmethod
    def is_padded(data: bytes, block_size: int = 16) -> bool:
        """
        Check if data has valid PKCS#7 padding.
        
        Args:
            data (bytes): Data to check
            block_size (int): Block size in bytes
            
        Returns:
            bool: True if padding is valid, False otherwise
            
        Raises:
            ValueError: If block_size < 1 or block_size > 255
            TypeError: If data is not bytes or block_size is not int
            
        Example:
            >>> Padding.is_padded(b'Hello\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b', 16)
            True
        """
        Padding._validate_parameters(data, block_size)
        
        try:
            Padding.get_padding_length(data, block_size)
            return True
        except ValueError:
            return False

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
            TypeError: If data is not bytes or block_size is not int
            
        Example:
            >>> Padding.get_padding_length(b'Hello\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b', 16)
            11
        """
        Padding._validate_parameters(data, block_size)
        
        if len(data) == 0:
            raise ValueError("Data cannot be empty")
            
        if len(data) % block_size != 0:
            raise ValueError(f"Data length ({len(data)}) must be a multiple of block_size ({block_size})")
            
        padding_length = data[-1]
        
        if padding_length < 1 or padding_length > block_size:
            raise ValueError(f"Invalid PKCS#7 padding length: {padding_length}")
            
        expected_padding = bytes([padding_length] * padding_length)
        if data[-padding_length:] != expected_padding:
            raise ValueError("Invalid PKCS#7 padding bytes")
            
        return padding_length
