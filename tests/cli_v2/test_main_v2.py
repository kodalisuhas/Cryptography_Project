"""Tests for V2 CLI entrypoint and router."""
import pytest
from pathlib import Path
from src.cli_v2.main_v2 import main, parse_args, EXIT_SUCCESS, EXIT_RUNTIME, EXIT_USAGE

# --- Routing ---
def test_zero_args_dispatch(monkeypatch):
    calls = []
    class MockMenuV2:
        def display_main_menu(self): calls.append("display_main_menu")
    monkeypatch.setattr("src.cli_v2.main_v2.MenuV2", MockMenuV2)
    assert main([]) == EXIT_SUCCESS
    assert calls == ["display_main_menu"]

def test_menu_arg_dispatch(monkeypatch):
    calls = []
    class MockMenuV2:
        def display_main_menu(self): calls.append("display_main_menu")
    monkeypatch.setattr("src.cli_v2.main_v2.MenuV2", MockMenuV2)
    assert main(["menu"]) == EXIT_SUCCESS
    assert calls == ["display_main_menu"]

def test_direct_routing_encrypt(monkeypatch, tmp_path):
    calls = []
    class MockCipherService:
        class MockFactory:
            def create_cipher(self, alg, size, mode): return self
            def generate_key(self): return b"A" * 32
        factory = MockFactory()
        def encrypt_data(self, *args, **kwargs):
            calls.append("encrypt_data")
            from src.engines.cipher_service import EncryptionResult
            return EncryptionResult(b"cipher", b"1234567890123456")
        def decrypt_data(self, *args, **kwargs):
            calls.append("decrypt_data")
            return b"plain"
    monkeypatch.setattr("src.cli_v2.main_v2.CipherService", MockCipherService)
    p = tmp_path / "in.txt"
    p.write_bytes(b"plain")
    assert main(["encrypt", "--input", str(p), "--key-size", "256", "--mode", "CBC", "--generate-key"]) == EXIT_SUCCESS
    assert calls == ["encrypt_data", "decrypt_data"]

def test_direct_routing_decrypt(monkeypatch, tmp_path):
    calls = []
    class MockCipherService:
        def decrypt_data(self, *args, **kwargs):
            calls.append("decrypt_data")
            return b"plain"
    monkeypatch.setattr("src.cli_v2.main_v2.CipherService", MockCipherService)
    p = tmp_path / "in.enc"
    p.write_bytes(b"cipher")
    assert main(["decrypt", "--input", str(p), "--key-size", "256", "--mode", "ECB", "--key", "A" * 64]) == EXIT_SUCCESS
    assert calls == ["decrypt_data"]

def test_direct_routing_batch_encrypt(monkeypatch, tmp_path):
    calls = []
    class MockBatchOrchestrator:
        def __init__(self, svc): pass
        def run_batch_encrypt(self, *args, **kwargs):
            calls.append("run_batch_encrypt")
            from src.cli_v2.batch_orchestrator import BatchSummary
            return BatchSummary(1, 1, 0, 0, 100, 10.0, None, [])
    monkeypatch.setattr("src.cli_v2.main_v2.BatchOrchestrator", MockBatchOrchestrator)
    assert main(["batch-encrypt", "--input", str(tmp_path), "--key-size", "256", "--mode", "CBC"]) == EXIT_SUCCESS
    assert calls == ["run_batch_encrypt"]

def test_direct_routing_batch_decrypt(monkeypatch, tmp_path):
    calls = []
    class MockBatchOrchestrator:
        def __init__(self, svc): pass
        def run_batch_decrypt(self, *args, **kwargs):
            calls.append("run_batch_decrypt")
            from src.cli_v2.batch_orchestrator import BatchSummary
            return BatchSummary(1, 1, 0, 0, 100, 10.0, None, [])
    monkeypatch.setattr("src.cli_v2.main_v2.BatchOrchestrator", MockBatchOrchestrator)
    assert main(["batch-decrypt", "--input", str(tmp_path), "--key-size", "256", "--mode", "CBC"]) == EXIT_SUCCESS
    assert calls == ["run_batch_decrypt"]

def test_direct_routing_benchmark(monkeypatch):
    calls = []
    class MockBenchmarkService:
        def run_performance_suite(self, *args, **kwargs):
            calls.append("run_performance_suite")
            return None
    class MockReportGenerator:
        @staticmethod
        def build_benchmark_report(coll):
            calls.append("build_benchmark_report")
            return Path("rep.html")
        @staticmethod
        def open_in_browser(path):
            calls.append("open_in_browser")
    monkeypatch.setattr("src.cli_v2.main_v2.BenchmarkService", MockBenchmarkService)
    monkeypatch.setattr("src.cli_v2.main_v2.ReportGenerator", MockReportGenerator)
    assert main(["benchmark"]) == EXIT_SUCCESS
    assert calls == ["run_performance_suite", "build_benchmark_report", "open_in_browser"]

def test_direct_routing_security(monkeypatch):
    calls = []
    class MockSecurityService:
        def run_security_suite(self, *args, **kwargs):
            calls.append("run_security_suite")
            return {}
    class MockReportGenerator:
        @staticmethod
        def build_security_report(res):
            calls.append("build_security_report")
            return Path("sec.html")
        @staticmethod
        def open_in_browser(path):
            calls.append("open_in_browser")
    monkeypatch.setattr("src.cli_v2.main_v2.SecurityService", MockSecurityService)
    monkeypatch.setattr("src.cli_v2.main_v2.ReportGenerator", MockReportGenerator)
    assert main(["security"]) == EXIT_SUCCESS
    assert calls == ["run_security_suite", "build_security_report", "open_in_browser"]

def test_direct_routing_report(monkeypatch, tmp_path):
    calls = []
    class MockReportGenerator:
        @staticmethod
        def open_in_browser(path):
            calls.append("open_in_browser")
    monkeypatch.setattr("src.cli_v2.main_v2.ReportGenerator", MockReportGenerator)
    p = tmp_path / "rep.html"
    p.write_text("html")
    assert main(["report", "--input", str(p)]) == EXIT_SUCCESS
    assert calls == ["open_in_browser"]

# --- Interactive/Non-interactive Boundary ---
def test_no_interactive_fallback(monkeypatch, tmp_path):
    class TripwireMenuV2:
        def __getattr__(self, name):
            if name.startswith("run_") and name.endswith("_wizard"):
                def tripwire(*args, **kwargs):
                    raise AssertionError(f"{name} should never be called by direct CLI")
                return tripwire
            raise AttributeError(name)
    monkeypatch.setattr("src.cli_v2.main_v2.MenuV2", TripwireMenuV2)
    # Give all subcommands mocked failure (ValueErrors etc) or success, just verify no tripwire is hit
    def throw_val(*args, **kwargs): raise ValueError("test")
    monkeypatch.setattr("src.cli_v2.main_v2._handle_encrypt", throw_val)
    monkeypatch.setattr("src.cli_v2.main_v2._handle_decrypt", throw_val)
    monkeypatch.setattr("src.cli_v2.main_v2._handle_batch_encrypt", throw_val)
    monkeypatch.setattr("src.cli_v2.main_v2._handle_batch_decrypt", throw_val)
    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw_val)
    monkeypatch.setattr("src.cli_v2.main_v2._handle_security", throw_val)
    monkeypatch.setattr("src.cli_v2.main_v2._handle_report", throw_val)

    # These should all just return EXIT_RUNTIME, no AssertionError
    assert main(["encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--generate-key"]) == EXIT_RUNTIME
    assert main(["decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--key", "a"*64]) == EXIT_RUNTIME
    assert main(["batch-encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC"]) == EXIT_RUNTIME
    assert main(["batch-decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC"]) == EXIT_RUNTIME
    assert main(["benchmark"]) == EXIT_RUNTIME
    assert main(["security"]) == EXIT_RUNTIME
    assert main(["report", "--input", "a.html"]) == EXIT_RUNTIME

# --- Argparse Validation ---
def test_argparse_validations():
    cases = [
        ["encrypt"], # 11
        ["encrypt", "--input", "a", "--mode", "CBC", "--generate-key"], # 12
        ["encrypt", "--input", "a", "--key-size", "256", "--generate-key"], # 13
        ["encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC"], # 14
        ["encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--generate-key", "--key", "a"*64], # 15
        ["encrypt", "--input", "a", "--key-size", "256", "--mode", "ECB", "--generate-key", "--iv", "a"*32], # 16
        ["decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC"], # 17
        ["decrypt", "--input", "a", "--key-size", "256", "--mode", "ECB", "--key", "a"*64, "--iv", "a"*32], # 18
        ["encrypt", "--input", "a", "--key-size", "100", "--mode", "CBC", "--generate-key"], # 19
        ["encrypt", "--input", "a", "--key-size", "256", "--mode", "GCM", "--generate-key"], # 20
        ["batch-encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--on-conflict", "invalid"], # 21
        ["encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--generate-key", "--shared-key"], # 22
        ["decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--key", "a"*64, "--shared-key"], # 23
        ["benchmark", "--shared-key"], # 24
        ["security", "--shared-key"], # 25
        ["report", "--input", "a.html", "--shared-key"], # 26
        ["encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--generate-key", "--dry-run"], # 27
        ["decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--key", "a"*64, "--dry-run"], # 28
        ["benchmark", "--dry-run"], # 29
        ["security", "--dry-run"], # 30
        ["report", "--input", "a.html", "--dry-run"], # 31
        ["encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--generate-key", "--on-conflict", "skip"], # 32
        ["decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--key", "a"*64, "--on-conflict", "skip"], # 33
        ["benchmark", "--on-conflict", "skip"], # 34
        ["encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--generate-key", "--no-open"], # 35
        ["decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--key", "a"*64, "--no-open"], # 36
        ["batch-encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--no-open"], # 37
        ["batch-decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--no-open"], # 38
        ["report"], # 39
        ["unknown"], # 40
    ]
    for case in cases:
        with pytest.raises(SystemExit) as exc:
            main(case)
        assert exc.value.code == EXIT_USAGE

# --- --verbose Propagation ---
def test_verbose_propagation():
    assert parse_args(["encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--generate-key", "--verbose"]).verbose is True
    assert parse_args(["decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--key", "a"*64, "--verbose"]).verbose is True
    assert parse_args(["batch-encrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--verbose"]).verbose is True
    assert parse_args(["batch-decrypt", "--input", "a", "--key-size", "256", "--mode", "CBC", "--verbose"]).verbose is True
    assert parse_args(["benchmark", "--verbose"]).verbose is True
    assert parse_args(["security", "--verbose"]).verbose is True
    assert parse_args(["report", "--input", "a.html", "--verbose"]).verbose is True

# --- Exit Code Contract ---
def test_exit_codes(monkeypatch, tmp_path):
    def throw(ex):
        def _throw(*args, **kwargs): raise ex
        return _throw

    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw(ValueError("test")))
    assert main(["benchmark"]) == EXIT_RUNTIME

    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw(FileNotFoundError("test")))
    assert main(["benchmark"]) == EXIT_RUNTIME

    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw(PermissionError("test")))
    assert main(["benchmark"]) == EXIT_RUNTIME

    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw(OSError("test")))
    assert main(["benchmark"]) == EXIT_RUNTIME

    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw(KeyboardInterrupt()))
    assert main(["benchmark"]) == EXIT_SUCCESS

    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw(TypeError("test")))
    with pytest.raises(TypeError): main(["benchmark"])

    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw(AttributeError("test")))
    with pytest.raises(AttributeError): main(["benchmark"])

    monkeypatch.setattr("src.cli_v2.main_v2._handle_benchmark", throw(KeyError("test")))
    with pytest.raises(KeyError): main(["benchmark"])

# --- Browser Auto-Open Behavior ---
def test_browser_auto_open(monkeypatch, tmp_path):
    calls = []
    class MockReportGenerator:
        @staticmethod
        def build_benchmark_report(*args): return Path("a")
        @staticmethod
        def build_security_report(*args): return Path("a")
        @staticmethod
        def open_in_browser(*args): calls.append("open_in_browser")
    class MockBenchmarkService:
        def run_performance_suite(self, *args): return None
    class MockSecurityService:
        def run_security_suite(self, *args, **kwargs): return {}
    monkeypatch.setattr("src.cli_v2.main_v2.ReportGenerator", MockReportGenerator)
    monkeypatch.setattr("src.cli_v2.main_v2.BenchmarkService", MockBenchmarkService)
    monkeypatch.setattr("src.cli_v2.main_v2.SecurityService", MockSecurityService)

    main(["benchmark"])
    assert calls == ["open_in_browser"]
    calls.clear()

    main(["benchmark", "--no-open"])
    assert calls == []

    main(["security"])
    assert calls == ["open_in_browser"]
    calls.clear()

    main(["security", "--no-open"])
    assert calls == []

    p = tmp_path / "a.html"
    p.write_text("a")
    main(["report", "--input", str(p)])
    assert calls == ["open_in_browser"]
    calls.clear()

    main(["report", "--input", str(p), "--no-open"])
    assert calls == []

# --- run-v2.bat Contract ---
def test_run_v2_bat_contract():
    bat_path = Path("run-v2.bat")
    content = bat_path.read_text(encoding="utf-8").strip()
    assert content == '@echo off\ncd /d "%~dp0"\npython -m src.cli_v2.main_v2 %*'
