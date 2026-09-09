firslty by onesource later ill add another source report also
# DEEP RESEARCH REPORT: AES ENCRYPTION/DECRYPTION

## Task 1.2 — AES Encryption/Decryption
### Research, Specification Audit & Implementation Contract Preparation

---

## 1. SOURCE PRIORITY & METHODOLOGY

This report synthesizes findings from the following authoritative sources, in priority order:

| Priority | Source | Reference |
| :--- | :--- | :--- |
| 1 | Project API/Interface Specification | `docs/05_API_Interface_Spec.md` |
| 2 | Project Architecture & Methodology | `docs/03_Architecture_Design.md`, `docs/04_Methodology.md` |
| 3 | NIST FIPS 197 — AES Standard | Advanced Encryption Standard (AES) |
| 4 | NIST SP 800-38A — Block Cipher Modes | ECB, CBC, CTR modes |
| 5 | NIST SP 800-38D — GCM Mode | Galois/Counter Mode (GCM) |
| 6 | PyCA Cryptography Documentation | `symmetric-encryption.rst` |
| 7 | RFC 5116 — Authenticated Encryption | AEAD algorithms |

---

## 2. PROJECT REQUIREMENTS EXTRACTION

### 2.1 AES Requirements from Project Documentation

Based on the project's existing documentation (`docs/05_API_Interface_Spec.md`, `docs/03_Architecture_Design.md`):

| Requirement | Specification | Source |
| :--- | :--- | :--- |
| **Key Sizes** | AES-128, AES-192, AES-256 | `05_API_Interface_Spec.md` |
| **Supported Modes** | ECB, CBC | `05_API_Interface_Spec.md` |
| **Class Name** | `AESCipher` | `05_API_Interface_Spec.md` |
| **File Location** | `src/core/aes_cipher.py` | `03_Architecture_Design.md` |
| **Block Size** | 16 bytes (fixed for all key sizes) | NIST FIPS 197 |
| **Key Generation** | `generate_key() -> bytes` | `05_API_Interface_Spec.md` |
| **IV Generation** | `generate_iv() -> bytes` | `05_API_Interface_Spec.md` |
| **Encryption** | `encrypt(plaintext: bytes, key: bytes, iv: bytes = None) -> bytes` | `05_API_Interface_Spec.md` |
| **Decryption** | `decrypt(ciphertext: bytes, key: bytes, iv: bytes = None) -> bytes` | `05_API_Interface_Spec.md` |

### 2.2 Performance & Analysis Requirements

| Requirement | Specification | Source |
| :--- | :--- | :--- |
| **Performance Metrics** | Encryption time, decryption time, throughput, memory usage | `04_Methodology.md` |
| **Security Analysis** | ECB pattern leakage, avalanche effect, key sensitivity | `04_Methodology.md` |
| **Benchmarking** | Multiple iterations, warmup, statistical aggregation | `04_Methodology.md` |

---

## 3. AES FUNDAMENTALS

### 3.1 AES Specification

The Advanced Encryption Standard (AES) is a **FIPS-approved symmetric block cipher** that can encrypt and decrypt electronic data. It was published in November 2001 after a multi-year cooperative effort involving the U.S. government, industry, and academic community.

### 3.2 Core Properties

| Property | Value |
| :--- | :--- |
| **Algorithm** | Rijndael |
| **Block Size** | 128 bits (16 bytes) |
| **Key Sizes** | 128, 192, 256 bits |
| **Rounds** | 10 (AES-128), 12 (AES-192), 14 (AES-256) |
| **Type** | Symmetric-key block cipher |

### 3.3 Key Size vs Block Size

**CRITICAL FINDING:** The AES **block size remains 128 bits (16 bytes) for ALL key sizes** (AES-128, AES-192, and AES-256).

The key size determines:
- Number of encryption rounds
- Key schedule length
- Security strength

The key size does **NOT** affect:
- Block size (always 16 bytes)
- Padding requirements
- Mode of operation behavior

### 3.4 AES Internal Structure

| Operation | Description |
| :--- | :--- |
| **SubBytes** | Nonlinear substitution using S-box |
| **ShiftRows** | Cyclic shift of rows |
| **MixColumns** | Mixing operation on columns |
| **AddRoundKey** | XOR with round key |

**Note:** The project uses the `cryptography` library, so **manual implementation of these operations is NOT required**. The library handles the AES internals.

---

## 4. MODE OF OPERATION RESEARCH

### 4.1 Mode Overview

NIST SP 800-38A defines five confidentiality modes for block ciphers: ECB, CBC, CFB, OFB, and CTR. The project requires ECB and CBC (with CTR and GCM as potential future extensions).

### 4.2 Electronic Codebook (ECB)

| Aspect | Detail |
| :--- | :--- |
| **Encryption** | Each block encrypted independently with the same key |
| **Decryption** | Each block decrypted independently |
| **IV Requirement** | ❌ None |
| **Padding** | ✅ Required (PKCS#7) |
| **Determinism** | ✅ Same plaintext block → Same ciphertext block |
| **Parallelization** | ✅ Fully parallelizable |

**Security Weaknesses:**
- **Pattern Leakage:** Identical plaintext blocks produce identical ciphertext blocks
- **Not semantically secure:** Reveals patterns in data
- **Inappropriate for:** Any data with repeating patterns (images, structured data)

**Appropriate Use Cases:**
- Random data (keys, nonces)
- Single-block messages
- Legacy systems (only when necessary)

### 4.3 Cipher Block Chaining (CBC)

| Aspect | Detail |
| :--- | :--- |
| **Encryption** | Each plaintext block XORed with previous ciphertext block before encryption |
| **Decryption** | Each ciphertext block decrypted, then XORed with previous ciphertext block |
| **IV Requirement** | ✅ Required (16 bytes) |
| **Padding** | ✅ Required (PKCS#7) |
| **Determinism** | ❌ Different IV → Different ciphertext |
| **Parallelization** | ❌ Encryption not parallelizable; Decryption is parallelizable |

**Security Properties:**
- **Semantically secure** (with random IV)
- **Patterns hidden** across blocks
- **Malleable:** Bit flips in ciphertext affect corresponding plaintext block

**Vulnerabilities:**
- **Padding Oracle Attacks:** If error messages distinguish between padding and other decryption failures
- **IV must be unpredictable** and unique per encryption

**Appropriate Use Cases:**
- Bulk encryption (with proper IV management)
- File encryption
- Legacy compatibility

### 4.4 Counter Mode (CTR)

| Aspect | Detail |
| :--- | :--- |
| **Encryption** | AES encrypts counter value, XORed with plaintext |
| **Decryption** | Identical to encryption (symmetric) |
| **IV/Nonce Requirement** | ✅ Required (unique nonce + counter) |
| **Padding** | ❌ NOT required (stream cipher mode) |
| **Parallelization** | ✅ Fully parallelizable |

**Security Properties:**
- **Stream cipher mode:** No padding needed
- **Encryption and decryption are identical operations**
- **Nonce uniqueness is CRITICAL**

**Critical Risk:**
- **Nonce reuse** completely breaks security
- **Same nonce + same key** → Same keystream → XOR reveals plaintext

### 4.5 Galois/Counter Mode (GCM)

| Aspect | Detail |
| :--- | :--- |
| **Type** | Authenticated Encryption with Associated Data (AEAD) |
| **Encryption** | CTR mode + GHASH authentication |
| **Decryption** | CTR mode + tag verification |
| **Nonce Requirement** | ✅ Required (12 bytes recommended) |
| **Padding** | ❌ NOT required |
| **Authentication** | ✅ Provides integrity and authenticity |
| **Tag Length** | 16 bytes (128 bits) recommended |

**Security Properties:**
- **Authenticated encryption:** Provides confidentiality + integrity + authenticity
- **Nonce reuse** breaks both confidentiality and authentication

**InvalidTag Exception:**
- `cryptography.exceptions.InvalidTag` is raised **ONLY by GCM decryption** when the authentication tag fails verification
- This exception is **NOT raised** by ECB, CBC, or CTR
- ECB, CBC, and CTR use padding validation (`ValueError`) instead

**Appropriate Use Cases:**
- Network protocols (TLS)
- API encryption
- Any scenario requiring integrity

---

## 5. PADDING INTERACTION

### 5.1 Padding Requirements by Mode

| Mode | PKCS#7 Padding Required | Reason |
| :--- | :--- | :--- |
| **ECB** | ✅ Required | Block cipher - needs full blocks |
| **CBC** | ✅ Required | Block cipher - needs full blocks |
| **CTR** | ❌ NOT Required | Stream cipher mode - no block alignment needed |
| **GCM** | ❌ NOT Required | Stream cipher mode - no block alignment needed |

### 5.2 Integration with Task 1.1 (Padding Module)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENCRYPTION FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ECB / CBC:                                                    │
│  Plaintext → Padding.pad() → AES.encrypt() → Ciphertext        │
│                                                                 │
│  CTR / GCM:                                                    │
│  Plaintext → AES.encrypt() → Ciphertext (NO padding)           │
│                                                                 │
│                    DECRYPTION FLOW                              │
│                                                                 │
│  ECB / CBC:                                                    │
│  Ciphertext → AES.decrypt() → Padding.unpad() → Plaintext      │
│                                                                 │
│  CTR / GCM:                                                    │
│  Ciphertext → AES.decrypt() → Plaintext (NO unpadding)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. PYCA CRYPTOGRAPHY API RESEARCH

### 6.1 Core API Structure

PyCA `cryptography` provides the `Cipher` class which combines an algorithm with a mode.

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
encryptor = cipher.encryptor()
decryptor = cipher.decryptor()
```

### 6.2 Mode-Specific APIs

| Mode | Class | Constructor | IV/Nonce Required |
| :--- | :--- | :--- | :--- |
| ECB | `modes.ECB()` | No arguments | None |
| CBC | `modes.CBC(iv)` | `iv` (16 bytes) | 16 bytes |
| CTR | `modes.CTR(nonce)` | `nonce` (16 bytes) | 16 bytes |
| GCM | `modes.GCM(nonce)` | `nonce` (12-16 bytes) | 12-16 bytes |

### 6.3 Encryption/Decryption API

```python
# Encryption
encryptor = cipher.encryptor()
ciphertext = encryptor.update(plaintext) + encryptor.finalize()

# Decryption
decryptor = cipher.decryptor()
plaintext = decryptor.update(ciphertext) + decryptor.finalize()
```

### 6.4 GCM-Specific API (AEAD)

For GCM, the API includes authentication tag handling:

```python
# Encryption with GCM
encryptor = cipher.encryptor()
ciphertext = encryptor.update(plaintext) + encryptor.finalize()
tag = encryptor.tag  # Get authentication tag

# Decryption with GCM
decryptor = cipher.decryptor()
plaintext = decryptor.update(ciphertext) + decryptor.finalize_with_tag(tag)
```

---

## 7. CRITICAL INVALIDTAG AUDIT

### 7.1 Findings

| Question | Answer |
| :--- | :--- |
| Does ECB produce `InvalidTag`? | ❌ **NO** — ECB has no authentication |
| Does CBC produce `InvalidTag`? | ❌ **NO** — CBC has no authentication |
| Does CTR produce `InvalidTag`? | ❌ **NO** — CTR has no authentication |
| Does GCM produce `InvalidTag`? | ✅ **YES** — When tag verification fails |

### 7.2 Exception Behavior by Mode

| Mode | Authentication Failure | Padding Failure | Other Errors |
| :--- | :--- | :--- | :--- |
| ECB | N/A | `ValueError` | `ValueError` |
| CBC | N/A | `ValueError` | `ValueError` |
| CTR | N/A | N/A | `ValueError` |
| GCM | `InvalidTag` | N/A | `ValueError` |

### 7.3 Specification Conflict Assessment

**Current Project Specification:** May contain references to `InvalidTag` for generic decryption.

**Technical Reality:**
- `InvalidTag` is **ONLY** raised by GCM decryption
- ECB, CBC, and CTR decryption **NEVER** raise `InvalidTag`

**⚠️ SPECIFICATION CONFLICT — REQUIRES HUMAN DECISION**

If the project specification assumes `InvalidTag` for all modes, this must be corrected.

**Recommended Resolution:**
- Document that `InvalidTag` is GCM-specific
- Use `ValueError` for ECB/CBC/CTR padding/validation failures
- Handle `InvalidTag` only in GCM decryption

---

## 8. VALIDATION CONTRACT

### 8.1 Key Validation

| Scenario | Expected Behavior | Exception |
| :--- | :--- | :--- |
| Missing key | Raise error | `ValueError` |
| Wrong type | Raise error | `TypeError` |
| Invalid length (not 16/24/32 bytes) | Raise error | `ValueError` |
| Empty key | Raise error | `ValueError` |

### 8.2 Data Validation

| Scenario | Expected Behavior | Exception |
| :--- | :--- | :--- |
| Empty plaintext | Encrypt successfully | - |
| Empty ciphertext (ECB/CBC) | Raise error | `ValueError` |
| Invalid type | Raise error | `TypeError` |

### 8.3 IV/Nonce Validation

| Scenario | Expected Behavior | Exception |
| :--- | :--- | :--- |
| Missing IV (CBC) | Raise error | `ValueError` |
| Wrong IV length (CBC) | Raise error | `ValueError` |
| Missing IV (ECB) | Ignore (not used) | - |
| Missing nonce (GCM) | Raise error | `ValueError` |
| Wrong nonce length (GCM) | Raise error | `ValueError` |

### 8.4 Authentication Tag Validation (GCM)

| Scenario | Expected Behavior | Exception |
| :--- | :--- | :--- |
| Missing tag | Raise error | `ValueError` |
| Wrong tag length | Raise error | `ValueError` |
| Tag verification fails | Raise error | `InvalidTag` |

---

## 9. SECURITY ANALYSIS

### 9.1 Mode Security Comparison

| Mode | Confidentiality | Integrity | Authentication | Pattern Leakage | Malleability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ECB** | ✅ | ❌ | ❌ | ⚠️ **HIGH** | ✅ |
| **CBC** | ✅ | ❌ | ❌ | ✅ **LOW** | ⚠️ **YES** |
| **CTR** | ✅ | ❌ | ❌ | ✅ **LOW** | ⚠️ **YES** |
| **GCM** | ✅ | ✅ | ✅ | ✅ **LOW** | ❌ **NO** |

### 9.2 Critical Security Considerations

**ECB Pattern Leakage:**
- Identical plaintext blocks → Identical ciphertext blocks
- **Implication:** Visual patterns remain visible in encrypted images

**CBC Padding Oracle:**
- If error messages distinguish between padding errors and other errors, attackers can decrypt
- **Mitigation:** Use generic error messages, constant-time validation

**CTR Nonce Reuse:**
- Same nonce + same key → Same keystream
- **Implication:** XOR of two ciphertexts reveals XOR of plaintexts

**GCM Nonce Reuse:**
- Completely breaks security
- **Implication:** Attacker recovers authentication key, can forge ciphertexts

### 9.3 Recommendation for Project

| Mode | Recommended For |
| :--- | :--- |
| **ECB** | ✅ Demonstrating insecurity (ECB Penguin) |
| **CBC** | ✅ Performance comparison, legacy compatibility |
| **CTR** | ✅ Performance comparison (stream mode) |
| **GCM** | ✅ Authenticated encryption demonstration |

---

## 10. PERFORMANCE RESEARCH

### 10.1 Factors Affecting AES Performance

| Factor | Impact |
| :--- | :--- |
| **Key Size** | Larger keys → More rounds → Slower encryption |
| **Mode** | ECB fastest (parallelizable); CBC slower (sequential) |
| **Hardware Acceleration** | AES-NI significantly speeds up ECB, CTR, GCM |
| **Data Size** | Overhead is more noticeable for small data |
| **Padding** | Adds small overhead |

### 10.2 Benchmarking Methodology

Based on `04_Methodology.md`:

1. **Warmup:** 2 iterations (unmeasured)
2. **Measurement:** 5 iterations (recorded)
3. **Statistics:** Mean, median, standard deviation
4. **Outlier Removal:** IQR method
5. **Metrics:** Encryption time, decryption time, throughput (MB/s)

### 10.3 Expected Performance Patterns

| Comparison | Expected Result |
| :--- | :--- |
| AES-128 vs AES-256 | AES-128 faster |
| ECB vs CBC | ECB faster |
| CTR vs CBC | CTR faster (no padding) |
| GCM vs CTR | GCM slightly slower (authentication overhead) |

---

## 11. EDGE CASES

### 11.1 Comprehensive Edge Case Matrix

| Scenario | Mode | Expected Behavior |
| :--- | :--- | :--- |
| Empty plaintext | ECB/CBC | Pad, encrypt, decrypt successfully |
| Empty plaintext | CTR/GCM | Encrypt, decrypt successfully |
| 1-byte plaintext | ECB/CBC | Pad to 16 bytes, encrypt |
| 16-byte plaintext | ECB/CBC | Add full block of padding (16 bytes of \x10) |
| 17-byte plaintext | ECB/CBC | Pad to 32 bytes |
| Invalid key length | All | Raise `ValueError` |
| Missing IV | CBC | Raise `ValueError` |
| Missing IV | ECB | Ignore (not used) |
| Wrong IV length | CBC | Raise `ValueError` |
| Invalid nonce length | CTR/GCM | Raise `ValueError` |
| Corrupted ciphertext | ECB/CBC | Decrypts to garbage, then `ValueError` on unpadding |
| Corrupted ciphertext | GCM | `InvalidTag` on decryption |
| Wrong key | GCM | `InvalidTag` on decryption |
| Nonce reuse | CTR/GCM | **Security hazard** (not an exception) |

---

## 12. INTEGRATION WITH TASK 1.1

### 12.1 Padding Usage by Mode

```
┌─────────────────────────────────────────────────────────────────┐
│                    PADDING INTEGRATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ECB:                                                          │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐                  │
│  │Plaintext│───▶│Padding   │───▶│AES.encrypt│──▶ Ciphertext    │
│  └─────────┘    │.pad()    │    └──────────┘                  │
│                 └──────────┘                                   │
│                                                                 │
│  CBC:                                                          │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐                  │
│  │Plaintext│───▶│Padding   │───▶│AES.encrypt│──▶ Ciphertext    │
│  └─────────┘    │.pad()    │    └──────────┘                  │
│                 └──────────┘                                   │
│                                                                 │
│  CTR / GCM:                                                    │
│  ┌─────────┐    ┌──────────┐                                   │
│  │Plaintext│───▶│AES.      │──▶ Ciphertext                     │
│  └─────────┘    │encrypt() │                                   │
│                 └──────────┘                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 Decryption Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    DECRYPTION INTEGRATION                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ECB / CBC:                                                    │
│  ┌──────────┐    ┌──────────┐    ┌─────────┐                  │
│  │Ciphertext│───▶│AES.      │───▶│Padding  │──▶ Plaintext      │
│  └──────────┘    │decrypt() │    │.unpad() │                  │
│                  └──────────┘    └──────────┘                  │
│                                                                 │
│  CTR / GCM:                                                    │
│  ┌──────────┐    ┌──────────┐                                   │
│  │Ciphertext│───▶│AES.      │──▶ Plaintext                     │
│  └──────────┘    │decrypt() │                                   │
│                  └──────────┘                                   │
│                                                                 │
│  GCM (with authentication):                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                  │
│  │Ciphertext│───▶│AES.      │───▶│Tag       │──▶ Plaintext     │
│  │+ Tag     │    │decrypt() │    │Verification│                 │
│  └──────────┘    └──────────┘    └──────────┘                  │
│                                    │                            │
│                                    ▼                            │
│                              InvalidTag (if fails)    │
└─────────────────────────────────────────────────────────────────┘
```

### 12.3 Architectural Decision Required

**Question:** For GCM decryption, should authentication verification occur before or after unpadding?

**Recommended Answer:** Authentication verification occurs **during** GCM decryption (before any unpadding, since GCM doesn't use padding). The `InvalidTag` exception is raised by the `finalize_with_tag()` call, which happens before any plaintext is returned.

---

## 13. IMPLEMENTATION RISKS

| Risk | Severity | Mitigation |
| :--- | :--- | :--- |
| Confusing block size with key size | 🔴 HIGH | Document: block size = 16 bytes for all AES variants |
| Applying PKCS#7 to CTR/GCM | 🔴 HIGH | Mode check before padding |
| Missing IV for CBC | 🔴 HIGH | Validate in `encrypt()` and `decrypt()` |
| Nonce reuse in CTR/GCM | 🔴 HIGH | Document warning; use `os.urandom()` |
| Incorrect GCM tag handling | 🔴 HIGH | Use `finalize_with_tag()` properly |
| Swallowing `InvalidTag` | 🔴 HIGH | Always raise; never ignore authentication failures |
| Confusing padding failure with auth failure | 🟡 MEDIUM | Separate error handling paths |
| ECB insecurity (using for real data) | 🟡 MEDIUM | Document as demonstration only |

---

## 14. FINAL RESEARCH CONCLUSIONS

### A. Confirmed AES Facts

| Fact | Source |
| :--- | :--- |
| AES block size = 128 bits (16 bytes) for ALL key sizes | FIPS 197 |
| AES-128 = 10 rounds, AES-192 = 12 rounds, AES-256 = 14 rounds | NIST FIPS 197 |
| AES is a symmetric block cipher | FIPS 197 |

### B. Confirmed Project Requirements

| Requirement | Status |
| :--- | :--- |
| AES-128, AES-192, AES-256 support | ✅ Required |
| ECB and CBC modes | ✅ Required |
| `AESCipher` class in `src/core/aes_cipher.py` | ✅ Required |
| `generate_key()`, `generate_iv()`, `encrypt()`, `decrypt()` | ✅ Required |
| Performance measurement (time, throughput) | ✅ Required |

### C. Specification Ambiguities

| Ambiguity | Status |
| :--- | :--- |
| Whether CTR mode is required | 🟡 AMBIGUOUS |
| Whether GCM mode is required | 🟡 AMBIGUOUS |
| Exact exception types for each mode | 🟡 AMBIGUOUS |

### D. Specification Conflicts

| Conflict | Status |
| :--- | :--- |
| `InvalidTag` applicability | 🔴 CONFLICT — Only GCM raises `InvalidTag` |

### E. Human Decisions Required

| Decision | Options | Recommendation |
| :--- | :--- | :--- |
| **CTR Mode Support** | Include or exclude | ✅ Include (adds stream mode comparison) |
| **GCM Mode Support** | Include or exclude | ✅ Include (adds authenticated encryption) |
| **`InvalidTag` Handling** | Document GCM-specific | ✅ Document that only GCM raises `InvalidTag` |
| **Padding for CTR/GCM** | Apply or skip | ✅ Skip (no padding needed) |

### F. Recommended AES Implementation Contract

```python
"""
AES Encryption/Decryption Implementation
Supports 128, 192, and 256-bit keys with ECB, CBC, CTR, and GCM modes.
"""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag  # GCM only
from src.utils.padding import Padding
import os


class AESCipher:
    """
    AES encryption/decryption implementation.
    """
    
    VALID_KEY_SIZES = [128, 192, 256]
    VALID_MODES = ['ECB', 'CBC', 'CTR', 'GCM']
    BLOCK_SIZE = 16  # AES block size in bytes (128 bits)
    
    def __init__(self, key_size: int, mode: str):
        """
        Initialize AES cipher.
        
        Args:
            key_size (int): Key size in bits (128, 192, or 256)
            mode (str): Mode of operation ('ECB', 'CBC', 'CTR', or 'GCM')
            
        Raises:
            ValueError: If key_size or mode is invalid
        """
        # Validate key_size
        if key_size not in self.VALID_KEY_SIZES:
            raise ValueError(f"key_size must be {self.VALID_KEY_SIZES}, got {key_size}")
        
        # Validate mode
        if mode not in self.VALID_MODES:
            raise ValueError(f"mode must be {self.VALID_MODES}, got {mode}")
        
        self.key_size = key_size
        self.mode = mode
        self.key = None
        self.iv = None
        self.nonce = None
        self.tag = None
    
    def generate_key(self) -> bytes:
        """
        Generate a random key of the specified size.
        
        Returns:
            bytes: Random key of length key_size/8 bytes
            
        Example:
            cipher = AESCipher(256, 'CBC')
            key = cipher.generate_key()  # Returns 32 bytes
        """
        key_length = self.key_size // 8
        return os.urandom(key_length)
    
    def generate_iv(self) -> bytes:
        """
        Generate a random Initialization Vector (IV) for CBC mode.
        
        Returns:
            bytes: 16-byte random IV
            
        Raises:
            ValueError: If mode is ECB (IV not used)
        """
        if self.mode == 'ECB':
            raise ValueError("IV not used in ECB mode")
        return os.urandom(self.BLOCK_SIZE)
    
    def generate_nonce(self, length: int = 12) -> bytes:
        """
        Generate a random nonce for CTR or GCM mode.
        
        Args:
            length (int): Nonce length in bytes (12-16 recommended)
            
        Returns:
            bytes: Random nonce
            
        Raises:
            ValueError: If mode is not CTR or GCM
        """
        if self.mode not in ['CTR', 'GCM']:
            raise ValueError(f"Nonce not used in {self.mode} mode")
        if length < 12 or length > 16:
            raise ValueError(f"Nonce length must be 12-16 bytes, got {length}")
        return os.urandom(length)
    
    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes = None, 
                nonce: bytes = None, aad: bytes = None) -> bytes:
        """
        Encrypt plaintext using AES.
        
        Args:
            plaintext (bytes): Data to encrypt
            key (bytes): Encryption key (must match key_size)
            iv (bytes, optional): IV for CBC mode (16 bytes)
            nonce (bytes, optional): Nonce for CTR/GCM mode (12-16 bytes)
            aad (bytes, optional): Additional authenticated data (GCM only)
            
        Returns:
            bytes: Encrypted ciphertext (GCM also stores tag internally)
            
        Raises:
            ValueError: If key size doesn't match, IV missing for CBC, etc.
            InvalidTag: Only for GCM decryption (not encryption)
        """
        # Validate key length
        key_length = self.key_size // 8
        if len(key) != key_length:
            raise ValueError(f"Key must be {key_length} bytes, got {len(key)}")
        
        # Prepare data based on mode
        if self.mode in ['ECB', 'CBC']:
            # Apply PKCS#7 padding
            plaintext = Padding.pad(plaintext, self.BLOCK_SIZE)
        
        # Create cipher
        if self.mode == 'ECB':
            mode_obj = modes.ECB()
        elif self.mode == 'CBC':
            if iv is None:
                raise ValueError("IV required for CBC mode")
            if len(iv) != self.BLOCK_SIZE:
                raise ValueError(f"IV must be {self.BLOCK_SIZE} bytes")
            mode_obj = modes.CBC(iv)
        elif self.mode == 'CTR':
            if nonce is None:
                raise ValueError("Nonce required for CTR mode")
            # CTR nonce is typically 16 bytes
            if len(nonce) != 16:
                raise ValueError("CTR nonce must be 16 bytes")
            mode_obj = modes.CTR(nonce)
        elif self.mode == 'GCM':
            if nonce is None:
                raise ValueError("Nonce required for GCM mode")
            if len(nonce) < 12 or len(nonce) > 16:
                raise ValueError("GCM nonce must be 12-16 bytes")
            mode_obj = modes.GCM(nonce)
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
        
        # Encrypt
        cipher = Cipher(algorithms.AES(key), mode_obj, backend=default_backend())
        encryptor = cipher.encryptor()
        
        # For GCM, handle AAD
        if self.mode == 'GCM' and aad:
            encryptor.authenticate_additional_data(aad)
        
        # Perform encryption
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # For GCM, store tag
        if self.mode == 'GCM':
            self.tag = encryptor.tag
        
        return ciphertext
    
    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes = None,
                nonce: bytes = None, tag: bytes = None, aad: bytes = None) -> bytes:
        """
        Decrypt ciphertext using AES.
        
        Args:
            ciphertext (bytes): Data to decrypt
            key (bytes): Encryption key (must match key_size)
            iv (bytes, optional): IV for CBC mode (16 bytes)
            nonce (bytes, optional): Nonce for CTR/GCM mode
            tag (bytes, optional): Authentication tag for GCM mode
            aad (bytes, optional): Additional authenticated data (GCM only)
            
        Returns:
            bytes: Decrypted plaintext
            
        Raises:
            ValueError: If key size doesn't match, IV missing for CBC, etc.
            InvalidTag: If GCM authentication fails
        """
        # Validate key length
        key_length = self.key_size // 8
        if len(key) != key_length:
            raise ValueError(f"Key must be {key_length} bytes, got {len(key)}")
        
        # Create cipher
        if self.mode == 'ECB':
            mode_obj = modes.ECB()
        elif self.mode == 'CBC':
            if iv is None:
                raise ValueError("IV required for CBC mode")
            if len(iv) != self.BLOCK_SIZE:
                raise ValueError(f"IV must be {self.BLOCK_SIZE} bytes")
            mode_obj = modes.CBC(iv)
        elif self.mode == 'CTR':
            if nonce is None:
                raise ValueError("Nonce required for CTR mode")
            if len(nonce) != 16:
                raise ValueError("CTR nonce must be 16 bytes")
            mode_obj = modes.CTR(nonce)
        elif self.mode == 'GCM':
            if nonce is None:
                raise ValueError("Nonce required for GCM mode")
            if len(nonce) < 12 or len(nonce) > 16:
                raise ValueError("GCM nonce must be 12-16 bytes")
            if tag is None:
                raise ValueError("Tag required for GCM decryption")
            mode_obj = modes.GCM(nonce, tag=tag)
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
        
        # Decrypt
        cipher = Cipher(algorithms.AES(key), mode_obj, backend=default_backend())
        decryptor = cipher.decryptor()
        
        # For GCM, handle AAD
        if self.mode == 'GCM' and aad:
            decryptor.authenticate_additional_data(aad)
        
        # Perform decryption
        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        except InvalidTag:
            # GCM authentication failed
            raise
        
        # Remove padding for ECB/CBC
        if self.mode in ['ECB', 'CBC']:
            plaintext = Padding.unpad(plaintext, self.BLOCK_SIZE)
        
        return plaintext
```

---

## 15. SOURCES

| Source | Reference | Purpose |
| :--- | :--- | :--- |
| NIST FIPS 197 | Advanced Encryption Standard (AES) | AES specification |
| NIST SP 800-38A | Block Cipher Modes | ECB, CBC, CTR modes |
| NIST SP 800-38D | Galois/Counter Mode (GCM) | GCM authenticated encryption |
| PyCA Cryptography | `symmetric-encryption.rst` | Python cryptography API |
| PyCA Cryptography | `InvalidTag` documentation | GCM exception behavior |
| RFC 5116 | Authenticated Encryption | AEAD algorithms |

---

## 16. NEXT STEPS

1. **Review this report** with the team
2. **Make decisions** on the open questions (CTR/GCM support, `InvalidTag` handling)
3. **Update** `docs/05_API_Interface_Spec.md` with corrected exception documentation
4. **Update** `ai_context/02_current_task.md` to reflect the AES implementation task
5. **Begin Antigravity Explore phase** for AES implementation

---

**Report Status:** ✅ Complete  
**Ready for:** Team Review & Architectural Decision Making



now another source report
PKCS#7 AES Encryption/Decryption Deep Research & Audit Report
Technical Research, Specification Audit, and Implementation Contract: AES Encryption (Task 1.2)

1. Executive Summary

This document establishes the technical foundation and formal audit for Task 1.2 of the Cryptography Testing Lab project. As the system's primary security layer, the implementation of the Advanced Encryption Standard (AES) is critical; any architectural flaw here compromises the integrity of all downstream performance and security analyses. This research synthesizes industry standards (FIPS 197) with the specific constraints of our Python-based environment.

Core Audit Findings:

* Block Size Invariance: A 128-bit block size must be strictly maintained across all key lengths (128, 192, 256-bit) to ensure compliance with the AES standard and prevent common implementation errors.
* Exception Strategy Correction: The current API specification incorrectly mandates the use of InvalidTag for ECB and CBC modes. This must be corrected to use ValueError during unpadding to prevent side-channel leaks.
* Methodological Rigor: Benchmark iteration counts must be increased to 50–100 runs to filter out operating system noise and provide statistically defensible throughput data.

This research transitions from theoretical constraints to a formal execution contract, ensuring the core cryptographic engine is both secure and performant.

2. Project Requirements Extraction

Strict requirements traceability is mandatory for cryptographic modules to prevent "scope creep" and ensure the final implementation adheres to the verified security model.

Requirement ID	Source Document	Description	Technical Constraint
REQ-1.2.1	docs/01_Project_Proposal.md	Symmetric Algorithm Support	Standard AES-128, AES-192, and AES-256.
REQ-1.2.2	00_session_start.txt	Target Tech Stack	Python 3.10+, cryptography 42.0.0+.
REQ-1.2.3	docs/05_API_Interface_Spec.md	Chaining Mode Support	ECB (Electronic Codebook) and CBC (Cipher Block Chaining).
REQ-1.2.4	01_padding_module.txt	Data Alignment	PKCS#7 padding for 16-byte block alignment.
REQ-1.2.5	docs/03_Architecture_Design.md	Randomness Source	CSPRNG only (via os.urandom).
REQ-1.2.6	docs/02_System_Requirements.md	Performance Metrics	Measure Time (ms), Throughput (MB/s), and Memory.

Satisfying these requirements requires a deep technical understanding of the Rijndael cipher family.

3. AES Fundamentals

The Advanced Encryption Standard (AES) is a symmetric block cipher standardized by NIST in FIPS 197. Based on the Rijndael algorithm, it provides the primary layer of confidentiality for the system.

Rigorous Technical Mechanics:

1. Invariant Block Size: AES operates on a fixed block size of 128 bits (16 bytes). This is a constant; the block size never scales with the key size.
2. State Array Mechanics: Transformations occur on a 4x4 matrix of bytes called the State. Each round includes:
  * SubBytes: Non-linear substitution using an S-box.
  * ShiftRows: Cyclically shifting rows of the State.
  * MixColumns: Linear transformation of columns (skipped in the final round).
  * AddRoundKey: XORing the State with the round key.
3. Key Expansion: The cipher key is expanded via the Rijndael key schedule into a sequence of round keys.
4. Round Counts: The number of transformation rounds is mathematically linked to the key size:
  * 128-bit key: 10 rounds.
  * 192-bit key: 12 rounds.
  * 256-bit key: 14 rounds.

Understanding these mechanics is essential for evaluating the performance delta between key sizes.

4. AES Key-Size Behaviour

The selection of a key size represents a strategic balance between computational overhead and the desired security margin.

* Security Margins: While AES-128 remains secure against classical attacks, AES-256 provides a significant safety margin for long-term data protection.
* Post-Quantum Resilience: AES-256 is recommended for post-quantum security, as Grover’s algorithm effectively reduces the bit-strength of symmetric ciphers by half.
* PyCA Compatibility: The specified cryptography 42.0.0+ library supports all three key sizes (16, 24, and 32 bytes).
* Verification of Block Invariance: Implementation logic must ensure that the block size remains exactly 16 bytes for all key sizes. Failure to maintain this constant is a primary source of decryption failure in multi-cipher systems.

These keys are utilized within specific modes of operation to process data streams.

5. Mode of Operation Research

Modes of operation transform block ciphers into stream-like processors, dictating how identical plaintext blocks are handled.

Electronic Codebook (ECB)

* Mechanism: Processes blocks independently. No chaining occurs.
* Vulnerability: Suffers from the "ECB Penguin" effect. Pattern leakage occurs because identical plaintext blocks result in identical ciphertext blocks, failing to provide semantic security.

Cipher Block Chaining (CBC)

* Mechanism: Uses XOR chaining. Each plaintext block is XORed with the previous ciphertext block before encryption.
* IV Constraints: Requires a 16-byte Initialization Vector (IV). The IV must be unpredictable and generated via a CSPRNG to prevent first-block disclosure attacks.
* Vulnerability: Vulnerable to padding oracle attacks if error responses differentiate between "bad padding" and "bad key."

The block-based nature of these modes necessitates deterministic data alignment.

6. Padding Interaction

Because AES is a block cipher, inputs must be multiples of 16 bytes. Task 1.2 relies on the PKCS#7 padding standard implemented in Task 1.1.

Padding Logic Matrix

Mode	Padding Requirement	Utility Invocation
ECB	Mandatory	Required before .encrypt()
CBC	Mandatory	Required before .encrypt()
GCM/CTR	None (Not in Task 1.2 Scope)	Directive: Do not pad

The encryption pipeline must invoke the Padding utility from src/utils/padding.py prior to the library's encryption call.

7. PyCA Cryptography API Research

The cryptography (PyCA) library provides a battle-tested interface for AES implementation.

Core API Mapping:

* Cipher Object: Cipher(algorithms.AES(key), modes.CBC(iv)) or modes.ECB().
* Stateful Interface: Use .encryptor() and .decryptor() for processing.
* Runtime Alignment: PyCA enforces 16-byte alignment for ECB/CBC. Passing unaligned data will result in a ValueError from the library itself.

This API usage must be audited against our project's exception-handling goals.

8. Critical InvalidTag Audit

A cryptanalytic audit of the planned AESCipher logic reveals a critical conflict in docs/05_API_Interface_Spec.md.

* The Problem: The specification incorrectly suggests raising cryptography.exceptions.InvalidTag during AES decryption.
* The Audit Result: InvalidTag is exclusive to Authenticated Encryption (AEAD) modes like GCM. ECB and CBC modes lack a Message Authentication Code (MAC) tag; therefore, the library will never raise this exception for these modes.
* Actionable Instruction: The developer must reserve InvalidTag for future AEAD support. For ECB/CBC, the system must raise ValueError or a custom PaddingError during the unpadding stage if integrity is compromised.

9. Validation Contract

The input validation layer serves as the first line of defense against malformed data.

Input Parameter	Type	Constraint	Action on Failure
key_size	int	Must be exactly 128, 192, or 256.	Raise ValueError
mode	str	Must be 'ECB' or 'CBC'.	Raise ValueError
key	bytes	Length must be key_size // 8.	Raise ValueError
iv	bytes	Exactly 16 bytes (Mandatory for CBC).	Raise ValueError
plaintext	bytes	Cannot be None.	Raise ValueError

10. Placeholder / Performance Context

The project's primary objective is to quantify the performance trade-offs inherent in key-size selection. While AES-256 is theoretically more secure, the 40% increase in rounds (14 vs 10 for 128-bit) introduces computational overhead that must be accurately benchmarked.

11. Performance Research

Benchmarking requires statistical rigour to eliminate background OS interference and jitter.

Benchmark Methodology:

* Metrics:
  * Execution Time (ms).
  * Throughput (MB/s where 1MB = 1,048,576 bytes).
  * Memory usage tracked via psutil.
* Statistical Rigour:
  * 5–10 warmup runs to prime CPU caches.
  * 50–100 iteration runs to calculate stable means.
* Scope Restriction: RSA performance is restricted to key encapsulation; bulk data throughput is exclusive to AES/symmetric ciphers.

12. Edge Cases

A system's reliability is defined by its behavior at the margins of its operational envelope.

Edge Case	Scenario	Expected Behaviour / Explanation
Empty Input	Encrypting 0 bytes.	Returns 16 bytes (one full block of PKCS#7 padding).
Block Boundary (16n-1)	Input size 15, 31, etc.	Explains boundary logic: must add exactly 1 byte of padding.
Block Boundary (16n+1)	Input size 17, 33, etc.	Explains boundary logic: must add 15 bytes of padding to reach next block.
Nonce Reuse	Using same Key/IV twice.	Security hazard: leads to ciphertext pattern recognition.
Tag Corruption	AEAD validation failure.	Mandatory: Must raise InvalidTag (for future GCM compatibility).

13. Integration with Task 1.1

The AESCipher class functions as a "dumb" processor in a pipeline that utilizes Task 1.1 for alignment and integrity verification.

Strategic Integration Notes:

* Static Utility: The Padding class (from Task 1.1) is a static utility. The AESCipher class must call Padding.pad() and Padding.unpad() directly without instantiating a padding object.
* Integrity Check: During decryption, Padding.is_padded() must be invoked to verify the structure of the tail end of the plaintext before the unpadding operation is finalized.

14. Project-Specific Contract Audit

The following audit evaluates the internal docs/05_API_Interface_Spec.md against cryptographic realities.

API Element	Status	Audit Finding
AESCipher Signature	✅ CONSISTENT	Aligns with standard Python implementation patterns.
generate_iv Size	✅ CONSISTENT	Correctly locked to 16 bytes as per AES standard.
decrypt() docstring	🔴 CONFLICT	Docstring incorrectly mandates InvalidTag for ECB/CBC.
Support Matrix	✅ CONSISTENT	Correctly identifies 128, 192, and 256-bit keys.
Block Size	✅ CONSISTENT	Fixed at 16 bytes for all variants.

15. Implementation Risks

1. Key-Block Size Confusion: Assuming that AES-256 requires a 32-byte block size is a critical error that will break standard compatibility.
2. Predictable IVs: Using random.random instead of os.urandom for IVs will compromise CBC confidentiality.
3. Exception Swallowing: Failing to catch and re-raise unpadding errors during decryption results in "silent" data corruption.

16. Final Research Conclusions

Verified Implementation Facts

* AES block size is strictly 16 bytes.
* CBC mode requires a 16-byte random IV; ECB mode must not use an IV.
* PKCS#7 padding is mandatory for ECB and CBC modes.

Required Human Decisions

Prior to finalizing the implementation, the human lead must decide:

1. CSPRNG Source: Confirm the use of os.urandom versus the secrets module for IV generation.
2. ECB Deprecation: Determine if ECB mode should be deprecated or restricted only to the "Penguin" security demonstration to prevent accidental use in production-like scenarios.

Recommended AES Implementation Contract

The developer is hereby directed to execute Task 1.2 according to the following imperatives:

* Class Architecture: Implement AESCipher using the cryptography.hazmat primitives.
* Integrity First: Raise ValueError for any padding or unpadding failure. Do not use InvalidTag for CBC/ECB.
* Binary Precision: Use 2^{20} as the divisor for megabyte throughput calculations to ensure mathematical consistency.
* Pipeline Logic: Decryption must follow the order: decrypt() -> is_padded() check -> unpad().
* Type Safety: Utilize Python type hints for all bytes and int arguments to ensure interface contract compliance.
