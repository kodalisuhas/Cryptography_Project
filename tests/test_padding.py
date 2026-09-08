"""Tests for the PKCS#7 padding utility."""

import pytest
from src.utils.padding import Padding


def test_pad_empty_data():
    """Test padding empty data."""
    # With block_size=16, should append 16 bytes of 0x10
    result = Padding.pad(b"", 16)
    assert result == b"\x10" * 16

def test_pad_short_data():
    """Test padding data shorter than block size."""
    # 5 bytes data with block_size=16, should append 11 bytes of 0x0b
    result = Padding.pad(b"Hello", 16)
    assert result == b"Hello" + b"\x0b" * 11

def test_pad_single_byte():
    """Test padding 1-byte data."""
    result = Padding.pad(b"A", 16)
    assert result == b"A" + b"\x0f" * 15

def test_pad_fifteen_bytes():
    """Test padding exactly block_size - 1 bytes."""
    data = b"A" * 15
    result = Padding.pad(data, 16)
    assert result == data + b"\x01"

def test_pad_exact_block_size():
    """Test padding data that is exactly the block size."""
    # 16 bytes data with block_size=16, should append 16 bytes of 0x10
    data = b"A" * 16
    result = Padding.pad(data, 16)
    assert result == data + b"\x10" * 16

def test_pad_seventeen_bytes():
    """Test padding data slightly larger than a block."""
    data = b"A" * 17
    result = Padding.pad(data, 16)
    assert result == data + b"\x0f" * 15

def test_pad_multi_block():
    """Test padding multiple blocks of data."""
    # 32 bytes data, should append 16 bytes of 0x10
    data = b"B" * 32
    result = Padding.pad(data, 16)
    assert result == data + b"\x10" * 16

def test_blowfish_block_size_8():
    """Test padding with Blowfish block size (8)."""
    # Empty
    assert Padding.pad(b"", 8) == b"\x08" * 8
    # 5 bytes
    assert Padding.pad(b"12345", 8) == b"12345\x03\x03\x03"
    # 8 bytes
    assert Padding.pad(b"12345678", 8) == b"12345678" + b"\x08" * 8

def test_boundary_block_size_1():
    """Test padding with minimal block size 1."""
    assert Padding.pad(b"ABC", 1) == b"ABC\x01"

def test_boundary_block_size_255():
    """Test padding with maximal block size 255."""
    data = b"A" * 250
    assert Padding.pad(data, 255) == data + b"\x05" * 5

def test_unpad_valid_data():
    """Test unpadding valid padded data."""
    padded = b"Hello" + b"\x0b" * 11
    assert Padding.unpad(padded, 16) == b"Hello"

def test_unpad_full_block_padding():
    """Test unpadding a full block of padding."""
    padded = b"\x10" * 16
    assert Padding.unpad(padded, 16) == b""

def test_unpad_empty_data_raises():
    """Test unpadding empty data raises ValueError."""
    with pytest.raises(ValueError, match="Data cannot be empty"):
        Padding.unpad(b"", 16)

def test_unpad_unaligned_data_raises():
    """Test unpadding unaligned data raises ValueError."""
    with pytest.raises(ValueError, match="multiple of block_size"):
        Padding.unpad(b"A" * 15, 16)
    with pytest.raises(ValueError, match="multiple of block_size"):
        Padding.unpad(b"A" * 17, 16)

def test_unpad_zero_byte_raises():
    """Test unpadding data ending with 0x00 raises ValueError."""
    padded = b"A" * 15 + b"\x00"
    with pytest.raises(ValueError, match="Invalid PKCS#7 padding length"):
        Padding.unpad(padded, 16)

def test_unpad_padding_greater_than_block_size():
    """Test unpadding data with padding byte > block size raises ValueError."""
    padded = b"A" * 15 + b"\x11"
    with pytest.raises(ValueError, match="Invalid PKCS#7 padding length"):
        Padding.unpad(padded, 16)

def test_unpad_inconsistent_padding_bytes():
    """Test unpadding data with inconsistent padding bytes raises ValueError."""
    padded = b"A" * 13 + b"\x03\x02\x03"
    with pytest.raises(ValueError, match="Invalid PKCS#7 padding bytes"):
        Padding.unpad(padded, 16)

def test_is_padded_returns_true_for_valid():
    """Test is_padded returns True for valid padded data."""
    padded = b"Hello" + b"\x0b" * 11
    assert Padding.is_padded(padded, 16) is True
    assert Padding.is_padded(b"\x10" * 16, 16) is True

def test_is_padded_returns_false_for_corrupt():
    """Test is_padded returns False for corrupt padding."""
    corrupt = b"A" * 13 + b"\x03\x02\x03"
    assert Padding.is_padded(corrupt, 16) is False
    # zero padding length
    assert Padding.is_padded(b"A" * 15 + b"\x00", 16) is False
    # length out of bounds
    assert Padding.is_padded(b"A" * 15 + b"\x11", 16) is False

def test_is_padded_returns_false_for_unaligned():
    """Test is_padded returns False for unaligned data."""
    assert Padding.is_padded(b"A" * 15, 16) is False

def test_is_padded_returns_false_for_empty():
    """Test is_padded returns False for empty data."""
    assert Padding.is_padded(b"", 16) is False

def test_get_padding_length_valid():
    """Test get_padding_length on valid padding."""
    assert Padding.get_padding_length(b"Hello" + b"\x0b" * 11, 16) == 11

def test_get_padding_length_full_block():
    """Test get_padding_length on a full block of padding."""
    assert Padding.get_padding_length(b"\x10" * 16, 16) == 16

def test_get_padding_length_invalid_raises():
    """Test get_padding_length raises ValueError for invalid padding."""
    with pytest.raises(ValueError):
        Padding.get_padding_length(b"A" * 13 + b"\x03\x02\x03", 16)
    with pytest.raises(ValueError):
        Padding.get_padding_length(b"A" * 15, 16)

def test_invalid_block_size_zero_or_negative():
    """Test block_size <= 0 raises ValueError across all methods."""
    methods = [Padding.pad, Padding.unpad, Padding.is_padded, Padding.get_padding_length]
    for method in methods:
        with pytest.raises(ValueError, match="between 1 and 255"):
            method(b"data", 0)
        with pytest.raises(ValueError, match="between 1 and 255"):
            method(b"data", -16)

def test_invalid_block_size_exceeds_255():
    """Test block_size > 255 raises ValueError across all methods."""
    methods = [Padding.pad, Padding.unpad, Padding.is_padded, Padding.get_padding_length]
    for method in methods:
        with pytest.raises(ValueError, match="between 1 and 255"):
            method(b"data", 256)

def test_invalid_block_size_type():
    """Test non-integer block_size raises TypeError across all methods."""
    methods = [Padding.pad, Padding.unpad, Padding.is_padded, Padding.get_padding_length]
    for method in methods:
        with pytest.raises(TypeError, match="must be an integer"):
            method(b"data", "16")
        with pytest.raises(TypeError, match="must be an integer"):
            method(b"data", 16.0)
        with pytest.raises(TypeError, match="must be an integer"):
            method(b"data", True)

def test_invalid_data_type():
    """Test non-bytes data raises TypeError across all methods."""
    methods = [Padding.pad, Padding.unpad, Padding.is_padded, Padding.get_padding_length]
    for method in methods:
        with pytest.raises(TypeError, match="must be bytes"):
            method("string", 16)
        with pytest.raises(TypeError, match="must be bytes"):
            method(12345, 16)
        with pytest.raises(TypeError, match="must be bytes"):
            method([1, 2, 3], 16)

def test_malformed_truncated_padding():
    """Test explicitly malformed or truncated padding."""
    # Length is 16, so it's a multiple of block size.
    # But the padding bytes are truncated or malformed (expected 5 bytes of 0x05, but got 0x05...0x04)
    malformed = b"A" * 11 + b"\x05\x05\x05\x05\x04"
    with pytest.raises(ValueError, match="Invalid PKCS#7 padding bytes"):
        Padding.unpad(malformed, 16)
    assert Padding.is_padded(malformed, 16) is False
    with pytest.raises(ValueError, match="Invalid PKCS#7 padding bytes"):
        Padding.get_padding_length(malformed, 16)

def test_round_trip():
    """Test pad and unpad round-trip with multiple sizes."""
    data_lengths = [0, 1, 5, 15, 16, 17, 31, 32, 33, 100]
    block_sizes = [1, 8, 16, 255]
    
    for bs in block_sizes:
        for length in data_lengths:
            data = bytes([i % 256 for i in range(length)])
            padded = Padding.pad(data, bs)
            assert len(padded) % bs == 0
            assert Padding.is_padded(padded, bs) is True
            unpadded = Padding.unpad(padded, bs)
            assert unpadded == data
