# TASK 1.2 — SPECIFICATION AUDIT REPORT

**Phase:** Specification Audit Only · **Mode:** READ-ONLY — no files created, edited, or committed.

---

## 1. Audit Scope

### Inspected for this audit:

#### AI engineering rules:
* `ai/CLAUDE.md`
* `ai/AI_RULES.md`
* `ai/SESSION_TEMPLATE.md`
* `ai/REVIEW_CHECKLIST.md`

#### Authoritative project documents:
* `docs/01_Project_Proposal.md` — scope, in/out-of-scope, tech stack
* `docs/02_System_Requirements.md` — dependencies, CSPRNG mandate, benchmark config
* `docs/03_Architecture_Design.md` — layers, AESCipher plan, exception hierarchy, settings
* `docs/04_Methodology.md` — benchmark methodology (5 iterations / 2 warmup)
* `docs/05_API_Interface_Spec.md` — AESCipher contract (§3.1), implementation order

#### Task 1.1 final state (CLOSED):
* `src/utils/padding.py`
* `tests/test_padding.py`
* Research, plan, implementation report, code review, verification report.

#### AES research (non-authoritative):
* [`docs/research/AES/DEEP RESEARCH REPORT AES ENCRYPTIONDECRYPTION.md`](docs/research/AES/DEEP%20RESEARCH%20REPORT%20AES%20ENCRYPTIONDECRYPTION.md) — treated as findings/recommendations only, not requirements.

#### Diagrams & team docs:
* `docs/diagrams/*` and `docs/team/*` — all confirmed to be stubs (single placeholder lines); they contain no specifications and introduce no constraints.

#### Current source state:
* `aes_cipher.py`, `rsa_cipher.py`, `blowfish_cipher.py`, `cipher_interface.py`, `cipher_factory.py`, `key_generator.py`, `test_aes.py` are all stubs. Task 1.2 is greenfield.

---

## 2. Confirmed Project Requirements (already consistent)

The following are consistent across the human-approved contract and authoritative docs — no change required (A):

| Requirement | Source | Consistent? |
| :--- | :--- | :---: |
| AES-128 / AES-192 / AES-256 | 01 §3, 05 §3.1 | ✅ |
| Modes ECB, CBC only (no CTR/GCM) | 01 §4, 05 §3.1, 03 §9.1 | ✅ |
| AES block size 16 bytes for all key sizes | 05 §3.1, research (FIPS 197) | ✅ |
| Key sizes map 128→16 B, 192→24 B, 256→32 B | 05 §3.1 (key_size/8) | ✅ |
| AESCipher class with generate_key / generate_iv / encrypt / decrypt | 05 §3.1, 03 §3.3 | ✅ |
| `__init__(key_size, mode)` raises ValueError on invalid values | 05 §3.1 | ✅ |
| `generate_iv()` raises ValueError if mode is ECB | 05 §3.1 | ✅ |
| CBC without IV → ValueError ("IV missing for CBC") | 05 §3.1 | ✅ |
| Decryption returns unpadded plaintext (unpad after decrypt) | 03 §4.2 (decryption flow "3. Unpad Plaintext") | ✅ |
| PKCS#7 padding consumed from utility layer, not duplicated | 03 §3.5, 05 §6.3 | ✅ |
| CSPRNG for key/IV generation (`os.urandom`/`secrets`) | 02 §13 + Rec 8, 03 §11 | ✅ |
| PyCA cryptography as cryptographic backend | 02 §4, 01 §7 | ✅ |
| Implementation order: Utility → Core → Service → Analysis → CLI | 05 §Implementation Order | ✅ |

---

## 3. Human Decisions Validated

### Decision #1 — Mode scope (ECB + CBC only)
Supported by authoritative docs. Proposal, API spec, and architecture all scope AES to ECB+CBC. Research is internally split: its "Confirmed Project Requirements" says ECB+CBC required with CTR/GCM as "potential future extensions" ([research line 100](docs/research/AES/DEEP%20RESEARCH%20REPORT%20AES%20ENCRYPTIONDECRYPTION.md)) and marks CTR/GCM "❌ NOT Required" (lines 203–204), but its "Recommended Implementation Contract" proposes `VALID_MODES = ['ECB','CBC','CTR','GCM']` (line 606) and its "Human Decisions Required" recommends including CTR and GCM (lines 580–583). Research is non-authoritative; the human decision correctly overrides it. No doc contradiction in authoritative sources.

### Decision #2 — No InvalidTag for ECB/CBC
Supported by technical reality and research (research §7, lines 183–186, 285–320: `InvalidTag` is GCM-only). But it CONFLICTS with `docs/05_API_Interface_Spec.md` §3.1, whose `decrypt()` docstring documents `cryptography.exceptions.InvalidTag: If decryption fails`. → Documentation correction required (B).

### Decision #3 — ValueError key contract (not backend-specific exceptions)
Partially supported. The API spec's `encrypt()`/`decrypt()` docstrings reference `cryptography.exceptions.InvalidKey` (lines ~101, ~123), which conflicts with the human's decision to own key validation and raise `ValueError`. → Documentation correction required (B). The architecture's custom exception hierarchy (§8.1) is a separate tension — see Section 5 / 10.

### Decision #4 — Exact IV / key / input validation
Mostly supported by the spec for `key_size`, `mode`, CBC-without-IV, ECB-`generate_iv`. The spec is silent (not contradictory) on: IV length validation, ECB-with-supplied-IV, plaintext/ciphertext type validation, ciphertext block alignment, and empty plaintext. These are additive implementation details → C (implementation decision) where the docs do not contradict.

---

## 4. Specification Conflicts

| # | File | Section | Current Requirement | Conflict | Class. | Proposed Action |
| :-: | :--- | :--- | :--- | :--- | :-: | :--- |
| 1 | `docs/05_API_Interface_Spec.md` | §3.1 `decrypt()` Raises (~L122) | `cryptography.exceptions.InvalidTag: If decryption fails` | `InvalidTag` is raised only by GCM; ECB/CBC never raise it. Task 1.2 has no GCM. | B | Remove `InvalidTag` from `decrypt()` Raises; replace with `ValueError` for invalid padding. No public API change (docstring only). |
| 2 | `docs/05_API_Interface_Spec.md` | §3.1 `encrypt()` Raises (~L101) | `cryptography.exceptions.InvalidKey: If key is invalid` | Decision #3: AES engine owns key validation → `ValueError`, no backend-specific exception for normal API. | B | Replace `InvalidKey` with `ValueError` (key length/type). No public API change. |
| 3 | `docs/05_API_Interface_Spec.md` | §3.1 `decrypt()` Raises (~L123) | `cryptography.exceptions.InvalidKey: If key is invalid` | Same as #2. | B | Same as #2. No public API change. |
| 4 | `docs/03_Architecture_Design.md` | §8.1 (L436–454) | Custom hierarchy: `InvalidKeyError`, `InvalidKeySizeError`, `InvalidModeError`, `PaddingError`, `DecryptionError`, `AlgorithmNotSupportedError` | Human error contract (#13) uses plain `ValueError` for all cases. Architecture documents custom classes. Human instructed: do not silently replace the architecture. | D | Human must confirm whether Task 1.2 raises plain `ValueError` (matches §3.1 method contract) or the architecture's custom classes. |
| 5 | `docs/03_Architecture_Design.md` | §9.1 (L521) | `BENCHMARK_ITERATIONS = 5`, `WARMUP = 2` | Research recommends 50–100 iterations. Human (Decision #16) declares methodology authoritative. | A (report only) | No change. Task 1.2 core engine does not implement benchmark iteration logic (Analysis layer's concern). |
| 6 | [`docs/research/AES/…md`](docs/research/AES/DEEP%20RESEARCH%20REPORT%20AES%20ENCRYPTIONDECRYPTION.md) | §F Recommended Contract (L585–606); "Human Decisions Required" (L580–583) | `VALID_MODES = ['ECB','CBC','CTR','GCM']`; "Include CTR"/"Include GCM" | Contradicts Decision #1 (ECB+CBC only). | A (research is non-authoritative) | No change. Human decision supersedes the research recommendation. |
| 7 | `docs/03_Architecture_Design.md` | §3.3 (L128–149); `docs/05` §3.1 | `generate_key()`/`generate_iv()` defined on the `AESCipher` class | Decision #14 asks whether generation belongs in `AESCipher` vs `key_generator.py`. Authoritative docs place it on `AESCipher`; `key_generator.py` is an unwired stub. | C | Keep generation on `AESCipher` (per docs). Whether it delegates internally to `key_generator` is an implementation choice for Explore/Plan. |
| 8 | [`docs/research/AES/…md`](docs/research/AES/DEEP%20RESEARCH%20REPORT%20AES%20ENCRYPTIONDECRYPTION.md) | §6 (L240–242, 594) | Example code uses `backend=default_backend()` | Deprecated in newer cryptography. Decision #3: don't depend on backend-specific behavior; PyCA stays backend. | C | Omit the deprecated `backend` argument in implementation. No doc correction needed (docs don't mandate it). |

> **Note:** `docs/02_System_Requirements.md` Rec. 6 also recommends `BENCHMARK_ITERATIONS=100` — same non-authoritative recommendation as Conflict #5; overridden by Decision #16 (methodology authoritative).

---

## 5. Exception Contract Audit

| Case | Human Contract | API Spec §3.1 | Architecture §8.1 | Status |
| :--- | :--- | :--- | :--- | :---: |
| Invalid `key_size` | `ValueError` | `ValueError` (`__init__`) | `InvalidKeySizeError` (subclass) | ⚠️ §3.1 OK; §8.1 tension → D |
| Invalid `mode` | `ValueError` | `ValueError` (`__init__`) | `InvalidModeError` (subclass) | ⚠️ §3.1 OK; §8.1 tension → D |
| Invalid key (wrong type/length) | `ValueError` | `cryptography.exceptions.InvalidKey` | `InvalidKeyError` (subclass) | B — spec names `InvalidKey` |
| Invalid plaintext type | `ValueError` | (not enumerated) | `ValidationError`-family (Rec 6) | C (doc silent) |
| Invalid ciphertext / non-block-aligned | `ValueError` | (not enumerated) | — | C (doc silent) |
| Invalid IV (wrong length) | `ValueError` | (not enumerated) | — | C (doc silent) |
| CBC without IV | `ValueError` | `ValueError` ("IV missing for CBC") | — | ✅ A |
| ECB with supplied IV | `ValueError` | (silent) | — | C (doc silent) |
| `generate_iv()` on ECB | `ValueError` | `ValueError` | — | ✅ A |
| Invalid padding (ECB/CBC) | `ValueError` | `InvalidTag` (wrong) | `PaddingError` (subclass) | B (spec) + D (hierarchy) |
| `InvalidTag` | Not exposed (no GCM) | Documented (wrong) | not in hierarchy | B — remove from spec |
| `cryptography.exceptions.InvalidKey` | Not relied on | Documented | not in hierarchy | B — replace with `ValueError` |
| Custom project exceptions | Undecided | not used in §3.1 | defined in §8.1 | D |

**Key finding:** The API spec §3.1 (the method-level contract) uses `ValueError`, so the human's `ValueError` direction is consistent with the most specific authoritative source. The architecture §8.1 defines a custom hierarchy but no AES method docstring in the spec uses those classes. The single genuine open question is whether to adopt the architecture's custom classes.

---

## 6. IV Contract Audit

| Scenario | Approved Behavior | Current Spec (§3.1) | Status |
| :--- | :--- | :--- | :---: |
| ECB + no IV (`iv=None`) | valid | ECB "does not use IV"; no IV param needed | ✅ A (silent but consistent) |
| ECB + supplied IV | `ValueError` | not specified | C (doc silent — implement as decided) |
| CBC + no IV (`iv=None`) | `ValueError` | `ValueError` ("IV missing for CBC") | ✅ A |
| CBC + invalid IV (≠16 bytes) | `ValueError` | not specified | C (doc silent — enforce 16 bytes) |
| CBC + valid IV (16 bytes) | valid | implied (CBC uses iv) | ✅ A |
| `generate_iv()` + ECB | `ValueError` | `ValueError` ("If mode is ECB") | ✅ A |
| `generate_iv()` + CBC | 16 random CSPRNG bytes | "16-byte random IV" | ✅ A |

No doc correction is required for the IV contract — the spec agrees or is simply silent (handled at implementation). The only hardening needed is explicit IV-length (16-byte) enforcement, which is an implementation detail (C).

---

## 7. Padding Integration Audit

Task 1.2 consumes the completed Task 1.1 utility exactly as decided:

```text
Encrypt:  plaintext  → Padding.pad(data, 16)   → AES(ECB/CBC) → ciphertext
Decrypt:  ciphertext → AES(ECB/CBC)            → padded plaintext → Padding.unpad(data, 16) → plaintext
```

* **Confirmed:** `src/utils/padding.py` `pad`/`unpad`/`is_padded`/`get_padding_length` are complete, tested (30/30), reviewed, and committed at `cf21434`. It is the correct, single PKCS#7 source.
* **Corrupted-ciphertext path:** CBC decryption of corrupted ciphertext yields garbage → `Padding.unpad(..., 16)` raises `ValueError("Invalid PKCS#7 padding...")`. This naturally satisfies Decision #2/#13 (invalid padding → `ValueError`, no `InvalidTag`). Consistent.
* **Empty plaintext:** `Padding.pad(b"", 16)` → `16×0x10` (full block), and `Padding.unpad(16×0x10, 16)` → `b""`. The utility already handles empty input correctly (verified in Task 1.1). Decision #12 is satisfiable with no new logic.
* **Task 1.1 protection (Section 20):** The approved decisions require zero changes to `src/utils/padding.py` or `tests/test_padding.py`. They are consumed, not modified. No blocker.

---

## 8. Scope Audit

| Element | In Task 1.2? | Authority |
| :--- | :---: | :--- |
| AES-128 / AES-192 / AES-256 | ✅ | Proposal, API spec |
| ECB | ✅ | Proposal, API spec |
| CBC | ✅ | Proposal, API spec |
| CTR | ❌ excluded | Human Decision #1; research itself says "future extension" |
| GCM | ❌ excluded | Human Decision #1; research itself says "future extension" |
| Service layer (`cipher_interface.py`, `cipher_factory.py`) | ❌ excluded | Implementation order (Utility → Core → Service). Human assumption confirmed: Core AES is Task 1.2; interface/factory are a separate future Service task. |

**Service-layer assumption validated:** The documented implementation order in 05 §Implementation Order places Core (AES) at step 2 and Service (interface + factory) at step 3 — a distinct later task. No doc correction needed (A).

---

## 9. Required Documentation Corrections

Minimal set — NOT made in this session. For approval before any edit.

| # | File | Location | Current | Proposed | Reason | Public API change? |
| :-: | :--- | :--- | :--- | :--- | :--- | :-: |
| 1 | `docs/05_API_Interface_Spec.md` | §3.1 `decrypt()` Raises | `cryptography.exceptions.InvalidTag: If decryption fails` | Remove `InvalidTag`; add `ValueError: If padding is invalid` | `InvalidTag` is GCM-only; Task 1.2 has ECB/CBC only | No — docstring only |
| 2 | `docs/05_API_Interface_Spec.md` | §3.1 `encrypt()` Raises | `cryptography.exceptions.InvalidKey: If key is invalid` | `ValueError: If key is invalid (wrong type or length)` | Decision #3: engine owns key validation, `ValueError`, no backend-specific exception | No — docstring only |
| 3 | `docs/05_API_Interface_Spec.md` | §3.1 `decrypt()` Raises | `cryptography.exceptions.InvalidKey: If key is invalid` | `ValueError: If key is invalid (wrong type or length)` | Same as #2 | No — docstring only |

*(Optional, non-blocking — recommend but not strictly required before implementation:)*

| # | File | Location | Current | Proposed | Reason | Public API change? |
| :-: | :--- | :--- | :--- | :--- | :--- | :-: |
| 4 | `docs/05_API_Interface_Spec.md` | §3.1 | — | (Optionally) state IV must be exactly 16 bytes; ECB-with-IV → `ValueError`; plaintext/ciphertext must be `bytes`/`bytearray`; ciphertext must be block-aligned | Documents Decision #4 contract explicitly | No |

These are the only corrections required. No other authoritative document needs editing for the approved decisions.

---

## 10. Remaining Human Decisions

Only one genuine open decision (all others are settled by the four approved decisions or are implementation details):

* **Exception hierarchy (Decision #13) — CONFIRM:** Does Task 1.2 raise plain `ValueError` for all validation failures (consistent with the API spec §3.1 method contract), or must it adopt the architecture's custom classes (`InvalidKeyError`, `PaddingError`, `DecryptionError`, etc. from §8.1)? The human's direction is `ValueError`; the architecture documents a custom hierarchy. Per the human's instruction to "not silently replace the architecture," this needs explicit confirmation. Recommendation: plain `ValueError` for Task 1.2, defer the custom hierarchy to a later task — this matches the authoritative per-method spec §3.1 and avoids over-engineering.

That is the sole **D**. Everything else is either aligned (A), doc-correction (B, Section 9), or implementation detail for Explore/Plan (C).

---

## 11. Final Verdict

### PASS WITH DOCUMENTATION CORRECTIONS REQUIRED

#### Rationale:
* Decisions #1 (ECB+CBC only), #4 (IV/key/input validation), and the Service-layer/benchmark scope are fully aligned with authoritative docs — no contradictions.
* Decision #2 (no `InvalidTag`) and Decision #3 (`ValueError` key contract) are correct and technically sound, but they require three small docstring corrections in `docs/05_API_Interface_Spec.md` §3.1 (remove `InvalidTag`, replace `cryptography.exceptions.InvalidKey` with `ValueError`). These are docstring-only, no public API change.
* Task 1.1 is fully protected — consumed, not modified.
* One non-blocking confirmation remains (exception hierarchy, Section 10) that can be resolved inline with the doc-correction approval; it does not block the corrections or the subsequent Explore/Plan.

**Next steps (per workflow — do NOT proceed autonomously):** approve the 3 docstring corrections (Section 9) and the exception-hierarchy confirmation (Section 10) → apply the minimal corrections → Explore → Plan for Task 1.2.

Session was READ-ONLY. No files were created, edited, or committed. The working tree is unchanged at `cf21434` on branch `dev` (untracked: `.claude/`, `DECISIONS.md`, `docs/research/AES/`).
