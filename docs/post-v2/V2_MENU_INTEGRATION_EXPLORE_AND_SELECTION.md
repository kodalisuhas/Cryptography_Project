# POST-V2 INTEGRATION EXPLORATION & SELECTION SPECIFICATION
## V2 INTERACTIVE MENU ROUTING TO FILE-SPECIFIC ENCRYPTION ANALYSIS LAB

**Document ID:** POST-V2-INTEG-SELECT-001
**Status:** PROPOSED — READY FOR INDEPENDENT REVIEW & METHODOLOGY FREEZE
**Date:** 2026-09-28
**Author:** Antigravity Engineering (Usability Layer & Systems Architecture)
**Target Milestone:** Post-V2 Menu Integration Selection Freeze
**Upstream Frozen Feature:** File-Specific Encryption Analysis Lab (`src/analysis_lab/`, commit `6ce9fc0`)
**Implementation Authorization:** **NOT AUTHORIZED** *(Exploration & Selection Phase Only; zero production code modified)*

---

## 1. Executive Summary & Context

The **File-Specific Encryption Analysis Lab** was completed, verified across 81 lab tests and 967 total repository tests, and permanently committed to `main` at commit `6ce9fc0`. In accordance with the approved Selection methodology (`POST-V2-FEAT-SELECT-002`), V2 interactive menu integration was deliberately deferred to protect the frozen V2 baseline during core feature development.

The objective of this new integration task is to expose the completed feature directly within the primary user-facing interactive launcher:
- **Launcher:** `run-v2.bat` (which invokes `python -m src.cli_v2.main_v2 %*`)
- **Interactive Menu:** `MenuV2.display_main_menu()` in `src/cli_v2/menu_v2.py`

This integration will expand the V2 main menu from 7 options to 8 options:
- Option 7: **File-Specific Encryption Analysis** (routing into the existing `src.analysis_lab.cli` wizard)
- Option 8: **Exit** (preserving universal exit tokens: `8`, `exit`, `quit`, `q`, `c`, `cancel`)

### Core Architectural Principle: Thin Routing Adapter
This integration task builds a thin UI routing bridge from `MenuV2` to `src.analysis_lab.cli`. **Under no circumstances will any logic from `src/analysis_lab/` be duplicated, modified, or reopened.** The Analysis Lab remains 100% frozen as commit `6ce9fc0`.

---

## 2. Technical Investigation of the Existing V2 CLI Architecture

A thorough inspection of `run-v2.bat`, `src/cli_v2/main_v2.py`, `src/cli_v2/menu_v2.py`, and `tests/cli_v2/` established the following architectural facts:

### 2.1 Launcher & Entrypoint Chain
1. `run-v2.bat` executes:
   ```cmd
   @echo off
   cd /d "%~dp0"
   python -m src.cli_v2.main_v2 %*
   ```
2. When invoked with no command-line arguments (the standard interactive double-click / terminal launch), `src/cli_v2/main_v2.py` executes:
   ```python
   if not cli_args or cli_args == ["menu"]:
       MenuV2().display_main_menu()
       return EXIT_SUCCESS
   ```
3. Therefore, `run-v2.bat` requires **zero modifications**. Any enhancements to `MenuV2.display_main_menu()` are immediately and automatically accessible via `run-v2.bat`.

### 2.2 Menu Representation & Dispatch (`MenuV2.display_main_menu`)
- The main menu operates inside a standard `while True:` loop.
- Header, banner, and options are printed to `stdout` sequentially.
- User input is captured via `raw = input("Select an option [1-7]: ").strip()`.
- Universal shortcuts are intercepted before numerical routing:
  - Exit tokens: `token in ("7", "exit", "quit", "q", "c", "cancel")`
  - Help tokens: `token in ("?", "help")` $\rightarrow$ calls `self.run_help_wizard()`; `continue`
  - Back tokens: `token in ("b", "back")` $\rightarrow$ prints `"(Already at main menu)"`; `continue`
- Numerical routing currently maps:
  - `"1"` $\rightarrow$ `self._handle_single_file_menu()`
  - `"2"` $\rightarrow$ `self._handle_batch_menu()`
  - `"3"` $\rightarrow$ `self.run_benchmark_wizard()`
  - `"4"` $\rightarrow$ `self.run_security_wizard()`
  - `"5"` $\rightarrow$ `self.run_report_viewer_wizard()`
  - `"6"` $\rightarrow$ `self.run_help_wizard()`

### 2.3 Wizard Return & Navigation Semantics
- Each wizard method in `MenuV2` executes synchronously and concludes with a simple `return`.
- When a wizard returns, control flows back into the `while True:` loop of `display_main_menu()`, which automatically re-renders the main menu banner and re-prompts the user.
- Wizards that generate HTML reports (`run_benchmark_wizard`, `run_security_wizard`) conclude by prompting whether to launch the browser (`"Open HTML report in web browser?"`), and immediately return to the main menu upon answer. No superfluous pause prompts are injected.

### 2.4 Exception Handling & Signal Resilience
- In `display_main_menu()`:
  - `except (EOFError, KeyboardInterrupt): print("\nExiting Cryptography Testing Lab. Goodbye!"); break`
  - Clean exit with zero unhandled tracebacks.
- Inside each wizard method:
  - `except KeyboardInterrupt: print("\n[!] Operation cancelled by user."); return`
  - `except Exception as exc: ErrorTranslator.display_error(exc, context="...", verbose=self._verbose); return`
  - Gracefully translates unexpected exceptions via `ErrorTranslator` and returns cleanly to the main menu loop.

### 2.5 Dependency Direction & Circular Import Safety
Inspection of existing imports confirms:
- `src.analysis_lab.cli` imports:
  - `from src.analysis_lab.runner import FileAnalysisRunner`
  - `from src.cli_v2.file_picker import FilePicker`
  - `from src.cli_v2.presentation import Presentation`
- `src.analysis_lab` does **NOT** import `src.cli_v2.menu_v2`.
- `FilePicker` and `Presentation` do **NOT** import `MenuV2`.
- Therefore, having `MenuV2` route into `src.analysis_lab.cli` introduces **zero circular import cycles**.
- Adopting a **lazy import** inside `MenuV2.run_file_analysis_wizard()` provides strict isolation: `src.analysis_lab.cli` is loaded only when the user explicitly triggers option 7.

---

## 3. Analysis of Integration Options & UX Decisions

### Option A: Direct Wizard Dispatch (Recommended)
When the user selects `7`, `MenuV2` invokes `run_file_analysis_wizard()`, which initializes `src.analysis_lab.cli.run_wizard_mode(args)`.

```text
CRYPTOGRAPHY TESTING LAB — V2
  ...
  7. File-Specific Encryption Analysis
  8. Exit
Select an option [1-8]: 7
      │
      ▼
============================================================
          FILE-SPECIFIC ENCRYPTION ANALYSIS WIZARD
============================================================
Enter target file path (drag-and-drop supported, 'c' to cancel):
      │
      ├── Step 1: File path input & validation
      ├── Step 2: Preflight inspection (size, SHA-256)
      ├── Step 3: Scope confirmation (6 AES configurations)
      ├── Step 4: Operational options (decryption, security)
      ├── Step 5: High-volume warning (>30 MB)
      ├── Step 6: Microbenchmarking & report generation
      ├── Step 7: Formatted terminal summary card
      └── Step 8: Auto-open HTML report prompt
      │
      ▼
Return cleanly to V2 Main Menu
```

**Evaluation:**
- **Pros:** Directly leverages the existing, fully-tested, 8-step wizard in `src.analysis_lab.cli`. Perfectly consistent with Option 3 (Benchmark Wizard) and Option 4 (Security Wizard). Zero redundant intermediary menus.
- **Cons:** None.

### Option B: Intermediate V2 Submenu
Selecting `7` renders an intermediate choice:
```text
File-Specific Analysis:
  1. Analyze an Individual File
  2. View Documentation
  3. Return to Main Menu
```

**Evaluation:**
- **Pros:** None; adds boilerplate.
- **Cons:** Violates UX ergonomics by forcing an unnecessary extra click for a single functional capability. Inconsistent with options 3, 4, and 5 in V2.

### Decision: Adopt Option A (Direct Wizard Dispatch).

---

## 4. Integration Contract & Method Specification

### 4.1 Main Menu Rendering & Option Contract
The menu in `MenuV2.display_main_menu()` will be updated as follows:

```text
============================================================
              CRYPTOGRAPHY TESTING LAB — V2
============================================================
  1. Single-File Operations (Encrypt, Decrypt, Verify)
  2. Batch Operations (Folder Encrypt, Folder Decrypt)
  3. Benchmark & Performance Suite
  4. Security & Cryptanalysis Lab
  5. View & Generate HTML Reports
  6. Help & Documentation
  7. File-Specific Encryption Analysis
  8. Exit
============================================================
```

- **Prompt Text:** `Select an option [1-8]: `
- **Exit Condition:** `if token in ("8", "exit", "quit", "q", "c", "cancel"):`
- **Routing for Option 7:**
  ```python
  elif raw == "7":
      self.run_file_analysis_wizard()
  ```
- **Invalid Option Handling:**
  `print("  Invalid option. Please enter a number between 1 and 8 (or '?' for help).")`

### 4.2 Wizard Method Contract: `run_file_analysis_wizard`
A new method will be added to `MenuV2`:

```python
    def run_file_analysis_wizard(self) -> None:
        """Run the File-Specific Encryption Analysis wizard.

        Routes user into the frozen post-V2 Analysis Lab interactive wizard
        (src.analysis_lab.cli.run_wizard_mode), providing comprehensive 6-config
        evaluation against an individual file payload with standalone HTML reporting.
        """
        print("\n--- File-Specific Encryption Analysis Lab ---")
        try:
            from src.analysis_lab.cli import build_parser, run_wizard_mode
            parser = build_parser()
            args = parser.parse_args([])
            args.verbose = self._verbose
            run_wizard_mode(args)
        except KeyboardInterrupt:
            print("\n[!] Analysis cancelled by user.")
            return
        except Exception as exc:
            ErrorTranslator.display_error(exc, context="File-Specific Analysis", verbose=self._verbose)
            return
```

### 4.3 Post-Execution Flow
When `run_wizard_mode(args)` finishes (whether via successful report generation, user cancellation with `'c'`, or input rejection), it returns control to `run_file_analysis_wizard()`. The method exits cleanly, and the `while True:` loop in `display_main_menu()` immediately redisplays the main menu.

---

## 5. Governance & Immutability Boundaries

To safeguard the completed feature and all historic releases, strict immutability boundaries are enforced:

| Subsystem / Directory | Governance Policy | Invariant |
|---|---|---|
| `src/analysis_lab/*` | **100% FROZEN** | Zero modifications allowed. Remains bit-for-bit identical to commit `6ce9fc0`. |
| `tests/analysis_lab/*` | **100% FROZEN** | Zero modifications allowed. All 81 tests remain bit-for-bit identical. |
| `src/core/*` | **100% FROZEN** | V1 release baseline remains bit-for-bit immutable (`git diff` clean). |
| `src/engines/*` | **100% FROZEN** | V1 release baseline remains bit-for-bit immutable (`git diff` clean). |
| `src/analyzers/*` | **100% FROZEN** | V1 release baseline remains bit-for-bit immutable (`git diff` clean). |
| `src/utils/*` | **100% FROZEN** | V1 release baseline remains bit-for-bit immutable (`git diff` clean). |
| `src/cli/*` | **100% FROZEN** | V1 release baseline remains bit-for-bit immutable (`git diff` clean). |
| `requirements.txt` | **100% FROZEN** | Zero new dependencies added. |
| `src/cli_v2/menu_v2.py` | **MODIFIABLE (Integration Scope)** | Add Option 7 to banner, prompt, and routing; implement `run_file_analysis_wizard()`. |
| `tests/cli_v2/test_menu_v2.py` | **MODIFIABLE (Integration Scope)** | Update main menu routing tests to reflect 8-option layout and test Option 7 dispatch. |

---

## 6. Testing & Quality Assurance Plan

### 6.1 Unit & Integration Test Updates in `tests/cli_v2/test_menu_v2.py`
The existing `TestMainMenuRouting` test class will be updated to reflect the 8-option menu:
1. `test_main_menu_exit_options`: Updated to test `"8"`, `"exit"`, `"quit"`, `"c"`, `"cancel"`.
2. `test_main_menu_help_token`: Exit token changed from `"7"` to `"8"`.
3. `test_main_menu_back_token`: Exit token changed from `"7"` to `"8"`.
4. `test_main_menu_invalid_choice_reprompts`: Exit token changed from `"7"` to `"8"`; assert range `1 and 8`.
5. `test_main_menu_routes_to_all_wizards`:
   - Updated existing dispatches (options 1–6) to exit on `"8"`.
   - Added explicit verification for Option 7: entering `["7", "8"]` invokes `menu.run_file_analysis_wizard`.
6. New Dedicated Integration Test:
   - `test_run_file_analysis_wizard_invokes_cli`: Verifies that `run_file_analysis_wizard` calls `run_wizard_mode` with clean arguments, passes `verbose`, and handles `KeyboardInterrupt` and exceptions cleanly via `ErrorTranslator`.

### 6.2 Acceptance Invariants
```bash
# 1. New V2 menu tests pass:
python -m pytest tests/cli_v2/test_menu_v2.py -v

# 2. Frozen lab suite remains 100% green:
python -m pytest tests/analysis_lab/ -v

# 3. Full repository regression remains 100% green:
python -m pytest
# Must pass all 960+ tests with 0 failures.
```

---

## 7. Status & Next Gate

```text
========================================================================
SELECTION & METHODOLOGY STATUS:
PROPOSED — READY FOR INDEPENDENT REVIEW & METHODOLOGY FREEZE

AUTHORIZATION STATE:
NOT AUTHORIZED (Exploration & Selection Phase Only; zero code modified)
========================================================================
```

**Next Step:** Submit this exploration and selection document for independent review. Upon approval, proceed to author the formal **Implementation Plan** (`POST-V2-INTEG-PLAN-001`). Zero code changes will be made until the Implementation Plan is reviewed and approved.
