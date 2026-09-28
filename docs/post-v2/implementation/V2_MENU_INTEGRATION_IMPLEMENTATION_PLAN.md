# POST-V2 INTEGRATION IMPLEMENTATION PLAN
## V2 INTERACTIVE MENU ROUTING TO FILE-SPECIFIC ENCRYPTION ANALYSIS LAB

**Document ID:** POST-V2-INTEG-PLAN-002
**Status:** PROPOSED — REVISED PER INDEPENDENT AUDIT (READY FOR PLAN FREEZE)
**Date:** 2026-09-28
**Author:** Antigravity Engineering (Implementation Architecture & Systems Engineering)
**Target Milestone:** Post-V2 Menu Integration Plan Freeze
**Upstream Frozen Selection:** `docs/post-v2/V2_MENU_INTEGRATION_EXPLORE_AND_SELECTION.md` (`POST-V2-INTEG-SELECT-001`, APPROVED & FROZEN)
**Upstream Frozen Feature:** File-Specific Encryption Analysis Lab (`src/analysis_lab/`, commit `6ce9fc0`)
**Implementation Authorization:** **NOT AUTHORIZED** *(Planning Phase Only; zero code modified)*

---

## Methodological Classification Key

In accordance with strict project governance, every specification in this implementation plan is categorized under the following taxonomy:

- `[FROZEN CONSTRAINT]`: Inviolable baseline boundary, frozen API contract, or immutability rule that cannot be altered under any circumstances.
- `[OBSERVED FACT]`: Verifiable property discovered through direct source code inspection and verified automated test execution.
- `[IMPLEMENTATION SPECIFICATION]`: The definitive engineering blueprint, module contract, error handling rule, and execution flow designed to realize the frozen Selection specification.
- `[OUT OF SCOPE]`: Feature, algorithm, or methodology explicitly excluded from this integration task.

---

## Audit Revisions Summary (from `PLAN-001` to `PLAN-002`)

In accordance with findings from the independent audit, the following six corrections have been incorporated:
1. **Targeted Exception Boundary:** Replaced blanket `except Exception` with strictly targeted `except (OSError, ValueError, RuntimeError) as exc:` while retaining `except KeyboardInterrupt:`. Internal programming defects (e.g. `TypeError`, `AttributeError`) are prohibited from being caught and must propagate unhandled.
2. **Verified Parser Contract `[OBSERVED FACT]`:** Empirically verified against `src/analysis_lab/cli.py` that `build_parser().parse_args([])` yields `Namespace(input_path=None, verbose=False, ...)`, which enters wizard mode deterministically.
3. **Refined Test Blueprint:** Added an explicit test verifying that programming defects propagate unhandled, and structured the mock boundary cleanly around `src.analysis_lab.cli.run_wizard_mode`.
4. **Resilient Presentation Criterion:** Rephrased acceptance criterion #5 to focus on functional contract ("Main menu presents eight options; option 7 is File-Specific Encryption Analysis, option 8 is Exit, and the input prompt accepts the `[1-8]` range") rather than over-rigid whitespace/punctuation.
5. **Non-Binding Test Counts:** Removed rigid test-count phrases (`all 967+ tests pass`) and replaced them with non-regression invariants requiring zero failures across all existing and new tests.
6. **Corrected Baseline Comparison:** Updated Stage 5 repository closure verification to compare against the known feature baseline commit: `git diff 6ce9fc0..HEAD -- src/analysis_lab tests/analysis_lab`.

---

## 1. Executive Summary & Purpose `[IMPLEMENTATION SPECIFICATION]`

This document establishes the authoritative, binding **Implementation Plan** for integrating the completed, frozen **File-Specific Encryption Analysis Lab** (`src/analysis_lab/`, commit `6ce9fc0`) into the primary V2 interactive terminal menu (`src/cli_v2/menu_v2.py`).

Its purpose is to provide the exact, line-by-line engineering blueprint required to execute the integration once implementation is formally authorized:
1. The precise modification of `MenuV2.display_main_menu()` to present an 8-option menu with Option 7 routing to File-Specific Analysis and Option 8 routing to Exit.
2. The implementation of `MenuV2.run_file_analysis_wizard()` as a thin, lazy-importing routing adapter to `src.analysis_lab.cli.run_wizard_mode()`, with strict exception containment limited to `(OSError, ValueError, RuntimeError)`.
3. The precise updates to `tests/cli_v2/test_menu_v2.py` to verify 8-option routing, Option 7 invocation, graceful cancellation, and defect propagation.
4. The exact immutability boundaries safeguarding the frozen Analysis Lab, the V1 release baseline, and all non-integration V2 modules.

---

## 2. Frozen Baselines & Governance Boundaries `[FROZEN CONSTRAINT]`

In accordance with independent audit governance, the system boundaries for this integration task are formally defined:

| Boundary Parameter | Target / Location | Governance Invariant |
| :--- | :--- | :--- |
| **Analysis Lab Baseline** | `src/analysis_lab/` and `tests/analysis_lab/` | **100% BIT-FOR-BIT IMMUTABLE**. Zero modifications permitted. Remains identical to commit `6ce9fc0`. |
| **V1 Release Baseline** | `src/core/`, `src/engines/`, `src/analyzers/`, `src/utils/`, `src/cli/` | **100% BIT-FOR-BIT IMMUTABLE**. `git diff v1.0-release..HEAD` must remain completely empty. |
| **Unmodified V2 Source** | `src/cli_v2/` (except `menu_v2.py`) | All other 9 files (`main_v2.py`, `batch_orchestrator.py`, `file_picker.py`, `key_manager.py`, `navigation.py`, `presentation.py`, `report_generator.py`, `error_translator.py`, `__init__.py`) remain **100% BIT-FOR-BIT IMMUTABLE**. |
| **Unmodified V2 Tests** | `tests/cli_v2/` (except `test_menu_v2.py`) | All other 9 test modules (`test_main_v2.py`, `test_batch_orchestrator.py`, etc.) remain **100% BIT-FOR-BIT IMMUTABLE**. |
| **Dependencies** | `requirements.txt` | **100% BIT-FOR-BIT IMMUTABLE**. Zero new dependencies added. |
| **Authorized Production Target** | `src/cli_v2/menu_v2.py` | Exclusively authorized for menu banner updates, prompt expansion to `[1-8]`, Option 7/8 dispatching, and `run_file_analysis_wizard()` implementation. |
| **Authorized Test Target** | `tests/cli_v2/test_menu_v2.py` | Exclusively authorized for updating `TestMainMenuRouting` to the 8-option contract and adding `test_run_file_analysis_wizard_*` test methods. |

---

## 3. Empirical Verification of CLI Parser Contract `[OBSERVED FACT]`

Direct source code inspection and automated Python namespace evaluation of `src/analysis_lab/cli.py` confirmed:
1. `build_parser().parse_args([])` evaluates to:
   ```python
   Namespace(
       input_path=None,
       output_path=None,
       skip_decryption=False,
       security=False,
       max_size_mb=100,
       no_open=False,
       include_absolute_path=False,
       no_hash=False,
       force=False,
       verbose=False
   )
   ```
2. In `src.analysis_lab.cli.main()`:
   ```python
   if args.input_path is not None:
       return run_direct_mode(args)
   else:
       return run_wizard_mode(args)
   ```
   Because `args.input_path` defaults to `None`, invoking `run_wizard_mode(args)` directly with default args enters the 8-step wizard mode deterministically.
3. `args.verbose` exists as a boolean field on the namespace, allowing `args.verbose = self._verbose` to propagate user verbosity preferences cleanly.

---

## 4. Production Code Blueprint: `src/cli_v2/menu_v2.py` `[IMPLEMENTATION SPECIFICATION]`

### 4.1 Main Menu Rendering & Routing Modifications

In `MenuV2.display_main_menu()`, lines 97–143 will be updated as follows:

```python
        while True:
            print("\n============================================================")
            print("              CRYPTOGRAPHY TESTING LAB — V2")
            print("============================================================")
            print("  1. Single-File Operations (Encrypt, Decrypt, Verify)")
            print("  2. Batch Operations (Folder Encrypt, Folder Decrypt)")
            print("  3. Benchmark & Performance Suite")
            print("  4. Security & Cryptanalysis Lab")
            print("  5. View & Generate HTML Reports")
            print("  6. Help & Documentation")
            print("  7. File-Specific Encryption Analysis")
            print("  8. Exit")
            print("============================================================")

            try:
                raw = input("Select an option [1-8]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting Cryptography Testing Lab. Goodbye!")
                break

            if not raw:
                continue

            token = raw.lower()
            if token in ("8", "exit", "quit", "q", "c", "cancel"):
                print("\nExiting Cryptography Testing Lab. Goodbye!")
                break
            elif token in ("?", "help"):
                self.run_help_wizard()
                continue
            elif token in ("b", "back"):
                print("  (Already at main menu)")
                continue

            if raw == "1":
                self._handle_single_file_menu()
            elif raw == "2":
                self._handle_batch_menu()
            elif raw == "3":
                self.run_benchmark_wizard()
            elif raw == "4":
                self.run_security_wizard()
            elif raw == "5":
                self.run_report_viewer_wizard()
            elif raw == "6":
                self.run_help_wizard()
            elif raw == "7":
                self.run_file_analysis_wizard()
            else:
                print("  Invalid option. Please enter a number between 1 and 8 (or '?' for help).")
```

### 4.2 Method Implementation: `MenuV2.run_file_analysis_wizard`

Directly after `run_help_wizard`, the new wizard method will be added with strict exception containment:

```python
    # =========================================================================
    # 9. File-Specific Encryption Analysis Wizard
    # =========================================================================

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
        except (OSError, ValueError, RuntimeError) as exc:
            ErrorTranslator.display_error(exc, context="File-Specific Analysis", verbose=self._verbose)
            return
```

### 4.3 Key Properties of the Method Implementation
1. **Lazy Import:** Imports `build_parser` and `run_wizard_mode` inside the method body. Ensures `src.analysis_lab.cli` is only loaded when Option 7 is invoked, avoiding any startup overhead or import cycles.
2. **Arguments Construction:** Uses `build_parser().parse_args([])` to initialize standard default arguments with `input_path=None`, which triggers `run_wizard_mode` naturally.
3. **Verbose Propagation:** Propagates `self._verbose` to `args.verbose` so user CLI verbosity preferences are preserved.
4. **Targeted Exception Containment:** Catches `KeyboardInterrupt` gracefully with a clean terminal message, and catches strictly expected operational/cryptographic exceptions `(OSError, ValueError, RuntimeError)` via `ErrorTranslator.display_error()`.
5. **Defect Visibility:** Prohibits catching blanket `Exception` or `BaseException`. Unexpected programming defects (e.g. `TypeError`, `AttributeError`, `IndexError`) propagate unhandled to prevent defect swallowing.
6. **Return Flow:** Synchronously completes and returns, allowing the `while True:` loop in `display_main_menu()` to immediately re-render the main menu banner.

---

## 5. Test Blueprint: `tests/cli_v2/test_menu_v2.py` `[IMPLEMENTATION SPECIFICATION]`

### 5.1 Modifications to Existing `TestMainMenuRouting`

The test class `TestMainMenuRouting` in `tests/cli_v2/test_menu_v2.py` will be updated:

1. **`test_main_menu_exit_options`:**
   ```python
   def test_main_menu_exit_options(self, monkeypatch, capsys):
       """Main menu cleanly exits on '8', 'exit', 'quit', 'c', 'cancel', EOFError, KeyboardInterrupt."""
       for exit_token in ["8", "exit", "quit", "c", "cancel"]:
           menu = MenuV2()
           monkeypatch.setattr("builtins.input", MockInput([exit_token]))
           menu.display_main_menu()
           out = capsys.readouterr().out
           assert "CRYPTOGRAPHY TESTING LAB — V2" in out
           assert "Exiting Cryptography Testing Lab. Goodbye!" in out
   ```
2. **`test_main_menu_help_token`:**
   Update mock input sequence to exit via `"8"`:
   `monkeypatch.setattr("builtins.input", MockInput(["?", "", "8"]))`
3. **`test_main_menu_back_token`:**
   Update mock input sequence to exit via `"8"`:
   `monkeypatch.setattr("builtins.input", MockInput(["b", "8"]))`
4. **`test_main_menu_invalid_choice_reprompts`:**
   Update mock input sequence to exit via `"8"`, and assert updated option range:
   `monkeypatch.setattr("builtins.input", MockInput(["99", "abc", "8"]))`
   `assert "Invalid option. Please enter a number between 1 and 8" in out`
5. **`test_main_menu_routes_to_all_wizards`:**
   Update mock inputs for options 1–6 to exit on `"8"`, mock `run_file_analysis_wizard`, and verify Option 7:
   ```python
   # Mock all wizard methods
   menu.run_single_encrypt_wizard = MagicMock()
   menu.run_single_decrypt_wizard = MagicMock()
   menu.run_batch_encrypt_wizard = MagicMock()
   menu.run_batch_decrypt_wizard = MagicMock()
   menu.run_benchmark_wizard = MagicMock()
   menu.run_security_wizard = MagicMock()
   menu.run_report_viewer_wizard = MagicMock()
   menu.run_help_wizard = MagicMock()
   menu.run_file_analysis_wizard = MagicMock()

   # Options 1-6 exit on "8"
   # ...
   # 9. File-Specific Encryption Analysis (7)
   monkeypatch.setattr("builtins.input", MockInput(["7", "8"]))
   menu.display_main_menu()
   menu.run_file_analysis_wizard.assert_called_once()
   ```

### 5.2 New Unit Tests: `test_run_file_analysis_wizard_*`

Four dedicated test methods will be added to `TestMainMenuRouting` to thoroughly test `run_file_analysis_wizard`:

```python
    def test_run_file_analysis_wizard_invokes_cli(self, monkeypatch, capsys):
        """Verify run_file_analysis_wizard dispatches to src.analysis_lab.cli.run_wizard_mode."""
        menu = MenuV2(verbose=True)

        with patch("src.analysis_lab.cli.run_wizard_mode") as mock_run:
            mock_run.return_value = 0
            menu.run_file_analysis_wizard()

            mock_run.assert_called_once()
            called_args = mock_run.call_args[0][0]
            assert called_args.input_path is None
            assert called_args.verbose is True

        out = capsys.readouterr().out
        assert "File-Specific Encryption Analysis Lab" in out

    def test_run_file_analysis_wizard_keyboard_interrupt(self, monkeypatch, capsys):
        """Verify run_file_analysis_wizard handles KeyboardInterrupt gracefully."""
        menu = MenuV2()

        with patch("src.analysis_lab.cli.run_wizard_mode", side_effect=KeyboardInterrupt):
            menu.run_file_analysis_wizard()

        out = capsys.readouterr().out
        assert "[!] Analysis cancelled by user." in out

    def test_run_file_analysis_wizard_expected_exception_handling(self, monkeypatch):
        """Verify run_file_analysis_wizard routes expected exceptions through ErrorTranslator."""
        menu = MenuV2()

        for exc_type in (OSError("disk error"), ValueError("bad value"), RuntimeError("engine failure")):
            with patch("src.analysis_lab.cli.run_wizard_mode", side_effect=exc_type):
                with patch("src.cli_v2.error_translator.ErrorTranslator.display_error") as mock_error:
                    menu.run_file_analysis_wizard()
                    mock_error.assert_called_once()
                    assert mock_error.call_args[1]["context"] == "File-Specific Analysis"

    def test_run_file_analysis_wizard_programming_defect_propagates(self):
        """Verify unexpected programming defects propagate unhandled."""
        menu = MenuV2()

        with patch("src.analysis_lab.cli.run_wizard_mode", side_effect=TypeError("programming bug")):
            with pytest.raises(TypeError, match="programming bug"):
                menu.run_file_analysis_wizard()
```

---

## 6. Five-Stage Integration Roadmap `[IMPLEMENTATION SPECIFICATION]`

```text
┌────────────────────────────────────────────────────────────────────────┐
│               V2 MENU INTEGRATION IMPLEMENTATION ROADMAP               │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 1: IMPLEMENTATION (src/cli_v2/menu_v2.py)                       │
│ - Update display_main_menu() banner with Option 7 and Option 8         │
│ - Update prompt text to [1-8] and exit tokens to 8/exit/quit/c/cancel  │
│ - Add Option 7 dispatch to self.run_file_analysis_wizard()             │
│ - Implement run_file_analysis_wizard() with targeted exception guard   │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 2: TEST ADAPTATION & EXPANSION (tests/cli_v2/test_menu_v2.py)    │
│ - Update existing TestMainMenuRouting to 8-option contract             │
│ - Add test for Option 7 routing                                        │
│ - Add tests for run_file_analysis_wizard invocation, cancellation,     │
│   expected exception handling, and defect propagation                  │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 3: AUTOMATED VERIFICATION & REGRESSION AUDIT                     │
│ - Execute python -m pytest tests/cli_v2/test_menu_v2.py -v             │
│ - Execute python -m pytest tests/analysis_lab/ -v (81/81 pass invariant│
│ - Execute full pytest regression suite and require zero failures/      │
│   regressions across the baseline; record actual counts                │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 4: LIVE MANUAL INTEGRATION VERIFICATION                          │
│ - Execute run-v2.bat / python -m src.cli_v2.main_v2                    │
│ - Verify 8-option banner displays correctly                            │
│ - Select Option 7 -> run analysis on sample file -> verify report      │
│ - Verify return to main menu -> select Option 8 to exit cleanly        │
├────────────────────────────────────────────────────────────────────────┤
│ STAGE 5: REPOSITORY CLOSURE (Commit & Push)                            │
│ - Verify git diff: ONLY menu_v2.py and test_menu_v2.py modified        │
│ - Verify git diff v1.0-release..HEAD is 100% clean                     │
│ - Verify git diff 6ce9fc0..HEAD -- src/analysis_lab tests/analysis_lab │
│   is 100% clean (zero modifications to frozen lab feature)             │
│ - Commit and push to origin/main                                       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Verifiable Acceptance Criteria `[IMPLEMENTATION SPECIFICATION]`

1. **Analysis Lab Immutability:** `git diff 6ce9fc0..HEAD -- src/analysis_lab tests/analysis_lab` is completely empty (0 files changed, 0 insertions, 0 deletions). The feature remains 100% frozen.
2. **V1 Release Immutability:** `git diff v1.0-release..HEAD -- src/core src/engines src/analyzers src/utils src/cli` is completely empty.
3. **Unmodified V2 Source Immutability:** Zero files in `src/cli_v2/` other than `menu_v2.py` differ from their `v2.0-release` baseline.
4. **Dependency Immutability:** `requirements.txt` remains bit-for-bit identical to release baseline.
5. **Menu Presentation Contract:** Main menu presents eight options; Option 7 is File-Specific Encryption Analysis, Option 8 is Exit, and the input prompt accepts the `[1-8]` range.
6. **Option 7 Dispatch:** Selecting `7` triggers `run_file_analysis_wizard()` and invokes `src.analysis_lab.cli.run_wizard_mode(args)`.
7. **Return Semantics:** Completing or cancelling the analysis wizard returns cleanly to the V2 main menu loop without crashing or terminating the session.
8. **Universal Exit Tokens:** Entering `8`, `exit`, `quit`, `q`, `c`, `cancel`, `EOFError`, or `KeyboardInterrupt` at the main menu cleanly exits the application.
9. **Unit & Integration Tests:** `tests/cli_v2/test_menu_v2.py` passes 100% with all new and updated tests.
10. **Zero Regression:** All 81 `tests/analysis_lab/` tests continue to pass; the full repository test suite passes with zero failures or regressions.

---

## 8. Plan Status & Authorization

```text
========================================================================
IMPLEMENTATION PLAN STATUS:
PROPOSED — REVISED PER INDEPENDENT AUDIT (READY FOR PLAN FREEZE)

IMPLEMENTATION AUTHORIZATION:
NOT AUTHORIZED (Awaiting Formal Review & Approval of this Plan)
========================================================================
```

**Formal Governance Rule:** No code in `src/cli_v2/menu_v2.py` or `tests/cli_v2/test_menu_v2.py` will be modified until this revised implementation plan is formally approved and frozen.
