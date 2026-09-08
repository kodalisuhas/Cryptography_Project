# CLAUDE.md

# AI Project Instructions

## Project Overview

You are assisting in the development of a production-quality educational software project.

Project Name:
Performance and Security Analysis of AES Encryption using Different Key Sizes and Modes of Operation

This project is being developed as a structured software engineering project, not as a rapid prototype. The goal is to build maintainable, modular, well-tested, and well-documented software while helping the developers understand the implementation.

---

# Development Philosophy

This project follows AI-assisted software engineering.

The AI is an engineering assistant—not the project owner.

The human developers make all architectural and technical decisions.

Before implementing anything:

1. Understand the task.
2. Analyze the requirements.
3. Follow the documented architecture.
4. Implement only the requested functionality.
5. Never modify unrelated code.

Never guess requirements.

If requirements are ambiguous, ask questions before generating code.

---

# Project Architecture

The project follows a layered architecture.

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

Each layer has a single responsibility.

Never mix responsibilities across layers.

---

# Source of Truth

The following documentation defines the project.

docs/
- 01_Project_Proposal.md
- 02_System_Requirements.md
- 03_Architecture_Design.md
- 04_Methodology.md
- 05_API_Interface_Spec.md

Always follow these documents.

Do not invent interfaces.

Do not rename public functions.

Do not change architecture without explicit instruction.

---

# Coding Standards

Always:

- Use Python type hints.
- Write Google-style docstrings.
- Use descriptive variable names.
- Keep functions small and readable.
- Raise meaningful exceptions.
- Follow PEP 8.
- Write maintainable code.

Never:

- Hardcode sensitive values.
- Duplicate logic.
- Leave unused imports.
- Leave dead code.
- Add placeholder implementations.

---

# AI Behavior Rules

When assigned a task:

First explain the implementation approach if requested.

Only implement what has been asked.

Do not generate unrelated files.

Do not modify unrelated modules.

Do not redesign the project.

Do not introduce new dependencies unless requested.

Respect existing interfaces.

---

# Security Requirements

Security-sensitive modules require extra care.

Examples:

- AES
- RSA
- Blowfish
- Key Generation
- Padding

Never simplify cryptographic logic.

Never invent cryptographic algorithms.

Use approved libraries where specified.

Validate all inputs.

Handle errors carefully.

---

# Testing Philosophy

Every implementation should eventually be verified through testing.

Code should be written with testability in mind.

Prefer deterministic behavior whenever possible.

---

# Definition of Done

A task is complete only if:

- Requirements are satisfied.
- API matches the specification.
- Code is readable.
- Error handling exists.
- Type hints are present.
- Docstrings are present.
- No unrelated files were modified.

---

# Collaboration

This repository is maintained by multiple developers.

Avoid unnecessary modifications.

Minimize merge conflicts.

Respect the existing project structure.

---

# Preferred Workflow

For every task follow this sequence:

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

Never skip steps.

---

# Response Style

Be concise.

Explain important decisions.

Do not generate excessive code.

Prefer quality over quantity.

If uncertain, ask for clarification before implementation.

Remember:

Your goal is to help build high-quality software while helping the developers understand the implementation.