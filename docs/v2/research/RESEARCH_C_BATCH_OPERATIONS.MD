# V2 RESEARCH C — BATCH OPERATIONS

**Document ID:** V2-RESEARCH-C  
**Status:**  DRAFT / CORRECTED — READY FOR INDEPENDENT VERIFICATION 
**Date:** 2026-09-15  
**Author:** V2 Batch Operations Research Lead  
**Scope Focus:** Category C (Batch Operations) & Directory-Level Cryptographic Processing  
**Target Milestone:** V2 Phase 1 (Research)  
**Authoritative References:** [V2_INTENT.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md) | [RESEARCH_A_MENU_UX.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_A_MENU_UX.md) | [RESEARCH_B_KEY_MANAGEMENT.MD](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_B_KEY_MANAGEMENT.MD)

---

> [!NOTE]
> **Research Scope Note:** Candidate workflows, policies, architecture options, and recommendations in this report are research findings and candidate approaches only. They are NOT frozen V2 decisions and may be changed, refined, or rejected during the V2 Project-Specific Selection phase. This report must not silently establish implementation requirements.

---

## 1. Research Objective

This research report investigates the architectural, operational, cryptographic, filesystem, and user-experience aspects of **Category C: Batch Operations** for the V2 usability layer of the Cryptography Testing Lab.

The central research objective is to resolve:

> **How should V2 orchestrate multi-file folder encryption, folder decryption, per-file result accounting, resilient error logging, sidecar coupling, and cancellation/progress UX across Windows and POSIX filesystems — while strictly preserving the frozen V1 single-buffer single-file core, maintaining zero new runtime dependencies, and ensuring compatibility with verified V1 artifact and interface conventions?**

In V1, cryptographic operations are strictly single-file: `python -m src.cli.main encrypt --input-file <path> --output-file <path> ...` accepts one input payload and produces one ciphertext output. Encrypting or decrypting an entire directory of test data, sample artifacts, or benchmark suites currently requires external scripting (e.g., PowerShell loops or Bash scripts) or repetitive CLI invocations.

This report establishes the technical foundation for candidate batch processing in V2, exploring:
1. Directory discovery, lexical sorting, and candidate filtering.
2. Error isolation models (ensuring that an unreadable, locked, or corrupt file does not abort an entire batch job).
3. Structured per-file result accounting and persistent batch execution logging.
4. Coordination with V1-established IV sidecars (`.iv`) and V2 candidate key sidecars (`.key`).
5. Safe filesystem policies, Windows path realities, and cancellation ergonomics.

---

## 2. V2 Category C Scope (C1–C4)

As defined in the authoritative [V2_INTENT.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md) (§5.3), Category C introduces four baseline batch capabilities:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CATEGORY C: BATCH SCOPE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  [C1] Batch Folder Encryption                                               │
│       • Encrypt all matching files within an input directory                │
│       • Write ciphertexts to a designated output directory                  │
│       • Generate corresponding .iv sidecars (and candidate .key sidecars)   │
├─────────────────────────────────────────────────────────────────────────────┤
│  [C2] Batch Folder Decryption                                               │
│       • Decrypt all matching ciphertext files within an input directory     │
│       • Locate and utilize matching sidecars (.iv, .key) or shared key      │
│       • Restore decrypted plaintexts to a designated output directory       │
├─────────────────────────────────────────────────────────────────────────────┤
│  [C3] Per-File Result Accounting & Progress                                 │
│       • Real-time console progress indicator ([x/N], filename, status)      │
│       • Structured in-memory tracking of success, failure, and skip states  │
│       • Clean tabular summary card upon batch completion                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  [C4] Resilient Error Logging & Fault Isolation                             │
│       • Isolate per-file runtime exceptions (PermissionError, corrupt data) │
│       • Continue batch iteration across remaining candidate files           │
│       • Write structured batch execution log (CSV / text)                   │
│       • Candidate policy prohibiting logging raw key material in log files  │
└─────────────────────────────────────────────────────────────────────────────┘
```

> [!NOTE]
> Supporting workflows discussed in this report (such as dry-run preview, console rate-throttling, interactive wizards, and cancellation cleanup) represent **supporting workflow considerations** for Category C, rather than additions to the frozen A+B+C+D scope defined in [V2_INTENT.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md).

---

## 3. V1 Context and Repository Evidence

### 3.1 V1 Single-File Architectural Invariants

An audit of the frozen V1 codebase establishes the exact interfaces and behaviors that constrain batch orchestration:

1. **`src/engines/cipher_service.py` ([`CipherService`](file:///C:/Users/kodal/Cryptography_Project/src/engines/cipher_service.py#L9-L34)):**
   * [`encrypt_data()`](file:///C:/Users/kodal/Cryptography_Project/src/engines/cipher_service.py#L13-L26) accepts `(algorithm, key_size, mode, plaintext, key, iv=None)` and returns an [`EncryptionResult`](file:///C:/Users/kodal/Cryptography_Project/src/engines/cipher_service.py#L4-L7) dataclass containing `ciphertext: bytes` and `iv: bytes | None`.
   * [`decrypt_data()`](file:///C:/Users/kodal/Cryptography_Project/src/engines/cipher_service.py#L28-L33) accepts `(algorithm, key_size, mode, ciphertext, key, iv=None)` and returns `plaintext: bytes`.
   * Operates purely in memory on byte buffers; contains no filesystem logic, directory traversal, or batch loop state.
2. **`src/cli/commands.py` ([`run_encrypt`](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L370-L406), [`run_decrypt`](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L407-L441)):**
   * `run_encrypt`: Reads input bytes via `FileHandler.read_bytes()`, delegates to `CipherService`, writes ciphertext via `FileHandler.write_bytes()`, and conditionally creates `<output_file>.iv` (containing 32 hex characters plus `\n`) if mode is `CBC` ([lines 402–404](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L402-L404)).
   * `run_decrypt`: Reads ciphertext bytes, reads `<input_file>.iv` text if mode is `CBC` ([lines 419–420](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L419-L420)), invokes `CipherService.decrypt_data()`, and writes plaintext via `FileHandler.write_bytes()`.
   * Overwrite check: `_check_overwrite(path, force)` calls `FileHandler.exists(path)` and raises `FileExistsError(f"Output file already exists: {path}")` if `--force` is false ([lines 86–90](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L86-L90)).
3. **`src/utils/file_handler.py` ([`FileHandler`](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L13-L105)):**
   * Static filesystem utility methods: `read_bytes` ([L21](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L21)), `write_bytes` ([L25](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L25)), `read_text` ([L37](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L37)), `write_text` ([L41](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L41)), `exists` ([L92](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L92)), `get_file_size` ([L96](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L96)), `ensure_directory` ([L101](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L101)).
   * `write_bytes()` and `write_text()` automatically call `p.parent.mkdir(parents=True, exist_ok=True)`.
4. **`src/cli/main.py` ([`main()`](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L43-L78)):**
   * Traps top-level exceptions and exits with `EXIT_RUNTIME = 1` or `EXIT_SUCCESS = 0`:
     * `KeyboardInterrupt` -> prints `"Cancelled"`, returns `EXIT_SUCCESS (0)` ([lines 58–60](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L58-L60)).
     * `FileExistsError` -> prints `f"Error: {exc}"`, returns `EXIT_RUNTIME (1)` ([lines 61–63](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L61-L63)).
     * `OSError` -> prints `f"Error: {exc}"`, returns `EXIT_RUNTIME (1)` ([lines 64–66](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L64-L66)).
     * `(ValueError, TypeError, KeyError)` -> prints `f"Error: {exc}"`, returns `EXIT_RUNTIME (1)` ([lines 67–69](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L67-L69)).

### 3.2 Key Forensic Takeaway for Batch Design

V1's core engine is synchronous and stateless. Batch processing in V2 does not require modifying `CipherService`, `AESCipher`, or `FileHandler`. Instead, V2 batch operations can be implemented as a higher-level presentation and orchestration controller that iterates across candidate files, delegates single-file operations to the verified V1 service pipeline, and traps exceptions at the file boundary.

---

## 4. Research Methodology

The research in this report is based on:
1. **Codebase Inspection:** Audited V1 command handlers, exception mapping in `src/cli/main.py`, and persistence helpers in `src/utils/file_handler.py`.
2. **API & Standard Library Analysis:** Evaluated Python standard library modules (`pathlib`, `os`, `os.replace`, `fnmatch`, `csv`, `time`) under Python 3.10+ on Windows and POSIX.
3. **Cross-Platform Filesystem & Path Analysis:** Analyzed path normalization, Windows MAX_PATH configuration dependencies, NTFS case preservation, reserved DOS device names, file locking, and directory reparse points / junctions.
4. **Security & Cryptographic Review:** Evaluated key distribution blast radiuses, sidecar coupling, and memory protection boundaries in coordination with [RESEARCH_B_KEY_MANAGEMENT.MD](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_B_KEY_MANAGEMENT.MD).
5. **Industry Practice Comparison:** Analyzed operational patterns from CLI tools including Robocopy, rsync, 7-Zip, and rclone.
6. **Failure-Mode & Recovery Analysis:** Constructed a structured matrix of non-fatal per-file failures versus fatal infrastructure abort conditions.

---

## 5. Directory Traversal Findings

### 5.1 Traversal Mechanisms Evaluated

| Mechanism | Traversal Scope | Return Type | Memory Characteristics | Traversal Order | Portability Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pathlib.Path.iterdir()` | Flat (single level) | Generator (`Path`) | Minimal per-entry overhead | Native filesystem order | Standard library; fully portable |
| `pathlib.Path.glob("*")` | Pattern-based flat | Generator (`Path`) | Minimal per-entry overhead | Native filesystem order | Standard library; fully portable |
| `pathlib.Path.rglob("*")`| Recursive subtree | Generator (`Path`) | Minimal per-entry overhead | Native filesystem order | Standard library; fully portable |
| `os.walk()` | Recursive subtree | Tuple generator | Stack depth proportional to tree depth | Native filesystem order | Standard library; fully portable |
| `os.scandir()` | Flat / Entry-based | Iterator (`DirEntry`) | Minimal; caches `stat` metadata | Native filesystem order | Faster entry metadata on POSIX/Win32 |

### 5.2 Flat vs. Recursive Traversal

* **Flat Traversal (`iterdir()` / `glob("*")`):** Scans only immediate children of the specified input folder. Subdirectories are ignored or skipped.
  * *Advantages:* Simple mapping to output directory; avoids unexpected deep traversal of large hierarchies.
  * *Trade-offs:* Cannot process subfolders in a single command pass.
* **Recursive Traversal (`rglob("*")` / `os.walk()`):** Scans the complete directory subtree.
  * *Advantages:* Enables processing entire nested directory hierarchies.
  * *Trade-offs:* Requires subtree mirroring in the output folder to prevent naming collisions (e.g., `input/a.txt` and `input/sub/a.txt`); introduces risks of deep traversal or cycle loops if directory junctions/symlinks are present.
* *Research Assessment:* Flat traversal appears suitable as the baseline default, with recursive subtree processing remaining an open choice for Selection.

### 5.3 Candidate Materialization and Progress Denominator

To display an accurate progress counter (e.g., `[05/42] (12%) Encrypting: data.txt...`), the total count $N$ of eligible candidate files must be known upfront:
* Streaming a generator without materialization does not provide $N$ unless a pre-scan pass is executed.
* Materializing the candidate list via `candidate_files = sorted([p for p in target_dir.iterdir() if p.is_file()])` is straightforward and consumes minimal memory for typical laboratory workloads.
* *Research Assessment:* Upfront candidate materialization and sorting is recommended for consideration during Selection.

---

## 6. File Filtering Findings

### 6.1 Pattern and Extension Matching

Batch processing requires flexible file selection while maintaining predictable operation:
1. **Glob / Wildcard Matching:** Supporting standard glob patterns (e.g., `*.txt`, `*.dat`, `sample_*.bin`) allows selective batch operations.
2. **Case Sensitivity on Windows vs. POSIX:**
   * On Windows NTFS, file matching is case-insensitive (e.g., `*.TXT` matches `document.txt`).
   * On Linux/macOS, matching is case-sensitive by default.
   * `pathlib.Path.match()` and `fnmatch` behavior across platforms should be accounted for during Selection.
3. **Empty File Handling (0 Bytes):**
   * In V1 AES-CBC and AES-ECB, an empty file (0 bytes) is mathematically valid under PKCS#7 padding (0 bytes is padded to a 16-byte block of `\x10`).
   * Batch operations can process 0-byte files using the verified V1 cipher pipeline without special-casing.

---

## 7. Exclusion Rules and Directory Overlap

### 7.1 Candidate Exclusion Matrix

To prevent workflow disruption, accidental re-encryption, or processing of non-data files, candidate exclusion patterns include:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CANDIDATE EXCLUSION MATRIX                            │
├───────────────────┬─────────────────────────────────────────────────────────┤
│ Target Pattern    │ Rationale / Purpose                                     │
├───────────────────┼─────────────────────────────────────────────────────────┤
│ *.enc             │ Prevents double-encrypting existing ciphertexts         │
│ *.key             │ Prevents encrypting candidate plaintext key sidecars    │
│ *.iv              │ Prevents encrypting V1 IV sidecars                      │
│ *.tmp / *.part    │ Prevents processing partially written temporary files   │
│ batch_log_*.csv   │ Prevents encrypting batch execution logs                │
│ Hidden files (.*) │ Platform-dependent (dotfiles on Unix, attributes on Win)│
│ Thumbs.db         │ Windows thumbnail cache metadata                        │
│ .DS_Store         │ macOS directory metadata                                │
└───────────────────┴─────────────────────────────────────────────────────────┘
```

> [!NOTE]
> Specific exclusion defaults (such as whether hidden files or specific extensions are skipped automatically or configurable via CLI flags) remain an **Open Decision** for the Selection phase.

### 7.2 Directory Overlap and Cycle Mitigation

If a user specifies an output directory that is identical to, or nested inside, the input directory (e.g., `input_dir = ./data`, `output_dir = ./data/encrypted`):
* Writing new files to `output_dir` during traversal could alter directory contents if traversed dynamically.
* *Candidate Mitigations:*
  1. Materializing the candidate list prior to starting iteration fixes the candidate snapshot.
  2. Resolving absolute paths (`Path(input_dir).resolve()` and `Path(output_dir).resolve()`) allows detecting whether `output_dir` is inside `input_dir` and skipping `output_dir` during recursive discovery.

---

## 8. Batch Key Strategy

The research evaluated three candidate key distribution models for batch encryption:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                     BATCH KEY STRATEGIES EVALUATED                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Option A: Single Shared Key for Entire Batch                               │
│  • User provides or generates one key applied to all files in the batch.    │
│  • Trade-offs: Generates fewer key sidecars; broader security blast radius │
│    if key is compromised; CBC mode still utilizes unique per-file IVs.       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Option B: Unique Random Key Per File (1:1 Sidecars)                        │
│  • Core factory generates a fresh random key for every individual file.     │
│  • Saves <filename>.enc.key for each ciphertext.                            │
│  • Trade-offs: Minimal blast radius per file; decouples individual files     │
│    for standalone decryption; creates N .key sidecar files in output dir.   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Option C: User Selectable (Wizard / CLI Option)                            │
│  • Allows user to select between unique per-file keys or a shared batch key.│
│  • Trade-offs: Provides flexibility for educational and testing workflows;   │
│    requires user input or CLI flag selection.                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.1 Cryptographic Safety and Blast Radius Analysis

* For confidentiality, reuse of an AES key across files can be acceptable when each encryption uses a fresh, unpredictable IV. Because V1's `CipherService.encrypt_data()` generates a fresh 16-byte IV via `cipher.generate_iv()` on every call ([L22](file:///C:/Users/kodal/Cryptography_Project/src/engines/cipher_service.py#L22)), Option A avoids predictable IV-reuse vulnerabilities across files. Note that AES-CBC does not itself provide authentication or integrity.
* Option B isolates each file with its own cryptographic key, ensuring that exposure of one key sidecar does not compromise other batch ciphertexts.
* *Research Assessment:* Option C (user selectable with a recommended default) appears suitable for consideration during Selection.

---

## 9. Key and IV Sidecar Interaction

### 9.1 Distinguishing V1-Established vs. V2 Candidate Sidecars

* **V1-Established Convention:** `<output_file>.iv` is a verified V1 mechanism created during CBC encryption ([`commands.py` L402–404](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L402-L404)) containing 32 hex characters plus `\n`.
* **V2 Candidate Convention:** `<output_file>.key` is a candidate sidecar convention researched in [RESEARCH_B_KEY_MANAGEMENT.MD](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_B_KEY_MANAGEMENT.MD) (§5, §11). It is **not** an existing V1 feature.

### 9.2 Candidate Sidecar Resolution Model for Selection

When performing candidate batch decryption, the researched candidate resolution order is:
1. Traversal identifies candidate ciphertext files (e.g., `*.enc`).
2. For each ciphertext `target.enc`:
   * **IV Resolution:** For CBC mode, locate `target.enc.iv`. If missing, check `target.iv`. If no IV sidecar exists and no explicit `--iv` is provided, record file failure and proceed.
   * **Key Resolution:** If a batch key is provided via CLI/prompt, use it; otherwise, locate `target.enc.key` (or `target.key`). If no key is found, record file failure and proceed.
3. Plaintext output target: `output_dir/target` (or stripping `.enc`).

*Selection Note:* The specific fallback sequence and prompting behavior remain subject to **Decision C-OPEN-05 (Sidecar Decryption Resolution)** during the Selection phase.

### 9.3 Security Notice Consolidation

In single-file V2 mode, generating an unencrypted key sidecar displays a Laboratory Security Notice box. Displaying this box repeatedly for every file in a 100-file batch would flood the terminal and obscure progress output.
* *Candidate Approach:* Suppress per-file notices during the batch loop and emit a single consolidated Laboratory Security Notice in the final batch summary.

---

## 10. Output Directory Handling

### 10.1 Output Structure Options

```text
Flat Input Directory:                     Mirrored Subtree (Candidate Recursive):
data/input/                               data/input/
├── report.txt                            ├── report.txt
├── memo.docx                             └── 2026/
                                              └── q1.xlsx
Flat Output:                              Mirrored Output:
data/output/                              data/output/
├── report.txt.enc                        ├── report.txt.enc
├── report.txt.enc.iv                     └── 2026/
├── report.txt.enc.key                        ├── q1.xlsx.enc
├── memo.docx.enc                             ├── q1.xlsx.enc.iv
├── memo.docx.enc.iv                          └── q1.xlsx.enc.key
└── memo.docx.enc.key
```

### 10.2 Directory Creation and Collision Handling

* A candidate batch implementation can reuse V1's `FileHandler.ensure_directory()` behavior to ensure output directories exist before writing ([`FileHandler` L101](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L101)).
* If duplicate basenames occur (e.g., in recursive traversal flattened to a single output folder), collision handling is governed by the overwrite policy.

---

## 11. Overwrite Policy for Batch Operations

| Overwrite Policy | Behavior on Destination Collision | Operational Impact | Resumption / Retry Characteristic | Selection Status |
| :--- | :--- | :--- | :--- | :--- |
| **Abort-Immediate** | Terminate batch on first existing output | Disruptive; leaves batch partially complete | None (requires manual cleanup) | Candidate Option |
| **Interactive Prompt** | Prompt user per collision `(y/n/all)` | Halts unattended automated batch runs | Inconvenient for large batches | Candidate Option |
| **Force / Overwrite** | Overwrite existing destination files | Re-encrypts all files; risk of unintended data overwrite | Re-processes entire dataset | Candidate Flag (`--force`) |
| **Skip Existing** | Skip file, increment `skipped` tally, continue | Safe, non-destructive, unattended execution | Enables skipping already-processed files | **Strong Candidate for Default** |

### 11.1 Resumption and Idempotency Limitations

> [!IMPORTANT]
> The combination of a candidate "Skip Existing" policy with per-file atomic writes may provide a practical retry/resumption model, but it does not by itself establish transactional completion or full idempotency across multiple artifacts.
>
> An existing `.enc` file does not automatically prove that the previous run finished completely, that the ciphertext is uncorrupted, or that corresponding `.iv` and `.key` sidecars exist and are valid. Multi-artifact consistency validation remains a candidate topic for Selection.

---

## 12. Error Isolation (C4 Requirement)

### 12.1 Non-Fatal Per-File Errors vs. Fatal Infrastructure Errors

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BATCH EXCEPTION CLASSIFICATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  NON-FATAL PER-FILE ERRORS (Trap, Record, and Continue Next File)           │
│  • PermissionError / AccessDenied (individual file locked or unreadable)    │
│  • FileNotFoundError (file removed or renamed during batch execution)       │
│  • IsADirectoryError (encountered directory when expecting file)            │
│  • MissingSidecarError (missing .iv or .key during batch decryption)        │
│  • ValueError: Invalid padding bytes (corrupt ciphertext or wrong key)      │
│  • ValueError: Malformed hex in key or IV sidecar                           │
│  • OSError: Individual path exceeds MAX_PATH on unconfigured Windows system │
├─────────────────────────────────────────────────────────────────────────────┤
│  FATAL INFRASTRUCTURE ERRORS (Halt Batch Execution)                         │
│  • OSError: [Errno 28 / WinError 112] Disk full / No space left on device   │
│  • PermissionError: Output directory cannot be created or is not writable   │
│  • FileNotFoundError: Specified input directory does not exist              │
│  • MemoryError: System memory exhausted                                     │
│  • KeyboardInterrupt: User cancellation via SIGINT (Ctrl+C)                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Per-File Isolation Model (Conceptual Pseudocode)

```python
# Conceptual per-file isolation structure (illustrative only — not executable code)
for candidate_path in candidate_files:
    try:
        # Step 1: Read input bytes
        data = FileHandler.read_bytes(candidate_path)
        
        # Step 2: Acquire per-file Key / IV
        key_bytes, iv_bytes = resolve_credentials(candidate_path)
        
        # Step 3: Invoke frozen CipherService
        result = cipher_service.encrypt_data(
            algorithm, key_size, mode, data, key_bytes, iv_bytes
        )
        
        # Step 4: Write candidate outputs
        write_candidate_outputs(output_path, result, key_bytes)
        
        accounting.record_success(candidate_path, len(data))
        
    except (PermissionError, FileNotFoundError, ValueError, OSError) as exc:
        accounting.record_failure(candidate_path, exc.__class__.__name__, str(exc))
        # Log failure and proceed to next file
```

---

## 13. Atomicity and Multi-Artifact Consistency

### 13.1 Per-Target File Atomicity vs. Multi-Artifact Consistency

> [!WARNING]
> `os.replace()` can provide atomic replacement semantics for an individual target file under appropriate filesystem conditions on Windows NTFS and POSIX.
>
> However, writing `.enc`, `.iv`, and `.key` sidecars involves **three separate filesystem operations**. Therefore, three `os.replace()` calls do NOT constitute a single multi-file transaction. A power failure or process kill between replacements can result in an incomplete artifact set.

### 13.2 Candidate Mitigation Strategies

To reduce the likelihood of inconsistent partial artifacts:
1. Write files to temporary filenames first (e.g., `output.tmp_enc`, `output.tmp_iv`, `output.tmp_key`).
2. Replace sidecars first (`.tmp_iv` -> `.iv`, `.tmp_key` -> `.key`), then replace the ciphertext (`.tmp_enc` -> `.enc`).
3. If an error occurs prior to completion, remove any temporary `.tmp_*` files for the active file.
4. *Selection Note:* Partial-artifact cleanup policies (whether to delete incomplete artifacts, retain them with warnings, or provide a cleanup flag) remain an **Open Decision**.

---

## 14. Progress Reporting and Rate-Throttling

### 14.1 Zero-Dependency Progress Mechanisms

In alignment with zero-dependency constraints, progress indicators can rely on Python standard library facilities (`sys.stdout`, `\r`, `time.monotonic`).

Report A established the single-line carriage return (`\r`) standard:
```text
[042/150] (28%) [====================>                    ] Encrypting: quarterly_report.pdf
```

### 14.2 Console I/O Throttling Considerations

* On Windows `cmd.exe` and PowerShell, writing high-frequency console updates across many small files may introduce noticeable terminal rendering overhead.
* *Candidate Throttling Options for Selection:*
  * Update stdout on every file (no throttling).
  * Time-based throttling (e.g., update at most once every $T$ milliseconds, such as 50 ms or 100 ms).
  * Count-based throttling (e.g., update every $K$ files).
  * User-controlled verbosity (quiet mode vs. normal progress).

---

## 15. Per-File Result Accounting (C3 Requirement)

### 15.1 In-Memory Accounting Structure

To support live progress rendering, final summary cards, and log generation, the orchestrator should maintain a structured in-memory state representation:

```python
# Conceptual accounting data model (illustrative only)
class BatchRecord:
    relative_path: str
    absolute_path: Path
    output_path: Path
    file_size_bytes: int
    status: str          # "SUCCESS", "FAILED", "SKIPPED"
    elapsed_time_ms: float
    error_type: str | None
    error_message: str | None

class BatchState:
    total_discovered: int
    success_count: int
    failed_count: int
    skipped_count: int
    total_bytes_processed: int
    records: list[BatchRecord]
```

---

## 16. Batch Execution Logging (C4 Requirement)

### 16.1 Log File Format and Location

At the conclusion of a batch operation, a structured log file should be written to the designated output folder:
* **Candidate Naming:** `batch_log_YYYYMMDD_HHMMSS.csv`
* **Candidate CSV Schema:**
  ```csv
  timestamp,relative_path,operation,status,size_bytes,elapsed_ms,error_type,error_message
  2026-09-15T15:30:01,documents/memo.pdf,ENCRYPT,SUCCESS,45020,1.25,,
  2026-09-15T15:30:01,documents/locked.docx,ENCRYPT,FAILED,0,0.12,PermissionError,File locked by another process
  2026-09-15T15:30:02,documents/old_data.bin,ENCRYPT,SKIPPED,12044,0.05,FileExistsError,Output file already exists
  ```

### 16.2 Candidate Security Policy: Key & Payload Privacy in Logs

> [!CAUTION]
> **Candidate Security Policy (Subject to Selection):** Under no circumstances should raw encryption keys, generated hex keys, passwords, or plaintext payload contents be written to batch execution logs. Logs should contain exclusively operational metadata (timestamps, relative paths, sizes, status, elapsed times, exception classes, and error messages).

---

## 17. Batch Summary Card

Following the visual design guidelines established in [RESEARCH_A_MENU_UX.md](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_A_MENU_UX.md), a completed batch operation presents an illustrative summary card:

```text
================================================================================
                         BATCH OPERATION SUMMARY
                 (Illustrative UX example — not yet frozen)
================================================================================
  Operation        : AES-256-CBC Encryption
  Input Directory  : C:\LabData\Samples
  Output Directory : C:\LabData\Encrypted_20260915_153000
  Total Files      : 25
  Successful       : 22
  Failed           : 2  (See log for details)
  Skipped          : 1  (Existing output file)
  Total Data Size  : 4.82 MB
  Execution Log    : Encrypted_20260915_153000\batch_log_20260915_153000.csv
================================================================================
  [!] LABORATORY SECURITY NOTICE:
      Key sidecars (.key) were saved alongside ciphertexts.
      These keys are stored in unencrypted plaintext on disk.
      Protect the output directory accordingly.
================================================================================
```

---

## 18. Cancellation and Interruption

### 18.1 V1-Inherited Interruption Behavior

In V1 (`src/cli/main.py` [lines 58–60](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L58-L60)), a `KeyboardInterrupt` prints `"Cancelled"` and returns `EXIT_SUCCESS (0)`.

In V2 batch operations, candidate cancellation handling involves:
1. Catching `KeyboardInterrupt` within the batch loop.
2. Cleaning up any in-flight temporary files (`.tmp_*`) for the actively processing file.
3. Marking the active file as `CANCELLED` in accounting.
4. Finalizing and writing the batch execution log for all files processed prior to cancellation.
5. Displaying a partial summary card indicating that processing was interrupted.
6. Preserving V1's clean exit behavior.

---

## 19. Large Folder Handling

### 19.1 Scalability Considerations

* For typical laboratory workloads (e.g., 1 to 500 files), in-memory list materialization and sequential iteration execute rapidly without measurable memory pressure.
* For very large folders (e.g., thousands of files):
  * Materializing large lists of `Path` objects consumes modest memory but may introduce brief discovery delays.
  * Rapid console updates may cause terminal lag unless throttled.
* *Open Question for Selection:* Should V2 introduce a confirmation prompt or warning when a batch operation detects a large candidate file set (e.g., exceeding a candidate threshold)?

---

## 20. Symlinks and Windows Junctions

### 20.1 Traversal Considerations

1. **Symbolic Links (`Path.is_symlink()`):**
   * On POSIX systems and Windows (with Developer Mode or appropriate privileges), symbolic links can point to files or directories outside the source hierarchy.
   * Traversing symlinks risks processing unintended external files or encountering circular directory references in recursive scans.
2. **Windows Directory Junctions / Reparse Points:**
   * NTFS directory junctions are distinct from POSIX symlinks.
   * `os.scandir()` and `pathlib.Path` handle reparse points according to Python runtime version and platform APIs.
3. *Candidate Traversal Options for Selection:*
   * Skip all symlinks and junctions (safest default).
   * Follow symlinks for individual files only.
   * Follow directory symlinks/junctions with explicit cycle detection.

---

## 21. Windows Path and Filesystem Considerations

### 21.1 Path Normalization and Styles

* Windows supports both forward slashes (`/`) and backslashes (`\`). `pathlib.Path` handles normalization consistently across platforms.
* **UNC Paths:** Network paths (e.g., `\\server\share\data`) must be handled properly by path resolution helpers.

### 21.2 MAX_PATH (260 Characters) vs. Long Paths

* Legacy Windows Win32 APIs enforce a 260-character limit (`MAX_PATH`).
* Python 3.10+ on Windows supports long paths when the system registry setting `LongPathsEnabled` is active and the application manifest allows it.
* Prefixing paths with `\\?\` can bypass MAX_PATH under specific Win32 API conditions, but introduces constraints (e.g., relative path limitations and strict slash requirements).
* *Research Assessment:* Long-path errors should be caught as non-fatal per-file `OSError` failures during batch iteration, allowing remaining files to proceed.

### 21.3 Reserved Windows Device Names

NTFS and FAT preserve legacy DOS device names. Files named `CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9` (or files with these base stems like `CON.txt`) cannot be opened using standard Win32 file APIs.
* Attempting to open these names raises `OSError` or `PermissionError`.
* Error isolation blocks should catch these exceptions and record them as per-file failures.

### 21.4 File Locking and Permissions

On Windows, open files held exclusively by other applications (e.g., Microsoft Word, Excel) raise `PermissionError` on read/write attempts. Per-file isolation ensures that locked files are recorded as failed while the batch job continues.

---

## 22. Concurrency Analysis

### 22.1 Technical Evaluation of Concurrency Models

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CONCURRENCY ARCHITECTURE TRADEOFFS                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Model 1: Strictly Sequential Iteration (Recommended Candidate)             │
│  • Single-threaded loop processing candidate files in deterministic order.  │
│  • Advantages: Predictable execution order; trivial error isolation; clean  │
│    console progress reporting without thread locks; minimal codebase risk.  │
│  • Trade-offs: Does not utilize multiple CPU cores for large datasets.      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Model 2: ThreadPoolExecutor (Multi-Threaded)                               │
│  • Note on GIL: The underlying `cryptography` C extension executes AES       │
│    operations outside Python bytecode, allowing true multi-core CPU work.   │
│  • Trade-offs: Complex console progress synchronization; non-deterministic │
│    completion order; thread-safe locking required for accounting & logging. │
├─────────────────────────────────────────────────────────────────────────────┤
│  Model 3: ProcessPoolExecutor (Multi-Process)                               │
│  • Spawns worker processes to parallelize batch operations.                 │
│  • Trade-offs: High process spawning overhead on Windows; complex IPC queue  │
│    for progress and accounting; excessive complexity for desktop lab scope. │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 22.2 Concurrency Assessment

While multi-threading could provide throughput gains for large multi-gigabyte datasets, the architectural complexity (thread-safe progress reporting, race conditions in logging, non-deterministic completion, and test synchronization) introduces substantial implementation and maintenance risks for a desktop testing lab.
* *Candidate Recommendation:* Strictly sequential iteration appears to be the most reliable baseline candidate for V2.

---

## 23. V1 Interoperability and Compatibility

V2 batch-generated ciphertext and applicable `.iv` sidecars should preserve compatibility with the verified V1 single-file cryptographic interface. V2-specific artifacts such as `.key` sidecars and batch execution logs are governed by V2 candidate conventions:
1. **Ciphertext Compatibility:** Output `.enc` files match the binary format produced by single-file V1 `encrypt`.
2. **IV Compatibility:** Output `.iv` sidecars match the 1-line hex format verified in V1 `run_decrypt()` ([`commands.py` L419–420](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L419-L420)).
3. **Decryption Compatibility:** Any individual file from a batch output directory can be decrypted using the standard V1 CLI:
   ```cmd
   rem Windows Command Prompt verification example
   python -m src.cli.main decrypt --algorithm AES --key-size 256 --mode CBC --key <HEX_KEY> --input-file data\output\sample.pdf.enc --output-file restored_sample.pdf
   ```
   *(Where `<HEX_KEY>` is retrieved from the corresponding `.key` sidecar or provided by the user).*

---

## 24. Interaction with Research B (Key Management)

Report C coordinates directly with findings from [RESEARCH_B_KEY_MANAGEMENT.MD](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_B_KEY_MANAGEMENT.MD):
1. **Sidecar Naming Standard:** References Report B's candidate `<output_file>.key` sidecar convention.
2. **Sidecar Format:** Strict ASCII hex string followed by `\n`.
3. **Validation Rules:** Leverages Report B's key-length and hex validation criteria.
4. **Security Warnings:** Aligns the candidate security-notice approach with Report B's research findings, consolidating batch notices into the final summary.

---

## 25. Industry Comparison

| Tool / System | Observed Pattern | Why the Pattern Matters | Potential Lesson for V2 |
| :--- | :--- | :--- | :--- |
| **Robocopy (Windows)** | Observed Windows CLI pattern for mirror replication; non-fatal logging of locked files; summary statistics card upon completion. | Demonstrates practical CLI UX for unattended batch file operations on Windows. | V2 can reference Robocopy's summary statistics and per-file error resilience as candidate models. |
| **rsync (Linux)** | Observed CLI pattern of skipping files based on attributes/timestamps; single-line progress ticker; exit codes reflecting partial vs. fatal failures. | Demonstrates standard CLI conventions for batch synchronization and status codes. | Informs candidate skip-existing overwrite policies and single-line progress tickers. |
| **7-Zip CLI** | Observed CLI pattern for archive operations; lexical file ordering; non-destructive archive creation. | Prioritizes data safety and deterministic processing order across platforms. | Reinforces candidate lexical path sorting and non-destructive source file handling. |
| **rclone** | Observed CLI pattern for sync operations; dry-run preview capability; structured logging. | Provides preview capabilities before modifying disk. | Informs candidate pre-flight Dry Run / Preview UX for V2 batch wizards. |

---

## 26. Alternative Architectures Evaluated

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURAL MODELS COMPARISON                          │
├───────────────────┬──────────────┬──────────────────┬───────────────────────┤
│ Architecture Model│ Complexity   │ Error Resilience │ UX & Progress Quality │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model A: Simple   │ Low          │ Poor (aborts on  │ Poor (terminal crash  │
│   Iterative Loop  │              │ first exception) │ on first locked file) │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model B: Sequen-  │ Moderate     │ High (per-file   │ High (deterministic   │
│   tial Result     │              │ try/catch with   │ single-line \r        │
│   Aggregation     │              │ accounting state)│ + summary card)       │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model C: Worker   │ High         │ High (isolated   │ Moderate (complex     │
│   Queue Pool      │              │ task boundaries) │ progress locking)     │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model D: Two-Phase│ Very High    │ All-or-nothing   │ Poor for large batches│
│   Transactional   │              │ (aborts all)     │ (discards valid work) │
├───────────────────┼──────────────┼──────────────────┼───────────────────────┤
│ Model E: Manifest-│ High         │ High (state      │ Moderate (excessive   │
│   Driven Database │              │ database)        │ complexity for lab)   │
└───────────────────┴──────────────┴──────────────────┴───────────────────────┘
```

* **Candidate Evaluation:**
  * **Model A (Simple Loop):** Not preferred due to lack of error isolation and inability to complete batches containing locked or corrupt files.
  * **Model B (Sequential Result Aggregation):** **Recommended Candidate** — provides the best balance of zero-dependency simplicity, robust error isolation, and clean terminal formatting.
  * **Model C (Worker Queue):** Deferred due to multi-threading complexity and progress synchronization overhead.
  * **Model D (Two-Phase Transactional):** Not preferred because all-or-nothing rollback discards successfully processed files on large batch jobs.
  * **Model E (Manifest Database):** Deferred as overly complex for desktop testing lab requirements.

---

## 27. Candidate Dry Run / Preview Feature (Candidate Recommendation C-14)

To support user confidence prior to executing large directory operations:
1. **Pre-Flight Directory Scan:** Discovers candidate files without reading payloads or writing outputs.
2. **Preview Display:** Presents:
   * Total eligible files matching patterns.
   * Total excluded files (e.g., `.enc`, `.key`, `.iv`, hidden files).
   * Total estimated input size (sum of `st_size`).
   * Potential output collisions (existing files in destination).
3. *Selection Note:* Whether dry-run is exposed via CLI flag (`--dry-run`), menu prompt, or both remains an **Open Decision**.

---

## 28. Deterministic Ordering

Filesystem iteration (`os.listdir()` / `Path.iterdir()`) returns entries in arbitrary file-system order depending on OS inode or NTFS directory indexing.
* Running a batch operation on the same folder could enumerate files in different orders across runs or platforms.
* *Candidate Approach:* Sorting candidate paths lexically (`sorted(candidate_files, key=lambda p: str(p.relative_to(base))))` produces a deterministic processing sequence given a fixed file set and stable path representation.

---

## 29. Candidate Data Safety Policies

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CANDIDATE DATA SAFETY POLICIES                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Non-Destructive Source Handling: Source files are not deleted,           │
│    truncated, or modified in-place during batch operations.                 │
│ 2. Separate Output Destination: Outputs are directed to a designated        │
│    folder or distinct filename extensions, avoiding source collisions.      │
│ 3. Temporary Write-and-Replace: Ciphertexts and sidecars are written to     │
│    temporary files first and renamed, reducing incomplete output files.     │
│ 4. Read-Only Source Compatibility: Source files with read-only filesystem    │
│    attributes are safely read without attempting attribute modification.    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 30. Failure-Mode Matrix

| Failure Mode | Detection Point | Impact | Candidate Classification | Recovery / Handling Candidate | Logging |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Missing Input Directory** | Pre-flight validation | Cannot start batch | Fatal | Abort batch immediately with clear error message | Console error; no log |
| **Empty Input Directory** | Pre-flight discovery | Zero files to process | Non-fatal | Display informational message and return `EXIT_SUCCESS` | Console notice |
| **Output Root Unavailable** | Pre-flight validation | Cannot write outputs | Fatal | Abort batch; prompt user for valid directory | Console error |
| **Output Dir Not Writable** | Output directory check | Write permissions denied | Fatal | Abort batch immediately | Console error |
| **Individual File Locked** | File read / open | File cannot be read | Non-fatal (Per-file) | Skip file; record failure; continue batch iteration | Recorded as `FAILED` |
| **Source File Disappears** | `FileHandler.read_bytes` | File deleted during run | Non-fatal (Per-file) | Catch `FileNotFoundError`; record failure; continue | Recorded as `FAILED` |
| **Disk Full (No Space)** | Output write / `os.replace` | Storage exhausted | Fatal | Abort batch; clean temporary files; preserve completed | Console error + partial log |
| **Ctrl+C User Cancel** | Batch iteration loop | User aborted batch | Cancellation | Catch `KeyboardInterrupt`; clean temp file; write log | Console card + log finalize |
| **Corrupt / Missing .iv** | Batch decryption step | CBC cannot decrypt | Non-fatal (Per-file) | Record missing IV failure; continue batch | Recorded as `FAILED` |
| **Corrupt / Missing .key** | Batch decryption step | Key unavailable | Non-fatal (Per-file) | Record missing key failure; continue batch | Recorded as `FAILED` |
| **Invalid Padding / Cipher**| `CipherService.decrypt` | Corrupt data or wrong key | Non-fatal (Per-file) | Catch `ValueError`; record failure; continue | Recorded as `FAILED` |
| **MAX_PATH Path Failure** | File I/O boundary | Path too long on Win32 | Non-fatal (Per-file) | Catch `OSError`; record failure; continue batch | Recorded as `FAILED` |
| **Reserved Windows Name** | File open boundary | DOS device name error | Non-fatal (Per-file) | Catch `OSError`/`PermissionError`; record failure | Recorded as `FAILED` |
| **Destination Collision** | Overwrite check | Output file exists | Non-fatal (Per-file) | Governed by overwrite policy (default: skip) | Recorded as `SKIPPED` |
| **Partial Artifact Set** | Decryption discovery | Mismatched sidecars | Non-fatal (Per-file) | Skip incomplete artifact; record failure | Recorded as `FAILED` |

---

## 31. Testing Strategy

The research identified candidate test scenarios to be covered in V2 implementation testing using pytest's `tmp_path` fixture:

```python
# Conceptual test structure (illustrative test specifications — not executable code)

def test_candidate_batch_encrypt_happy_path(tmp_path):
    """Verify batch encryption of multiple valid files produces matching sidecars."""
    # 1. Populate tmp_path / "input" with sample files.
    # 2. Execute candidate batch encrypt.
    # 3. Assert output folder contains expected .enc, .iv, and .key files.
    # 4. Assert summary accounting reports total_discovered == success_count.

def test_candidate_batch_error_isolation(tmp_path):
    """Verify an unreadable or corrupt file does not abort remaining batch files."""
    # 1. Populate input folder with 3 valid files and 1 locked/unreadable file.
    # 2. Execute candidate batch encrypt.
    # 3. Assert 3 files succeed, 1 file is recorded as failed.
    # 4. Assert execution log contains error entry for failed file.

def test_candidate_skip_existing_resumption(tmp_path):
    """Verify skip-existing policy skips existing outputs without re-processing."""
    # 1. Pre-populate output folder with one existing ciphertext.
    # 2. Execute candidate batch encrypt.
    # 3. Assert existing file is tallied as SKIPPED, new files are processed.

def test_candidate_v1_interoperability_decrypt(tmp_path):
    """Verify individual ciphertext from batch can be decrypted by V1 command."""
    # 1. Batch-encrypt input directory.
    # 2. Invoke V1 run_decrypt() on a single output .enc + .iv using the .key file.
    # 3. Assert decrypted plaintext matches original source file.
```

### 31.1 Comprehensive Test Coverage Areas
* Deterministic lexical ordering.
* Candidate exclusion patterns (`.enc`, `.key`, `.iv`, hidden files).
* Overwrite policies (skip, force, error).
* Non-fatal error isolation across exception types (`PermissionError`, `FileNotFoundError`, `ValueError`).
* Interruption and cleanup on `KeyboardInterrupt`.
* Windows long paths and reserved device names.
* Execution log schema validation and key privacy compliance.

---

## 32. Candidate Recommendations

The following candidate recommendations synthesize research findings for evaluation during the V2 Selection phase. All recommendations remain non-frozen:

* **RECOMMENDATION C-01 (NOT YET FROZEN):**  
  * *Recommendation:* Adopt Architecture Model B (Sequential Iteration with Result Aggregation) as the baseline batch execution engine.  
  * *Rationale:* Provides high error resilience, deterministic progress reporting, and thread-safe logging with minimal architectural complexity.  
  * *Trade-off:* Does not parallelize CPU work across multiple cores.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-02 (NOT YET FROZEN):**  
  * *Recommendation:* Implement flat directory traversal (`iterdir()`) as the default batch discovery mode, with upfront candidate list materialization and lexical sorting.  
  * *Rationale:* Ensures predictable operations, stable progress denominators, and reproducible processing order.  
  * *Trade-off:* Does not process subdirectories unless recursive mode is selected.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-03 (NOT YET FROZEN):**  
  * *Recommendation:* Apply a Candidate Exclusion Matrix automatically skipping `.enc`, `.key`, `.iv`, `.tmp`, and OS metadata files (`.DS_Store`, `Thumbs.db`).  
  * *Rationale:* Prevents recursive re-encryption and sidecar corruption.  
  * *Trade-off:* Users wishing to encrypt `.key` files must explicitly override exclusions.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-04 (NOT YET FROZEN):**  
  * *Recommendation:* Support Option C key strategy (allowing user selection between unique per-file keys and a shared batch key, defaulting to unique keys).  
  * *Rationale:* Combines minimal blast radius with flexibility for educational benchmarks.  
  * *Trade-off:* Generates multiple sidecar files when unique keys are used.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-05 (NOT YET FROZEN):**  
  * *Recommendation:* Generate `<output>.enc.key` and `<output>.enc.iv` sidecars for encrypted files to maintain compatibility with single-file V1 decryption workflows.  
  * *Rationale:* Allows any batch output to be decrypted individually via V1 CLI.  
  * *Trade-off:* Triples the file count in output directories.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-06 (NOT YET FROZEN):**  
  * *Recommendation:* Adopt "Skip Existing" as the strong candidate for default batch overwrite behavior.  
  * *Rationale:* Provides non-destructive operation and a practical resumption mechanism for interrupted batches.  
  * *Trade-off:* Does not detect corrupted partial artifacts from prior aborted runs without explicit validation.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-07 (NOT YET FROZEN):**  
  * *Recommendation:* Wrap each file operation in a dedicated per-file exception handler trapping `PermissionError`, `FileNotFoundError`, `ValueError`, and non-fatal `OSError`.  
  * *Rationale:* Satisfies Intent requirement C4 for fault-tolerant batch processing.  
  * *Trade-off:* Requires comprehensive classification of fatal vs. non-fatal exceptions.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-08 (NOT YET FROZEN):**  
  * *Recommendation:* Use temporary write-and-replace (`.tmp_*` -> `os.replace()`) to reduce the likelihood of half-written output files on cancellation or failure.  
  * *Rationale:* Mitigates corrupt artifact generation during unexpected interruptions.  
  * *Trade-off:* Does not provide multi-file transactional atomicity across `.enc`, `.iv`, and `.key` sets.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-09 (NOT YET FROZEN):**  
  * *Recommendation:* Implement single-line `\r` console progress with rate-throttling options to prevent terminal latency on Windows.  
  * *Rationale:* Balances live visual feedback with execution throughput.  
  * *Trade-off:* Throttle interval requires Selection resolution.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-10 (NOT YET FROZEN):**  
  * *Recommendation:* Record structured batch execution accounting and write a standardized CSV log (`batch_log_*.csv`) into the output directory upon completion.  
  * *Rationale:* Fulfills C4 persistent logging requirements in an easily auditable format.  
  * *Trade-off:* Leaves execution log artifacts in the destination folder.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-11 (NOT YET FROZEN):**  
  * *Recommendation:* Enforce Candidate Security Policy prohibiting raw encryption keys, hex keys, and plaintext payloads from being written to execution logs.  
  * *Rationale:* Essential security boundary protecting cryptographic secrets from log leakage.  
  * *Trade-off:* Debugging key-related errors requires inspecting error messages rather than key contents.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-12 (NOT YET FROZEN):**  
  * *Recommendation:* Display a consolidated terminal summary card and single Laboratory Security Notice upon batch completion.  
  * *Rationale:* Follows Report A visual aesthetics and prevents repetitive terminal security warnings.  
  * *Trade-off:* Security notice is seen only at batch conclusion.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-13 (NOT YET FROZEN):**  
  * *Recommendation:* Handle `KeyboardInterrupt` by cleaning in-flight temporary files, finalizing the execution log, and exiting cleanly with `EXIT_SUCCESS (0)` in accordance with V1 conventions.  
  * *Rationale:* Preserves clean cancellation ergonomics.  
  * *Trade-off:* Interrupted batch leaves completed files on disk alongside a partial log.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-14 (NOT YET FROZEN):**  
  * *Recommendation:* Provide a pre-flight Dry Run / Preview option to display candidate file counts, exclusions, and collision warnings prior to disk modification.  
  * *Rationale:* Enhances user clarity and prevents accidental bulk operations.  
  * *Trade-off:* Adds an extra step or CLI option.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

* **RECOMMENDATION C-15 (NOT YET FROZEN):**  
  * *Recommendation:* Enforce strict non-destructive source handling, ensuring input files are never deleted, truncated, or modified in-place.  
  * *Rationale:* Protects user data integrity during cryptographic operations.  
  * *Trade-off:* Requires sufficient destination storage space for full ciphertext duplicates.  
  * *Status:* Candidate Recommendation (Decision status: NOT YET FROZEN).

---

## 33. Open Decisions (Deferred to Selection Phase)

The following design choices remain open and will be evaluated and decided during the V2 Selection phase:
1. **Decision C-OPEN-01 (Traversal Mode):** Should batch traversal be flat-only in V2, or should an opt-in recursive mode (`--recursive`) with directory tree mirroring be supported?
2. **Decision C-OPEN-02 (Output Destination Policy):** Should batch output default to an auto-generated timestamped folder (e.g., `data/output/batch_YYYYMMDD_HHMMSS/`) or require an explicit user-provided destination path?
3. **Decision C-OPEN-03 (Overwrite Policy):** Should the default overwrite policy be "Skip Existing", "Refuse/Error", or an interactive prompt in guided menu mode?
4. **Decision C-OPEN-04 (Key Strategy Default):** In batch encryption, should unique per-file keys or a single shared batch key be the default option in the guided wizard?
5. **Decision C-OPEN-05 (Sidecar Decryption Resolution):** In batch decryption, if a file lacks a `.key` sidecar and no shared key was supplied, should the batch skip the file or prompt interactively?
6. **Decision C-OPEN-06 (Hidden Files Policy):** Should hidden files (Unix dotfiles / Windows hidden attributes) be excluded automatically or governed by a CLI flag?
7. **Decision C-OPEN-07 (Symlink & Junction Policy):** Should symlinks and Windows directory junctions be skipped, followed for files only, or followed with cycle detection?
8. **Decision C-OPEN-08 (Progress Throttling Rate):** What should be the default console progress throttling interval (e.g., 50 ms vs. 100 ms vs. every $K$ files)?
9. **Decision C-OPEN-09 (Large-Folder Confirmation):** Should V2 display a warning or confirmation prompt when a batch scan discovers a large candidate file set (e.g., exceeding a specific candidate threshold)?
10. **Decision C-OPEN-10 (Partial-Output Cleanup):** When a batch is cancelled or encounters a fatal error, should partial/incomplete temporary artifacts be deleted immediately, retained with a `.corrupt` extension, or managed via an explicit cleanup option?
11. **Decision C-OPEN-11 (Log Format & Timestamping):** Should batch logs be formatted as CSV-only, dual CSV/text, and should timestamps use UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ`) or local system time?
12. **Decision C-OPEN-12 (Dry-Run Exposure):** Should the dry-run preview be exposed as a CLI flag (`--dry-run`), a menu prompt step, or both?

---

## 34. Deferred Decisions (Explicitly Post-V2)

1. **Multi-Threaded / Multi-Process Concurrency:** Parallel execution engines are deferred to post-V2 to preserve simplicity and zero-dependency terminal UI stability.
2. **Streaming Archive Encryption:** Direct encryption of folder trees into single `.tar.enc` or `.zip.enc` archive containers is deferred.
3. **Cloud & Remote Storage Backends:** S3/Blob storage batch targets are out of scope.
4. **Cryptographic Manifest Signatures:** Generating signed batch manifests (HMAC / RSA signatures over batch hashes) is deferred.

---

## 35. Risks and Trade-offs

1. **Sidecar File Sprawl:** Generating `.key` and `.iv` sidecars for large numbers of files creates multiple sidecars per input file. While this preserves standalone single-file V1 decryptability, it increases folder clutter.
2. **Console Rendering Latency:** Rapid terminal updates on Windows `cmd.exe` or PowerShell can introduce rendering delays on large batches of small files. Rate-throttling mitigates this risk.
3. **Windows Long-Path Limits:** Deep directory structures combined with double extensions (e.g., `.pdf.enc.key`) may encounter MAX_PATH limits on systems where long paths are not configured. Per-file error isolation prevents application crashes.

---

## 36. Conclusion

Batch operations in V2 can be implemented safely, predictably, and efficiently by layering a sequential, result-aggregating orchestration controller over the verified V1 `CipherService` and `FileHandler` pipeline. By isolating errors per-file, managing sidecars consistently with verified V1 IV conventions and Report B candidate key conventions, enforcing safe non-destructive filesystem policies, providing throttled progress feedback, and generating structured execution logs without secret key leakage, V2 can achieve full Category C capability while preserving the integrity of the frozen V1 core.

---

## 37. Sources and Evidence

### Repository Evidence
* [`src/engines/cipher_service.py`](file:///C:/Users/kodal/Cryptography_Project/src/engines/cipher_service.py) — Stateless in-memory cipher service interface ([L13-L33](file:///C:/Users/kodal/Cryptography_Project/src/engines/cipher_service.py#L13-L33)).
* [`src/cli/commands.py`](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py) — V1 single-file command orchestration ([L370-L441](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L370-L441)), overwrite check ([L86-L90](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L86-L90)), IV persistence ([L402-L404](file:///C:/Users/kodal/Cryptography_Project/src/cli/commands.py#L402-L404)).
* [`src/utils/file_handler.py`](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py) — Static persistence leaf and directory creation ([L21-L105](file:///C:/Users/kodal/Cryptography_Project/src/utils/file_handler.py#L21-L105)).
* [`src/cli/main.py`](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py) — Top-level exception handling, exit codes, and `KeyboardInterrupt` handling ([L43-L78](file:///C:/Users/kodal/Cryptography_Project/src/cli/main.py#L43-L78)).
* [`tests/cli/test_persistence.py`](file:///C:/Users/kodal/Cryptography_Project/tests/cli/test_persistence.py) — V1 persistence and sidecar test suite.
* [`docs/v2/V2_INTENT.md`](file:///C:/Users/kodal/Cryptography_Project/docs/v2/V2_INTENT.md) — Category C Scope (§5.3) and Non-Destructive Principles (§3.2).
* [`docs/v2/research/RESEARCH_A_MENU_UX.md`](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_A_MENU_UX.md) — Console UI Design System, Progress Indicators, Summary Cards.
* [`docs/v2/research/RESEARCH_B_KEY_MANAGEMENT.MD`](file:///C:/Users/kodal/Cryptography_Project/docs/v2/research/RESEARCH_B_KEY_MANAGEMENT.MD) — Candidate Key Sidecar Formats, Hex Validation, Laboratory Security Notices.

### Python / Standard Library Documentation
* Python `pathlib` — Object-oriented filesystem paths and directory traversal.
* Python `os.replace` — Atomic file replacement semantics across platforms.
* Python `csv` — Standard CSV file writing and parsing.

### Industry Tools Consulted
* **Microsoft Robocopy:** Observed Windows CLI pattern for replication; logging locked files; summary statistics card upon completion.
* **rsync:** Observed CLI pattern for skipping files based on attributes/timestamps; single-line progress tickers; exit codes reflecting partial vs. fatal failures.
* **7-Zip CLI:** Observed CLI pattern for sequential archive operations; lexical file ordering; non-destructive archive creation.
* **rclone:** Observed CLI pattern for sync operations; pre-flight dry-run inspection; structured execution logging.