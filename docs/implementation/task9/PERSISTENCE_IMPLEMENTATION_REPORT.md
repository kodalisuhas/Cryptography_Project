# Persistence Layer Implementation Report

**Task:** Task 9 — Persistence Layer Implementation (Persistence V1)
**Status:** **IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION REVIEW**

| Field | Value |
|---|---|
| Report date | 2026-09-10 |
| Governing selection | `docs/implementation/task8/PERSISTENCE_PROJECT_SPECIFIC_SELECTION_AND_PLAN.md` |
| Governing execution plan | `docs/implementation/task9/PERSISTENCE_IMPLEMENTATION_PLAN.md` |
| Authority order | Frozen selection > Execution plan > This report |
| Frozen-layer changes | **None** |
| New dependencies | **None** |
| Commits / pushes | **None** |

---

## 1. Files Implemented / Created

| File | Action | Purpose |
|---|---|---|
| `src/utils/file_handler.py` | Implemented (stub → 11 methods, 104 lines) | Thin persistence leaf: filesystem reads/writes, CSV, JSON, figure saving. No instance state, no project-module imports, native exceptions only. |
| `src/cli/commands.py` | Created (untracked → new module) | CLI command handlers with persistence orchestration. CLI owns base64 conversion, graph generation, figure lifecycle, overwrite checks, directory creation, and `.iv` sidecar handling. |
| `tests/utils/test_file_handler.py` | Created (untracked) | 19 unit tests for FileHandler. 17 pass, 2 skipped (Windows: `IsADirectoryError` and permission-denied tests). |
| `tests/cli/test_persistence.py` | Created (untracked) | 23 CLI integration tests (19 integration + 4 edge cases) driving the real `main()` entry point end to end. |

### Files Modified (CLI layer only)

| File | Change |
|---|---|
| `src/cli/main.py` | Added `matplotlib.use("Agg")` at top (before any pyplot/GraphGenerator import); added `validate_persistence_args(parser, args)` call after `parse_args`; added `FileExistsError` and `OSError` handlers BEFORE the combined `ValueError/TypeError/KeyError` handler (`FileExistsError` is an `OSError` subclass, ordering matters). |
| `src/cli/argument_parser.py` | `--input` on `encrypt`/`decrypt` changed from `required=True` to `required=False`; added `--input-file`, `--output-file`, `--force` (encrypt and decrypt); added `--save-csv DIR`, `--save-graphs DIR` (benchmark); added `--save-report DIR` (security); added `validate_persistence_args()` enforcing exactly one of `--input` / `--input-file`. |
| `tests/cli/test_argument_parser.py` | `test_missing_input` route through `main()` instead of `parse_args` — see Deviations §6. |

---

## 2. Methods Implemented — `src/utils/file_handler.py`

`FileHandler` — 11 static methods, no constructor, no instance state:

| # | Method | Signature | Behavior |
|---|---|---|---|
| 1 | `read_bytes` | `(path: str \| Path) -> bytes` | `Path(path).read_bytes()` |
| 2 | `write_bytes` | `(path, data: bytes) -> None` | Creates parent dirs, writes binary |
| 3 | `read_text` | `(path, encoding="utf-8") -> str` | `Path(path).read_text(encoding)` |
| 4 | `write_text` | `(path, text, encoding="utf-8") -> None` | Creates parent dirs, writes UTF-8 |
| 5 | `save_dataframe_csv` | `(df: Any, path, float_format="%.6f") -> None` | Duck-typed `df.to_csv(path, index=False, float_format=...)`; no pandas import |
| 6 | `save_figure` | `(fig: Any, path, dpi=300) -> None` | Duck-typed `fig.savefig(..., bbox_inches="tight", format="png")`; no matplotlib import |
| 7 | `write_json` | `(data: dict, path, indent=2) -> None` | Serializes dict; no tuple/bytes allowed — CLI must pre-convert |
| 8 | `read_json` | `(path) -> dict` | `json.loads(Path(path).read_text())` |
| 9 | `exists` | `(path) -> bool` | `Path(path).exists()` |
| 10 | `get_file_size` | `(path) -> int` | Byte size of target file |
| 11 | `ensure_directory` | `(path) -> None` | Creates directory tree if absent |

All methods raise only native exceptions (`FileNotFoundError`, `OSError`, `ValueError`, `json.JSONDecodeError`). No custom exception classes.

---

## 3. CLI Persistence Features Implemented

| Feature | Frozen requirement | Implementation |
|---|---|---|
| `encrypt --input-file` | File input replaces `--input` string | `FileHandler.read_bytes` reads raw binary plaintext |
| `encrypt --output-file` | Write ciphertext file | `_check_overwrite` → `ensure_directory` → `write_bytes` |
| CBC `.iv` sidecar | CBC encrypt writes `output_file + ".iv"`; CBC decrypt reads it | `write_text(output_file + ".iv", iv.hex() + "\n")` on encrypt; `read_text(input_file + ".iv")` → `bytes.fromhex` on decrypt; ECB never creates or reads it |
| `--force` | Overwrite existing output only with `--force` | `FileExistsError` raised → caught in `main()` → `EXIT_RUNTIME` |
| `decrypt --input-file` | File input | `FileHandler.read_bytes`; CBC reads sidecar IV |
| `decrypt --output-file` | Write recovered plaintext | `_check_overwrite` → `ensure_directory` → `write_bytes` |
| `benchmark --save-csv DIR` | Summary + raw CSVs | `benchmark_summary_<ts>.csv` + `benchmark_raw_<ts>.csv` via `save_dataframe_csv` |
| `benchmark --save-graphs DIR` | 3 graph PNGs | `key_size_comparison_<ts>.png`, `mode_comparison_<ts>.png`, `throughput_analysis_<ts>.png`. Multi-payload: the two comparison graphs filter to the smallest `data_size_bytes`; throughput uses the full summary (Selection §39). |
| `security --save-report DIR` | JSON report | `security_report_<mode>_<ts>.json` via `write_json`; `ecb_weakness` binary fields base64-encoded to ASCII strings (CLI concern) |
| Path conventions | Frozen `results/...` structure | Timestamps `YYYYMMDD_HHMMSS`; user supplies base dir |

**Data flow boundary:** FileHandler never receives bytes that are not already serializable. The CLI performs base64 conversion (`original_header`, `original_pixel_data`, `ecb_ciphertext`, `cbc_ciphertext`, `bmp_trailing_data`) in `_build_security_report` before calling `write_json`.

---

## 4. Tests Added

### `tests/utils/test_file_handler.py` (19 tests)
Unit coverage of all 11 methods plus error/edge paths. 2 skipped on Windows (permission / `IsADirectoryError` semantics differ).

### `tests/cli/test_persistence.py` (23 tests)

| Class | Count | Covers |
|---|---|---|
| `TestFileRoundtrip` | 2 | ECB / CBC file encrypt→decrypt round-trips |
| `TestIvSidecar` | 4 | CBC creates `.iv`; ECB does not; no `*.iv` files; sidecar format (32 hex + `\n`) |
| `TestDecryptErrors` | 1 | CBC decrypt with missing `.iv` → `EXIT_RUNTIME` (`No such file`) |
| `TestOverwrite` | 2 | Refusal without `--force` (target unchanged); success with `--force` |
| `TestInputErrors` | 1 | Missing input file → `EXIT_RUNTIME` |
| `TestBenchmarkPersistence` | 4 | 2 CSVs, exact column sets, 3 PNGs, valid PNG magic bytes |
| `TestSecurityPersistence` | 3 | JSON file created, structure/metadata/base64 fields, base64 round-trip |
| `TestBackwardCompat` | 1 | No persistence flags → in-memory behavior, no files written |
| `TestPaths` | 1 | Round-trip through a directory with spaces |
| `TestEdgeCases` | 4 | Empty, 1-byte, block-exact, over-block file payloads |

All tests drive `main()` end to end (parse → `validate_persistence_args` → dispatch → error mapping).

---

## 5. Test Results

### Targeted — `tests/utils/test_file_handler.py`
```
19 passed, 2 skipped   (17 passed + 2 Windows skips)
```

### Targeted — `tests/cli/test_persistence.py`
```
23 passed in 1.68s
```

### Full regression — `python -m pytest --tb=no -q`
```
434 passed, 2 skipped in 2.49s
```
All pre-existing baseline tests AND all new persistence tests pass together. (Also re-verified after smoke tests: `434 passed, 2 skipped in 2.33s`.)

### Manual smoke tests (Phase 10)
Performed in `results/smoke_test_phase10/` (artifacts cleaned afterward); all passed:

| # | Scenario | Result |
|---|---|---|
| 1 | CBC encrypt file → sidecar `.iv` written (32 hex + newline) | PASS |
| 2 | CBC decrypt reads sidecar → recovered bytes match original (`cmp` → `ROUND-TRIP MATCH`) | PASS |
| 3 | ECB encrypt → NO `.iv` sidecar created | PASS |
| 4 | Overwrite refused without `--force` (exit 1, target untouched); succeeds with `--force` (exit 0) | PASS |
| 5 | Benchmark → 2 CSVs (summary + raw) + 3 PNGs (valid `\x89PNG` magic) | PASS |
| 6 | Security → JSON report with metadata + base64 `ecb_weakness` fields | PASS |

---

## 6. Deviations / Decisions

1. **`test_missing_input` contract conflict (intentional, frozen design wins).**
   The pre-existing test asserted `create_parser().parse_args()` raises `SystemExit(2)` when `--input` is missing. The frozen selection changes `--input` to `required=False` precisely so `--input-file` can substitute; the conditional requirement is unexpressible in `argparse` and is enforced post-parse by `validate_persistence_args()`. The test was updated to route through `main()` (which calls the validator) — preserving its intent: missing input → usage error exit 2.

2. **Defensive `getattr(args, field, default)` in all four handlers.**
   Pre-existing CLI tests build partial `argparse.Namespace` objects without the new persistence fields. All handlers now read persistence options via `getattr` with defaults (`input_file`, `output_file`, `force`, `save_csv`, `save_graphs`, `save_report`), preserving backward compatibility with those tests. No pre-existing frozen test file was modified except the one documented above.

3. **Multi-payload benchmark graphs filter to smallest size.**
   `generate_key_size_comparison` / `generate_mode_comparison` require a single `data_size_bytes`. When the CLI benchmarks multiple payload sizes, those two graphs are generated from the summary filtered to the smallest size (frozen Selection §39); `throughput_analysis` uses the full summary (supports multiple sizes natively).

4. **`Agg` backend forced at the top of `src/cli/main.py`.**
   Required so `GraphGenerator` / `pyplot` import work headlessly. `test_persistence.py` mirrors this before any pyplot-touching import.

5. **Exception ordering in `main()`.**
   `FileExistsError` is caught before `OSError` (it is a subclass) so overwrite conflicts report their specific message rather than being folded into a generic `OSError`.

6. **`.iv` sidecar is CBC-only and one-line hex.**
   Format frozen: 32 hex chars (16-byte IV) + trailing `\n`. ECB never creates or reads the sidecar and still rejects `--iv`.

---

## 7. Frozen-Layer Verification

| Check | Result |
|---|---|
| `git diff --stat src/core src/engines src/analyzers src/utils/padding.py` | **Empty** — no changes |
| `src/analyzers/metric_collector.py` (frozen) | Unchanged; its `FileHandler` mention is a pre-existing deprecation note for the forbidden `export_to_csv` — not persistence logic added by this task |
| `requirements.txt` | **Unchanged** (byte identical) |
| `.gitignore` | **Unchanged** (byte identical) |
| Custom exception classes | **None** — all new code raises only native exceptions |
| Persistence code inside Service/Analysis | **None** — file I/O, base64, graph generation, and overwrite logic live exclusively in `src/cli/commands.py` + `src/utils/file_handler.py` |
| Frozen service/core/analyst APIs | Untouched; no signatures changed |

Changed files are confined to the CLI presentation layer (`src/cli/`) and the new persistence leaf (`src/utils/file_handler.py`), both permitted by the frozen selection.

---

## 8. Dependency Verification

- **No new dependencies.**
- `src/utils/file_handler.py` imports only the standard library (`json`, `pathlib`, `typing`).
- CLI additions reuse already-approved modules: `base64`, `getpass`, `struct`, `datetime`, `pathlib` (stdlib) and `matplotlib` / `tabulate` (both already required by the existing CLI/graph layer).
- `matplotlib.use("Agg")` selects an existing backend; it adds no package.

---

## 9. Final Changed-File List

**Modified (tracked):**
- `src/cli/main.py`
- `src/cli/argument_parser.py`
- `tests/cli/test_argument_parser.py`

**Created (untracked):**
- `src/utils/file_handler.py` (tracked — implemented from stub)
- `src/cli/commands.py`
- `tests/utils/test_file_handler.py`
- `tests/cli/test_persistence.py`

**Pre-existing CLI changes (not from this task, present in the working tree before Task 9 began):** `src/cli/__init__.py`, `src/cli/menu.py`.

Note: `git status` also shows untracked `docs/implementation/task6/`, `docs/implementation/task7/`, `docs/implementation/task8/`, `docs/implementation/task9/`, `docs/research/`, `.claude/` and unrelated deleted review docs — all outside the persistence implementation scope.

---

## 10. Confirmation

```text
Persistence Implementation
        ↓
Implementation Complete ✓
        ↓
Tests Passing ✓ (434 passed, 2 skipped)
        ↓
Manual Smoke Tests Passing ✓ (6/6 scenarios)
        ↓
Frozen Layers Verified ✓
        ↓
Implementation Report Created ✓
        ↓
🔜 INDEPENDENT IMPLEMENTATION REVIEW
```

**IMPLEMENTATION COMPLETE — READY FOR INDEPENDENT IMPLEMENTATION REVIEW**

No commit. No push. No freeze declared.