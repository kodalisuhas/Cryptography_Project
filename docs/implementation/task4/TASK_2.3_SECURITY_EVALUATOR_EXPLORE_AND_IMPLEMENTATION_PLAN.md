# SecurityEvaluator — Implementation Plan

## 1. Executive Summary
This document outlines the final, implementation-ready plan for `SecurityEvaluator` (Task 2.3). The evaluator calculates cryptographic security properties, specifically the Avalanche Effect, Key Sensitivity, and ECB pattern leakage. Architectural decisions have been explicitly locked to guarantee no file I/O operations occur within the Analysis layer. The contract specifies deterministic handling of CBC initialization vectors and strict structural integrity for BMP manipulation.

## 2. Current Repository State
- **Task 1.1 & 1.2**: AES Core Engine and Padding are fully implemented and frozen.
- **Task 2.1 & 2.2**: `PerformanceTimer` and `MetricCollector` are implemented.
- **Test Suite**: 176 tests passing.
- **Target File**: `src/analyzers/security_evaluator.py` and `tests/test_security_evaluator.py`.

## 3. Security Metrics In Scope
1. **Hamming Distance**: Pure mathematical primitive.
2. **Avalanche Effect**: Security experiment evaluating bit diffusion when the plaintext mutates by exactly one bit.
3. **Key Sensitivity**: Security experiment evaluating output diffusion when the key mutates by exactly one bit.
4. **ECB Pattern Leakage (ECB Penguin)**: Encrypts uncompressed `.bmp` pixel data to visually demonstrate ECB's structural vulnerability compared to CBC.

## 4. Architecture Boundary Confirmed
- **SecurityEvaluator**:
  - Performs security calculations.
  - May invoke the cipher abstraction (`AESCipher`).
  - Returns structured results (`dict`, `float`, `bytes`, `str`).
  - **Does not write files.**
  - **Does not generate graphs.**
  - **Does not own CSV persistence.**
  - **Does not modify AES.**
  - **Does not perform benchmarking.**
- **FileHandler**: Exclusively owns file persistence.
- **GraphGenerator**: Exclusively owns graph generation.
- **PerformanceTimer**: Exclusively owns timing.
- **MetricCollector**: Exclusively owns benchmark aggregation.

## 5. Mathematical Definitions & Semantics

### Hamming Distance
The exact number of differing bits between two sequences of identical length.
`HammingDistance = sum(bin(b1 ^ b2).count('1') for b1, b2 in zip(data1, data2))`

### Avalanche Effect Experiment
A controlled cryptographic experiment isolating plaintext influence.
```text
P1 = baseline plaintext
P2 = baseline plaintext with exactly one bit intentionally flipped
K  = identical key
IV = identical IV for CBC
C1 = Encrypt(P1)
C2 = Encrypt(P2)

Avalanche % = HammingDistance(C1, C2) / TotalCiphertextBits × 100
```
*Note: The ~45–55% range is an empirical expectation, not an automatic programmatic pass/fail rule.* Identical plaintexts must not be treated as a valid avalanche security experiment, although the math primitive correctly yields 0%.

### Key Sensitivity Experiment
A controlled cryptographic experiment isolating key influence.
```text
P  = identical plaintext
K1 = baseline key
K2 = baseline key with exactly one bit intentionally flipped
IV = identical IV for CBC
C1 = Encrypt(P, K1)
C2 = Encrypt(P, K2)

Sensitivity % = HammingDistance(C1, C2) / TotalCiphertextBits × 100
```

### CBC Experiment Control
For ECB testing, IV is unused. For CBC mode across all experiments (Avalanche, Key Sensitivity, ECB Demo), an **explicitly supplied IV** is mandatory. The `SecurityEvaluator` will **never** generate a random IV internally. The caller must inject the same exact 16-byte IV into both `encrypt` calls for differential experiments. 

## 6. ECB Pattern Demonstration (BMP Handling)
The `test_ecb_weakness` method visually demonstrates pattern leakage by encrypting a BMP's structured pixel payload under controlled conditions. It is a cryptographic visualization experiment, not a general-purpose decryptable image format. 

**No Pillow dependency will be added.**

**Rigorous BMP Byte Contract & AES Alignment**:
1. **Signature Validation**: The first two bytes must be exactly `b'BM'`.
2. **Offset Extraction**: The pixel-data offset is parsed as a 4-byte little-endian integer at offset `0x0A`.
3. **Format Validation**: 
   - The DIB header size (read at `0x0E`) must be supported (e.g., 40 for `BITMAPINFOHEADER`).
   - Bits-per-pixel (read at `0x1C`) must be exactly `24`.
   - Compression method (read at `0x1E`) must be exactly `0` (BI_RGB, uncompressed).
4. **Dimension Validation**: Width (offset `0x12`) and Height (offset `0x16`) fields must be parseable.
5. **Boundary Definition**: The file is partitioned into `header = data[:offset]` and `payload = data[offset:]`. 
6. **Block Alignment & Encryption Strategy**: 
   - Cryptographic ciphertext must **never** be truncated. It must remain structurally whole.
   - The evaluator defines an AES-block-aligned demonstration region: `aligned_length = (len(payload) // 16) * 16`.
   - Only this block-aligned region (`payload[:aligned_length]`) is encrypted via `AESCipher`.
   - Any non-aligned trailing bytes (`payload[aligned_length:]`) are intentionally preserved **unchanged and unencrypted**.
7. **PKCS#7 Expansion Handling**: 
   - `AESCipher.encrypt` strictly applies PKCS#7 padding. The resulting ciphertext will always be exactly 16 bytes longer than `aligned_length`.
   - To produce a structurally consistent demonstration buffer, the evaluator constructs the payload as `header + ciphertext + unencrypted_trailing_bytes`.
   - To maintain perfect BMP structural validity without ciphertext truncation, the evaluator explicitly updates the 4-byte `File Size` field (offset `0x02`) and the 4-byte `Image Size` field (offset `0x22`) in the reconstructed header by adding exactly 16 to account for the PKCS#7 expansion.
8. **Unsupported Behavior**: Rejects non-BMP formats, compressed formats, or malformed offsets via `ValueError`.

## 7. Public API Contract

| Method | Exact Signature | Output | Errors | Purpose |
|---|---|---|---|---|
| `calculate_hamming_distance` | `(data1: bytes, data2: bytes)` | `int` | `ValueError`: unequal lengths, invalid types | Count bit differences between equal-length byte sequences. |
| `calculate_avalanche_effect` | `(plaintext1: bytes, plaintext2: bytes, cipher, key: bytes, iv: bytes = None)` | `float` | `ValueError`: empty inputs, invalid types, unequal lengths, missing IV for CBC | Run plaintext diffusion experiment. |
| `test_key_sensitivity` | `(cipher, plaintext: bytes, key1: bytes, key2: bytes, iv: bytes = None)` | `float` | `ValueError`: empty inputs, invalid types, unequal key lengths, missing IV for CBC | Run key diffusion experiment. |
| `test_ecb_weakness` | `(image_bytes: bytes, key: bytes, iv: bytes)` | `dict` | `ValueError`: not a BMP, invalid bits/compression, payload missing | Demonstrate ECB structural patterns. Returns `{'ecb_demo_bmp': bytes, 'cbc_demo_bmp': bytes}`. |
| `generate_test_report` | `(results: dict)` | `str` | `ValueError`: invalid type | Format numerical security results into a structured markdown report. |

*Conflict Resolution*: The legacy API spec omitted the IV for `test_ecb_weakness` and used `**kwargs` elsewhere. These have been explicitly replaced with `iv: bytes` (mandatory for ECB vs CBC demonstration) and `iv: bytes = None` (for clean typed contracts).

## 8. Error Contract

| Component | Error Condition | Result |
|---|---|---|
| **Hamming Distance** | Invalid types, unequal lengths, empty inputs | Raise `ValueError` |
| **Avalanche** | Invalid plaintext types, empty plaintext, unequal plaintext lengths, invalid key type, missing IV for CBC, unequal ciphertext lengths | Raise `ValueError` |
| **Key Sensitivity** | Invalid key types, unequal key lengths, unsupported key size, missing IV for CBC, unequal ciphertext lengths | Raise `ValueError` |
| **BMP / ECB** | Missing `b'BM'`, invalid bits-per-pixel (not 24), compression enabled, payload bounds invalid | Raise `ValueError` |

## 9. Test Plan

### Hamming
- Identical sequences (returns 0).
- Known partial bit difference.
- Completely inverted sequences.
- Unequal lengths (raises `ValueError`).
- Invalid types (raises `ValueError`).
- Empty inputs (raises `ValueError`).

### Avalanche
- Provide exactly one-bit plaintext mutation.
- Deterministic key and IV.
- Verify explicit IV is successfully injected into both CBC calls.
- Verify equal ciphertext lengths before processing.
- Reject identical plaintexts, empty plaintexts, unequal lengths, missing IV.

### Key Sensitivity
- Provide exactly one-bit key mutation.
- Deterministic plaintext and IV.
- Verify explicit IV is injected into both CBC calls.
- Verify equal ciphertext lengths before processing.
- Reject invalid inputs, identical keys, missing IV.

### ECB Weakness
- Supply a deterministic 24-bit uncompressed BMP byte fixture.
- Verify explicit IV is correctly passed to the CBC encryption.
- Assert ciphertexts are strictly a multiple of 16 bytes (block-aligned).
- Assert no ciphertext truncation occurs.
- Assert the demonstration payload correctly isolates the block-aligned pixel region.
- Assert trailing unaligned payload bytes are strictly preserved unencrypted.
- Assert the BMP `File Size` and `Image Size` metadata fields accurately reflect the PKCS#7 +16 byte expansion.
- Verify malformed/unsupported non-BMP data rejection.
- Assert no file I/O occurs within `SecurityEvaluator`.

### Report Generation
- Supply structured input dictionary.
- Verify deterministic string formatting.
- Assert no file writing occurs.

## 10. Locked Decisions

1. **Analysis layer performs no file I/O.**
2. **ECB demonstration uses in-memory BMP data.**
3. **No Pillow dependency in Task 2.3.**
4. **BMP format validation is rigorous (24-bit, uncompressed, strictly checked).**
5. **SecurityEvaluator never truncates AES ciphertext; complete PKCS#7 expansion is preserved and the BMP header is updated to match.**
6. **Trailing non-aligned BMP payload bytes are preserved unencrypted.**
7. **Key sensitivity is in scope.**
8. **Avalanche/key-sensitivity experiments use controlled mutations.**
9. **CBC IV is explicitly required in the API signatures and must remain identical across comparisons.**
10. **45–55% is empirical expectation, not automatic pass/fail.**

## 11. Final Verdict

🟢 **PASS — IMPLEMENTATION READY**
