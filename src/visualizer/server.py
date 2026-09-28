"""
Zero-dependency Local HTTP & SSE Server for Live Cryptography Workflow Visualizer.

Serves local static assets (HTML/CSS/JS), provides REST workflow triggers,
and streams Server-Sent Events (SSE) from the TelemetryBridge.
"""

from __future__ import annotations

import errno
import json
import hashlib
import os
import urllib.parse
import webbrowser
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from src.visualizer.explain_data import EXPLAIN_NODES
from src.visualizer.telemetry_bridge import TelemetryBridge

STATIC_DIR = Path(__file__).parent / "static"
WSAEADDRINUSE = 10048

MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB
STAGING_DIR = (Path.cwd() / "results" / "visualizer_staging").resolve()
OUTPUTS_DIR = (Path.cwd() / "results" / "visualizer_outputs").resolve()
REPORTS_DIR = (Path.cwd() / "results" / "reports").resolve()


class VisualizerRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler supporting static assets, REST control, and SSE streams."""

    # Silence default console logging
    def log_message(self, format: str, *args: Any) -> None:
        pass

    @property
    def bridge(self) -> TelemetryBridge:
        return self.server.bridge  # type: ignore[attr-defined]

    @property
    def server_instance(self) -> VisualizerServer:
        return self.server.server_instance  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        """Handle static file requests and REST API GETs."""
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/visualizer.css":
            self._serve_file(STATIC_DIR / "visualizer.css", "text/css; charset=utf-8")
        elif path == "/visualizer.js":
            self._serve_file(STATIC_DIR / "visualizer.js", "application/javascript; charset=utf-8")
        elif path == "/api/status":
            self._send_json(200, {
                "status": "running" if self.bridge.is_busy else "idle",
                "active_workflow": self.bridge.active_workflow,
                "port": self.server.server_port,  # type: ignore[attr-defined]
            })
        elif path == "/api/explain":
            self._send_json(200, EXPLAIN_NODES)
        elif path == "/api/events":
            self._handle_sse_stream()
        elif path == "/api/open_report":
            query = self.path.split("?")
            if len(query) > 1:
                qs = urllib.parse.parse_qs(query[1])
                report_path_str = qs.get("path", [""])[0]
                if report_path_str:
                    target = Path(report_path_str).resolve()
                    if not target.is_relative_to(REPORTS_DIR):
                        self._send_json(403, {"error": "Access denied: Report path must be inside results/reports/"})
                        return
                    if target.is_file() and target.suffix.lower() == ".html":
                        webbrowser.open(target.as_uri())
                        self._send_json(200, {"status": "opened"})
                        return
            self._send_json(404, {"error": "Report not found or access denied"})
        elif path == "/api/open_folder":
            query = self.path.split("?")
            if len(query) > 1:
                qs = urllib.parse.parse_qs(query[1])
                folder_path_str = qs.get("path", [""])[0]
                if folder_path_str:
                    target = Path(folder_path_str).resolve()
                    if not target.is_relative_to(OUTPUTS_DIR):
                        self._send_json(403, {"error": "Access denied: Folder path must be inside results/visualizer_outputs/"})
                        return
                    if target.is_dir():
                        import subprocess
                        import sys
                        if sys.platform == "win32":
                            subprocess.Popen(["explorer", str(target)])
                        elif sys.platform == "darwin":
                            subprocess.Popen(["open", str(target)])
                        else:
                            subprocess.Popen(["xdg-open", str(target)])
                        self._send_json(200, {"status": "opened"})
                        return
            self._send_json(404, {"error": "Folder not found or access denied"})
        elif path == "/api/detect_sidecars":
            query = self.path.split("?")
            if len(query) > 1:
                qs = urllib.parse.parse_qs(query[1])
                enc_path_str = qs.get("path", [""])[0]
                if enc_path_str:
                    target = Path(enc_path_str).resolve()
                    # Allow sidecars in staging or outputs
                    if not target.is_relative_to(STAGING_DIR) and not target.is_relative_to(OUTPUTS_DIR):
                        self._send_json(403, {"error": "Access denied: Path outside allowed roots"})
                        return
                    if target.is_file():
                        from src.cli_v2.key_manager import KeyManager
                        key_path, iv_path = KeyManager.auto_detect_sidecars(target)

                        self._send_json(200, {
                            "status": "detected",
                            "key": str(key_path) if key_path else None,
                            "iv": str(iv_path) if iv_path else None
                        })
                        return
            self._send_json(404, {"error": "Not found"})
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self) -> None:
        """Handle REST API POST triggers and server shutdown."""
        path = self.path.split("?")[0]

        if path == "/api/stage_file" or path == "/api/stage_batch_file":
            content_len_str = self.headers.get("Content-Length", "0")
            content_len = int(content_len_str) if content_len_str.isdigit() else 0

            if content_len > MAX_UPLOAD_SIZE_BYTES:
                self._send_json(413, {"error": "File exceeds the visualizer's 100 MB input limit. Use the existing CLI File Analysis Lab for larger inputs."})
                return
            if content_len <= 0:
                self._send_json(400, {"error": "Empty upload payload"})
                return

            filename = urllib.parse.unquote(self.headers.get("X-Filename", "upload.bin"))
            # Prevent path traversal in filename
            filename = Path(filename).name

            dest_dir = STAGING_DIR
            if path == "/api/stage_batch_file":
                batch_id = self.headers.get("X-Batch-ID", "default")
                batch_id = "".join(c for c in batch_id if c.isalnum() or c in "-_")
                if not batch_id:
                    batch_id = "default"
                dest_dir = STAGING_DIR / f"batch_{batch_id}"

            dest_dir.mkdir(parents=True, exist_ok=True)
            staged_path = dest_dir / filename

            if path == "/api/stage_batch_file" and staged_path.exists():
                base = staged_path.stem
                ext = staged_path.suffix
                counter = 1
                while True:
                    staged_path = dest_dir / f"{base}_{counter}{ext}"
                    if not staged_path.exists():
                        break
                    counter += 1

            hasher = hashlib.sha256()
            bytes_written = 0
            chunk_size = 65536

            try:
                with open(staged_path, "wb") as f:
                    while bytes_written < content_len:
                        to_read = min(chunk_size, content_len - bytes_written)
                        chunk = self.rfile.read(to_read)
                        if not chunk:
                            break
                        hasher.update(chunk)
                        f.write(chunk)
                        bytes_written += len(chunk)

                if bytes_written != content_len:
                    staged_path.unlink(missing_ok=True)
                    self._send_json(400, {"error": f"Incomplete upload: expected {content_len} bytes, got {bytes_written}"})
                    return
            except Exception as exc:
                self._send_json(500, {"error": f"Failed to stage file: {exc}"})
                return

            self._send_json(200, {
                "status": "staged",
                "filename": filename,
                "size_bytes": bytes_written,
                "sha256": hasher.hexdigest().lower(),
                "file_path": str(staged_path),
                "folder_path": str(dest_dir) if path == "/api/stage_batch_file" else None
            })

        elif path.startswith("/api/run/"):
            mode = path[len("/api/run/"):]
            params = self._read_json_body()

            # HTTP-Boundary Trust Validation
            for key in ["file_path", "folder_path", "enc_path", "key_path", "iv_path"]:
                if key in params and params[key]:
                    try:
                        p = Path(params[key]).resolve()
                        if not (p.is_relative_to(STAGING_DIR) or p.is_relative_to(OUTPUTS_DIR)):
                            self._send_json(403, {"error": f"Access denied: Path for {key} is outside allowed roots"})
                            return
                    except Exception as e:
                        self._send_json(400, {"error": f"Invalid path for {key}: {e}"})
                        return


            if mode in ("single", "file_lab"):
                if not params.get("file_path"):
                    self._send_json(400, {"error": f"Missing required input: file_path is required for {mode} workflow."})
                    return
            elif mode == "decrypt":
                if not params.get("enc_path") or not params.get("key_path"):
                    self._send_json(400, {"error": "Missing required input: enc_path and key_path are required for decrypt workflow."})
                    return
                # CBC requires IV, ECB doesn't.
                cipher_mode = str(params.get("mode", "CBC")).upper()
                if cipher_mode == "CBC" and not params.get("iv_path"):
                    self._send_json(400, {"error": "Missing required input: iv_path is required for CBC decryption."})
                    return
            elif mode == "batch":
                if not params.get("folder_path"):
                    self._send_json(400, {"error": "Missing required input: folder_path is required for batch workflow."})
                    return

            started = self.bridge.run_workflow_async(mode, params)
            if started:
                self._send_json(202, {"status": "started", "workflow": mode})
            else:
                self._send_json(409, {
                    "error": "Workflow already in progress",
                    "active_workflow": self.bridge.active_workflow,
                })

        elif path == "/api/shutdown":
            self._send_json(200, {"status": "shutting_down"})
            # Gracefully trigger shutdown from a separate thread
            threading.Thread(target=self.server_instance.shutdown, daemon=True).start()

        else:
            self._send_json(404, {"error": "Not Found"})

    def _serve_file(self, filepath: Path, content_type: str) -> None:
        """Serve a static file from disk."""
        if not filepath.exists() or not filepath.is_file():
            self._send_json(404, {"error": f"File '{filepath.name}' not found"})
            return

        try:
            content = filepath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except OSError:
            self._send_json(500, {"error": "Failed to read file"})

    def _read_json_body(self) -> dict[str, Any]:
        """Read and parse optional JSON request body."""
        content_len = self.headers.get("Content-Length")
        if not content_len:
            return {}
        try:
            raw_body = self.rfile.read(int(content_len))
            return json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            return {}

    def _send_json(self, status_code: int, data: dict[str, Any]) -> None:
        """Send a JSON HTTP response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _handle_sse_stream(self) -> None:
        """Stream real-time events to connected browser client via Server-Sent Events."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        q = self.bridge.subscribe()
        try:
            # Send initial connected event
            init_msg = f"event: connect\ndata: {json.dumps({'status': 'connected', 'active_workflow': self.bridge.active_workflow})}\n\n"
            self.wfile.write(init_msg.encode("utf-8"))
            self.wfile.flush()

            while not self.server_instance.is_shutting_down:
                try:
                    event_data = q.get(timeout=1.0)
                    msg = f"event: workflow_event\ndata: {json.dumps(event_data)}\n\n"
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # Heartbeat comment to keep connection alive
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.bridge.unsubscribe(q)


class VisualizerServer:
    """Manages the lifecycle of the ThreadingHTTPServer daemon."""

    def __init__(
        self,
        port: int = 8765,
        bridge: TelemetryBridge | None = None,
    ) -> None:
        self.desired_port = port
        self.bridge = bridge or TelemetryBridge()
        self._is_shutting_down = False
        self._thread: threading.Thread | None = None

        # Targeted port binding with fallback on address-in-use
        try:
            self.httpd = ThreadingHTTPServer(("127.0.0.1", port), VisualizerRequestHandler)
        except OSError as exc:
            is_addr_in_use = (
                exc.errno == errno.EADDRINUSE
                or getattr(exc, "winerror", None) == WSAEADDRINUSE
                or exc.errno == WSAEADDRINUSE
            )
            if is_addr_in_use:
                # Fall back to OS-assigned ephemeral port
                self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), VisualizerRequestHandler)
            else:
                raise

        # Attach references for the handler
        self.httpd.bridge = self.bridge  # type: ignore[attr-defined]
        self.httpd.server_instance = self  # type: ignore[attr-defined]
        self.actual_port = self.httpd.server_port

    @property
    def port(self) -> int:
        """Actual bound local port."""
        return self.actual_port

    @property
    def server_url(self) -> str:
        """Localhost URL for browser dispatch."""
        return f"http://127.0.0.1:{self.actual_port}"

    @property
    def is_shutting_down(self) -> bool:
        """True when server shutdown has been initiated."""
        return self._is_shutting_down

    def start(self) -> None:
        """Start the server in a dedicated background daemon thread."""
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def shutdown(self) -> None:
        """Cleanly stop the server from accepting new requests."""
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
