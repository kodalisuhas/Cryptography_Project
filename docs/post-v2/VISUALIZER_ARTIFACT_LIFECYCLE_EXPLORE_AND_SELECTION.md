# Visualizer Artifact Lifecycle: Explore & Selection Revision

## 1. Goal Description
The current Live Workflow Visualizer successfully demonstrates cryptographic operations by invoking the frozen V2 backend. However, it lacks a complete, explicit, and secure artifact lifecycle. Operations merely stage inputs and report metrics, failing to securely direct generated artifacts (`.enc`, `.key`, `.iv`, and decrypted plaintext) to designated output locations.

The goal is to design a secure, explicit, user-facing artifact workflow for both encryption and decryption within the visualizer, explicitly separating temporary input staging from permanent artifact persistence.

---

## 2. Encryption Output Artifact Model

When a user executes the Single-File Encryption workflow, the visualizer will:
1. **Retain standard backend artifacts**: The frozen `CipherService` inherently yields a ciphertext payload, a decryption key, and an IV (for CBC).
2. **Project-managed output**: Since browsers cannot write arbitrary paths via `fetch`, all generated artifacts are persisted under the deterministic project-managed output directory:
   - **Target Directory**: `results/visualizer_outputs/encryption/`
   - **Files**: `[basename].enc`, `[basename].key`, `[basename].iv` (if CBC).
   - **Collision-Safe Naming**: If an artifact already exists (e.g., `sample.enc`), the backend will never silently overwrite it. It will dynamically append an incrementing suffix (e.g., `sample_1.enc`, `sample_1.key`, `sample_1.iv`) to guarantee distinct output sessions are preserved safely.
3. **User Feedback (Manifest)**: The UI will display an "Encryption Complete" manifest showing the input checksum, cipher configuration, artifact paths, and verification status.
4. **Actionable OS Bridge**: The UI will provide an `[ Open Output Folder ]` button. This will trigger a backend API (`/api/open_folder?path=...`) that safely dispatches `webbrowser.open(f"file:///{absolute_path}")` to open the user's native file explorer.

---

## 3. Decryption Input Model

Decryption requires three inputs (Ciphertext, Key, IV). The visualizer will replace its single file picker with an explicit, robust dependency model.

1. **UX Layout**:
   - `[ Choose .enc File ]`
   - `[ Choose .key File ]`
   - `[ Choose .iv File ]` (Disabled/Hidden if ECB mode is selected)

2. **Convenient Sidecar Mode (Auto-detection)**:
   - When the user selects the `.enc` file, the UI will invoke an API (`/api/detect_sidecars`).
   - The backend will utilize the frozen `KeyManager.auto_detect_sidecars(file_path)` to check for sidecars. Auto-detection is performed relative to the selected ciphertext artifact's directory, subject to the existing `KeyManager` contract (not merely assuming a temporary staging location).
   - If sidecars exist, the UI will automatically pre-fill the logical key/IV requirements and present: `✓ Matching sidecar files detected`.
   - The user may opt to override this and manually select different `.key` or `.iv` files.

---

## 4. Plaintext Output Behavior

Upon successful decryption, the visualizer will follow a similar explicit output protocol:
1. **Target Directory**: `results/visualizer_outputs/decryption/`
2. **File**: `[original_basename].decrypted.[ext]`
3. **Verification**:
   - Ensure decryption succeeded, PKCS#7 padding validation succeeded, and the plaintext artifact was written successfully.
   - **Optional**: If a known original plaintext is supplied (e.g., during an explicit round-trip test), compare `SHA-256(original) == SHA-256(decrypted)`. A standalone decryption workflow cannot make this comparison as the original plaintext is unknown.
4. **Actionable OS Bridge**: `[ Open Output Folder ]` button identical to the encryption workflow.

---

## 5. Artifact Privacy & Security Boundaries

The strict isolation between cryptographic secrets and the presentation layer must be rigidly maintained:
1. **No Raw Secrets in Telemetry**: Generated keys and IVs will **never** be converted to hex strings and transmitted via Server-Sent Events (SSE).
2. **Metadata Only**: The SSE payload will only announce the paths and file sizes of the generated artifacts (e.g., `key_path: ".../sample.txt.key", key_size: 32`).
3. **Server-Side Key Handling**: The `TelemetryBridge` and `KeyManager` will continue to handle raw key material purely in memory or on the local filesystem. The browser JS remains entirely ignorant of the cryptographic bytes.

---

## 6. Browser Filesystem Constraints

The architecture adheres to native browser constraints:
1. **No Absolute Path Prompts**: We will avoid attempting to use experimental/restricted browser File System Access APIs for output folders to ensure maximum compatibility.
2. **Deterministic Write**: All writes go unconditionally to `results/visualizer_outputs/`.
3. **Native Explorer Handoff**: The backend Python server (running locally) will bridge the gap by launching the OS file explorer targeting the deterministic output directory upon user request.

---

## 7. End-to-End Acceptance Tests

To verify this complete lifecycle, the integration test suite (`tests/visualizer/test_server.py` and `tests/visualizer/test_telemetry.py`) must implement comprehensive tests:

1. **Test: CBC Encryption Lifecycle**
   - Provide plaintext -> trigger encrypt -> assert `.enc`, `.key`, and `.iv` are generated in `results/visualizer_outputs/encryption/`.
2. **Test: ECB Encryption Lifecycle**
   - Provide plaintext -> trigger encrypt -> assert `.enc`, `.key` are generated (no `.iv`).
3. **Test: Full CBC Decryption Round-Trip**
   - Pass the explicit `.enc`, `.key`, `.iv` paths -> decrypt -> assert plaintext is generated in `results/visualizer_outputs/decryption/` -> assert `SHA-256(original) == SHA-256(decrypted)`.
4. **Negative Tests**:
   - Trigger decryption with missing `.key` -> HTTP 400.
   - Trigger decryption with missing `.iv` (in CBC mode) -> HTTP 400.
   - Trigger ECB decryption providing `.enc`, `.key`, and `.iv` -> IV is actively ignored/not required for successful ECB decryption.
   - Trigger decryption with incorrect key -> proper rejection without crashing.
5. **Test: Artifact Collision Safety**
   - Encrypt the same basename twice -> assert the existing artifact is preserved, and the new artifact receives a collision-safe name (e.g., `_1`).

---

## Next Steps

**Gate Request:** Please review this Visualizer Artifact Lifecycle specification. If this strategy aligns with your expectations, authorize it, and I will generate the corresponding `IMPLEMENTATION_PLAN.md` to begin coding.
