# TASK 1.2 — INDEPENDENT CODE REVIEW REPORT

**Phase:** Code Review Only · **Mode:** READ-ONLY — no files modified, no fixes applied, no commits/pushes.

**Reviewer basis:** Independent re-read of the actual on-disk `src/core/aes_cipher.py` and `tests/test_aes.py` (not the prior reports), live pytest execution, direct PyCA re-verification of all four KAT vectors, and git status scope check.

---

## 1. Review Scope

| Item | Detail |
| :--- | :--- |
| **Files under review** | `src/core/aes_cipher.py` (208 lines), `tests/test_aes.py` (447 lines) |
| **Sources of truth** | `docs/05_API_Interface_Spec.md` §3.1, `docs/03_Architecture_Design.md`, `docs/02_System_Requirements.md`, `docs/04_Methodology.md`, approved `TASK_1.2_AES_EXPLORE_AND_IMPLEMENTATION_PLAN.md` (incl. 5 corrections), Task 1.1 `src/utils/padding.py` |
| **Mode** | Strictly read-only |

---

## 2. Test Execution (independent)

* `pytest tests/test_aes.py` → 123 passed in 0.26s (all parametrizations, including the bool/float/str/None edge cases for `key_size`, all modes, all plaintext shapes, and the 4 KAT tests).
* `pytest tests/test_padding.py` → 30 passed (Task 1.1 intact, no regression).
* **Full suite:** 153 collected, 153 passed. The prior "153/153 green" claim is independently confirmed.

---

## 3. API Contract Compliance (§3.1)

All five methods match the authoritative spec exactly — signatures, parameter order, defaults, and return types:

| Method | Spec | Implementation | Verdict |
| :--- | :--- | :--- | :---: |
| `__init__(key_size, mode)` | `ValueError` on invalid | `key_size` not in (128, 192, 256) and `mode` not in ('ECB', 'CBC') → `ValueError` | ✅ |
| `generate_key() -> bytes` | `key_size/8` random | `os.urandom(self.key_size // 8)` | ✅ |
| `generate_iv() -> bytes` | 16-byte; `ValueError` if ECB | ECB → `ValueError`; else `os.urandom(16)` | ✅ |
| `encrypt(plaintext, key, iv=None)` | `ValueError` on bad key/IV/plaintext | full validation + pad → AES → ciphertext | ✅ |
| `decrypt(ciphertext, key, iv=None)` | `ValueError` on bad key/IV/padding/alignment | validation + alignment check + AES → unpad | ✅ |

Constructor accepts `bytearray` as well as `bytes` throughout (matching the documented Padding convention). The public error contract is plain `ValueError` — no `InvalidTag`, no `InvalidKey`, no custom hierarchy. The spec's §3.1 note (`InvalidTag` not exposed for ECB/CBC) is honored.

---

## 4. Key Validation

`_validate_key` (`aes_cipher.py:140`) rejects non-bytes/bytearray types and enforces `len(key) == key_size // 8` (16/24/32) with a clear message, normalizing to bytes. Tests cover wrong lengths (15/17/23/25/31/33 across all key sizes), wrong types (str/int/None/list), and `bytearray` acceptance. ✅

---

## 5. IV Contract

`_validate_iv` (`aes_cipher.py:163`) enforces: ECB + supplied IV → `ValueError`; CBC + `iv=None` → `ValueError`; CBC IV must be bytes/bytearray and exactly 16 bytes. No silent auto-generation (verified by `test_cbc_encrypt_does_not_auto_generate_iv`). Tests cover missing IV, wrong lengths (0/8/15/17/32), wrong types, ECB-with-IV, and `bytearray` IV. ✅

---

## 6. Padding Integration

* `encrypt`: `Padding.pad(data, 16)` before AES; `decrypt`: `Padding.unpad(padded, 16)` after AES — the documented consumption flow, using the frozen Task 1.1 utility with zero modification.
* Empty plaintext → `Padding.pad(b"", 16)` = `16×0x10` → round-trips to `b""` (verified).
* Corrupted ciphertext → garbage → `Padding.unpad` raises `ValueError`; never `InvalidTag` (ECB/CBC). Confirmed by `test_corrupted_ciphertext_raises_value_error_not_invalid_tag`.
* `src/utils/padding.py` and `tests/test_padding.py` show no diff since `cf21434` — Task 1.1 remains frozen. ✅

---

## 7. Cryptographic Correctness

* PyCA usage is modern and correct: `Cipher(algorithms.AES(key), modes.ECB())` / `modes.CBC(iv)`, no deprecated `backend=` argument (`aes_cipher.py:203-207`).
* `encryptor().update(padded) + encryptor().finalize()` — the required call pattern; no state is reused across calls (each `_build_cipher` returns a fresh `Cipher`, so no cross-operation state leakage).
* ECB produces identical output for identical key/plaintext (deterministic); CBC output varies with the IV (`test_cbc_iv_mixing`). ✅

---

## 8. Security

* Key/IV generation uses `os.urandom()` (CSPRNG) as mandated by `docs/02_System_Requirements.md` Rec. 8 / the approved plan. The non-determinism tests are correctly framed as lightweight checks, not proof of randomness quality (matching plan correction #1).
* The diffusion test flips exactly one bit and asserts ciphertexts differ — a correctness sanity check, explicitly distinguished from the later dedicated avalanche analysis (correction #2).
* Wrong-key test correctly accepts either `ValueError` (invalid padding) or a non-matching returned plaintext (correction #3) — no fabricated deterministic exception expectation.
* The report wording on padding oracles is conservative and does not over-claim CBC padding-oracle resistance from the exception type alone. ✅

---

## 9. Known-Answer Vector Independence

All four vectors were independently re-verified in this review against PyCA directly (not merely trusted from the test file):

| Vector | Source | Independent result |
| :--- | :--- | :--- |
| **AES-128 ECB** | FIPS 197 C.1 | matches (`3925841d…`) ✅ |
| **AES-192 ECB** | FIPS 197 C.2 | matches (`bd334f1d…`) ✅ |
| **AES-256 ECB** | FIPS 197 C.3 | matches (`f3eed1bd…`) ✅ |
| **AES-128 CBC** | SP 800-38A F.2.1 | matches (`7649abac…`) ✅ |

No KAT transcription defect. The ECB/CBC first-block-only assertion is sound given the 2-block padded output. No limitation needs to be stated — values were independently confirmed.

---

## 10. Architecture & Scope

* Implementation lives in `src/core/` (Core layer) as `AESCipher`, consuming `src/utils/padding.py` — matches the documented Utility → Core layering and the §3.1 contract.
* Key/IV generation correctly stays on `AESCipher` (locked decision #9); `key_generator.py` remains an unwired stub.
* No CTR/GCM/AEAD/authentication implemented — scope discipline honored.
* `git status --short` shows exactly the two authorized implementation files modified: `M src/core/aes_cipher.py`, `M tests/test_aes.py`. The `M docs/05_API_Interface_Spec.md` is the pre-existing, separately-approved spec correction (not a Task 1.2 change). Untracked items (`.claude/`, `DECISIONS.md`, `docs/implementation/task2/`, `docs/research/AES/`) are pre-existing and untouched.

---

## 11. Code Quality

Clear, well-documented, idiomatically structured (private validator helpers `_validate_data`/`_validate_key`/`_validate_iv`/`_build_cipher` keep the public methods minimal and readable). Docstrings match behavior. Comments are accurate and appropriately qualified.

### Non-blocking observations (informational only — no changes required):
* In `test_corrupted_ciphertext_raises_value_error_not_invalid_tag`, the trailing `try/except InvalidTag` block is redundant: the preceding `pytest.raises(ValueError)` already proves the exception is a `ValueError` (not `InvalidTag`, which is not a `ValueError` subclass). Harmless defensive code.
* `test_non_block_aligned_ciphertext[0]` (empty input, `bad_len=0`) actually raises `ValueError` from `Padding.unpad` (empty unpad), not from the alignment check (0 is block-aligned). The assertion is still valid and correct; only the label is a slight misnomer.
* Neither affects correctness, coverage, or the contract.

---

## FINAL VERDICT

### PASS

* All 123 AES tests pass; 30/30 padding tests pass; 153/153 full suite, no regressions.
* Every authoritative contract (§3.1 API, key/IV validation, padding integration, error contract, CSPRNG, ECB/CBC-only scope) is satisfied.
* All four NIST KAT vectors independently verified correct.
* Only the two authorized files were modified; Task 1.1 and all other artifacts remain untouched.
* No defect, bug, or spec violation found. The two observations above are cosmetic and do not warrant any change.

**Status:** APPROVED FOR COMMIT / PUSH — awaiting explicit human approval before any commit, per workflow. The review was strictly read-only; no files were created, edited, or committed.
