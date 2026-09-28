"""
Unit and integration tests for VisualizerServer and VisualizerRequestHandler in src.visualizer.server.
"""

from __future__ import annotations

import errno
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.visualizer.server import VisualizerServer, WSAEADDRINUSE
from src.visualizer.telemetry_bridge import TelemetryBridge


class TestVisualizerServer:
    """Verifies server initialization, static routing, REST endpoints, and lifecycle."""

    @pytest.fixture
    def live_server(self):
        """Create and start a live test server on an ephemeral port."""
        server = VisualizerServer(port=0)
        server.start()
        # Wait a moment for server thread to start
        time.sleep(0.1)
        yield server
        server.shutdown()

    def test_static_asset_serving(self, live_server: VisualizerServer) -> None:
        """Verify server serves index.html, visualizer.css, and visualizer.js."""
        base_url = live_server.server_url

        # 1. Index
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type")
            content = resp.read().decode("utf-8")
            assert "CRYPTOGRAPHY TESTING LAB" in content

        # 2. CSS
        with urllib.request.urlopen(f"{base_url}/visualizer.css") as resp:
            assert resp.status == 200
            assert "text/css" in resp.headers.get("Content-Type")

        # 3. JS
        with urllib.request.urlopen(f"{base_url}/visualizer.js") as resp:
            assert resp.status == 200
            assert "application/javascript" in resp.headers.get("Content-Type")

    def test_api_status_endpoint(self, live_server: VisualizerServer) -> None:
        """Verify /api/status returns idle state and bound port."""
        url = f"{live_server.server_url}/api/status"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "idle"
            assert data["active_workflow"] is None
            assert data["port"] == live_server.port

    def test_api_explain_endpoint(self, live_server: VisualizerServer) -> None:
        """Verify /api/explain returns full node documentation dictionary."""
        url = f"{live_server.server_url}/api/explain"
        with urllib.request.urlopen(url) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert "node_aes_cipher" in data
            assert data["node_aes_cipher"]["module"] == "src.core.aes.AESCipher"
            assert "node_metric_collector" in data

    def test_workflow_run_trigger_and_concurrency_lock(self, live_server: VisualizerServer, tmp_path) -> None:
        """Verify POST /api/run/<mode> returns 202, and concurrent calls return 409."""
        from src.visualizer.server import STAGING_DIR
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        import time
        dummy_file = STAGING_DIR / f"dummy_{int(time.time()*1000)}.txt"
        dummy_file.write_bytes(b"content")

        url = f"{live_server.server_url}/api/run/single"
        req = urllib.request.Request(
            url,
            data=json.dumps({"key_size": 256, "mode": "CBC", "file_path": str(dummy_file)}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req) as resp:
            assert resp.status == 202
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "started"

        # While running, a second trigger should receive HTTP 409 Conflict
        with patch.object(live_server.bridge, "run_workflow_async", return_value=False):
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 409

    def test_missing_required_inputs_returns_400(self, live_server: VisualizerServer) -> None:
        """Verify endpoints return 400 when missing required input paths."""
        endpoints = [
            ("/api/run/single", {"key_size": 256}),
            ("/api/run/file_lab", {}),
            ("/api/run/decrypt", {}),
            ("/api/run/batch", {}),
        ]

        for ep, data in endpoints:
            req = urllib.request.Request(
                f"{live_server.server_url}{ep}",
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(req)
            assert exc_info.value.code == 400

    def test_targeted_port_fallback_on_addr_in_use(self) -> None:
        """Verify server retries on port 0 only when address is in use."""
        # 1. Simulate address in use (errno.EADDRINUSE)
        with patch("src.visualizer.server.ThreadingHTTPServer") as mock_httpd:
            in_use_error = OSError(errno.EADDRINUSE, "Address already in use")
            in_use_error.errno = errno.EADDRINUSE

            mock_instance = MagicMock()
            mock_instance.server_port = 54321
            mock_httpd.side_effect = [in_use_error, mock_instance]

            server = VisualizerServer(port=8765)
            assert server.port == 54321
            assert mock_httpd.call_count == 2
            # Second call was with port 0
            assert mock_httpd.call_args_list[1][0][0] == ("127.0.0.1", 0)

    def test_unrelated_socket_error_propagates(self) -> None:
        """Verify unrelated OSError (e.g. PermissionDenied / EACCES) propagates unmasked."""
        with patch("src.visualizer.server.ThreadingHTTPServer") as mock_httpd:
            perm_error = OSError(errno.EACCES, "Permission denied")
            perm_error.errno = errno.EACCES
            mock_httpd.side_effect = perm_error

            with pytest.raises(OSError) as exc_info:
                VisualizerServer(port=8765)
            assert exc_info.value.errno == errno.EACCES

    def test_safe_server_shutdown(self, live_server: VisualizerServer) -> None:
        """Verify shutdown closes the server cleanly without hanging."""
        assert not live_server.is_shutting_down
        live_server.shutdown()
        assert live_server.is_shutting_down

    def test_e2e_file_lab_report_generation(self, live_server: VisualizerServer, tmp_path) -> None:
        """Verify browser file -> staging -> FileAnalysisRunner -> HTML report works E2E."""
        # 1. Simulate browser uploading a file to /api/stage_file
        test_payload = b"Cryptography E2E Analysis Target File" * 1024  # ~38KB
        url_stage = f"{live_server.server_url}/api/stage_file"
        req_stage = urllib.request.Request(
            url_stage,
            data=test_payload,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(test_payload)),
                "X-Filename": "e2e_target.bin"
            },
            method="POST",
        )

        with urllib.request.urlopen(req_stage) as resp:
            assert resp.status == 200
            stage_data = json.loads(resp.read().decode("utf-8"))
            assert stage_data["status"] == "staged"
            assert "file_path" in stage_data
            staged_file_path = stage_data["file_path"]

        # 2. Trigger File Lab workflow on the staged file
        url_run = f"{live_server.server_url}/api/run/file_lab"
        req_run = urllib.request.Request(
            url_run,
            data=json.dumps({"file_path": staged_file_path}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_run) as resp:
            assert resp.status == 202

        # 3. Wait for the workflow to complete via SSE
        import queue
        q = live_server.bridge.subscribe()
        report_path = None

        # Give the background thread time to run the analysis (which takes time)
        timeout = time.time() + 10.0
        while time.time() < timeout:
            try:
                event = q.get(timeout=1.0)
                if event["workflow"] == "file_lab" and event["stage"] == "STAGE_COMPLETE":
                    report_path = event["data"].get("report_path")
                    break
            except queue.Empty:
                pass

        live_server.bridge.unsubscribe(q)
        assert report_path is not None, "Did not receive STAGE_COMPLETE with report_path"

        # 4. Verify the report path is accepted by /api/open_report
        # (We use a mock for webbrowser.open so it doesn't pop up)
        with patch("src.visualizer.server.webbrowser.open") as mock_open:
            url_open = f"{live_server.server_url}/api/open_report?path={urllib.parse.quote(report_path)}"
            with urllib.request.urlopen(url_open) as resp:
                assert resp.status == 200
                data = json.loads(resp.read().decode("utf-8"))
                assert data["status"] == "opened"

            mock_open.assert_called_once()
            call_arg = mock_open.call_args[0][0]
            assert call_arg.startswith("file://")
            assert call_arg.endswith(".html")

    def test_batch_duplicate_filename_staging(self, live_server: VisualizerServer) -> None:
        """Verify batch staging safely renames duplicate basenames in a flat directory."""
        payload = b"test payload"
        import time
        test_batch_id = f"test_batch_{int(time.time() * 1000)}"

        # Upload first file
        req1 = urllib.request.Request(
            f"{live_server.server_url}/api/stage_batch_file",
            data=payload,
            headers={
                "Content-Length": str(len(payload)),
                "X-Filename": "duplicate.txt",
                "X-Batch-ID": test_batch_id
            },
            method="POST",
        )
        with urllib.request.urlopen(req1) as resp:
            data1 = json.loads(resp.read().decode("utf-8"))
            assert data1["status"] == "staged"
            assert data1["filename"] == "duplicate.txt"
            path1 = Path(data1["file_path"])
            assert path1.exists()

        # Upload second file with SAME basename and SAME batch ID
        req2 = urllib.request.Request(
            f"{live_server.server_url}/api/stage_batch_file",
            data=payload,
            headers={
                "Content-Length": str(len(payload)),
                "X-Filename": "duplicate.txt",
                "X-Batch-ID": test_batch_id
            },
            method="POST",
        )
        with urllib.request.urlopen(req2) as resp:
            data2 = json.loads(resp.read().decode("utf-8"))
            assert data2["status"] == "staged"
            assert data2["filename"] == "duplicate.txt"

            path2 = Path(data2["file_path"])
            assert path2.exists()
            assert path2.name == "duplicate_1.txt"
            assert path1 != path2

    def test_open_folder_endpoint(self, live_server) -> None:
        import urllib.request
        import urllib.error
        from pathlib import Path
        malicious_path = str((Path.cwd() / "results" / "visualizer_outputs" / ".." / "..").resolve())
        req = urllib.request.Request(f"{live_server.server_url}/api/open_folder?path={urllib.parse.quote(malicious_path)}")
        try:
            with urllib.request.urlopen(req) as response:
                assert False, "Should have thrown HTTPError"
        except urllib.error.HTTPError as e:
            assert e.code == 403

    def test_detect_sidecars_endpoint_and_security(self, live_server, tmp_path) -> None:
        import urllib.request
        import urllib.error
        import urllib.parse
        import json
        from pathlib import Path
        from src.visualizer.server import OUTPUTS_DIR
        enc_dir = OUTPUTS_DIR / "encryption"
        enc_dir.mkdir(parents=True, exist_ok=True)
        enc_file = enc_dir / "test.enc"
        key_file = enc_dir / "test.enc.key"
        enc_file.write_bytes(b"data")
        key_file.write_bytes(b"key")

        req = urllib.request.Request(f"{live_server.server_url}/api/detect_sidecars?path={urllib.parse.quote(str(enc_file))}")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            assert data["status"] == "detected"
            assert data["key"] == str(key_file)
            assert data["iv"] is None

        malicious_path = str(tmp_path / "test.enc")
        Path(malicious_path).write_bytes(b"data")
        req = urllib.request.Request(f"{live_server.server_url}/api/detect_sidecars?path={urllib.parse.quote(malicious_path)}")
        try:
            with urllib.request.urlopen(req) as response:
                assert False, "Should have thrown 403"
        except urllib.error.HTTPError as e:
            assert e.code == 403

    def test_rejects_decryption_path_outside_allowed_roots(self, live_server, tmp_path) -> None:
        import urllib.request
        import urllib.error
        import json
        from pathlib import Path
        malicious_enc = str(tmp_path / "bad.enc")
        malicious_key = str(tmp_path / "bad.key")
        Path(malicious_enc).write_bytes(b"data")
        Path(malicious_key).write_bytes(b"key")

        payload = json.dumps({"enc_path": malicious_enc, "key_path": malicious_key, "mode": "ECB"}).encode()
        req = urllib.request.Request(f"{live_server.server_url}/api/run/decrypt", data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                assert False, "Should have thrown 403 immediately at HTTP boundary"
        except urllib.error.HTTPError as e:
            assert e.code == 403
