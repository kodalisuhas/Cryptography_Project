
## 1. Previous Methodology

The old methodology specified:
- **Iterations:** 2 warmup iterations and 5 measured iterations.
- **Outliers:** Standard IQR method was used to silently remove measurements outside the bounds (`< Lower Bound` or `> Upper Bound`). Only after removal were final statistics calculated.
- **Research Conflict:** The research reports originally proposed a requirement of 50-100 iterations and an arbitrary rule to apply IQR filtering only if the standard deviation exceeded 10% of the mean.

## 2. Approved Decisions

The following methodology has been strictly applied:
- 5 warmup iterations
- 30 measured iterations (described as the project's selected experimental methodology, not a universal minimum)
- IQR calculated for every sample set (Tukey fences outlier detection)
- Raw observations preserved
- No SD > 10% trigger permitted
- No silent deletion of data

## 3. Files Modified

The primary file edited was:
- `docs/04_Methodology.md`

To ensure internal cross-document consistency regarding the iteration counts, the following documents were also updated (after identifying that they explicitly contradicted the new methodology by enforcing the old `5` iteration counts):
- `docs/02_System_Requirements.md`
- `docs/03_Architecture_Design.md`
- `docs/05_API_Interface_Spec.md`

## 4. Documentation Changes

**`docs/04_Methodology.md`**
- Updated the introductory "Threats to Validity" and "Data Size Variations" tables to specify 5 warmup / 30 measured iterations.
- Updated the Flowchart in Section 2.1 to reflect the new 5/30 sequence.
- Replaced the "Outlier Removal" step in the flowchart with "Outlier Flagging (Tukey Fences)", mandating that primary stats must be based on raw observations.
- Updated the `benchmark_config.yaml` code snippet defaults.
- Re-wrote Section "5.2 Outlier Methodology" to explicitly forbid silent deletion, define the Tukey fences, mandate the calculation of IQR for every sample, and enforce that raw stats (including sample count, mean, median, SD, min, max, Q1, Q3, and IQR) remain primary.
- Updated the Reproducibility Checklist to align with the new iterations and outlier rules.
- Re-wrote Recommendation #1 in the refinements section to state that the project's selected methodology of 5/30 was adopted.

**`docs/02_System_Requirements.md`**
- Updated `BENCHMARK_ITERATIONS=30` in the `.env` example.
- Updated Recommendation #6 to state that the default was changed to 30 to reflect the adopted methodology.

**`docs/03_Architecture_Design.md`**
- Updated `BENCHMARK_ITERATIONS = 30` and `BENCHMARK_WARMUP_ITERATIONS = 5` in the `Settings` class snippet.
- Updated Recommendation #3 to reflect the adopted threshold defaults.

**`docs/05_API_Interface_Spec.md`**
- Updated the `measure_time_with_warmup` decorator signature to `iterations: int = 30, warmup: int = 5`.
- Updated Recommendation #5 to reflect the adopted system defaults.

## 5. Consistency Audit

- System Requirements remain consistent (defaults matched to 30).
- Architecture remains consistent (settings matched to 30/5).
- API Specification remains consistent (decorators and recommendations matched).
- Research remains properly classified (historical analysis unchanged, current methodology is now the absolute source of truth).
- CHANGELOG remains consistent (no changes affecting completed tasks).

## 6. Regression / Scope Check

- Task 1.1 untouched
- Task 1.2 untouched
- source code untouched
- tests untouched
- no dependencies changed

## 7. Git Status

- **modified files:** 
  - `CHANGELOG.md` (from previous task)
  - `docs/02_System_Requirements.md`
  - `docs/03_Architecture_Design.md`
  - `docs/04_Methodology.md`
  - `docs/05_API_Interface_Spec.md`
- **untracked files:**
  - `.claude/`
  - `DECISIONS.md`
  - `docs/implementation/task2/`
  - `docs/implementation/task3/`
  - `docs/research/AES/`
  - `docs/research/analysis/`
  - `docs/reviews/task2/`
- **branch:** `dev`
- **HEAD:** `04fb4fa feat: implement AES core engine`

## 8. Final Verdict

**🟢 PASS — METHODOLOGY DECISIONS RESOLVED**