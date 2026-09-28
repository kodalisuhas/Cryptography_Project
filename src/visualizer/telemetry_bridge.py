"""
Telemetry Bridge for the Live Cryptography Workflow Visualizer.

Acts as the exclusive presentation adapter between the web server and the
frozen V1/V2 backends. Enforces single-workflow concurrency via a mutex,
dispatches real-time SSE events, and delegates all cryptographic operations
directly to the authoritative services without recreating workflow logic.
"""

from __future__ import annotations

import datetime
import hashlib
import queue
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from src.analysis_lab.runner import FileAnalysisRunner
from src.cli_v2.batch_orchestrator import BatchOrchestrator
from src.cli_v2.key_manager import KeyManager
from src.engines.benchmark_service import BenchmarkService
from src.engines.cipher_factory import CipherFactory
from src.engines.cipher_service import CipherService
from src.engines.security_service import SecurityService
from src.utils.file_handler import FileHandler


def _create_minimal_bmp(width: int = 16, height: int = 16) -> bytes:
    """Generate minimal valid 24-bpp uncompressed BMP image bytes."""
    row_bytes = width * 3
    row_stride = ((row_bytes + 3) // 4) * 4
    pixel_data_size = row_stride * height
    file_size = 54 + pixel_data_size

    header = bytearray(54)
    header[0:2] = b"BM"
    header[2:6] = file_size.to_bytes(4, "little")
    header[10:14] = (54).to_bytes(4, "little")
    header[14:18] = (40).to_bytes(4, "little")
    header[18:22] = width.to_bytes(4, "little", signed=True)
    header[22:26] = height.to_bytes(4, "little", signed=True)
    header[26:28] = (1).to_bytes(2, "little")
    header[28:30] = (24).to_bytes(2, "little")
    header[30:34] = (0).to_bytes(4, "little")
    header[34:38] = pixel_data_size.to_bytes(4, "little")

    # Generate distinct 8x8 checkerboard pattern
    pixel_data = bytearray(pixel_data_size)
    for y in range(height):
        row_offset = y * row_stride
        for x in range(width):
            color = 255 if ((x // 4) + (y // 4)) % 2 == 0 else 0
            pixel_offset = row_offset + (x * 3)
            pixel_data[pixel_offset] = color
            pixel_data[pixel_offset + 1] = color
            pixel_data[pixel_offset + 2] = color

    return bytes(header + pixel_data)


STAGING_DIR = (Path.cwd() / "results" / "visualizer_staging").resolve()
OUTPUTS_DIR = (Path.cwd() / "results" / "visualizer_outputs").resolve()


class TelemetryBridge:
    """Thread-safe telemetry adapter delegating to frozen cryptographic backends."""

    def __init__(
        self,
        cipher_service: CipherService | None = None,
        benchmark_service: BenchmarkService | None = None,
        security_service: SecurityService | None = None,
    ) -> None:
        self._cipher_service = cipher_service or CipherService()
        self._benchmark_service = benchmark_service or BenchmarkService()
        self._security_service = security_service or SecurityService()

        self._lock = threading.Lock()
        self._active_workflow: str | None = None

        self._subscribers_lock = threading.Lock()
        self._subscribers: list[queue.Queue] = []

    @property
    def active_workflow(self) -> str | None:
        """Return the ID of the currently executing workflow, or None if idle."""
        return self._active_workflow

    @property
    def is_busy(self) -> bool:
        """True when a workflow is currently executing."""
        return self._active_workflow is not None

    def subscribe(self) -> queue.Queue:
        """Register a new SSE client subscriber queue."""
        q: queue.Queue = queue.Queue(maxsize=1000)
        with self._subscribers_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        """Unregister an SSE client subscriber queue."""
        with self._subscribers_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def emit(
        self,
        workflow: str,
        stage: str,
        status: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast a structured telemetry event to all active SSE subscribers."""
        event_payload = {
            "workflow": workflow,
            "stage": stage,
            "status": status,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "data": data or {},
        }
        with self._subscribers_lock:
            dead_queues = []
            for q in self._subscribers:
                try:
                    q.put_nowait(event_payload)
                except queue.Full:
                    dead_queues.append(q)
            for dead_q in dead_queues:
                if dead_q in self._subscribers:
                    self._subscribers.remove(dead_q)

    def _enforce_path_security(self, path: Path) -> Path:
        resolved = path.resolve()
        if not (resolved.is_relative_to(STAGING_DIR) or resolved.is_relative_to(OUTPUTS_DIR)):
            raise ValueError("Access denied: Path outside allowed roots")
        return resolved

    def _allocate_artifact_stem(self, dest_dir: Path, basename: str) -> str:
        dest_dir.mkdir(parents=True, exist_ok=True)
        stem = basename
        if not (dest_dir / f"{stem}.enc").exists() and not (dest_dir / f"{stem}.key").exists() and not (dest_dir / f"{stem}.iv").exists():
            return stem

        counter = 1
        b_stem = Path(basename).stem
        b_ext = Path(basename).suffix
        while True:
            candidate = f"{b_stem}_{counter}{b_ext}"
            if not (dest_dir / f"{candidate}.enc").exists() and not (dest_dir / f"{candidate}.key").exists() and not (dest_dir / f"{candidate}.iv").exists():
                return candidate
            counter += 1

    def run_workflow_async(
        self,
        mode: str,
        params: dict[str, Any] | None = None,
    ) -> bool:
        """
        Trigger asynchronous execution of a workflow mode.

        Returns True if workflow started, or False if another workflow is already active (HTTP 409).
        """
        if not self._lock.acquire(blocking=False):
            return False

        self._active_workflow = mode
        worker = threading.Thread(
            target=self._execute_wrapper,
            args=(mode, params or {}),
            daemon=True,
        )
        worker.start()
        return True

    def _execute_wrapper(self, mode: str, params: dict[str, Any]) -> None:
        """Internal worker executing the requested workflow within the mutex boundary."""
        try:
            self.emit(mode, "STAGE_INITIALIZING", "ACTIVE", {"mode": mode})

            if mode == "single":
                self._run_single(params)
            elif mode == "decrypt":
                self._run_decrypt(params)
            elif mode == "batch":
                self._run_batch(params)
            elif mode == "benchmark":
                self._run_benchmark(params)
            elif mode == "security":
                self._run_security(params)
            elif mode == "file_lab":
                self._run_file_lab(params)
            else:
                self.emit(mode, "STAGE_ERROR", "ERROR", {"error": f"Unknown workflow mode: {mode}"})

        except Exception as exc:
            self.emit(mode, "STAGE_ERROR", "ERROR", {"error": str(exc)})
        finally:
            self.emit(mode, "STAGE_FINISHED", "IDLE", {})
            self._active_workflow = None
            self._lock.release()

    # -------------------------------------------------------------------------
    # Delegated Workflow Implementations
    # -------------------------------------------------------------------------

    def _run_single(self, params: dict[str, Any]) -> None:
        """Single-file encryption and immediate in-memory round-trip verification."""
        file_path_str = params.get("file_path")
        if not file_path_str:
            raise ValueError("No input file selected. Please choose a file before starting the workflow.")

        file_path = self._enforce_path_security(Path(file_path_str))
        if not file_path.is_file():
            raise ValueError(f"Selected file not found: {file_path.name}")

        algorithm = str(params.get("algorithm", "AES")).upper()
        key_size = int(params.get("key_size", 256))
        mode = str(params.get("mode", "CBC")).upper()

        if key_size not in (128, 192, 256):
            raise ValueError(f"Invalid key_size: {key_size}")
        if mode not in ("CBC", "ECB"):
            raise ValueError(f"Invalid mode: {mode}")

        plaintext = file_path.read_bytes()
        sha256_hash = hashlib.sha256(plaintext).hexdigest()

        self.emit("single", "STAGE_INPUT", "ACTIVE", {
            "filename": file_path.name,
            "payload_bytes": len(plaintext),
            "sha256": sha256_hash,
            "algorithm": algorithm,
            "key_size": key_size,
            "mode": mode,
        })

        cipher = CipherFactory().create_cipher(algorithm, key_size, mode)
        key = cipher.generate_key()
        iv = cipher.generate_iv() if mode == "CBC" else None

        self.emit("single", "STAGE_KEY", "ACTIVE", {
            "key_status": f"AES-{key_size} Generated ✓ (Protected In-Memory)",
            "key_size": key_size,
            "mode": mode,
            "iv_status": "Generated (16 bytes)" if iv else "None (ECB Mode)",
        })

        # Measure wall execution latency around cipher_service.encrypt_data
        t0 = time.perf_counter()
        enc_res = self._cipher_service.encrypt_data(algorithm, key_size, mode, plaintext, key, iv)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        self.emit("single", "STAGE_ENCRYPT", "COMPLETE", {
            "elapsed_ms": round(elapsed_ms, 3),
            "ciphertext_size": len(enc_res.ciphertext),
            "iv_bytes": len(enc_res.iv) if enc_res.iv else 0,
        })

        # Round-trip verification via cipher_service.decrypt_data
        t1 = time.perf_counter()
        decrypted = self._cipher_service.decrypt_data(algorithm, key_size, mode, enc_res.ciphertext, key, enc_res.iv)
        dec_elapsed_ms = (time.perf_counter() - t1) * 1000.0
        verified = (decrypted == plaintext)

        enc_dir = OUTPUTS_DIR / "encryption"
        stem = self._allocate_artifact_stem(enc_dir, file_path.name)

        enc_path = enc_dir / f"{stem}.enc"
        key_path = Path(str(enc_path) + ".key")
        iv_path = Path(str(enc_path) + ".iv")

        enc_path.write_bytes(enc_res.ciphertext)
        KeyManager.save_key(key, key_path)
        if enc_res.iv:
            KeyManager.save_iv(enc_res.iv, iv_path)

        self.emit("single", "STAGE_VERIFY", "COMPLETE", {
            "verified": verified,
            "status": "PASSED (In-memory round-trip match verified)" if verified else "FAILED",
            "dec_elapsed_ms": round(dec_elapsed_ms, 3),
        })

        self.emit("single", "STAGE_COMPLETE", "COMPLETE", {
            "operation": "Single-File Encryption & Round-Trip Verification",
            "filename": file_path.name,
            "configuration": f"{algorithm}-{key_size}-{mode}",
            "plaintext_bytes": len(plaintext),
            "ciphertext_bytes": len(enc_res.ciphertext),
            "encrypt_elapsed_ms": round(elapsed_ms, 3),
            "decrypt_elapsed_ms": round(dec_elapsed_ms, 3),
            "verification": "MATCH_VERIFIED" if verified else "MATCH_FAILED",
            "output_dir": str(enc_dir),
            "enc_path": str(enc_path),
            "key_path": str(key_path),
            "iv_path": str(iv_path) if enc_res.iv else None,
        })

    def _run_decrypt(self, params: dict[str, Any]) -> None:
        """Standalone decryption workflow."""
        enc_path_str = params.get("enc_path")
        if not enc_path_str:
            raise ValueError("No ciphertext file selected.")

        enc_path = self._enforce_path_security(Path(enc_path_str))
        if not enc_path.is_file():
            raise ValueError(f"Selected encrypted file not found: {enc_path.name}")

        algorithm = str(params.get("algorithm", "AES")).upper()
        mode = str(params.get("mode", "CBC")).upper()

        key_path_str = params.get("key_path")
        if not key_path_str:
            raise ValueError("No key file selected.")
        key_path = self._enforce_path_security(Path(key_path_str))
        key, key_size = KeyManager.load_key(key_path)

        # Mode & IV Acquisition
        iv = None
        if mode == "CBC":
            iv_path_str = params.get("iv_path")
            if not iv_path_str:
                raise ValueError("CBC mode requires an IV sidecar (.iv).")
            iv_path = self._enforce_path_security(Path(iv_path_str))
            iv = KeyManager.load_iv(iv_path)

        ciphertext = enc_path.read_bytes()

        self.emit("decrypt", "STAGE_INGEST", "ACTIVE", {
            "filename": enc_path.name,
            "ciphertext_bytes": len(ciphertext),
            "mode": mode,
            "key_size": key_size,
            "has_iv": iv is not None,
            "key_status": "Loaded (Protected In-Memory)"
        })

        t0 = time.perf_counter()
        dec_bytes = self._cipher_service.decrypt_data(algorithm, key_size, mode, ciphertext, key, iv)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        dec_dir = OUTPUTS_DIR / "decryption"
        dec_dir.mkdir(parents=True, exist_ok=True)

        original_name = enc_path.name
        if original_name.lower().endswith(".enc"):
            suggested_name = original_name[:-4]
        else:
            suggested_name = f"{original_name}.dec"

        plaintext_path = dec_dir / suggested_name
        counter = 1
        while plaintext_path.exists():
            suggested_stem = Path(suggested_name).stem
            suggested_ext = Path(suggested_name).suffix
            new_name = f"{suggested_stem}_{counter}{suggested_ext}"
            plaintext_path = dec_dir / new_name
            counter += 1

        plaintext_path.write_bytes(dec_bytes)

        self.emit("decrypt", "STAGE_COMPLETE", "COMPLETE", {
            "operation": "Standalone Decryption",
            "filename": enc_path.name,
            "configuration": f"{algorithm}-{key_size}-{mode}",
            "ciphertext_bytes": len(ciphertext),
            "plaintext_bytes": len(dec_bytes),
            "elapsed_ms": round(elapsed_ms, 3),
            "integrity": "VALID_PKCS7_UNPADDED",
            "output_dir": str(dec_dir),
            "plaintext_path": str(plaintext_path),
        })

    def _run_batch(self, params: dict[str, Any]) -> None:
        """Batch operation delegated directly to BatchOrchestrator."""
        folder_path_str = params.get("folder_path")
        if not folder_path_str:
            raise ValueError("No input folder or files selected. Please select a folder before starting the batch workflow.")

        src_dir = self._enforce_path_security(Path(folder_path_str))
        if not src_dir.is_dir():
            raise ValueError(f"Selected batch folder not found: {src_dir.name}")

        with tempfile.TemporaryDirectory() as temp_dir:
            dest_dir = Path(temp_dir) / "destination"
            dest_dir.mkdir()

            self.emit("batch", "STAGE_PREFLIGHT", "ACTIVE", {
                "source_directory": src_dir.name,
                "file_count": len([f for f in src_dir.iterdir() if f.is_file()]),
                "policy": "skip",
            })

            def _on_progress(current: int, total: int, filename: str) -> None:
                self.emit("batch", "STAGE_FILE_PROGRESS", "ACTIVE", {
                    "current": current,
                    "total": total,
                    "filename": filename,
                })

            orchestrator = BatchOrchestrator(cipher_service=self._cipher_service)
            summary = orchestrator.run_batch_encrypt(
                source_dir=src_dir,
                dest_dir=dest_dir,
                algorithm="AES",
                key_size=256,
                mode="CBC",
                progress_callback=_on_progress,
            )

            file_outcomes = [
                {
                    "filename": r.source_file.name,
                    "size_bytes": r.size_bytes,
                    "elapsed_ms": round(r.elapsed_ms, 2),
                    "status": r.status,
                }
                for r in summary.results
            ]

            tput = (summary.total_bytes / 1048576.0) / (summary.total_time_ms / 1000.0) if summary.total_time_ms > 0 else 0.0

            self.emit("batch", "STAGE_COMPLETE", "COMPLETE", {
                "total_files": summary.total_files,
                "success_count": summary.success_count,
                "total_bytes": summary.total_bytes,
                "total_time_ms": round(summary.total_time_ms, 2),
                "throughput_mb_s": round(tput, 2),
                "files": file_outcomes,
            })

    def _run_benchmark(self, params: dict[str, Any]) -> None:
        """Benchmark suite delegated directly to BenchmarkService without loop recreation."""
        configs = [
            {"algorithm": "AES", "key_size": 128, "mode": "CBC"},
            {"algorithm": "AES", "key_size": 256, "mode": "CBC"},
            {"algorithm": "AES", "key_size": 128, "mode": "ECB"},
            {"algorithm": "AES", "key_size": 256, "mode": "ECB"},
        ]
        payload = b"\x00" * 1024  # 1 KB standard payload

        self.emit("benchmark", "STAGE_CONFIG", "ACTIVE", {
            "configurations": [f"{c['algorithm']}-{c['key_size']}-{c['mode']}" for c in configs],
            "payload_bytes": len(payload),
            "warmup_iterations": 5,
            "measured_iterations": 30,
        })

        self.emit("benchmark", "STAGE_WARMUP", "ACTIVE", {
            "message": "Executing 5 warmup cycles in frozen timing loop...",
        })

        # Frozen timing loop executes uninterrupted inside BenchmarkService
        collector = self._benchmark_service.run_performance_suite(configs, [payload])

        # Consume strictly public APIs: get_summary_dataframe and get_raw_dataframe
        summary_df = collector.get_summary_dataframe()
        raw_df = collector.get_raw_dataframe()

        summary_rows = summary_df.to_dict(orient="records")
        first_row = summary_rows[0] if summary_rows else {}

        # Extract exactly 30 observations for the first configuration
        first_config_raw = raw_df[
            (raw_df["algorithm"] == configs[0]["algorithm"])
            & (raw_df["key_size"] == configs[0]["key_size"])
            & (raw_df["mode"] == configs[0]["mode"])
        ]
        raw_times_30 = first_config_raw["elapsed_time_ms"].tolist()[:30]

        self.emit("benchmark", "STAGE_COMPLETE", "COMPLETE", {
            "sample_configuration": f"{configs[0]['algorithm']}-{configs[0]['key_size']}-{configs[0]['mode']}",
            "observation_count": len(raw_times_30),
            "raw_times_ms": [round(x, 4) for x in raw_times_30],
            "mean_ms": round(float(first_row.get("mean_time_ms", 0.0)), 4),
            "median_ms": round(float(first_row.get("median_time_ms", 0.0)), 4),
            "std_dev_ms": round(float(first_row.get("std_dev_time_ms", 0.0)), 4),
            "min_ms": round(float(first_row.get("min_time_ms", 0.0)), 4),
            "max_ms": round(float(first_row.get("max_time_ms", 0.0)), 4),
            "q1_ms": round(float(first_row.get("q1_ms", 0.0)), 4),
            "q3_ms": round(float(first_row.get("q3_ms", 0.0)), 4),
            "iqr_ms": round(float(first_row.get("iqr_ms", 0.0)), 4),
            "outlier_count": int(first_row.get("outlier_count", 0)),
            "throughput_mb_s": round(float(first_row.get("throughput_mb_s", 0.0)), 2),
            "all_configs_summary": [
                {
                    "config": f"{r['algorithm']}-{r['key_size']}-{r['mode']}",
                    "mean_ms": round(float(r["mean_time_ms"]), 4),
                    "throughput_mb_s": round(float(r["throughput_mb_s"]), 2),
                }
                for r in summary_rows
            ],
        })

    def _run_security(self, params: dict[str, Any]) -> None:
        """Security diffusion evaluation reusing authoritative V2 input conventions."""
        configs = [
            {"algorithm": "AES", "key_size": 256, "mode": "CBC"},
            {"algorithm": "AES", "key_size": 256, "mode": "ECB"},
        ]

        # Established V2 inputs (menu_v2.py lines 1326-1338)
        p1 = b"CryptographyTestingLabV2KeySafe!"[:16]
        p2 = bytearray(p1)
        p2[0] ^= 0x01
        plaintext2 = bytes(p2)

        k1 = b"\x01\x23\x45\x67\x89\xab\xcd\xef\xfe\xdc\xba\x98\x76\x54\x32\x10\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff"
        k2 = bytearray(k1)
        k2[0] ^= 0x01
        key2 = bytes(k2)

        iv = b"\x12\x34\x56\x78\x9a\xbc\xde\xf0\x0f\xed\xcb\xa9\x87\x65\x43\x21"
        image_bytes = _create_minimal_bmp(16, 16)

        self.emit("security", "STAGE_MUTATION", "ACTIVE", {
            "mutation_type": "single_bit",
            "bits_differing": 1,
            "plaintext_size_bytes": len(p1),
        })

        results = self._security_service.run_security_suite(
            configs=configs,
            plaintext1=p1,
            plaintext2=plaintext2,
            key1=k1,
            key2=key2,
            image_bytes=image_bytes,
            iv=iv,
        )

        cbc_res = results.get("AES-256-CBC", {})
        ecb_res = results.get("AES-256-ECB", {})

        avalanche_pct = float(cbc_res.get("avalanche_effect", 0.0))
        key_sens_pct = float(cbc_res.get("key_sensitivity", 0.0))
        ecb_weakness = ecb_res.get("ecb_weakness")

        self.emit("security", "STAGE_COMPLETE", "COMPLETE", {
            "avalanche_effect_pct": round(avalanche_pct, 2),
            "avalanche_reference_note": "Approximately 50% indicates strong one-bit diffusion.",
            "key_sensitivity_pct": round(key_sens_pct, 2),
            "key_sensitivity_reference_note": "Approximately 50% indicates strong one-bit key diffusion.",
            "ecb_pattern_leakage_analyzed": ecb_weakness is not None,
            "header_bytes": len(ecb_weakness["original_header"]) if ecb_weakness else 0,
            "pixel_bytes": len(ecb_weakness["original_pixel_data"]) if ecb_weakness else 0,
        })

    def _run_file_lab(self, params: dict[str, Any]) -> None:
        """File-specific analysis lab delegated directly to FileAnalysisRunner."""
        file_path_str = params.get("file_path")
        if not file_path_str:
            raise ValueError("No input file selected. Please choose a file before starting the workflow.")

        target_path = self._enforce_path_security(Path(file_path_str))
        if not target_path.is_file():
            raise ValueError(f"Selected file not found: {target_path.name}")

        sha256 = FileAnalysisRunner.compute_sha256(target_path)
        self.emit("file_lab", "STAGE_PREFLIGHT", "ACTIVE", {
            "filename": target_path.name,
            "file_size": target_path.stat().st_size,
            "sha256": sha256,
        })

        runner = FileAnalysisRunner(
            file_path=target_path,
            no_open=True,
            security_enabled=True,
        )
        result, report_path, exit_code = runner.run()

        if result is None or exit_code != 0:
            raise RuntimeError("FileAnalysisRunner failed to execute.")

        config_results = []
        for cfg in result.configurations:
            enc_mean = cfg.encryption_metrics.mean_ms if cfg.encryption_metrics else None
            dec_mean = cfg.decryption_metrics.mean_ms if cfg.decryption_metrics else None
            config_results.append({
                "config_name": cfg.config_name,
                "status": cfg.status,
                "enc_mean_ms": round(enc_mean, 4) if enc_mean else "N/A",
                "dec_mean_ms": round(dec_mean, 4) if dec_mean else "N/A",
            })

        self.emit("file_lab", "STAGE_COMPLETE", "COMPLETE", {
            "total_configurations": len(result.configurations),
            "fastest_observed_encryption": result.fastest_encryption_config or "None",
            "fastest_observed_decryption": result.fastest_decryption_config or "None",
            "report_path": str(report_path) if report_path else None,
            "configurations": config_results,
        })
