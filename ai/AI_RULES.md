# AI_RULES.md

# AI Engineering Rules

These rules are mandatory for all AI-assisted development in this repository.

Violation of these rules may produce inconsistent, unmaintainable, or insecure code.

---

# 1. General Principles

Always:

- Think before implementing.
- Understand the task completely.
- Follow the documented architecture.
- Respect existing interfaces.
- Produce production-quality code.
- Optimize for readability and maintainability.
- Explain reasoning when requested.

Never assume missing requirements.

If anything is unclear, ask for clarification before implementation.

---

# 2. Scope Control

Implement only the requested task.

Do NOT:

- Modify unrelated modules.
- Rename existing classes or functions.
- Add extra features.
- Change folder structure.
- Rewrite existing architecture.

Small, focused changes are preferred.

---

# 3. Architecture Compliance

Always follow the layered architecture.

Presentation Layer
- src/cli/

Engine Layer
- src/engines/

Core Layer
- src/core/

Analysis Layer
- src/analyzers/

Utility Layer
- src/utils/

Responsibilities must never overlap.

---

# 4. API Compliance

Public interfaces defined in:

docs/05_API_Interface_Spec.md

are considered stable.

Never:

- Rename methods.
- Change function signatures.
- Change return types.

Unless explicitly instructed.

---

# 5. Coding Standards

Every implementation must:

- Follow PEP 8.
- Use type hints.
- Use Google-style docstrings.
- Use meaningful variable names.
- Keep functions focused.
- Avoid duplicated logic.

Never:

- Leave TODO placeholders.
- Leave commented-out code.
- Leave unused imports.
- Hardcode values unnecessarily.

---

# 6. Error Handling

Validate all external inputs.

Raise meaningful exceptions.

Do not silently ignore errors.

Error messages should help developers identify the problem.

---

# 7. Security Rules

Security-sensitive modules include:

- AES
- RSA
- Blowfish
- Padding
- Key Generation

Never:

- Invent cryptographic algorithms.
- Weaken cryptographic behavior.
- Hardcode keys.
- Skip input validation.

Always use approved libraries where specified.

---

# 8. Documentation Rules

Every public function should include:

- Purpose
- Parameters
- Returns
- Exceptions (if applicable)

Keep documentation synchronized with implementation.

---

# 9. Testing Rules

Implementation should be testable.

After completing a module:

- Write or update tests.
- Cover normal cases.
- Cover edge cases.
- Cover invalid inputs.

Do not claim a task is complete without verification.

---

# 10. AI Session Rules

Each AI session should focus on ONE module only.

Examples:

✔ padding.py

✔ aes_cipher.py

✔ metric_collector.py

Avoid mixing multiple modules in one request.

---

# 11. Review Rules

Before considering any implementation complete, verify:

- Requirements satisfied
- API respected
- Architecture respected
- Error handling present
- Type hints present
- Docstrings present
- Readability acceptable

---

# 12. Git Rules

Commit only logical units of work.

Recommended commit prefixes:

feat:
fix:
docs:
test:
refactor:
chore:

Avoid large commits containing unrelated changes.

---

# 13. AI Collaboration Workflow

For every task follow:

Understand

↓

Analyze

↓

Plan

↓

Implement

↓

Review

↓

Test

↓

Commit

↓

Push

Never skip review.

---

# 14. Communication Style

Responses should be:

- Clear
- Technical
- Concise
- Honest

If uncertain:

State the uncertainty instead of guessing.

---

# 15. Performance Considerations

Prefer:

- Readability first
- Correctness second
- Performance third

Only optimize when measurements justify it.

---

# 16. Definition of Complete

A task is complete only if:

✓ Requirements implemented

✓ API preserved

✓ Architecture respected

✓ Code reviewed

✓ Tests considered

✓ Documentation updated (if needed)

✓ Ready for commit

---

# Final Rule

The objective is not simply to generate code.

The objective is to build reliable, maintainable, well-tested software while helping the developers understand every implementation.