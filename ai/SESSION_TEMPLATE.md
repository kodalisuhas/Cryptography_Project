# SESSION_TEMPLATE.md

# AI Development Session Template

Use this template at the beginning of every implementation, debugging, review, or testing session.

---

# 1. Session Goal

Clearly state the objective of this session.

Examples:

- Implement PKCS#7 Padding
- Implement AES Encryption
- Fix CBC IV validation
- Review RSA implementation
- Write unit tests for AES

Current Goal:

______________________________________

---

# 2. Project Context

Reference the project instructions instead of rewriting them.

Required Context:

@ai/CLAUDE.md

@ai/AI_RULES.md

Relevant Documentation:

@docs/03_Architecture_Design.md

@docs/05_API_Interface_Spec.md

Only include additional documents when necessary.

---

# 3. Current Module

Module:

______________________________________

Location:

______________________________________

Layer:

□ Presentation

□ Engine

□ Core

□ Analysis

□ Utility

Purpose:

______________________________________

---

# 4. Files Involved

Primary File

@

Supporting Files

@

@

@

Only attach files required for this task.

Avoid unnecessary context.

---

# 5. Current Status

Completed:

-

-

-

Currently Working On:

______________________________________

Next Module:

______________________________________

---

# 6. Task Description

Describe exactly one task.

Examples:

Implement pad()

Implement encrypt()

Generate AES key

Write unit tests

Never combine multiple unrelated tasks.

Task:

______________________________________

---

# 7. Requirements

List implementation requirements.

Example:

- Follow API specification
- Preserve interfaces
- Add docstrings
- Add type hints
- Raise ValueError where appropriate

Requirements:

-

-

-

---

# 8. Constraints

Must NOT:

- Rename interfaces
- Modify unrelated files
- Change architecture
- Add unnecessary dependencies

Additional Constraints:

______________________________________

---

# 9. Expected Output

Choose one.

□ Explain implementation only

□ Design review only

□ Generate implementation

□ Review existing code

□ Debug issue

□ Generate tests

□ Refactor code

Output Expectations:

______________________________________

---

# 10. Review Checklist

Before considering the task complete, verify:

□ Requirements satisfied

□ API preserved

□ Architecture respected

□ Type hints present

□ Google docstrings present

□ Error handling included

□ No unrelated changes

---

# 11. Completion Criteria

The session is complete only when:

- Requested task is finished.
- Output satisfies requirements.
- Code is ready for review.
- No unrelated modifications were made.

---

# 12. Final Instruction to AI

Read all referenced files before responding.

Think about the implementation before generating code.

If any requirement is unclear, ask for clarification first.

Implement only the requested task.

Do not expand the scope.

Follow project architecture and engineering rules at all times.