# Task 1.1 — PKCS#7 Padding: Implementation Plan

## 1. Overview
Implementation plan for Task 1.1 (PKCS#7 Padding) of the Cryptography Project.

Target module:
`src/utils/padding.py`

Target test file:
`tests/test_padding.py`

## 2. Public API Contract
```python
class Padding:
    @staticmethod
    def pad(data: bytes, block_size: int = 16) -> bytes:
        ...

    @staticmethod
    def unpad(data: bytes, block_size: int = 16) -> bytes:
        ...

    @staticmethod
    def is_padded(data: bytes, block_size: int = 16) -> bool:
        ...

    @staticmethod
    def get_padding_length(data: bytes, block_size: int = 16) -> int:
        ...
```

## 3. Core Validation & Logic Design

### Validation Rules
- `1 <= block_size <= 255` (raises `ValueError` if out of bounds).
- `block_size` must be strictly `int` and not `bool` (raises `TypeError`).
- `data` must be `bytes` or `bytearray` (raises `TypeError`).

### Authoritative Validation: `get_padding_length()`
- Performs parameter validation on `block_size` and `data`.
- Rejects empty data with `ValueError("Data cannot be empty")`.
- Rejects data length not divisible by `block_size` with `ValueError`.
- Reads `padding_length = data[-1]`.
- Checks `1 <= padding_length <= block_size`.
- Verifies all bytes in `data[-padding_length:]` equal `padding_length`.
- Returns `padding_length`.

### Delegation Architecture
- `unpad()` delegates validation to `get_padding_length()` and slices `data[:-padding_length]`.
- `is_padded()` performs parameter checks, invokes `get_padding_length()` inside `try...except ValueError`, returning `True` on success and `False` on invalid padding/unaligned payload.

## 4. Test Matrix
- **Normal Cases**: Empty input, short data, single byte, 15 bytes, 16 bytes (full block), 17 bytes, multi-block.
- **Block Sizes**: 1, 8 (Blowfish), 16 (AES), 255 (Max).
- **Unpadding**: Valid padding, full block padding, empty input, unaligned data, zero byte, byte > block_size, inconsistent padding bytes.
- **`is_padded()`**: True for valid padding; False for corrupt, unaligned, or empty data.
- **`get_padding_length()`**: Correct value for valid data; raises `ValueError` for invalid.
- **Type/Parameter Validation**: Range bounds (0, -1, 256), type errors (`"16"`, `16.0`, `True`, string data).
- **Round-Trip**: `unpad(pad(data, bs), bs) == data` across multiple lengths and block sizes.
