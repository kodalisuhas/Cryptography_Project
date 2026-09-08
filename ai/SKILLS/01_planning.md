# Skill: Planning

## Purpose

Use this skill before implementing any new module, feature, or major change.

The objective is to fully understand the task, identify dependencies, evaluate constraints, and create a structured implementation plan before writing code.

---

# When to Use

Use this skill when:

- A new module is assigned.
- A new feature is requested.
- Project requirements change.
- Architecture decisions are required.
- Existing functionality needs significant enhancement.

Do NOT use this skill for simple bug fixes or formatting changes.

---

# Required Inputs

Provide:

- Current task description
- Relevant documentation
- Related source files (if applicable)
- API specification
- Architecture document

---

# Workflow

## Step 1 — Understand

Read the task carefully.

Identify:

- Objective
- Expected outcome
- Acceptance criteria

---

## Step 2 — Analyze

Determine:

- Dependencies
- Existing interfaces
- Required modules
- External libraries
- Constraints

---

## Step 3 — Architecture Review

Verify:

- Which layer owns this responsibility.
- Whether existing architecture already supports the task.
- Whether any design conflicts exist.

Never redesign the architecture unless explicitly instructed.

---

## Step 4 — Risk Analysis

Identify:

- Edge cases
- Security concerns
- Performance considerations
- Backward compatibility issues

---

## Step 5 — Implementation Plan

Create a step-by-step implementation roadmap.

Example:

1. Implement validation.
2. Implement core logic.
3. Add error handling.
4. Write tests.
5. Review.

Do NOT generate code.

---

# Output

Return:

- Task summary
- Dependencies
- Risks
- Edge cases
- Implementation steps
- Testing approach

---

# Success Criteria

A planning session is complete only when:

- Requirements are understood.
- Architecture is respected.
- Dependencies identified.
- Risks documented.
- Implementation plan approved.

No code should be generated during this skill.