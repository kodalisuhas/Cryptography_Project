# TASK 1.2 — AES EXPLORE & IMPLEMENTATION PLAN

**Phase:** Explore + Plan (READ-ONLY — no files created, modified, or committed)

---

## 1. Explore Summary

Inspected and verified against the live environment:

* **Task 1.2 artifacts** — `TASK_1.2_CONTEXT_RECONSTRUCTION_REPORT.md`, `TASK_1.2_SPECIFICATION_AUDIT_REPORT.md`, `TASK_1.2_APPLY_APPROVED_SPECIFICATION_CORRECTIONS.md` (all consistent; corrections already applied to the spec).
* **Authoritative docs** — `01`–`05`, `ai/*` (AI rules, session template, review checklist).
* **Source stubs** — confirmed greenfield: `aes_cipher.py`, `test_aes.py`, `key_generator.py`, `cipher_interface.py`, `cipher_factory.py` are all single-line stubs.
* **Task 1.1 dependency** — `padding.py` (5 methods) and `test_padding.py` (30 tests) complete and frozen.
* **Environment** — Python 3.13.0, `cryptography 49.0.0`, `pytest 9.1.1`. No `pyproject.toml`/`pytest.ini`/`conftest.py`; tests import via `from src...` (run from repo root), as `test_padding.py` already does.
* **PyCA API (verified live, version 49.0.0):** `Cipher(algorithms.AES(key), modes.ECB())` / `modes.CBC(iv)` work with no `backend=` argument (the deprecated explicit form is omitted; the `Cipher` constructor's backend defaults to `None`). Encrypt/decrypt lifecycle is `encryptor()` / `update(...)` + `finalize()`.
* **Behavioral probes (read-only `python -c`, no files touched):**
  * ECB & CBC round-trips succeed; ciphertext is block-aligned.
  * Wrong-length key → PyCA raises plain `ValueError` (*Invalid key size (…) for AES.*) — not `InvalidKey` — so our own `ValueError` contract is naturally consistent.
  * Corrupted CBC ciphertext decrypts to garbage (block-aligned), then `Padding.unpad(..., 16)` raises `ValueError("Invalid PKCS#7 padding bytes")`. No `InvalidTag` — confirms the error contract end-to-end.
  * Empty plaintext `b""` → `Padding.pad(b"", 16)` → 16-byte padding block → round-trips back to `b""`.

---

## 2. Current Repository State

| File | Status |
| :--- | :--- |
| `src/core/aes_cipher.py` | Stub (`# AES stub`) — target |
| `tests/test_aes.py` | Stub (`# AES tests`) — target |
| `src/utils/padding.py` | Complete, frozen (Task 1.1, `cf21434`) |
| `tests/test_padding.py` | Complete, 30/30 passing (Task 1.1) |
| `src/utils/key_generator.py` | Stub — out of Task 1.2 scope |
| `src/engines/cipher_interface.py`, `cipher_factory.py` | Stubs — later Service-layer task |
| `docs/05_API_Interface_Spec.md` | Modified (approved §3.1 corrections) — authoritative current version |
| Untracked | `docs/implementation/task2/`, `.claude/`, `DECISIONS.md`, `docs/research/AES/` |

**Git:** branch `dev`, HEAD `cf21434`. Working tree has the one spec change (`M docs/05_API_Interface_Spec.md`) plus intentional untracked items — none staged, none modified by this session.

---

## 3. Authoritative Requirements

Only those grounded in project docs:

* **AES-128 / AES-192 / AES-256; modes ECB and CBC only** (no CTR/GCM/AEAD). — Proposal §3–4, Spec §3.1, Architecture §3.3/§9.1
* **AES block size 16 bytes for all key sizes.** — Spec §3.1, FIPS 197
* **Key mapping:** 128→16 B, 192→24 B, 256→32 B. — Spec §3.1 (`key_size/8`)
* **`AESCipher` with `__init__(key_size, mode)`, `generate_key()`, `generate_iv()`, `encrypt(plaintext, key, iv=None)`, `decrypt(ciphertext, key, iv=None)`.** — Spec §3.1, Architecture §3.3
* **`generate_iv()` raises `ValueError` if mode is ECB; returns 16 CSPRNG bytes for CBC.** — Spec §3.1
* **PKCS#7 padding consumed from the utility layer, not duplicated.** — Architecture §3.5, Spec §6.3
* **CSPRNG (`os.urandom`/`secrets`) for all key/IV generation.** — Docs 02 §13 + Rec. 8, Architecture §11
* **PyCA cryptography as backend; omit deprecated `backend=` argument.** — Docs 02 §4; research (non-authoritative but technically correct)
* **Implementation order:** Utility → Core (Task 1.2) → Service → Analysis → CLI. — Spec §Implementation Order

---

## 4. Locked Human Decisions

Already approved (from the three task2 artifacts) — not reopened:

* **Mode scope:** ECB + CBC only; no CTR/GCM.
* **InvalidTag:** not part of ECB/CBC; invalid padding → `ValueError`.
* **Key validation:** AES engine owns it → `ValueError` (wrong type/length); no backend-specific exception as public contract.
* **Input validation:** `key_size ∈ {128, 192, 256}`; `mode ∈ {'ECB', 'CBC'}`; key 16/24/32 B; plaintext/ciphertext `bytes`/`bytearray`; non-block-aligned ciphertext → `ValueError`.
* **IV contract:** ECB `iv=None` valid, supplied IV → `ValueError`, `generate_iv()` ECB → `ValueError`; CBC 16-byte IV required (`iv=None` → `ValueError`, wrong length → `ValueError`); `generate_iv()` CBC → 16 CSPRNG bytes.
* **Padding:** consume `Padding.pad(data, 16)` / `Padding.unpad(data, 16)`.
* **Empty plaintext:** `b""` valid; pads to full block; decrypt returns `b""`.
* **Error contract:** plain `ValueError` for all public-API failures.
* **Key/IV generation on `AESCipher`** (per Spec §3.1 / Architecture §3.3).
* **Service layer excluded from Task 1.2.**
* **Benchmark methodology unchanged** (5 iterations / 2 warmup — Analysis layer concern).

---

## 5. Architecture Fit

* **Layer:** Core (`src/core/`). AES is the first Core implementation — correct position per the Utility→Core→Service order.
* **Position:** `AESCipher` sits in the Core layer, consuming the Utility layer's `Padding` (Task 1.1). It must not implement its own PKCS#7 or read/write files (that is file_handler/Persistence). No business logic (Service), no metrics (Analysis).
* **Integration with Task 1.1:** a pure consumer relationship — `AESCipher` imports `Padding` and delegates block alignment. Task 1.1 stays frozen.
* **No coupling to Service layer:** `cipher_interface.py`/`cipher_factory.py` are a separate future task; Task 1.2 does not import them. (Verified against the implementation order, not assumed.)

---

## 6. Proposed Implementation Design

```python
# src/core/aes_cipher.py
"""AES encryption/decryption engine (ECB, CBC)."""
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from src.utils.padding import Padding

class AESCipher:
    VALID_KEY_SIZES = (128, 192, 256)
    VALID_MODES = ("ECB", "CBC")
    BLOCK_SIZE = 16

    def __init__(self, key_size: int, mode: str): ...
    def generate_key(self) -> bytes: ...
    def generate_iv(self) -> bytes: ...
    def encrypt(self, plaintext: bytes, key: bytes, iv: bytes = None) -> bytes: ...
    def decrypt(self, ciphertext: bytes, key: bytes, iv: bytes = None) -> bytes: ...

    # private helpers (justified below)
    def _validate_data(self, data, name) -> bytes: ...
    def _validate_key(self, key) -> bytes: ...
    def _validate_iv(self, iv): ...
    def _build_cipher(self, key, iv): ...
```

### Design decisions:
* **`__init__(key_size, mode)`** — validates `key_size ∈ VALID_KEY_SIZES` and `mode ∈ VALID_MODES`; stores both. Invalid → `ValueError`. No case-insensitive aliases (locked contract; do not silently add them).
* **`generate_key()`** — `os.urandom(self.key_size // 8)`. CSPRNG per docs. Key generation stays on the class (locked decision #9).
* **`generate_iv()`** — `ValueError` if ECB; else `os.urandom(16)`.
* **`encrypt` / `decrypt`** — full flow in §7/§8. IV is never auto-generated inside encrypt (locked contract — CBC without IV must error).
* **Private helpers (4, all shared by encrypt and decrypt — genuine DRY, not over-abstraction):**
  * `_validate_data(data, name)` → type-check `bytes`/`bytearray`, return `bytes`, else `ValueError`.
  * `_validate_key(key)` → type-check + `len == key_size // 8`, return `bytes`, else `ValueError`.
  * `_validate_iv(iv)` → mode semantics (ECB: must be `None`; CBC: must be 16-byte `bytes`/`bytearray`), else `ValueError`.
  * `_build_cipher(key, iv)` → constructs `Cipher(algorithms.AES(key), modes.ECB() | modes.CBC(iv))` — centralizes mode→object mapping so encrypt/decrypt don't duplicate it.

---

## 7. Detailed Encryption Flow

`encrypt(plaintext, key, iv=None)`:

1. Validate plaintext (type `bytes`/`bytearray`) → `ValueError`
2. Validate key (type + `len == key_size // 8`) → `ValueError`
3. Validate IV (ECB: must be `None`; CBC: 16 B) → `ValueError`
4. Pad plaintext: `Padding.pad(plaintext, 16)`
5. Build cipher: `_build_cipher(key, iv)`
6. `encryptor()` + `update(padded)` + `finalize()`
7. Return ciphertext

---

## 8. Detailed Decryption Flow

`decrypt(ciphertext, key, iv=None)`:

1. Validate ciphertext (type `bytes`/`bytearray`) → `ValueError`
2. Validate alignment (`len % 16 == 0`) → `ValueError`
3. Validate key (type + `len == key_size // 8`) → `ValueError`
4. Validate IV (ECB: `None`; CBC: 16 B) → `ValueError`
5. Build cipher: `_build_cipher(key, iv)`
6. `decryptor()` + `update(ciphertext)` + `finalize()`
7. Unpad padded plaintext: `Padding.unpad(padded, 16)` → `ValueError` on invalid padding
8. Return plaintext

* **Block-alignment check (#2)** is explicit and early for a clear, specific error before touching PyCA (which would otherwise raise its own `ValueError` on misaligned input).
* **Unpad (#7)** is the single authority for padding validity and raises `ValueError` (never `InvalidTag`) — verified live.
* Step 2 and step 7 both touch alignment, but they serve different purposes (early clear error vs. final padding-validity gate) and `Padding.unpad`'s re-check is cheap and consistent. This is not redundant padding logic — it is a one-line early guard.

---

## 9. Task 1.1 Integration

* `from src.utils.padding import Padding` (same import style as `test_padding.py`).
* **Encrypt:** `Padding.pad(plaintext, 16)`.
* **Decrypt:** `Padding.unpad(padded, 16)`.
* **`is_padded()` decision (Section 20):** use `Padding.unpad()` alone — it already performs full validation (length, range, alignment, byte-for-byte padding check) and raises `ValueError` on failure. Wrapping decrypt in `is_padded()` first would double-validate the same bytes for zero benefit and adds a redundant branch. Do not adopt the research's decrypt → is_padded → unpad chain. `unpad` alone satisfies the error contract with no duplication.
* No modification to `padding.py` or `test_padding.py`.

---

## 10. Validation Matrix

| Input | Valid Condition | Invalid Condition | Error |
| :--- | :--- | :--- | :--- |
| `key_size` | `∈ {128, 192, 256}` | `0`, negative, `512`, non-int, bool | `ValueError` |
| `mode` | `"ECB"`, `"CBC"` (exact) | `"CTR"`, `"GCM"`, lowercase, empty, non-str | `ValueError` |
| `key` | `bytes`/`bytearray`, `len == key_size/8` (16/24/32) | wrong type, wrong length | `ValueError` |
| `plaintext` | `bytes`/`bytearray` (incl. `b""`) | `str`, `int`, `None`, list | `ValueError` |
| `ciphertext` | `bytes`/`bytearray`, block-aligned | wrong type; non-multiple-of-16 | `ValueError` |
| `iv` (ECB) | `None` | any supplied IV | `ValueError` |
| `iv` (CBC) | `bytes`/`bytearray`, exactly 16 B | `None` (missing), ≠16 B, wrong type | `ValueError` |
| Padding (decrypt) | valid PKCS#7 | corrupted/garbage → invalid padding | `ValueError` (never `InvalidTag`) |

---

## 11. Test Plan

**File:** `tests/test_aes.py` (`pytest`; import `from src.core.aes_cipher import AESCipher`). All configs iterate the full 3 key sizes × 2 modes matrix.

* **Constructor** — valid AES-128/192/256 for both modes; invalid `key_size` (0, -128, 512, float, bool) → `ValueError`; invalid `mode` ("CTR", "GCM", "ecb", "", non-str) → `ValueError`.
* **Key generation** — primary verification: `generate_key()` returns `bytes` of the correct length (16/24/32 for 128/192/256); the implementation source is `os.urandom()` (CSPRNG, verifiable by code inspection). A "two calls differ" check may remain only as a lightweight non-determinism sanity check — it does NOT prove cryptographic randomness quality.
* **IV generation** — primary verification: CBC returns `bytes` of length 16 (all key sizes); the implementation source is `os.urandom()`; ECB raises `ValueError`. A "two calls differ" check is only a lightweight non-determinism sanity check, not proof of randomness quality.
* **ECB encrypt/decrypt** — normal, empty (`b""`), short (5 B), 15 B, exactly 16 B, 17 B, multiple blocks; round-trips restore exact input for AES-128/192/256; ciphertext length is block-aligned.
* **CBC encrypt/decrypt** — same plaintext cases × all key sizes × valid 16-byte IV; round-trips restore exact input; empty-plaintext round-trip returns `b""`.
* **Validation** — invalid key type (`str`/`int`), invalid key length (15/17/23/31/33 B); invalid plaintext/ciphertext type; missing CBC IV (`None` → `ValueError`); wrong IV length (8/15/17/32 B → `ValueError`); ECB with supplied IV → `ValueError`; non-block-aligned ciphertext → `ValueError`.
* **Padding failure** — corrupt one ciphertext byte → decrypt raises `ValueError` (not `InvalidTag`); assert `InvalidTag` is not raised.
* **Wrong key (different valid key)** — decrypt the valid ciphertext with a different valid key. Do NOT require it to always raise an exception: a wrong key may produce invalid padding (then `ValueError` is expected), but it may also produce bytes that happen to have valid padding. The test must accept either outcome — if decryption raises `ValueError`, that is acceptable; if it returns plaintext, that plaintext must NOT equal the original plaintext. Do not turn a probabilistic cryptographic assumption into a deterministic test requirement.
* **Determinism / diffusion (lightweight correctness sanity check)** — ECB: same (key, plaintext) → identical ciphertext (deterministic); CBC: same (key, plaintext) with different IV → different ciphertext (IV mixing). For the bit-flip diffusion check: use a fixed key and plaintext, flip exactly one plaintext bit, and compare the two ciphertexts. If Hamming distance is measured, the threshold must be explicit and justified — e.g., the two ciphertexts must differ in at least one byte (block-level diffusion), since a strict percentage threshold is not statistically guaranteed in any single run. This is only a lightweight diffusion sanity check; it is distinct from the project's later, dedicated avalanche-effect security analysis (Analysis layer) and is not a substitute for it. No avalanche analyzer is created in Task 1.2.

---

## 12. Known-Answer / Reference Vectors

* **Authoritative source:** NIST FIPS 197, Appendix C (official AES-128/192/256 known-answer vectors — (key, plaintext-block, ciphertext-block) triples). Transcribe these directly from FIPS 197 Appendix C during implementation — do not invent or fabricate values.
* **Usage in our padded engine:** our `encrypt()` pads a 16-byte input to a 2-block payload (plaintext + `16×0x10`). Because ECB encrypts each block independently, the first ciphertext block equals FIPS 197's single-block ciphertext. Test asserts `encrypted[:16] == FIPS_CIPHERTEXT` for each key size — a valid, reproducible KAT without bypassing padding.
* **CBC (authoritative KAT):** use NIST SP 800-38A — its Appendix F provides AES-CBC test vectors (e.g., F.2.1 CBC-AES128.Encrypt) giving a known AES key, known IV, known plaintext, and expected ciphertext. Transcribe the vector values directly from NIST SP 800-38A (do not invent or fabricate). Our padded CBC engine pads a 16-byte plaintext to a 2-block payload (plaintext + `16×0x10`); the KAT check asserts that the first ciphertext block equals the NIST expected ciphertext for the single block (since block 1 = E_K(P1 ⊕ IV)). This independently verifies the CBC construction rather than relying only on round-trip tests.
* **Keep** the FIPS 197 Appendix C AES primitive vectors as planned (used for the ECB KAT).

---

## 13. Security Considerations

* **ECB:** no IV; deterministic block behavior — identical plaintext blocks → identical ciphertext blocks. Plan explicitly acknowledges pattern leakage (the "ECB Penguin" weakness). The engine must not claim ECB provides indistinguishability or any security beyond raw confidentiality for non-repeating data.
* **CBC:** IV must be supplied by the caller (CSPRNG-generated by `generate_iv()`); engine never auto-generates it inside encrypt. The plan does not claim CBC provides authentication, integrity, or AEAD security — it is malleable and (absent MAC) no authenticity guarantee.
* **Padding oracle:** the AES engine does not expose a distinct `InvalidTag`/authentication failure for ECB/CBC. Padding failures follow the common `ValueError` API contract. Padding-oracle resistance is a broader system-level security concern and is not established by exception type alone.
* **Key/IV randomness:** `os.urandom()` (CSPRNG) only.
* **No InvalidTag** — Task 1.2 has no AEAD modes.

---

## 14. Performance Considerations

* Single-pass, in-memory encryption via `encryptor().update(...)` + `finalize()` — no per-block Python loops (PyCA is C-backed). Fastest correct shape.
* Padding is pure-Python overhead (~O(n)); negligible for the core, and its cost is a deliberate Task 1.1/1.2 design trade-off (educational transparency). No optimization needed now.
* Benchmark methodology is NOT implemented here (5 iterations/2 warmup, Analysis layer). No timing decorators, metrics, or iterations in `aes_cipher.py`.

---

## 15. Files To Be Modified During Implementation

| File | Change | Justification |
| :--- | :--- | :--- |
| `src/core/aes_cipher.py` | Implement `AESCipher` | The Task 1.2 deliverable (Core layer). |
| `tests/test_aes.py` | Add comprehensive AES test suite | Task 1.2 tests (per workflow, Review→Test). |

No other file must change. `key_generator.py` is intentionally left a stub — per locked decision #9, generation lives on `AESCipher` (Spec §3.1 / Architecture §3.3). Wiring AES to `key_generator.py` would expand Task 1.2 beyond documented scope; if you later want that delegation, it should be a separate, explicit task. If you disagree, this is the one open point to flag before approval.

---

## 16. Files That Must Remain Untouched

* `src/utils/padding.py` (Task 1.1, frozen)
* `tests/test_padding.py` (Task 1.1, frozen)
* `src/utils/key_generator.py` (out of scope)
* `src/engines/cipher_interface.py`, `cipher_factory.py`, `context_manager.py` (Service layer — later task)
* `src/core/rsa_cipher.py`, `blowfish_cipher.py`, `classical_ciphers.py` (other algorithms)
* All `docs/*` (including the three task2 artifacts), `requirements.txt`, `CHANGELOG.md`, `DECISIONS.md`, `.claude/`, `verify_environment.py`

---

## 17. Risks / Open Issues

Only genuine risks; locked decisions are not reopened.

* **KAT transcription** — FIPS 197 Appendix C values must be copied verbatim from the authoritative source at implementation time; a transcription error would fail tests (caught immediately) but must be avoided.
* **`key_generator.py` scope** — resolved in favor of keeping generation local to AES (in scope). Flagged for your confirmation (see §15); not a blocker under the locked decision.
* **Exception-hierarchy residual** — architecture §8.1 documents custom classes; Task 1.2 uses plain `ValueError` per locked decision. This is a documented-but-deferred tension, not reopened here. No action for Task 1.2.
* **No `conftest.py` / packaging config exists** — tests rely on running pytest from repo root (established by Task 1.1). No change needed; noted only to explain the import convention.
* **Environment is Python 3.13 (docs say 3.10+)** — verified `cryptography 49.0.0` works on it; no change required, noted for environment-record accuracy.

---

## 18. Implementation Sequence

1. Implement `AESCipher` in `src/core/aes_cipher.py` (constructor + key/IV generation + private helpers + encrypt/decrypt).
2. Write `tests/test_aes.py` (per §11, including FIPS 197 §12 vectors).
3. Run `pytest` from repo root — confirm new suite passes and no Task 1.1 regression (padding tests still green).
4. Review against `ai/REVIEW_CHECKLIST.md` (API compliance, error handling, type hints, docstrings, scope).
5. Report results; wait for human approval before any commit/push (commit + push are out of this phase and out of the Explore/Plan deliverable).

---

## 19. Final Plan Verdict

### READY FOR HUMAN APPROVAL

* Scope, API contract, error contract, IV/key/padding/empty-plaintext behaviors are fully pinned by the locked decisions and confirmed compatible with the live environment (verified: `ValueError` path, no `InvalidTag`, empty round-trip, modern PyCA API).
* Only two files change during implementation (`aes_cipher.py`, `test_aes.py`); Task 1.1 and all other modules stay untouched.
* One non-blocking confirmation offered (§15/§17): key generation stays local to AES (recommended, in scope); wiring `key_generator.py` is out of scope.

No files were created or modified in this Explore + Plan session. The git working tree is unchanged by this phase. I will stop here and await your approval.
