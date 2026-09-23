# Specification Correction Report

## Files Modified
* `docs/05_API_Interface_Spec.md` — the only file modified. All edits confined to §3.1 `AESCipher` docstrings.

---

## Corrections Applied
* **`encrypt()` Raises (§3.1):** Removed `cryptography.exceptions.InvalidKey: If key is invalid`. Replaced with the `ValueError` contract: *"If key size doesn't match, key is invalid (wrong type or length), IV missing for CBC, etc."*
* **`decrypt()` Raises (§3.1):** Removed `cryptography.exceptions.InvalidTag: If decryption fails` and `cryptography.exceptions.InvalidKey: If key is invalid`. Replaced with: *"If key size doesn't match, key is invalid (wrong type or length), IV missing for CBC, padding is invalid, etc."*
* **`decrypt()` ECB/CBC clarification (§3.1):** Added an explicit note: *"ECB/CBC mode does not expose InvalidTag (authentication tags are only used by AEAD modes such as GCM, which are not part of Task 1.2)."*

No method signature, heading, example, architecture, or methodology text was altered.

---

## Unchanged
* **Task 1.1:** `src/utils/padding.py` and `tests/test_padding.py` untouched.
* **All source/test files:** `aes_cipher.py`, `test_aes.py`, and all other source untouched.
* **Other docs:** `03_Architecture_Design.md`, `04_Methodology.md`, AI/research files untouched.

---

## Git Diff Scope
`git status --short` shows exactly one modified tracked file: `M docs/05_API_Interface_Spec.md`. The diff is a minimal two-hunk change limited to the two Raises blocks. No Task 1.1 or source file appears in the diff.

> ⚠️ **Transparency note:** The working tree also shows an untracked `docs/implementation/task2/` directory (alongside pre-existing `.claude/`, `DECISIONS.md`, `docs/research/AES/`). This directory was not created or modified by me and is not part of my changes — I flag it for your awareness, but I did not touch it, per scope.

---

## Verification
Confirmed in the corrected §3.1:

* ✅ AES-128/192/256 scope unchanged (ECB/CBC only; CTR/GCM excluded).
* ✅ Method signatures unchanged (encrypt/decrypt parameter lists intact).
* ✅ `InvalidTag` no longer required for ECB/CBC — removed and explicitly disclaimed.
* ✅ `InvalidKey` no longer required for encrypt/decrypt — replaced with `ValueError`.
* ✅ `ValueError` documented for invalid key (wrong type or length).
* ✅ `ValueError` documented for invalid padding.

---

## Verdict
**PASS — APPROVED SPECIFICATION CORRECTIONS APPLIED**

No commit or push performed. The three approved docstring corrections are the only changes to tracked files.
