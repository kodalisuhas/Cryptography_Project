"""
Unit and integration tests for TelemetryBridge in src.visualizer.telemetry_bridge.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch
import pytest

from src.visualizer.telemetry_bridge import TelemetryBridge


class TestTelemetryBridge:
    """Verifies SSE event dispatch, mutex concurrency lock, and backend delegation."""

    def test_subscriber_event_dispatch(self) -> None:
        """Verify subscribers receive emitted events and unsubscription cleans up."""
        bridge = TelemetryBridge()
        q = bridge.subscribe()

        bridge.emit("single", "STAGE_TEST", "COMPLETE", {"test_key": "test_val"})

        event = q.get(timeout=1.0)
        assert event["workflow"] == "single"
        assert event["stage"] == "STAGE_TEST"
        assert event["status"] == "COMPLETE"
        assert event["data"]["test_key"] == "test_val"

        bridge.unsubscribe(q)
        assert q not in bridge._subscribers

    def test_single_workflow_mutex_lock(self) -> None:
        """Verify only one workflow can run at a time; competing triggers return False."""
        bridge = TelemetryBridge()

        # Simulate in-progress workflow by holding the lock
        bridge._lock.acquire()
        bridge._active_workflow = "single"
        try:
            assert bridge.is_busy is True
            assert bridge.active_workflow == "single"
            # Second call immediately returns False (HTTP 409)
            assert bridge.run_workflow_async("benchmark", {}) is False
        finally:
            bridge._active_workflow = None
            bridge._lock.release()

        # Mutex should now be free
        assert bridge.is_busy is False
        assert bridge.active_workflow is None

    def test_single_file_workflow_execution(self, tmp_path) -> None:
        """Verify single-file encryption delegates to CipherService and emits real metrics."""
        from src.visualizer.telemetry_bridge import STAGING_DIR
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        test_file = STAGING_DIR / f"test_single_{int(time.time()*1000)}.txt"
        test_file.write_bytes(b"Secret telemetry payload")

        bridge = TelemetryBridge()
        q = bridge.subscribe()

        bridge._run_single({"algorithm": "AES", "key_size": 256, "mode": "CBC", "file_path": str(test_file)})

        events = []
        while not q.empty():
            events.append(q.get_nowait())

        stages = [e["stage"] for e in events]
        assert "STAGE_INPUT" in stages
        assert "STAGE_KEY" in stages
        assert "STAGE_ENCRYPT" in stages
        assert "STAGE_VERIFY" in stages
        assert "STAGE_COMPLETE" in stages

        encrypt_event = next(e for e in events if e["stage"] == "STAGE_ENCRYPT")
        assert encrypt_event["data"]["elapsed_ms"] >= 0.0
        assert encrypt_event["data"]["ciphertext_size"] > 0
        assert "iv_bytes" in encrypt_event["data"]

        verify_event = next(e for e in events if e["stage"] == "STAGE_VERIFY")
        assert verify_event["data"]["verified"] is True

    def test_benchmark_workflow_delegation_and_public_api(self) -> None:
        """Verify benchmark delegates to BenchmarkService and consumes public DataFrames."""
        bridge = TelemetryBridge()
        q = bridge.subscribe()

        bridge._run_benchmark({})

        events = []
        while not q.empty():
            events.append(q.get_nowait())

        stages = [e["stage"] for e in events]
        assert "STAGE_CONFIG" in stages
        assert "STAGE_WARMUP" in stages
        assert "STAGE_COMPLETE" in stages

        complete_event = next(e for e in events if e["stage"] == "STAGE_COMPLETE")
        data = complete_event["data"]
        # Exactly 30 raw observation timings collected
        assert len(data["raw_times_ms"]) == 30
        assert data["mean_ms"] >= 0.0
        assert "q1_ms" in data
        assert "q3_ms" in data
        assert "iqr_ms" in data
        assert "outlier_count" in data

    def test_security_workflow_delegation_and_descriptive_reference(self) -> None:
        """Verify security delegates to SecurityService and provides descriptive reference notes."""
        bridge = TelemetryBridge()
        q = bridge.subscribe()

        bridge._run_security({})

        events = []
        while not q.empty():
            events.append(q.get_nowait())

        stages = [e["stage"] for e in events]
        assert "STAGE_MUTATION" in stages
        assert "STAGE_COMPLETE" in stages

        complete_event = next(e for e in events if e["stage"] == "STAGE_COMPLETE")
        data = complete_event["data"]
        assert "avalanche_effect_pct" in data
        assert "key_sensitivity_pct" in data
        # Descriptive reference, zero pass/fail threshold claims
        assert "Approximately 50%" in data["avalanche_reference_note"]

    def test_batch_workflow_progress_callbacks(self, tmp_path) -> None:
        """Verify batch delegates to BatchOrchestrator and receives real-time progress events."""
        from src.visualizer.telemetry_bridge import STAGING_DIR
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        src_dir = STAGING_DIR / f"source_{int(time.time()*1000)}"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "doc.txt").write_bytes(b"content" * 10)

        bridge = TelemetryBridge()
        q = bridge.subscribe()

        bridge._run_batch({"folder_path": str(src_dir)})

        events = []
        while not q.empty():
            events.append(q.get_nowait())

        stages = [e["stage"] for e in events]
        assert "STAGE_PREFLIGHT" in stages
        assert "STAGE_FILE_PROGRESS" in stages
        assert "STAGE_COMPLETE" in stages

        complete_event = next(e for e in events if e["stage"] == "STAGE_COMPLETE")
        assert complete_event["data"]["total_files"] == 1
        assert complete_event["data"]["success_count"] == 1

    def test_file_lab_workflow_delegation(self, tmp_path) -> None:
        """Verify file lab delegates to FileAnalysisRunner with fastest observed semantics."""
        from src.visualizer.telemetry_bridge import STAGING_DIR
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        test_file = STAGING_DIR / f"lab_target_{int(time.time()*1000)}.bin"
        test_file.write_bytes(b"0" * 1024)

        bridge = TelemetryBridge()
        q = bridge.subscribe()

        bridge._run_file_lab({"file_path": str(test_file)})

        events = []
        while not q.empty():
            events.append(q.get_nowait())

        stages = [e["stage"] for e in events]
        assert "STAGE_PREFLIGHT" in stages
        assert "STAGE_COMPLETE" in stages

        complete_event = next(e for e in events if e["stage"] == "STAGE_COMPLETE")
        assert complete_event["data"]["total_configurations"] == 6
        assert "fastest_observed_encryption" in complete_event["data"]

    def test_e2e_encryption_lifecycle(self, tmp_path) -> None:
        """Trigger single encrypt, assert collision-safe files appear in outputs."""
        import time
        from pathlib import Path
        from src.visualizer.telemetry_bridge import STAGING_DIR, OUTPUTS_DIR
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        test_file = STAGING_DIR / f"lifecycle_{int(time.time()*1000)}.txt"
        test_file.write_bytes(b"Encrypt me")

        bridge = TelemetryBridge()
        q = bridge.subscribe()
        bridge._run_single({"algorithm": "AES", "key_size": 256, "mode": "CBC", "file_path": str(test_file)})

        enc_dir = OUTPUTS_DIR / "encryption"
        assert (enc_dir / f"{test_file.name}.enc").exists()
        assert (enc_dir / f"{test_file.name}.enc.key").exists()
        assert (enc_dir / f"{test_file.name}.enc.iv").exists()

    def test_artifact_collision_safety(self) -> None:
        """Trigger encryption twice for same input, assert _1 suffix."""
        import time
        from pathlib import Path
        from src.visualizer.telemetry_bridge import STAGING_DIR, OUTPUTS_DIR
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        test_file = STAGING_DIR / f"collision_{int(time.time()*1000)}.txt"
        test_file.write_bytes(b"Collide me")

        bridge = TelemetryBridge()
        q = bridge.subscribe()

        # First pass
        bridge._run_single({"algorithm": "AES", "key_size": 256, "mode": "CBC", "file_path": str(test_file)})
        enc_dir = OUTPUTS_DIR / "encryption"

        assert (enc_dir / f"{test_file.name}.enc").exists()
        assert not (enc_dir / f"{test_file.stem}_1{test_file.suffix}.enc").exists()

        # Second pass
        bridge._run_single({"algorithm": "AES", "key_size": 256, "mode": "CBC", "file_path": str(test_file)})

        assert (enc_dir / f"{test_file.stem}_1{test_file.suffix}.enc").exists()
        assert (enc_dir / f"{test_file.stem}_1{test_file.suffix}.enc.key").exists()
        assert (enc_dir / f"{test_file.stem}_1{test_file.suffix}.enc.iv").exists()

    def test_e2e_decryption_lifecycle_cbc(self) -> None:
        """Trigger explicit CBC decryption."""
        import time
        from src.visualizer.telemetry_bridge import STAGING_DIR, OUTPUTS_DIR
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        test_file = STAGING_DIR / f"cbc_dec_{int(time.time()*1000)}.txt"
        test_file.write_bytes(b"CBC decrypt payload")

        bridge = TelemetryBridge()
        q = bridge.subscribe()
        bridge._run_single({"algorithm": "AES", "key_size": 256, "mode": "CBC", "file_path": str(test_file)})

        enc_dir = OUTPUTS_DIR / "encryption"
        enc_path = enc_dir / f"{test_file.name}.enc"
        key_path = enc_dir / f"{test_file.name}.enc.key"
        iv_path = enc_dir / f"{test_file.name}.enc.iv"

        bridge._run_decrypt({"algorithm": "AES", "key_size": 256, "mode": "CBC", "enc_path": str(enc_path), "key_path": str(key_path), "iv_path": str(iv_path)})

        dec_dir = OUTPUTS_DIR / "decryption"
        dec_path = dec_dir / f"{test_file.name}"
        assert dec_path.exists()
        assert dec_path.read_bytes() == b"CBC decrypt payload"

    def test_e2e_decryption_lifecycle_ecb(self) -> None:
        """Trigger explicit ECB decryption, verify IV is ignored/not required."""
        import time
        from src.visualizer.telemetry_bridge import STAGING_DIR, OUTPUTS_DIR
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        test_file = STAGING_DIR / f"ecb_dec_{int(time.time()*1000)}.txt"
        test_file.write_bytes(b"ECB decrypt payload")

        bridge = TelemetryBridge()
        q = bridge.subscribe()
        bridge._run_single({"algorithm": "AES", "key_size": 256, "mode": "ECB", "file_path": str(test_file)})

        enc_dir = OUTPUTS_DIR / "encryption"
        enc_path = enc_dir / f"{test_file.name}.enc"
        key_path = enc_dir / f"{test_file.name}.enc.key"

        bridge._run_decrypt({"algorithm": "AES", "key_size": 256, "mode": "ECB", "enc_path": str(enc_path), "key_path": str(key_path), "iv_path": "anything (ignored)"})

        dec_dir = OUTPUTS_DIR / "decryption"
        dec_path = dec_dir / f"{test_file.name}"
        assert dec_path.exists()
        assert dec_path.read_bytes() == b"ECB decrypt payload"
