# V2 RESEARCH A — GUIDED MENU UX

**Document ID:** V2-RESEARCH-A  
**Status:** DRAFT / RESEARCH COMPLETE (Recommendations Not Yet Frozen)  
**Date:** 2026-09-15  
**Author:** V2 Research & Architecture Planning  
**Scope Focus:** Category A (Guided Menu UX) & Cross-Cutting Interaction Architecture  
**Target Milestone:** V2 Phase 1 (Research)  
**Authoritative Reference:** [V2_INTENT.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md)

---

> [!NOTE]
> **Research Scope Note:** This report contains both research findings and candidate design suggestions. Research findings describe observed usability principles, technical constraints, V1 friction points, and evidence from external research. Candidate workflows, UI structures, policies, architectures, and recommendations are not frozen decisions. They are proposals for consideration during the Project-Specific Selection phase and may be accepted, rejected, or modified. Final V2 architecture, behavior, defaults, and implementation decisions are deferred to Selection and subsequent approval.

---

## 1. Research Objective

This research report investigates how the user experience (UX) of the **Cryptography Testing Lab** can be transitioned from a developer-centric, flag-intensive command-line interface into an intuitive, guided, and highly accessible terminal workflow for students, educators, evaluators, and practical users.

The core research question addressed is:

> **How can we make existing V1 cryptography workflows significantly easier and more practical without modifying the frozen V1 core, weakening security rigor, or altering underlying cryptographic behavior?**

This report examines terminal menu ergonomics, step-by-step wizard patterns, safe default management, interactive validation, error communication, contextual educational aids, long-operation progress indicators, post-operation summaries, file selection strategies on Windows, interactive testability, and cross-cutting UX architectures.

---

## 2. V2 Context

### 2.1 V1 Current CLI Architecture

The V1 CLI (`src/cli/`) is a lightweight presentation layer over the frozen service layer (`CipherService`, `BenchmarkService`, `SecurityService`). V1 provides five subcommands via `argparse`:

```text
python -m src.cli.main encrypt    [--algorithm AES] --key-size <bits> --mode <ECB|CBC> ...
python -m src.cli.main decrypt    --key-size <bits> --mode <ECB|CBC> --key <HEX> ...
python -m src.cli.main benchmark  [--key-sizes <L>] [--modes <M>] [--payload-sizes <P>] ...
python -m src.cli.main security   --key <HEX> --mode <ECB|CBC> ...
python -m src.cli.main menu
```

#### V1 Strengths
* **Deterministic & Scriptable:** Arguments map directly to service parameters with zero ambiguity.
* **Rigorous Validation:** Exact key-length verification, mutual exclusivity enforcement (e.g., `--input` vs. `--input-file`), and strict mode rules (rejecting IVs for ECB).
* **Zero Dependencies:** Pure Python standard library (`argparse`, `getpass`, `pathlib`, `struct`).

#### V1 Usability Friction Points
* **Cognitive Load:** Requires memorizing and correctly combining up to 7 distinct CLI flags per command.
* **Hex String Ergonomics:** Users must manually copy, format, and paste 32-character, 48-character, or 64-character hexadecimal keys and IVs across separate command invocations.
* **Zero-Argument Invocation Failure:** Invoking `python -m src.cli.main` without subcommands raises an `argparse` usage error (`exit code 2`) rather than opening a guided interface.
* **Single-File Constraint:** Encryption/decryption requires invoking individual commands per file.
* **Terminal-Only Artifacts:** Benchmark tables and security evaluation results are printed directly to stdout or saved as raw CSV/JSON files, requiring external tools to inspect comfortably.

### 2.2 Existing V1 Menu Analysis

V1 includes a basic interactive menu in `src/cli/menu.py` (`python -m src.cli.main menu`):

```text
=== Cryptography Testing Lab ===

1. Encrypt
2. Decrypt
3. Benchmark
4. Security Analysis
5. Exit
```

#### How V1 Menu Operates
1. Prompts for option `1-5` in a `while True` loop.
2. Prompts sequentially for parameters using `input()` and `_prompt_choice_*` helpers.
3. Constructs an `argparse.Namespace` matching the subcommand structure.
4. Dispatches the namespace directly to `commands.run_*`.
5. Catches `(ValueError, TypeError, KeyError)` to prevent crashes, prints `Error: <msg>`, and loops back to the top-level menu.

#### V1 Menu Limitations
* **Linear & Unidirectional:** No "Back" option. If a user mistypes an option at step 5 of 6, they must either complete the workflow or kill the process with `Ctrl+C`.
* **No File Browsing:** File paths must be typed manually and accurately without directory auto-discovery or file-picker assistance.
* **No Key Persistence:** Generated keys are printed to terminal stdout; the user must manually copy the hex string before it scrolls out of view.
* **No Post-Operation Actionability:** After encryption, the menu returns immediately to the top-level prompt without offering round-trip verification, output folder navigation, or sidecar generation.
* **Jargon-Heavy Prompts:** Expects the user to know whether ECB or CBC is appropriate, whether 128 or 256 bits is needed, and what an IV is.

### 2.3 V2 Intent Requirements

According to [V2_INTENT.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md), V2 introduces four core functional categories:
* **Category A: Guided Menu UX** (Interactive file picker, auto-save prompts, round-trip verification, output folder navigation, post-op summaries, friendly error diagnostics, contextual in-app help).
* **Category B: Key Management** (Sidecar `.key` files, key loading, validation, security warnings).
* **Category C: Batch Operations** (Folder-level encrypt/decrypt, per-file status accounting, resilient error logging).
* **Category D: Reporting** (Consolidated benchmark metrics, standalone HTML reports, comparative security visualizations, auto-launch in default browser).

V2 must satisfy the **V1 Non-Modification Contract**: zero changes to `src/core/`, `src/engines/`, `src/analyzers/`, `src/utils/`, and `src/cli/`, zero new third-party dependencies, and native Python exception handling.

---

## 3. Research Methodology

This research combines:
1. **Repository Evidence & Code Analysis:** Review of V1 CLI architecture (`src/cli/`), engine interfaces (`src/engines/`), and test harnesses (`tests/cli/`).
2. **Terminal Human Interface Guidelines (HIG):** Standards derived from POSIX CLI conventions, Nielsen Norman Group CLI usability principles, and modern developer CLI tools (`git`, `gh`, `docker`, `npm`, `aws-cli`).
3. **Cognitive Walkthroughs:** Analyzing typical user task flows (e.g., "Encrypt a student assignment file and verify it can be decrypted") to identify interaction bottlenecks.
4. **State Machine & Navigation Modeling:** Evaluating navigation models (linear, stack-based, hierarchical) for terminal wizard interfaces.
5. **Standard Library Constraints Analysis:** Researching standard library capabilities (`input`, `getpass`, `pathlib`, `shutil`, `subprocess`, `webbrowser`, `os`) to avoid external dependencies.

---

## 4. CLI Menu UX Findings

### 4.1 Menu Hierarchy and Option Density

#### Evidence & Usability Principles
* **Miller's Law (Cognitive Load):** Humans hold $7 \pm 2$ chunks of information in working memory. Menus with more than 7–8 top-level options create visual clutter and decision paralysis.
* **Hick's Law (Human-Factors Principle):** Decision time tends to increase with the number and complexity of choices ($T = b \cdot \log_2(n + 1)$). Rather than a rigid engineering formula for menu limits, this principle indicates that reducing top-level clutter and categorizing related actions decreases cognitive search time and error rates.

#### Findings
1. **Top-Level Grouping:** A flat list of 10+ options (e.g., Encrypt File, Decrypt File, Batch Encrypt, Batch Decrypt, Benchmark, Security, Generate Key, Inspect Key, HTML Report, Help, Exit) is overwhelming.
2. **Task-Centric Grouping:** Grouping operations into 5–6 logical clusters (e.g., File Cryptography, Batch Operations, Benchmarks & Analysis, Key Utilities, Help & Settings, Exit) reduces cognitive friction.
3. **Numbered vs. Alphabetic Selection:** Numeric keys (`1`, `2`, `3`) are universally understood, faster to parse visually in terminal columns, and consistent across keyboard layouts.

### 4.2 Visual Formatting and Layout Consistency

#### Findings
* **Visual Anchors:** Top-level menus and sub-wizards should feature standardized headers (title banner, current location/breadcrumb, clear numbered options, and consistent prompt line).
* **Consistent Prompt Format:** 
  ```text
  [Step N/M] Prompt Label (valid/choices) [default]: 
  ```
* **Clear Section Separation:** Visual divider lines (e.g., `----------------------------------------`) cleanly demarcate steps, preventing wall-of-text fatigue.

---

## 5. Guided Workflow Findings

A "Guided Workflow" (Wizard pattern) breaks a complex cryptographic operation into sequential, validated atomic configuration steps followed by a post-operation summary stage.

### 5.1 Wizard Step Anatomy

Every guided step should adhere to a uniform structure:
1. **Context/Purpose:** Short, plain-English explanation of the parameter being configured.
2. **Input with Recommendation:** Clear prompt showing valid choices with the recommended default highlighted.
3. **Immediate Validation:** Immediate syntax and semantic validation before moving to the next step.
4. **Step Memory:** Ability to retain previous answers if the user navigates backward.

### 5.2 Workflow Step Breakdown Analysis

A workflow consists of **input/configuration steps** followed by a distinct **post-operation summary stage**:

| Workflow | Configuration Steps | Step Breakdown | Post-Op Summary Stage |
| :--- | :--- | :--- | :--- |
| **File Encryption** | 4 steps | 1. Select Input File<br>2. Select Algorithm/Mode (Defaults provided)<br>3. Key Strategy (Generate / Load / Enter)<br>4. Confirm Execution & Auto-Save Options | Structured summary card + next actions |
| **File Decryption** | 3 steps | 1. Select Ciphertext File<br>2. Key Acquisition (Load `.key` / Enter Hex)<br>3. Output Confirmation | Structured summary card + next actions |
| **Batch Encrypt/Decrypt**| 4 steps | 1. Select Source Directory<br>2. Configuration / Key Selection<br>3. Output Directory & Overwrite Policy<br>4. Confirm Batch Execution | Batch completion table + failure log summary |
| **Benchmark Suite** | 3 steps | 1. Select Preset (Quick / Standard / Exhaustive)<br>2. Output Options (Terminal / CSV / HTML / Graphs)<br>3. Confirm Execution | Summary table + file paths + browser prompt |
| **Security Evaluation** | 3 steps | 1. Mode Selection (ECB vs CBC Comparison)<br>2. Key & Sample Selection<br>3. Output Report Options | Metric summary + JSON report path |

---

## 6. Defaults and Safe Choices

### 6.1 Cryptographic Defaults & The "Explicit Visibility" Principle

Cryptographic tools face a unique dilemma:
* Inconvenient security leads to user bypass or error.
* Hidden or opaque security leads to false assumptions.

#### Findings & Security Nuance
1. **Candidate Default Mode:** For general file encryption, **AES-256-CBC with a random IV per file** may be used within the V2 scope, but CBC provides confidentiality and does not by itself provide authentication or integrity. V2 must not present CBC as authenticated encryption. Authenticated modes such as GCM remain outside the current V2 scope. ECB should never be the default and should carry an educational warning about pattern leakage.
2. **Default Key Handling:** Default to **Generate New Key & Save Sidecar (`.key`)** during encryption, with explicit display of where the key is stored.
3. **Default Paths:** Derive sensible output paths automatically:
   * Plaintext: `data/input/sample.txt`
   * Ciphertext: `data/output/sample.txt.enc`
   * Key Sidecar: `data/output/sample.txt.key`
   * IV Sidecar: `data/output/sample.txt.iv`
4. **Explicit Confirmation:** Never apply defaults silently. The prompt must display `[AES-256 / CBC]` and allow one-key acceptance (`Enter`) or explicit reconfiguration.

---

## 7. Back / Cancel / Retry Navigation Model

Interactive terminal applications often fail because they treat input collection as a linear script rather than a stateful navigation stack.

### 7.1 Navigation Commands

At any step prompt, the user should have access to standard control tokens:
* `b` or `back`: Return to the previous configuration step in the active workflow, preserving previously entered valid choices.
* `c` or `cancel`: Abort the current workflow immediately and return to the main menu without executing any operations or leaving orphaned temporary files.
* `?` or `help`: Display contextual explanation for the current prompt.

### 7.2 State Machine Representation

```text
               +------------------------------+
               |          Main Menu           |
               +--------------+---------------+
                              | Select Workflow
                              v
               +------------------------------+
         +---->| Step 1: Input File (Config)  |<---+
         |     +--------------+---------------+    |
         |                    | Valid              | Back
  Cancel |                    v                    |
         |     +------------------------------+    |
         +---->| Step 2: Settings / Key Mode  +----+
         |     +--------------+---------------+    |
         |                    | Valid              | Back
         |                    v                    |
         |     +------------------------------+    |
         +---->| Step 3: Key Acquisition      +----+
         |     +--------------+---------------+    |
         |                    | Valid              | Back
         |                    v                    |
         |     +------------------------------+    |
         +---->| Step 4: Confirm & Execute    +----+
         |     +--------------+---------------+
         |                    | Execute Operation
         |                    v
         |     +------------------------------+
         +-----+ Post-Operation Summary Stage +----> [Return to Menu]
               +------------------------------+
```

---

## 8. Input Validation Ergonomics

### 8.1 Validation Strategy

V1 validates inputs inside command handlers or via `argparse`, which aborts execution or returns immediately to the top-level menu. V2 should validate at the **point of entry**.

```text
[User Input] ---> [Validator] ---> Valid? --YES--> [Next Step]
                       |
                       NO
                       v
             [Explain Error Clearly]
             [Show Valid Format Example]
             [Re-prompt Current Step]
```

### 8.2 Validation Rules Matrix

| Input Field | Validation Criteria | Error Guidance Example |
| :--- | :--- | :--- |
| **File Path** | Must exist, must be readable file, not directory | `"File not found: 'data/test.txt'. Please check the path or use the file picker."` |
| **Hex Key** | Exactly 32 (128-bit), 48 (192-bit), or 64 (256-bit) hex chars | `"Invalid key length: 40 hex characters entered. AES requires 32, 48, or 64 characters (128, 192, or 256 bits)."` |
| **Hex IV** | Exactly 32 hex chars (16 bytes) | `"Invalid IV: Must be exactly 32 hex characters (16 bytes). Press Enter to auto-generate."` |
| **Choice Option** | In allowed set $\{1..N\}$ | `"Invalid option '7'. Please enter a number between 1 and 5."` |
| **Directory** | Must exist (or prompt to create), must be writable | `"Directory 'output/' does not exist. Create it now? (Y/n)"` |

---

## 9. Error UX and Diagnostic Communication

### 9.1 The Three-Tier Error Model

Error messages must be empathetic, precise, and actionable:

```text
+-------------------------------------------------------------+
| 1. What failed (The immediate failure symptom)              |
| 2. Why it failed (Root cause analysis in plain language)    |
| 3. What to do next (Actionable resolution steps)            |
+-------------------------------------------------------------+
```

#### Example: Padding / Wrong Key Failure
* **V1 Output:** `Error: Padding is invalid or corrupted`
* **V2 Output:**
  ```text
  [!] Decryption Failed: Cryptographic Padding Error
  ------------------------------------------------------------
  Why: The ciphertext could not be decrypted properly. This almost
       always occurs when the wrong key or wrong IV is used, or if
       the ciphertext file was modified/corrupted.
  
  What to do:
    1. Verify that you selected the exact .key file generated during encryption.
    2. For CBC mode, confirm the matching .iv file is present.
    3. Ensure the ciphertext file has not been truncated or altered.
  ```

### 9.2 Avoiding Technical Obfuscation

* Do not display raw Python stack traces (`Traceback (most recent call last)...`) during standard menu operations.
* Preserve an optional `--verbose` or diagnostic mode for developers and advanced troubleshooting.

---

## 10. Educational UX & Progressive Disclosure

The testing lab is used by students and evaluators who are learning applied cryptography.

### 10.1 In-Context Micro-Tooltips

Short, one-line conceptual cues embedded directly in prompts:
* `Mode [1=CBC (Confidentiality / Recommended default), 2=ECB (Demonstration only -- leaks patterns)]: `
* `Key Size [1=128-bit (Fast), 2=192-bit, 3=256-bit (Largest supported key size)]: `

### 10.2 Contextual Help Command (`?`)

Typing `?` at any prompt displays an in-place explanation:
```text
=== About AES Modes ===
* CBC (Cipher Block Chaining): Each block is XORed with the previous
  ciphertext block before encryption. Requires a unique IV. Provides
  confidentiality (not integrity/authentication). Recommended default.
* ECB (Electronic Codebook): Each block is encrypted independently.
  Identical plaintext blocks produce identical ciphertext blocks, leaking
  data patterns. Use only for academic comparison.
```

---

## 11. Progress and Long Operations

Operations such as multi-file batch encryption, multi-iteration benchmarks (30 measured iterations $\times$ multiple payloads), and security avalanche analyses can take several seconds.

### 11.1 Zero-Dependency Progress Mechanisms

Without external packages (like `tqdm` or `rich`), clean progress indicators can be built using Python standard library:
1. **Batch Item Progress Counter:**
   ```text
   [04/25] (16%) Encrypting: report_q3.pdf ... OK (1.2 ms)
   [05/25] (20%) Encrypting: dataset_large.dat ... OK (45.8 ms)
   ```
2. **Deterministic Step Indicators:**
   ```text
   [1/3] Running warmup iterations (5 cycles) ................. Done
   [2/3] Executing measured benchmark (30 iterations) ......... Done
   [3/3] Compiling throughput and latency statistics ......... Done
   ```
3. **Status Line Updates:** Using standard `\r` (carriage return) and `sys.stdout.flush()` to update dynamic status lines cleanly in standard terminals.

---

## 12. Post-Operation Summaries

After an operation completes, the user needs immediate visual confirmation of the result and clear guidance on what to do next.

### 12.1 Structured Summary Card (Illustrative)

```text
============================================================
              OPERATION SUCCESSFUL: ENCRYPTION
============================================================
  Input File        : data/input/financial_records.csv (48,291 bytes) [Illustrative]
  Ciphertext Output : data/output/financial_records.csv.enc (48,304 bytes) [Illustrative: 48,291 bytes + 13 bytes PKCS#7 padding]
  Algorithm / Mode  : AES-256-CBC
  Key Location      : data/output/financial_records.csv.key
  IV Location       : data/output/financial_records.csv.iv
  Execution Time    : 14.2 ms
  Round-Trip Verify : [Illustrative -- verification behavior pending Selection]
============================================================

Next Actions:
  [1] Open output folder in File Explorer
  [2] Decrypt this file now (test workflow)
  [3] Return to Main Menu
Select action [1-3] (default: 3): 
```

*Note: The summary card above is an illustrative example of layout ergonomics, not a frozen UI specification. Whether round-trip verification is executed automatically, offered as an optional post-operation step, or omitted by default remains an open design decision deferred to the Selection phase.*

---

## 13. Key Handling UX

### 13.1 Key Safety vs. Usability

Key management is the most error-prone aspect of cryptographic CLI usage.

#### Key Findings & Safety Nuance
1. **The Hex Copy-Paste Hazard:** Forcing users to copy 64 hex characters results in missing characters, leading/trailing whitespace, and lost keys.
2. **Automated Sidecar Files:** Writing keys to `<filename>.key` by default enables one-click decryption while keeping the key location explicit.
3. **Candidate Key-Safety Warning UX:** Plaintext key persistence on disk has notable security implications. In a testing lab context, saving keys as sidecar files provides usability, but risks leaving unencrypted keys in the workspace. As a candidate UX treatment, displaying a clear educational notice upon key save is proposed:
   ```text
   [!] Lab Security Notice: The encryption key has been saved as a plaintext
       sidecar file (.key) for laboratory and testing convenience. In production
       environments, cryptographic keys must be stored in secure key vaults.
   ```
   *The exact V2 key-storage policy, sidecar behavior, and warning wording are subject to the Selection phase and dedicated research in **Report B (Key Management)**.*
4. **Key Verification on Load:** When loading a `.key` file, immediately inspect the byte length and validate hex encoding, providing specific error advice before executing decryption.

---

## 14. File Selection UX on Windows

### 14.1 CLI File Selection Strategies

While graphical file dialogs (such as `tkinter.filedialog`) are available on Windows, V2 is intended to remain a terminal-first application. GUI popups introduce window-management complexity, focus-stealing behavior, and create a disjoint interaction model from the rest of the CLI. A terminal-native file selection approach keeps the application simple, cohesive, and fully aligned with its CLI environment.

#### Approach A: Direct Path Input with Smart Cleaning
* User enters or pastes a path.
* **Smart Cleaning:** Automatically strip surrounding quotation marks (`"C:\path\file.txt"` $\to$ `C:\path\file.txt`), trim whitespace, and resolve relative paths.

#### Approach B: Directory Enumeration Picker
* When prompted for input, the wizard scans a default directory (e.g., `data/input/`) and lists available files:
  ```text
  Available files in 'data/input/':
    [1] sample.txt (1,024 bytes)
    [2] image_sample.bmp (196,662 bytes)
    [3] secret_notes.pdf (45,120 bytes)
    [c] Enter custom path
  Select file [1-3 or 'c']: 
  ```

#### Evaluation
Combining **Directory Enumeration** for standard folders with **Smart Direct Path Entry** provides optimal usability for both novices and power users.

---

## 15. Menu Information Architecture

### 15.1 Architectural Models Compared

#### Model 1: Flat Menu (10+ items)
* *Structure:* Single list containing all commands, batch tools, and utilities.
* *Pros:* Everything visible in one screen.
* *Cons:* Severe visual clutter, intimidating for beginners.

#### Model 2: Task-Oriented Hierarchical Menu (Candidate)
* *Structure:* 5 core categories + Help + Exit.
  ```text
  1. Single-File Operations (Encrypt, Decrypt, Verify)
  2. Batch Operations (Folder Encrypt, Folder Decrypt)
  3. Performance & Benchmark Suite (Quick Test, Custom Suite)
  4. Security & Cryptanalysis Lab (Avalanche, ECB Leakage Demo)
  5. Key & Report Utilities (Key Tools, View HTML Reports)
  6. Help & Documentation
  7. Exit
  ```
* *Pros:* Clear categorization, scalable, low cognitive load.
* *Cons:* Requires 1 extra keystroke to enter sub-categories.

---

## 16. Beginner vs. Advanced User Experience

### 16.1 Progressive Disclosure

Progressive disclosure presents only the necessary information for basic completion, while making advanced parameters accessible on demand.

```text
+-------------------------------------------------------------+
| Standard Workflow (Beginner / Default):                     |
| Select File ---> [Use Recommended AES-256-CBC] ---> Encrypt |
+------------------------------+------------------------------+
                               | Optional: "Customize Settings"
                               v
+-------------------------------------------------------------+
| Advanced Parameter Tweaks:                                  |
| * Custom Key Size (128/192/256)                             |
| * Custom Cipher Mode (ECB/CBC)                              |
| * Manual Hex Key / Custom IV Input                          |
| * Custom Output File Naming & Directories                   |
+-------------------------------------------------------------+
```

---

## 17. Interactive CLI Testing Strategies

Testing interactive terminal applications requires deterministic, isolated automation.

### 17.1 Pytest Simulation Patterns

#### 1. Input Stream Injection (`monkeypatch`)
* Simulate multi-step user interaction by passing an iterator of strings to `builtins.input`:
  ```python
  inputs = iter(["1", "sample.txt", "1", "y", "b", "5"])
  monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
  ```

#### 2. Navigation State Verification
* Test `back` navigation by verifying that moving back from Step 3 to Step 2 retains Step 1 parameters and allows updating Step 2 without state corruption.

#### 3. Output Capture (`capsys`)
* Assert on presence of visual cards, progress indicators, and error explanations without coupling tests to exact whitespace formatting.

#### 4. Filesystem Isolation (`tmp_path`)
* Run all file creation, sidecar generation, and batch tests within pytest's temporary directories.

---

## 18. Terminal Accessibility and Robustness

1. **No Color-Only Information:** Never rely solely on ANSI color codes (red/green) to communicate success or failure; always include textual status markers (`[SUCCESS]`, `[FAILED]`, `[!]`).
2. **ASCII Baseline for Reliable Rendering:** ASCII should serve as the safe baseline for all interactive prompts, menus, and status messages. Unicode decoration (such as box-drawing borders or special glyphs) should not be assumed to render identically across every Windows terminal environment (e.g., legacy `cmd.exe` code pages vs. Windows Terminal UTF-8). Fancy Unicode spinners or borders must not be required for correct operation; if Unicode is used, it should be treated as an optional visual enhancement subject to environment and encoding support.
3. **Graceful Interruption & Signal Handling:**
   * **Windows Console:** `Ctrl+C` raises `KeyboardInterrupt`, which must be caught cleanly to abort operations and clean up any transient locks or temp files with an `"Operation cancelled."` message. Note that `Ctrl+Z` in Windows terminal input triggers console EOF semantics on an enter key, which behaves differently from Unix `Ctrl+D` and should be handled gracefully via input stream checks without crashing.
   * **Unix-like Environments:** `Ctrl+C` raises `KeyboardInterrupt`, while `Ctrl+D` signals end-of-file (which standard Python `input()` surfaces as `EOFError`), which should cleanly return to the menu or exit without traceback dumps.

---

## 19. Windows-Specific Considerations

1. **Drag-and-Drop Path Pasting:** In Windows Terminal / CMD, dragging a file into the terminal inserts the path wrapped in double quotes (and occasionally with trailing spaces). Path prompts must strip these quotes automatically.
2. **Launching Windows Explorer:**
   ```python
   import os, subprocess, sys
   if sys.platform == "win32":
       os.startfile(output_directory)
   ```
3. **Launching Default Web Browser for HTML Reports:**
   ```python
   import webbrowser
   webbrowser.open(report_html_path.as_uri())
   ```
4. **Path Separators:** Always normalize via `pathlib.Path` to avoid backslash escaping issues.

---

## 20. Approaches Compared

| Criteria | Approach 1: Thin Script Over V1 Menu | Approach 2: Stateful Guided Wizard Engine (Promising Candidate) | Approach 3: Command-Line Flag Builder (Educational Candidate) |
| :--- | :--- | :--- | :--- |
| **Concept** | Minor cosmetic tweaks to `src/cli/menu.py` | Dedicated modular V2 UX layer with step stack, validation, and summaries | Interactive assistant that builds and prints a V1 CLI command string |
| **Usability** | Low -- still linear, no back navigation, no file picker | High -- full back/cancel navigation, auto-sidecars, clear summaries | Medium -- user still has to copy/run CLI flags |
| **V1 Protection** | Risk of touching frozen V1 files | Clean separation: additive V2 modules consuming V1 services | Clean separation: generates text command strings |
| **Error Recovery**| Returns to top menu on any error | In-place retry, step retention, contextual suggestions | Returns generated string |
| **Educational Value**| Low | High (contextual tooltips, clear summaries) | High (teaches exact CLI flag syntax to students) |
| **Suitability for Non-Technical Users**| Low | High | Moderate (requires executing generated CLI command) |

### Note on Architecture Selection
* **Approach 2** is an attractive and promising candidate because it directly addresses the core usability friction points of V1 through step navigation, `Back`, `Cancel`, and automated persistence.
* **Approach 3** holds distinct educational value by demonstrating how guided inputs map to underlying CLI flags, which can help students learn the V1 command interface.
* **Final Selection:** Final selection between stateful, stateless, or hybrid interaction architecture is deferred to the **Project-Specific Selection phase**.

---

## 21. Project-Specific Recommendations

The following recommendations represent research findings and candidate proposals to guide the eventual V2 Selection phase. **They are not frozen decisions.**

### RECOMMENDATION A-01: Task-Centric Hierarchical Menu Structure
* **Topic:** Menu Information Architecture
* **Finding:** A flat list of 10+ options creates decision fatigue; grouping into 5–6 logical clusters aligns with human cognitive constraints.
* **Recommendation:** Organize the V2 main menu into clear task categories: Single-File Operations, Batch Operations, Benchmarks & Analysis, Key Utilities, Help, and Exit.
* **Reason:** Allows clean expansion of batch and reporting features without crowding basic file encryption.
* **Trade-offs:** Adds one intermediate selection step for nested actions.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-02: Universal Step Navigation (`Back` and `Cancel`)
* **Topic:** Workflow Navigation
* **Finding:** Linear input prompts force users to abort the entire process on simple typos.
* **Recommendation:** Support `b` (`back`) to return to the previous prompt and `c` (`cancel`) to return to the main menu at every wizard step.
* **Reason:** Drastically improves user confidence and eliminates the friction of restarting workflows.
* **Trade-offs:** Requires wizards to maintain a step history stack.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-03: Safe Defaults with Explicit Visibility
* **Topic:** Cryptographic Defaults
* **Finding:** Hiding defaults causes uncertainty; requiring all technical flags causes fatigue.
* **Recommendation:** Default to AES-256 and CBC mode for file encryption, but explicitly display these settings and allow one-key confirmation or customization.
* **Reason:** Ensures cryptographic confidentiality while keeping workflows swift.
* **Trade-offs:** Advanced users must select "Customize" to change key sizes.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-04: Hybrid File Selection (Enumeration + Smart Path)
* **Topic:** File Selection UX
* **Finding:** Typing raw Windows paths is error-prone; GUI pickers introduce unwanted OS dependencies.
* **Recommendation:** Present a numbered list of available files in `data/input/`, while providing a prompt option to paste or type a custom path (with automatic quote-stripping).
* **Reason:** Provides one-click convenience for standard samples while supporting arbitrary files.
* **Trade-offs:** Directory scanning must handle empty folders gracefully.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-05: Automated Sidecar Key Management
* **Topic:** Key Persistence UX
* **Finding:** Manual hex copying is the primary cause of lost keys and failed decryptions.
* **Recommendation:** Propose prompting to save generated keys to `<filename>.key` sidecar files, accompanied by an educational notice regarding plaintext key storage in lab environments.
* **Reason:** Enables seamless, reliable decryption while teaching key management principles.
* **Trade-offs:** Creates additional files on disk that users must manage.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-06: Automatic Round-Trip Decryption Verification
* **Topic:** Data Integrity Verification
* **Finding:** Users lack immediate confidence that an encrypted file can be restored correctly.
* **Recommendation:** Propose an in-memory round-trip verification step after encryption that validates the ciphertext decrypts back to the exact plaintext.
* **Reason:** Instills total user confidence before the user closes the session or deletes original files.
* **Trade-offs:** Adds an additional decryption/read operation and therefore increases execution time and I/O; the practical impact depends on file size.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-07: Structured Post-Operation Summary Cards
* **Topic:** Operation Feedback
* **Finding:** V1 outputs raw hex or minimal "Saved" lines, leaving users unsure of execution details.
* **Recommendation:** Render a clean visual summary card displaying input/output paths, sizes, algorithm, key location, and execution time, followed by contextual next actions (e.g., Open in Explorer).
* **Reason:** Delivers a polished, informative desktop application experience.
* **Trade-offs:** Slightly higher terminal line output per operation.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-08: Three-Tier Actionable Error Diagnostics
* **Topic:** Error Communication
* **Finding:** Raw exception strings (e.g., "Padding is invalid") confuse non-specialists.
* **Recommendation:** Format errors with: 1. What failed, 2. Probable cryptographic/system cause, 3. Concrete resolution steps, while preserving a verbose debug flag.
* **Reason:** Transforms errors into learning opportunities and reduces user frustration.
* **Trade-offs:** Requires maintaining a mapping of common cryptographic failure modes.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-09: Contextual In-App Help & Micro-Tooltips
* **Topic:** Educational Aids
* **Finding:** Users often do not know the practical difference between ECB and CBC.
* **Recommendation:** Include 1-line guidance directly in selection prompts and support a `?` query token at any prompt to display detailed explanations.
* **Reason:** Bridges the gap between academic theory and practical tool usage.
* **Trade-offs:** Must be kept concise to avoid terminal clutter.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-10: Native OS Integration (Explorer & Browser Launchers)
* **Topic:** Workflow Completion
* **Finding:** Users have to manually browse Windows Explorer or open web browsers to locate output files and HTML reports.
* **Recommendation:** Offer post-operation actions to launch the output directory via `os.startfile` and open generated HTML reports via `webbrowser.open`.
* **Reason:** Dramatically streamlines evaluation and report inspection workflows on Windows.
* **Trade-offs:** Must include fallback handling for headless or non-GUI environments.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-11: Zero-Dependency Progress Feedback for Long Operations
* **Topic:** Progress Feedback
* **Finding:** Benchmarks and batch operations appear frozen when executing without console updates.
* **Recommendation:** Use standard library carriage-return updates (`\r`) and item counters (`[N/Total]`) for batch operations and benchmarks without adding external progress-bar libraries.
* **Reason:** Maintains strict zero-dependency policy while keeping the UI responsive.
* **Trade-offs:** Slightly simpler visual appearance compared to third-party rich UI libraries.
* **Decision status:** `NOT YET FROZEN`

### RECOMMENDATION A-12: Decoupled Interactive Testing Architecture
* **Topic:** Testability
* **Finding:** Testing stateful interactive CLI loops can be brittle if coupled directly to terminal I/O.
* **Recommendation:** Structure wizard controllers to accept injectable input/output streams, allowing comprehensive pytest test suites using standard `monkeypatch` and `capsys`.
* **Reason:**Supports deterministic and comprehensive testing of defined navigation paths, errors, and retries.
* **Trade-offs:** Requires clean separation between presentation logic and terminal stream I/O.
* **Decision status:** `NOT YET FROZEN`

---

## 22. Open Decisions for V2 Selection

The following architectural and design questions remain open and must be formally resolved in the **V2 Selection Document**:

1. **Menu Depth vs. Dynamic Modes:** Should V2 use a standard 2-level hierarchy, or an interactive Beginner/Advanced mode toggle?
2. **Round-Trip Verification Policy:** Should post-encryption verification be mandatory/automatic or an optional user prompt?
3. **Key Sidecar File Extension & Naming:** Should sidecar files strictly follow `<filename>.key` / `<filename>.iv` or allow custom sidecar naming schemes?
4. **Direct Command Invocation in V2:** Whether V2 should expose direct CLI invocation (e.g., `python -m src.cli_v2.main_v2 encrypt ...`) alongside the guided menu, or focus exclusively on the guided menu with scriptable execution handled by V1. The exact invocation strategy and subcommands must be confirmed during Selection.
5. **Output Directory Auto-Creation:** Should missing destination directories be created silently or require user confirmation?
6. **Overwrite Confirmation Granularity:** In batch operations, should overwrite confirmation be asked once globally (All/None/Prompt) or per-file?

---

## 23. Explicitly Deferred Decisions

To maintain research scope boundaries:
* **Detailed Key Management Architecture:** File formats, checksums, and key validation routines are deferred to **Phase 1 Research Report B (Key Management)**.
* **Batch Scheduling & Concurrency Architecture:** Folder scanning algorithms, failure logging structures, and batch error isolation are deferred to **Phase 1 Research Report C (Batch Operations)**.
* **HTML Report Layout & Styling Technology:** CSS frameworks, graph embedding methods, and HTML generation engines are deferred to **Phase 1 Research Report D (Reporting)**.
* **Module & Class Design:** Final Python module structures and class signatures are deferred to **Phase 3 (Selection)**.

---

## 24. Risks and Trade-offs

| Risk Area | Potential Failure Mode | Proposed Mitigation Strategy |
| :--- | :--- | :--- |
| **Terminal Compatibility** | Unicode borders or control sequences failing in legacy `cmd.exe` | Use standard ASCII fallbacks and test across Windows Terminal, CMD, and PowerShell. |
| **State Complexity** | Complex navigation stacks causing state corruption on multiple `Back` actions | Keep wizard step state immutable per step; pop step state cleanly on `Back`. |
| **False Sense of Security** | Users assuming `.key` files on disk are production-grade safe | Prominently display laboratory educational security warnings on every key save. |
| **Input Deadlocks** | Infinite validation loops on automated or piped input | Implement max retry bounds (e.g., 3 retries) with graceful fallback to main menu on repeated invalid input. |
| **V1 Regression** | Accidental coupling with V1 internal CLI code | Build V2 as a standalone package (`src/cli_v2/`) importing only frozen V1 Services (`src.engines`). |

---

## 25. Conclusion

This research demonstrates that transitioning the Cryptography Testing Lab to an intuitive, guided user experience is entirely feasible **while preserving V1 with zero changes** and **without introducing any external dependencies**.

By evaluating:
* A task-centric hierarchical menu,
* A stateful wizard workflow with universal `Back` and `Cancel` capabilities,
* Safe defaults with transparent visibility,
* Intelligent hybrid file selection,
* Automated sidecar key management with educational safety notices, and
* Clear, actionable error diagnostics,

V2 can empower students, educators, and evaluators to perform sophisticated cryptographic testing with high confidence and minimal cognitive friction. Final architecture and policy choices will be determined in the subsequent Selection phase.

---

## 26. Sources & Evidence

### Project Repository Evidence
* `src/cli/main.py` — V1 dispatch logic, argument handling, and exception mapping.
* `src/cli/menu.py` — V1 linear menu structure and prompt helpers.
* `src/cli/argument_parser.py` — V1 CLI flag definitions, constraints, and persistence validation.
* `src/cli/commands.py` — V1 service orchestration, file handling, and terminal formatting.
* `tests/cli/test_menu.py` — Existing pytest monkeypatch patterns for terminal menu testing.
* `docs/v2/V2_INTENT.md` — Authoritative V2 scope, requirements, and frozen boundaries.

### External Research & Technical Standards
* **Python Standard Library Documentation:** `argparse`, `pathlib`, `getpass`, `webbrowser`, `os`, `shutil` (Python 3.10+).
* **Nielsen Norman Group:** *Command-Line Interface Usability* & *10 Usability Heuristics for User Interface Design* (Error Prevention, Recognition rather than Recall, Visibility of System Status).
* **POSIX & GNU CLI Standards:** Standard input parsing, exit codes, and signal handling conventions.
* **Modern CLI Tool Patterns:** Interactive wizard and prompt designs in `gh` (GitHub CLI), `npm init`, and `aws configure`.
* **Pytest Documentation:** Standard fixtures (`monkeypatch`, `capsys`, `tmp_path`) for isolated interactive CLI testing.

---

*End of RESEARCH_A_MENU_UX.md*

