# Visualizer Artifact Lifecycle Implementation Plan

## Goal Description
Implement the authorized explicit artifact lifecycle for the Live Workflow Visualizer. The visualizer will separate temporary inputs from permanent output, persisting encryption and decryption artifacts directly to `results/visualizer_outputs/` with collision-safe naming. Decryption will mandate explicit file selection for `.enc`, `.key`, and `.iv`, supported by an optional sidecar auto-detection bridge.

## User Review Required
- **Collision Naming Scheme**: The plan specifies appending an underscore and incrementing integer (e.g. `file_1.enc`) upon collision.
- **Output Hierarchy**: Artifacts are strictly partitioned into `results/visualizer_outputs/encryption/` and `results/visualizer_outputs/decryption/`.

## Proposed Changes

---

### `visualizer/server.py`

#### [MODIFY] `server.py`
- **Add `/api/open_folder` Endpoint**: Takes a `path` parameter. Validates the path is confined within `results/visualizer_outputs/`. Dispatches `webbrowser.open(f"file:///{absolute_path}")` to native OS explorer. Rejects unauthorized roots.
- **Add `/api/detect_sidecars` Endpoint**: Takes a `path` parameter (the `.enc` file). Validates path existence and strict confinement to `results/visualizer_staging/` or `results/visualizer_outputs/`, then delegates to `KeyManager.auto_detect_sidecars(path)` to search for `.key` and `.iv` exactly adjacent to the selected ciphertext. Returns a JSON mapping of found sidecars.
- **Update `/api/run/decrypt` Validation**: Update pre-flight checks in `do_POST` to mandate `enc_path`, `key_path`, and (if CBC) `iv_path`.

---

### `visualizer/telemetry_bridge.py`

#### [MODIFY] `telemetry_bridge.py`
- **Implement Path Security Enforcement**: Add a helper `_enforce_path_security(path: Path) -> Path` that resolves the path and ensures `is_relative_to(STAGING_DIR)` or `is_relative_to(OUTPUTS_DIR)`. Reject with `ValueError` otherwise.
- **Implement Session-Level Collision Helper**: Add an internal helper `_allocate_artifact_stem(dest_dir: Path, basename: str) -> str` that determines a single collision-safe stem (e.g., `sample`, `sample_1`) by ensuring `[stem].enc`, `[stem].key`, and `[stem].iv` do not exist.
- **Update `_run_single`**:
  - Ensure the AES key is generated dynamically.
  - After ciphertext is produced, allocate one artifact stem for the entire session.
  - Write the `[stem].enc`, `[stem].key`, and `[stem].iv` (if CBC) bytes into `results/visualizer_outputs/encryption/`.
  - Strip raw key/IV from SSE events. Add `"output_dir"`, `"enc_path"`, `"key_path"`, and `"iv_path"` to the `"STAGE_COMPLETE"` event payload metadata.
- **Update `_run_decrypt`**:
  - Replace `file_path` single input with `enc_path`, `key_path`, and `iv_path`.
  - Read input bytes from these specific paths.
  - After successful decryption, write the plaintext to `results/visualizer_outputs/decryption/` using the collision-safe helper.
  - Add `"output_dir"` and `"plaintext_path"` to the `"STAGE_COMPLETE"` payload metadata.

---

### `visualizer/static/visualizer.js`

#### [MODIFY] `visualizer.js`
- **Update Decryption UI Elements**:
  - Replace single file picker with three distinct `filePicker` elements for `.enc`, `.key`, and `.iv`.
  - Add logic to disable/hide `.iv` input when ECB mode is selected.
  - When `.enc` is staged, trigger `/api/detect_sidecars`. If positive, visually alert user "✓ Matching sidecar files detected" and populate the logical paths for the backend.
- **Add "Open Output Folder" action**:
  - On `STAGE_COMPLETE` for Single and Decrypt workflows, render a button that hits `/api/open_folder` passing the `output_dir` from the telemetry payload.

---

### Tests

#### [MODIFY] `tests/visualizer/test_server.py`
- Add `test_detect_sidecars_endpoint`: Stage dummy files, query endpoint, verify correct mapping.
- Add `test_open_folder_endpoint`: Verify security bounds checking prevents traversal outside `results/`.
- Add `test_detect_sidecars_rejects_path_outside_allowed_roots`: Pass arbitrary external paths and assert HTTP 400/403.
- Update `test_missing_required_inputs_returns_400`: Expand decrypt payload validation (missing `.key`, `.iv`).
- Add `test_rejects_decryption_path_outside_allowed_roots`: Pass arbitrary external paths to decryption API, assert HTTP 400/403 and no filesystem read occurs.

#### [MODIFY] `tests/visualizer/test_telemetry.py`
- Add `test_e2e_encryption_lifecycle`: Trigger single encrypt, assert collision-safe files appear in `results/visualizer_outputs/encryption/`.
- Add `test_e2e_decryption_lifecycle_cbc`: Trigger explicit decryption with staged `.enc`, `.key`, `.iv`, assert plaintext is written and matches original.
- Add `test_e2e_decryption_lifecycle_ecb`: Trigger ECB decryption, verify IV is ignored.
- Add `test_artifact_collision_safety`: Trigger encryption twice for the same input, assert `_1` suffixes are correctly generated without clobbering.

## Verification Plan
1. **Automated Tests**: Run `python -m pytest tests/visualizer/` to verify all lifecycle constraints, safety boundaries, and negative assertions.
2. **Global Integration**: Run `python -m pytest` to ensure `CipherService` and `KeyManager` remain untouched and functional across legacy apps.
3. **Manual Validation (Deferred)**: Final confirmation of OS integration (`webbrowser.open`) behavior within standard Chrome environments post-implementation.
