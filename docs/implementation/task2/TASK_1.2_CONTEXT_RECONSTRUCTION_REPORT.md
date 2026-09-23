# TASK 1.2 — CONTEXT RECONSTRUCTION REPORT

### AES Encryption / Decryption Engine
**Session type:** READ-ONLY reconstruction. No files were created, edited, deleted, renamed, or committed. Git working tree is untouched.

---

## A. Project Understanding

**Project name:** Performance and Security Analysis of AES Encryption using Different Key Sizes and Modes of Operation (`ai/CLAUDE.md`, `docs/01_Project_Proposal.md`).

The system is a CLI-based cryptographic analysis lab that implements AES, RSA, Blowfish, and classical ciphers (Caesar, Vigenère), then measures performance (execution time, memory, throughput) and security (ECB penguin, avalanche effect) across them. AES is the primary focus.

### Core AES scope (authoritative, from `docs/01_Project_Proposal.md`):
* **Key sizes:** 128, 192, 256-bit
* **Modes:** ECB, CBC
* **Block size:** 128-bit (16 bytes) — constant across all key sizes
* Uses the PyCA cryptography library (`cryptography 42.0.0+`, per `docs/02_System_Requirements.md`)
* **In-scope for analysis:** performance benchmarking + security demonstrations (ECB pattern leakage, avalanche effect)
* **Out-of-scope:** DES, 3DES, ChaCha20, hash functions, web/GUI interfaces

### Layered architecture (`docs/03_Architecture_Design.md`):
```text
src/
├── cli/         Presentation layer (menus, terminal UI)
├── engines/     Service layer (cipher_interface.py, cipher_factory.py)
├── core/        Core cipher engines (aes_cipher.py, rsa_cipher.py, blowfish_cipher.py)
├── analyzers/   Analysis layer (benchmarking, security evaluator)
└── utils/       Utility layer (padding.py, key_generator.py, converters)
```

---

## B. Current Repository State

* **Branch:** `dev`
* **Git log (HEAD → oldest):**
  * `cf21434` — feat: implement PKCS#7 padding utility ← Task 1.1 committed
  * `3fb988e` — docs: fix API ambiguity - add block_size to unpad/is_padded
  * `8336ccf` — chore: complete project foundation and AI engineering framework
  * `072a5c8` — docs: add AI context files for consistent prompting
  * `ddc6aa1` — chore: add environment verification script
  * `dd4c072`, `f5f5f2a` — initial structure/documentation
* **Untracked (working tree, NOT committed):**
  * `.claude/`
  * `DECISIONS.md`
  * `docs/research/AES/` ← contains the AES research report (not yet in version control)
* **Existing cipher source files are all stubs (confirmed by reading):**
  * `src/core/aes_cipher.py` → `# AES stub`
  * `src/core/rsa_cipher.py` → `# RSA stub`
  * `src/core/blowfish_cipher.py` → `# Blowfish stub`
  * `src/engines/cipher_interface.py` → `# Interface stub`
  * `src/engines/cipher_factory.py` → `# Factory stub`
  * `src/utils/key_generator.py` → `# Key generator stub`
  * `tests/test_aes.py` → `# AES tests`

Task 1.2 has zero prior implementation. `aes_cipher.py` is a pure placeholder. This is a greenfield build.

---

## C. Task 1.1 Final State (DONE)

* **Deliverable:** `src/utils/padding.py` — pure-Python `Padding` class, 5 methods (4 public static + 1 private validator).
* **Tests:** `tests/test_padding.py` — 30 tests, 30 passed, full suite green.
* **Verification:** `docs/verification/task1/TASK_1.1_PADDING_VERIFICATION.md` — 2,400+ combinations (8 block sizes × 300 lengths) verified programmatically. Verdict: PASS WITH MINOR NON-BLOCKING OBSERVATION — APPROVED FOR COMMIT.
* **Review:** `docs/reviews/task1/TASK_1.1_PADDING_CODE_REVIEW.md` — PASS WITH MINOR CHANGES, resolved via test hardening.
* **API contract:** `pad`/`unpad`/`is_padded`/`get_padding_length(data, block_size=16)`, `block_size` range 1–255, accepts `bytes`/`bytearray`, always returns `bytes`.
* **Known minor (accepted, non-blocking):** implementation accepts `bytearray` despite `bytes` type hint in API — documented as intentional, keep as-is.
* Committed on `dev` at `cf21434`.

**Why this matters for Task 1.2:** `Padding.pad(plaintext, 16)` is the exact dependency AES ECB/CBC needs for block alignment. The utility is complete, tested, and committed — Task 1.2 can consume it directly with zero modification.

---

## D. Task 1.1 → Task 1.2 Integration

### How Task 1.2 consumes Task 1.1
* ECB and CBC are block modes requiring block-aligned input (16 bytes). Task 1.2's `encrypt()` must apply `Padding.pad(plaintext, 16)` before encryption and `Padding.unpad(ciphertext, 16)` after decryption.
* This is a hard dependency: the `Padding` class in `src/utils/padding.py` is imported by the future AES engine.
* **Constraint:** Task 1.2 must NOT modify `padding.py`. It is committed, frozen, and reviewed. It is a consumer relationship only.

### Implementation-order context
The documented build order (`docs/05_API_Interface_Spec.md`) is: Utility → Core → Service → Analysis → CLI → System Integration → Tests. Padding (Utility) is done. AES (Core) is next — Task 1.2. So Task 1.2 is correctly positioned as the next build step.

### Follow-on dependencies (future, not Task 1.2's responsibility unless required by spec)
`cipher_interface.py` (ABC) and `cipher_factory.py` (Service layer) — these may become relevant to AES, but the authoritative API spec for AES (`AESCipher` class) does not require implementing the factory/interface as part of Task 1.2. Needs a decision (see Section I).

---

## E. Task 1.2 Requirements — Categorized

### REQUIRED (authoritative — from `docs/05_API_Interface_Spec.md` §3.1 and `docs/03_Architecture_Design.md`)
The `AESCipher` class must provide:

| Method | Signature | Behavior (from spec) |
| :--- | :--- | :--- |
| `__init__` | `(key_size: int, mode: str)` | `key_size ∈ {128, 192, 256}`; `mode ∈ {'ECB', 'CBC'}`. Raises `ValueError` on invalid values. |
| `generate_key` | `() -> bytes` | Random key of length `key_size/8` bytes. CSPRNG required (`os.urandom`/`secrets` — mandated by `docs/02_System_Requirements.md` Rec. 8 and research). |
| `generate_iv` | `() -> bytes` | 16-byte random IV. Raises `ValueError` if mode is ECB. |
| `encrypt` | `(plaintext: bytes, key: bytes, iv: bytes = None) -> bytes` | Raises `ValueError`, `InvalidKey`. |
| `decrypt` | `(ciphertext: bytes, key: bytes, iv: bytes = None) -> bytes` | Raises `ValueError`, `InvalidTag`, `InvalidKey`. |

#### Other REQUIRED elements:
* Block size 16 bytes for all key sizes.
* ECB mode: no IV; PKCS#7 padding required.
* CBC mode: 16-byte IV required; PKCS#7 padding required.
* CSPRNG for all key and IV generation (`docs/02_System_Requirements.md` Sec. 13 + Rec. 8).
* Exceptions raised via `ValueError` for invalid inputs (per spec); internal exception hierarchy (`CryptographyError`, `InvalidKeyError`, `InvalidModeError`, `PaddingError`, `DecryptionError`, `AlgorithmNotSupportedError`) defined in `docs/03_Architecture_Design.md`.
* **Interface Stability Policy:** Version 1.0 interfaces are frozen.

### RESEARCH RECOMMENDATION (from `docs/research/AES/` — NOT required, flagged as beyond current scope)
* Add CTR and GCM modes — research proposes `VALID_MODES = ['ECB', 'CBC', 'CTR', 'GCM']`. Project proposal/spec explicitly scope to ECB+CBC only.
* Increase benchmark iterations from 5 to 50–100 (`docs/04_Methodology.md`, `docs/02_System_Requirements.md` Rec. 6).
* `backend=default_backend()` deprecation — research notes this is deprecated in newer cryptography versions; not passing a backend is preferred.

### UNKNOWN / NEEDS DECISION
* Whether `cipher_interface.py` (ABC) and `cipher_factory.py` must be built as part of Task 1.2, or deferred to the Service-layer task.
* Exact exception type mapping (see Section F, items 1–2).
* Whether the two spec docstrings (`InvalidTag`, `InvalidKey`) are corrected in docs or just handled correctly in code.

---

## F. AES Specification Conflicts (must be resolved by human before planning)

1. **`InvalidTag` in `decrypt()` docstring:** `docs/05_API_Interface_Spec.md` §3.1 documents `decrypt()` raising `cryptography.exceptions.InvalidTag: If decryption fails`. This is technically incorrect for ECB/CBC: `InvalidTag` is raised only by GCM (authenticated decryption) when the tag fails verification. ECB/CBC decryption with PyCA raises `InvalidTag` never — corrupted ciphertext in CBC raises nothing (it simply produces garbage, which then fails `Padding.unpad()` with a `ValueError`). This spec line is a defect unless GCM is added.
2. **`cryptography.exceptions.InvalidKey`:** the spec references this exception for both encrypt/decrypt. `InvalidKey` is a real cryptography exception (raised when a key has wrong length/type), but the spec does not describe it consistently, and its interaction with the project's own `InvalidKeyError` hierarchy is ambiguous. Needs confirmation of the exact name and that PyCA raises it as documented.
3. **CTR/GCM scope:** project docs (proposal, API spec, architecture) list ECB+CBC only. AES research recommends adding CTR+GCM. This is a scope decision — the largest one for Task 1.2. If GCM is added, `InvalidTag` becomes meaningful; if not, the spec docstring must be corrected.
4. **Benchmark iterations:** `docs/03_Architecture_Design.md` and `docs/04_Methodology.md` set `BENCHMARK_ITERATIONS = 5` (warmup 2). Research + `docs/02_System_Requirements.md` Rec. 6 recommend 50–100. This affects the analysis layer more than Task 1.2's core engine, but the engine's encrypt/decrypt signatures and any iteration parameters should align.
5. **Padding/decryption failure behavior:** not fully pinned: on CBC decryption of corrupted ciphertext, should the engine raise a `PaddingError`/`DecryptionError` (wrapping `ValueError`), or propagate a raw `ValueError`? The spec's `InvalidTag` reference suggests the authors intended a distinctive failure signal, but none exists for CBC without GCM.
6. **IV requirements:** `generate_iv()` raises `ValueError` if mode is ECB; `encrypt`/`decrypt` accept `iv: bytes = None`. Spec is silent on: what if `iv` is `None` for CBC (auto-generate? error?), what if `iv` is provided for ECB (ignore? error?), and IV length validation (must be exactly 16 bytes).
7. **Key validation:** spec does not state whether `encrypt`/`decrypt` validate key length against `key_size` before calling PyCA (which raises `InvalidKey` on wrong-length keys). The class already knows `key_size` from `__init__`; whether it validates `len(key) == key_size/8` is unspecified.
8. **`backend=default_backend()`:** research flags deprecation in newer cryptography; the AES implementation should omit the deprecated backend argument.

---

## G. Files That Must NOT Be Modified (during Task 1.2)

These are committed, frozen, reviewed, or out of Task 1.2 scope. Do not touch.

* `src/utils/padding.py` — completed, reviewed, committed (`cf21434`). Task 1.2 only imports it.
* `tests/test_padding.py` — completed, 30/30 passing.
* `src/core/rsa_cipher.py`, `src/core/blowfish_cipher.py` — out of scope (separate tasks).
* **All project documentation (`docs/01–docs/05`):** unless a human explicitly approves a spec-doc correction for the InvalidTag/InvalidKey conflict (Section F items 1–2). Even then, that's a docs change, reviewed separately.
* `CHANGELOG.md` — modified but pre-existing; not part of Task 1.2 core work (only append an entry if/when Task 1.2 is committed, per workflow).
* `DECISIONS.md`, `.claude/`, `docs/research/AES/` — untracked working-tree items; not Task 1.2 deliverables.
* `requirements.txt` / dependencies — no installs, no updates (per session constraints).

---

## H. Files Expected to Be Relevant to Task 1.2

### Primary deliverable (new content):
* `src/core/aes_cipher.py` — implement the `AESCipher` class (currently stub).

### Tests (new content):
* `tests/test_aes.py` — AES unit tests (currently stub).

### Consumed (read-only, already complete):
* `src/utils/padding.py` — `Padding.pad`/`unpad` for block alignment.
* `src/utils/key_generator.py` — possibly a home for CSPRNG key/IV helpers (currently stub; decide whether AES uses it or its own `os.urandom`/`secrets` — needs decision).

### May be relevant (Service layer, needs decision on scope):
* `src/engines/cipher_interface.py` — ABC stub.
* `src/engines/cipher_factory.py` — factory stub.

### Reference (authoritative contracts):
* `docs/05_API_Interface_Spec.md` §3.1 — the `AESCipher` API contract.
* `docs/03_Architecture_Design.md` — architecture + exception hierarchy + settings.
* `docs/research/AES/DEEP RESEARCH REPORT AES ENCRYPTIONDECRYPTION.md` — technical reference (modes, PyCA API, edge cases); recommendations only, not requirements.

---

## I. Questions Requiring Human Approval

Before any Task 1.2 implementation plan can be finalized, these must be decided:

1. **Mode scope:** ECB+CBC only, or add CTR/GCM? (Section F item 3). This is the single biggest decision and changes the API, the `InvalidTag` handling, the padding logic, and the test matrix. Recommendation: stay with ECB+CBC per the authoritative proposal/spec; defer CTR/GCM as a separate enhancement task.
2. **`InvalidTag` spec defect:** is the docstring in `docs/05_API_Interface_Spec.md` §3.1 corrected (approved docs change), or is Task 1.2 expected to implement GCM to make it valid, or does the AES engine simply not raise `InvalidTag` (and we note the doc discrepancy)? (Section F item 1)
3. **`InvalidKey` exception:** confirm the exact exception contract for wrong-length keys: does the engine validate key length and raise `ValueError` (per project hierarchy) or let PyCA raise `cryptography.exceptions.InvalidKey`? (Section F items 2, 7)
4. **IV/ECB/CBC edge behavior:** what happens when: `iv=None` for CBC, `iv` provided for ECB, `iv` wrong length, plaintext empty, ciphertext not block-aligned? (Section F item 6; padding-failure behavior item 5)
5. **Key/IV generation location:** CSPRNG logic in `key_generator.py` or self-contained in `aes_cipher.py`?
6. **Service-layer scope:** must Task 1.2 also build `cipher_interface.py` + `cipher_factory.py`, or are those a separate task? (Section D/H)
7. **Benchmark iterations:** is the AES work expected to reflect the 5-iteration default or the 50–100 recommendation? (Section F item 4; likely Analysis-layer, but confirms alignment.)

---

## J. Final Readiness Assessment

**READY FOR TASK 1.2 PLANNING — CONDITIONAL (with the Section I decisions resolved first)**

### What is firmly in place:
* ✅ Padding dependency complete, tested, committed (`cf21434`).
* ✅ Authoritative API contract for `AESCipher` documented (§3.1 of the spec).
* ✅ Architecture, exception hierarchy, and settings documented.
* ✅ AES research report available (as untracked `docs/research/AES/`).
* ✅ Clear implementation target: `src/core/aes_cipher.py` + `tests/test_aes.py`.
* ✅ Stubs confirm no accidental prior implementation to reconcile.
* ✅ Workflow position is correct: Utility (done) → Core (next) → Service → Analysis → CLI.

### What blocks a final, unambiguous plan (must be resolved by the human first):
* ⚠️ Mode scope (ECB+CBC vs. +CTR/GCM) — changes everything.
* ⚠️ `InvalidTag` / `InvalidKey` spec contract — whether to correct docs or change implementation.
* ⚠️ IV/key edge-case behavior — unspecified.
* ⚠️ Service-layer scope — factory/interface in or out.

**Bottom line:** The project is structurally ready for Task 1.2 — the foundational work and the exact dependency it needs are done. But the plan cannot be signed off until the 7 decisions in Section I (especially #1 mode scope and #2/#3 exception contract) receive human approval. My recommendation is a short planning session to lock decisions I-1 through I-4, after which Task 1.2 planning can proceed directly and confidently.

No files were modified in this session. The working tree matches the snapshot at session start (`cf21434`, branch `dev`, untracked: `.claude/`, `DECISIONS.md`, `docs/research/AES/`).
