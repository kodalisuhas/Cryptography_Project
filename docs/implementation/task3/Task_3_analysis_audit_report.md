# CRYPTOGRAPHY_PROJECT — ANALYSIS SYSTEM CONTEXT RECONSTRUCTION & AUDIT

## 1. Repository State
- **Current Branch**: `dev` (up to date with `origin/dev`)
- **Current HEAD**: `04fb4fa feat: implement AES core engine`
- **Latest Commits**:
  - `04fb4fa feat: implement AES core engine`
  - `cf21434 feat: implement PKCS#7 padding utility`
  - `3fb988e docs: fix API ambiguity...`
- **Working Tree**:
  - *Modified*: `CHANGELOG.md`, `docs/05_API_Interface_Spec.md`
  - *Untracked*: `.claude/`, `DECISIONS.md`, `docs/implementation/task2/`, `docs/research/AES/`, `docs/research/analysis/`, `docs/reviews/task2/`

## 2. Project Architecture
The actual architecture is explicitly defined in `docs/03_Architecture_Design.md` as a 5-layer design:
1. **Presentation Layer**: CLI interfaces
2. **Service Layer**: Algorithm orchestration (`cipher_factory.py`, `cipher_interface.py`, `context_manager.py`)
3. **Core Layer**: Cryptographic Implementations (`aes_cipher.py`, `rsa_cipher.py`, etc.)
4. **Analysis Layer**: Performance & Security Evaluation (`performance_timer.py`, `metric_collector.py`, `security_evaluator.py`, `graph_generator.py`)
5. **Persistence Layer**: Data storage and outputs (CSV export, image writing)

## 3. Current Project Status
- Task 1.1 — PKCS#7 Padding     🟢 CLOSED
- Task 1.2 — AES Core Engine    🟢 CLOSED
- Analysis System               🟡 NEXT
- Service Layer                 ⏳ LATER
- CLI                           ⏳ LATER
- Final Reporting               ⏳ LATER

## 4. Task 1.1 Reconstruction
- **Files**: `src/utils/padding.py`, `tests/test_padding.py`
- **Contract**: Functions `pad()`, `unpad()`, `is_padded()`, `get_padding_length()`. Supports block sizes 1-255.
- **Tests**: 30/30 passed, covering 2400 combinations of sizes and lengths.
- **Verification**: Independently reviewed and approved.
- **Commit**: `cf21434`
- **Final Status**: FROZEN / CLOSED.

## 5. Task 1.2 Reconstruction
- **Files**: `src/core/aes_cipher.py`, `tests/test_aes.py`
- **AES Modes**: Strictly ECB and CBC. (GCM/CTR are out of scope).
- **Key Sizes**: 128, 192, 256 bits.
- **IV Rules**: ECB takes `iv=None`. CBC requires exactly 16 bytes. `generate_iv()` uses `os.urandom`.
- **Padding**: Integrates `Padding.pad(..., 16)`.
- **Exceptions**: `ValueError` is strictly enforced for invalid inputs, padding failures, and key length errors. `InvalidTag` is intentionally excluded from ECB/CBC logic.
- **Validation Tests**: FIPS 197 and NIST SP 800-38A known-answer tests, invalid key behavior, padding failures, and round trips.
- **Tests**: 153/153 total tests PASSED.
- **Commit**: `04fb4fa`
- **Final Status**: FROZEN / CLOSED.

## 6. Changelog Verification
`CHANGELOG.md` explicitly lists "Sprint 1: AES Core + Padding" as fully checked off (✅) including modules and unit tests. The entries directly match the repository commit history and file state. There are no contradictions.

## 7. Analysis Research Audit
- **`REPORT 2.MD`**: Focuses on nanosecond-level precision using `time.perf_counter()`. Argues that 5 iterations is insufficient and mandates $\ge$ 50 for statistical validity. Recommends `psutil` (RSS) for memory tracking over alternatives. Details an IQR rule applied *only* if standard deviation $>10\%$ of the mean. Outlines the requirement to move `graph_generator.py` into the Analysis Layer. Reaffirms the `ValueError` contract over `InvalidTag`.
- **`RESEARCH ANALYSIS SYSTEM.md`**: Outlines equations and detailed formulas for Throughput (MB/s). Highlights the open conflict between the methodology document (5 iterations) and standard benchmarking needs (30+ iterations). Recommends standardizing binary megabytes (1 MB = 1,048,576 bytes).

## 8. Requirement Matrix

| Topic | Project Requirement | Approved Decision | Research Recommendation | Conflict? | Status |
|---|---|---|---|---|---|
| **Timing** | `time.perf_counter()` | - | - | No | REQUIRED |
| **Warmup iterations** | 2 iterations | - | 5-10 iterations | Yes | OPEN DECISION |
| **Measured iterations** | 5 iterations | - | 30 to 50+ iterations | Yes | OPEN DECISION |
| **Throughput** | MB/s | - | 1 MB = 1,048,576 bytes | No | RECOMMENDED |
| **Memory** | `memory_profiler` or `psutil` | - | Standardize on `psutil` | No | RECOMMENDED |
| **Statistics** | Mean, Median, StdDev | - | Report median as primary | No | REQUIRED |
| **IQR Filtering** | IQR for outliers | - | Only if StdDev > 10% mean | Yes | OPEN DECISION |
| **CSV schema** | Config + Metrics | - | Add environment metadata | No | RECOMMENDED |
| **Graphs** | Key, Mode, Throughput | - | Use Matplotlib, Bar/Line | No | REQUIRED |
| **Security analysis** | Avalanche, ECB Penguin | - | Avalanche target 45%-55% | No | REQUIRED |
| **Architecture** | Analysis Layer | - | `graph_generator.py` inside | No | RECOMMENDED |
| **Error handling** | - | `ValueError` for AES | Re-raise crypto errors | No | APPROVED |
| **Testing** | Integration tests | - | Validate correctness first | No | REQUIRED |

## 9. Conflicts / Ambiguities
1. **Iteration Counts**: `docs/04_Methodology.md` strictly requires 2 warmup and 5 measured iterations. The research strongly advises 50+ measured iterations for basic statistical validity.
2. **IQR Application Condition**: The methodology applies standard IQR removal across the board. The research advises running IQR removal *only* if the standard deviation exceeds 10% of the mean (due to mathematical instability on small sample sizes).

## 10. Decisions Already Locked
- **No `InvalidTag` for ECB/CBC**: Must raise `ValueError`.
- **Scope limitation**: AES engine implements only ECB and CBC. (GCM/CTR deferred).
- **Service Layer deferral**: Do not build `cipher_interface.py` or `cipher_factory.py` yet.
- **Task 1.1 / 1.2 Frozen**: No architecture redesigns or structural modifications for `padding.py` or `aes_cipher.py`.

## 11. Recommended Analysis System Architecture
The components fit perfectly into the established `docs/03_Architecture_Design.md` Analysis Layer:
- `src/analyzers/performance_timer.py`
- `src/analyzers/metric_collector.py`
- `src/analyzers/security_evaluator.py`
- `src/analyzers/graph_generator.py`

*Note: Generating the graph images happens in the Analysis Layer, but saving the physical `.png` and `.csv` files is the responsibility of the Persistence Layer.*

## 12. Proposed Implementation Sequence
The research proposal is justified by architectural dependencies:
1. `performance_timer.py` (Must exist to measure anything)
2. `metric_collector.py` (Depends on timer)
3. `security_evaluator.py` (Independent mathematical logic)
4. `graph_generator.py` (Depends on metric structures)

## 13. Exact Next Gate
**Methodology decisions** $\rightarrow$ **Implementation plan**
Before generating an implementation plan, the project must explicitly declare its methodology rules regarding benchmarking sample sizes and IQR filtration triggers.

## 14. Final Verdict
🟠 **BLOCKED — DECISION REQUIRED**
The Analysis System cannot be implemented immediately. While the architectural scope is clear, the core statistical parameters in `docs/04_Methodology.md` (5 iterations) fundamentally conflict with the statistical minimums required to generate defensible metrics and use IQR filtering effectively. These parameters directly govern the internal logic of `metric_collector.py` and must be formally resolved before an implementation plan is drafted.
