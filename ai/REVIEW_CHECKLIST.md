# REVIEW_CHECKLIST.md

# AI Code Review Checklist

This checklist must be completed before accepting any AI-generated code.

The purpose is to ensure every implementation follows the project architecture, coding standards, security requirements, and quality expectations.

---

# Review Information

Date:

Reviewer:

Module:

File:

Task:

Commit (optional):

---

# Phase 1 — Requirement Verification

## Scope

- [ ] Only the requested task was implemented.
- [ ] No unrelated functionality was added.
- [ ] No unnecessary files were modified.
- [ ] Requirements are fully satisfied.

Notes:

---

# Phase 2 — Architecture Review

- [ ] Layered architecture is respected.
- [ ] Module responsibilities are correct.
- [ ] No business logic exists inside utility modules.
- [ ] No architecture violations introduced.

Notes:

---

# Phase 3 — API Compliance

Reference:

docs/05_API_Interface_Spec.md

Verify:

- [ ] Public interfaces unchanged.
- [ ] Function names unchanged.
- [ ] Parameters unchanged.
- [ ] Return types unchanged.
- [ ] No breaking API changes.

Notes:

---

# Phase 4 — Code Quality

Verify:

- [ ] PEP 8 followed.
- [ ] Type hints added.
- [ ] Google-style docstrings present.
- [ ] Code is readable.
- [ ] Variable names are meaningful.
- [ ] Functions are focused.
- [ ] No duplicated logic.

Notes:

---

# Phase 5 — Error Handling

Verify:

- [ ] Inputs validated.
- [ ] Appropriate exceptions raised.
- [ ] Error messages are descriptive.
- [ ] No silent failures.

Notes:

---

# Phase 6 — Security Review

For cryptographic modules only.

Verify:

- [ ] Uses approved cryptography library.
- [ ] No hardcoded keys.
- [ ] Random values generated securely.
- [ ] Inputs validated.
- [ ] Cryptographic behavior preserved.

If not applicable:

Mark N/A.

Notes:

---

# Phase 7 — Performance Review

Verify:

- [ ] No unnecessary loops.
- [ ] No repeated expensive operations.
- [ ] No obvious memory waste.
- [ ] Readability preserved.

Notes:

---

# Phase 8 — Testing Review

Verify:

- [ ] Existing tests still valid.
- [ ] New tests required?

If yes:

- [ ] Normal cases covered.
- [ ] Edge cases covered.
- [ ] Invalid input tested.

Notes:

---

# Phase 9 — Documentation Review

Verify:

- [ ] Docstrings updated.
- [ ] Comments accurate.
- [ ] Documentation updated if required.

Notes:

---

# Phase 10 — Git Review

Verify:

- [ ] Only intended files changed.
- [ ] Commit message appropriate.
- [ ] Ready to commit.

Recommended Commit Prefixes

- feat:
- fix:
- docs:
- test:
- refactor:
- chore:

---

# Final Decision

Implementation Status

Choose one:

☐ Approved

☐ Approved with Minor Changes

☐ Needs Revision

☐ Reject

Reason

______________________________________________________

---

# Lessons Learned

What did we learn?

______________________________________________________

______________________________________________________

______________________________________________________

---

# Next Task

______________________________________________________

______________________________________________________