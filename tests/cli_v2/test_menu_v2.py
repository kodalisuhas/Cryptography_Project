"""Comprehensive behavioral test suite for V2 Menu & Wizard Engine (Stage 4).

Verifies task-centric 8-option main menu, universal navigation (b/c/?),
all 6 primary workflows (Single Encrypt, Single Decrypt, Batch Encrypt,
Batch Decrypt, Benchmark, Security), supporting views (Report Viewer, Help),
automatic in-memory round-trip verification, sidecar detection, 3-tier
error diagnostics, Explorer and browser launch dispatches, and real V1 integration.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.analyzers.metric_collector import MetricCollector
from src.cli_v2.batch_orchestrator import BatchOrchestrator, BatchSummary, BatchFileResult
from src.cli_v2.key_manager import KeyManager
from src.cli_v2.menu_v2 import MenuV2, _create_minimal_bmp
from src.cli_v2.navigation import NavigationEngine
from src.cli_v2.presentation import Presentation
from src.engines.benchmark_service import BenchmarkService
from src.engines.cipher_factory import CipherFactory
from src.engines.cipher_service import CipherService
from src.engines.security_service import SecurityService
from src.utils.file_handler import FileHandler


# =============================================================================
# Helpers and Fixtures
# =============================================================================


class MockInput:
    """Helper to inject a sequence of simulated terminal inputs."""

    def __init__(self, inputs: list[str]):
        self._inputs = iter(inputs)

    def __call__(self, prompt: str = "") -> str:
        try:
            val = next(self._inputs)
            return val
        except StopIteration:
            raise EOFError("No more mock inputs")


@pytest.fixture
def clean_menu(tmp_path, monkeypatch):
    """Provide a MenuV2 instance with paths mapped to tmp_path."""
    input_dir = tmp_path / "data" / "input"
    output_dir = tmp_path / "data" / "output"
    decrypted_dir = tmp_path / "data" / "decrypted"
    reports_dir = tmp_path / "results" / "reports"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    decrypted_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(MenuV2, "DEFAULT_INPUT_DIR", input_dir)
    monkeypatch.setattr(MenuV2, "DEFAULT_OUTPUT_DIR", output_dir)
    monkeypatch.setattr(MenuV2, "DEFAULT_DECRYPTED_DIR", decrypted_dir)
    monkeypatch.setattr(MenuV2, "DEFAULT_REPORTS_DIR", reports_dir)

    menu = MenuV2()
    return menu


# =============================================================================
# 1. Main Menu Navigation & Routing Tests
# =============================================================================


class TestMainMenuRouting:
    """Verify top-level main menu rendering, routing to all 9 options, and exits."""

    def test_main_menu_exit_options(self, monkeypatch, capsys):
        """Main menu cleanly exits on '9', 'exit', 'quit', 'q', 'c', 'cancel', EOFError, KeyboardInterrupt."""
        for exit_token in ["9", "exit", "quit", "q", "c", "cancel"]:
            menu = MenuV2()
            monkeypatch.setattr("builtins.input", MockInput([exit_token]))
            menu.display_main_menu()
            out = capsys.readouterr().out
            assert "CRYPTOGRAPHY TESTING LAB — V2" in out
            assert "Exiting Cryptography Testing Lab. Goodbye!" in out

    def test_main_menu_eof_and_interrupt(self, monkeypatch, capsys):
        """Main menu exits cleanly on EOFError and KeyboardInterrupt without traceback."""
        menu = MenuV2()
        monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(EOFError))
        menu.display_main_menu()
        out = capsys.readouterr().out
        assert "Exiting Cryptography Testing Lab. Goodbye!" in out

        monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(KeyboardInterrupt))
        menu.display_main_menu()
        out = capsys.readouterr().out
        assert "Exiting Cryptography Testing Lab. Goodbye!" in out

    def test_main_menu_help_token(self, monkeypatch, capsys):
        """Entering '?' or 'help' at main menu triggers help and re-prompts."""
        menu = MenuV2()
        monkeypatch.setattr("builtins.input", MockInput(["?", "", "9"]))
        menu.display_main_menu()
        out = capsys.readouterr().out
        assert "CRYPTOGRAPHY TESTING LAB — V2 HELP" in out
        assert "Exiting Cryptography Testing Lab. Goodbye!" in out

    def test_main_menu_back_token(self, monkeypatch, capsys):
        """Entering 'b' or 'back' at main menu informs user they are at top level."""
        menu = MenuV2()
        monkeypatch.setattr("builtins.input", MockInput(["b", "9"]))
        menu.display_main_menu()
        out = capsys.readouterr().out
        assert "(Already at main menu)" in out

    def test_main_menu_invalid_choice_reprompts(self, monkeypatch, capsys):
        """Entering invalid option at main menu displays friendly error and reprompts."""
        menu = MenuV2()
        monkeypatch.setattr("builtins.input", MockInput(["99", "abc", "9"]))
        menu.display_main_menu()
        out = capsys.readouterr().out
        assert "Invalid option. Please enter a number between 1 and 9" in out

    def test_main_menu_routes_to_all_wizards(self, monkeypatch):
        """Verify main menu dispatches correctly to all 6 workflows, analysis lab, visualizer, and help/report views."""
        menu = MenuV2()

        # Mock all wizard methods
        menu.run_single_encrypt_wizard = MagicMock()
        menu.run_single_decrypt_wizard = MagicMock()
        menu.run_batch_encrypt_wizard = MagicMock()
        menu.run_batch_decrypt_wizard = MagicMock()
        menu.run_benchmark_wizard = MagicMock()
        menu.run_security_wizard = MagicMock()
        menu.run_report_viewer_wizard = MagicMock()
        menu.run_help_wizard = MagicMock()
        menu.run_file_analysis_wizard = MagicMock()
        menu.run_live_workflow_wizard = MagicMock()

        # 1. Single File Encrypt (1 -> 1)
        monkeypatch.setattr("builtins.input", MockInput(["1", "1", "9"]))
        menu.display_main_menu()
        menu.run_single_encrypt_wizard.assert_called_once()

        # 2. Single File Decrypt (1 -> 2)
        monkeypatch.setattr("builtins.input", MockInput(["1", "2", "9"]))
        menu.display_main_menu()
        menu.run_single_decrypt_wizard.assert_called_once()

        # 3. Batch Encrypt (2 -> 1)
        monkeypatch.setattr("builtins.input", MockInput(["2", "1", "9"]))
        menu.display_main_menu()
        menu.run_batch_encrypt_wizard.assert_called_once()

        # 4. Batch Decrypt (2 -> 2)
        monkeypatch.setattr("builtins.input", MockInput(["2", "2", "9"]))
        menu.display_main_menu()
        menu.run_batch_decrypt_wizard.assert_called_once()

        # 5. Benchmark (3)
        monkeypatch.setattr("builtins.input", MockInput(["3", "9"]))
        menu.display_main_menu()
        menu.run_benchmark_wizard.assert_called_once()

        # 6. Security (4)
        monkeypatch.setattr("builtins.input", MockInput(["4", "9"]))
        menu.display_main_menu()
        menu.run_security_wizard.assert_called_once()

        # 7. Report Viewer (5)
        monkeypatch.setattr("builtins.input", MockInput(["5", "9"]))
        menu.display_main_menu()
        menu.run_report_viewer_wizard.assert_called_once()

        # 8. Help (6)
        monkeypatch.setattr("builtins.input", MockInput(["6", "9"]))
        menu.display_main_menu()
        menu.run_help_wizard.assert_called_once()

        # 9. File-Specific Encryption Analysis (7)
        monkeypatch.setattr("builtins.input", MockInput(["7", "9"]))
        menu.display_main_menu()
        menu.run_file_analysis_wizard.assert_called_once()

        # 10. Live Cryptography Workflow Visualizer (8)
        monkeypatch.setattr("builtins.input", MockInput(["8", "9"]))
        menu.display_main_menu()
        menu.run_live_workflow_wizard.assert_called_once()

    def test_run_file_analysis_wizard_invokes_cli(self, monkeypatch, capsys):
        """Verify run_file_analysis_wizard dispatches to src.analysis_lab.cli.run_wizard_mode."""
        menu = MenuV2(verbose=True)

        with patch("src.analysis_lab.cli.run_wizard_mode") as mock_run:
            mock_run.return_value = 0
            menu.run_file_analysis_wizard()

            mock_run.assert_called_once()
            called_args = mock_run.call_args[0][0]
            assert called_args.input_path is None
            assert called_args.verbose is True

        out = capsys.readouterr().out
        assert "File-Specific Encryption Analysis Lab" in out

    def test_run_file_analysis_wizard_keyboard_interrupt(self, monkeypatch, capsys):
        """Verify run_file_analysis_wizard handles KeyboardInterrupt gracefully."""
        menu = MenuV2()

        with patch("src.analysis_lab.cli.run_wizard_mode", side_effect=KeyboardInterrupt):
            menu.run_file_analysis_wizard()

        out = capsys.readouterr().out
        assert "[!] Analysis cancelled by user." in out

    def test_run_file_analysis_wizard_expected_exception_handling(self, monkeypatch):
        """Verify run_file_analysis_wizard routes expected exceptions through ErrorTranslator."""
        menu = MenuV2()

        for exc_type in (OSError("disk error"), ValueError("bad value"), RuntimeError("engine failure")):
            with patch("src.analysis_lab.cli.run_wizard_mode", side_effect=exc_type):
                with patch("src.cli_v2.error_translator.ErrorTranslator.display_error") as mock_error:
                    menu.run_file_analysis_wizard()
                    mock_error.assert_called_once()
                    assert mock_error.call_args[1]["context"] == "File-Specific Analysis"

    def test_run_file_analysis_wizard_programming_defect_propagates(self):
        """Verify unexpected programming defects propagate unhandled."""
        menu = MenuV2()

        with patch("src.analysis_lab.cli.run_wizard_mode", side_effect=TypeError("programming bug")):
            with pytest.raises(TypeError, match="programming bug"):
                menu.run_file_analysis_wizard()

    def test_run_live_workflow_wizard_normal_lifecycle(self, monkeypatch, capsys):
        """Verify run_live_workflow_wizard starts server, opens browser, and shuts down on 'q'."""
        menu = MenuV2()
        monkeypatch.setattr("builtins.input", MockInput(["q"]))

        mock_server = MagicMock()
        mock_server.server_url = "http://127.0.0.1:8765"

        with patch("src.visualizer.server.VisualizerServer", return_value=mock_server), \
             patch("webbrowser.open") as mock_browser:
            menu.run_live_workflow_wizard()

            mock_server.start.assert_called_once()
            mock_browser.assert_called_once_with("http://127.0.0.1:8765")
            mock_server.shutdown.assert_called_once()

        out = capsys.readouterr().out
        assert "Live Cryptography Workflow Visualizer" in out
        assert "Visualizer server active at: http://127.0.0.1:8765" in out
        assert "Visualizer server stopped cleanly." in out

    def test_run_live_workflow_wizard_keyboard_interrupt(self, monkeypatch, capsys):
        """Verify run_live_workflow_wizard handles KeyboardInterrupt gracefully and shuts down server."""
        menu = MenuV2()
        monkeypatch.setattr("builtins.input", lambda prompt="": (_ for _ in ()).throw(KeyboardInterrupt))

        mock_server = MagicMock()
        mock_server.server_url = "http://127.0.0.1:8765"

        with patch("src.visualizer.server.VisualizerServer", return_value=mock_server):
            menu.run_live_workflow_wizard()
            mock_server.shutdown.assert_called_once()

        out = capsys.readouterr().out
        assert "Visualizer server stopped cleanly." in out

    def test_run_live_workflow_wizard_expected_exception_handling(self, monkeypatch):
        """Verify run_live_workflow_wizard routes expected exceptions through ErrorTranslator."""
        menu = MenuV2()

        for exc_type in (OSError("bind error"), ValueError("bad param"), RuntimeError("server error")):
            with patch("src.visualizer.server.VisualizerServer", side_effect=exc_type):
                with patch("src.cli_v2.error_translator.ErrorTranslator.display_error") as mock_error:
                    menu.run_live_workflow_wizard()
                    mock_error.assert_called_once()
                    assert mock_error.call_args[1]["context"] == "Live Workflow Visualizer"

    def test_run_live_workflow_wizard_programming_defect_propagates(self):
        """Verify unexpected programming defects propagate unmasked."""
        menu = MenuV2()

        with patch("src.visualizer.server.VisualizerServer", side_effect=TypeError("programming bug")):
            with pytest.raises(TypeError, match="programming bug"):
                menu.run_live_workflow_wizard()


# =============================================================================
# 2. Single-File Encryption Wizard Tests
# =============================================================================


class TestSingleEncryptWizard:
    """Verify single-file encryption wizard, in-memory round-trip verify, and sidecars."""

    def test_single_encrypt_full_flow_default_cbc(self, clean_menu, tmp_path, monkeypatch, capsys):
        """Encrypt a file using default AES-256-CBC, auto-generating sidecar key and IV."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "plain.txt"
        sample_file.write_text("Hello Cryptography Testing Lab!", encoding="utf-8")

        # Inputs:
        # Step 1: select file 1 (plain.txt)
        # Step 2: select config 1 (AES-256-CBC)
        # Step 3: select key strategy 1 (Generate New)
        # Step 4: accept default destination (press Enter)
        # Step 6: next action 3 (Return to Main Menu)
        inputs = ["1", "1", "1", "", "3"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_encrypt_wizard()
        out = capsys.readouterr().out

        expected_dest = clean_menu.DEFAULT_OUTPUT_DIR / "plain.txt.enc"
        expected_key = clean_menu.DEFAULT_OUTPUT_DIR / "plain.txt.enc.key"
        expected_iv = clean_menu.DEFAULT_OUTPUT_DIR / "plain.txt.enc.iv"

        assert expected_dest.exists()
        assert expected_key.exists()
        assert expected_iv.exists()

        assert "OPERATION SUCCESSFUL: ENCRYPTION" in out
        assert "Round-Trip Verify" in out
        assert "PASSED" in out
        assert "Laboratory Key" in out

    def test_single_encrypt_ecb_mode_no_iv_sidecar(self, clean_menu, tmp_path, monkeypatch, capsys):
        """Encrypt using ECB mode: displays educational notice and does NOT create .iv sidecar."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "data.bin"
        sample_file.write_bytes(b"SecretBytes12345" * 4)

        # Inputs:
        # Step 1: select file 1
        # Step 2: select config 4 (AES-256-ECB)
        # Step 3: generate new key (1)
        # Step 4: default dest ("")
        # Step 6: return (3)
        inputs = ["1", "4", "1", "", "3"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_encrypt_wizard()
        out = capsys.readouterr().out

        expected_dest = clean_menu.DEFAULT_OUTPUT_DIR / "data.bin.enc"
        expected_key = clean_menu.DEFAULT_OUTPUT_DIR / "data.bin.enc.key"
        expected_iv = clean_menu.DEFAULT_OUTPUT_DIR / "data.bin.enc.iv"

        assert expected_dest.exists()
        assert expected_key.exists()
        assert not expected_iv.exists()  # ECB must not create .iv

        assert "Security Notice: ECB mode does NOT hide data patterns" in out
        assert "AES-256-ECB" in out

    def test_single_encrypt_manual_key_prompts_byte_counts(self, clean_menu, monkeypatch, capsys):
        """Verify AES-128, AES-192, and AES-256 manual hex key prompts display correct byte/char counts."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "prompt.txt"
        sample_file.write_text("Hello", encoding="utf-8")

        def run_with_inputs(inputs):
            inputs_iter = iter(inputs)
            def mock_input(prompt=""):
                print(prompt) # print so capsys captures it
                try:
                    return next(inputs_iter)
                except StopIteration:
                    raise EOFError("No more mock inputs")
            monkeypatch.setattr("builtins.input", mock_input)
            clean_menu.run_single_encrypt_wizard()
            return capsys.readouterr().out

        out_128 = run_with_inputs(["1", "2", "3", "c"])
        assert "Enter 16-byte hex key (32 chars)" in out_128

        out_192 = run_with_inputs(["1", "3", "3", "c"])
        assert "Enter 24-byte hex key (48 chars)" in out_192

        out_256 = run_with_inputs(["1", "1", "3", "c"])
        assert "Enter 32-byte hex key (64 chars)" in out_256

    def test_single_encrypt_with_custom_hex_key(self, clean_menu, monkeypatch, capsys):
        """Encrypt using a user-supplied 256-bit hexadecimal key."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "doc.txt"
        sample_file.write_text("Confidential Content", encoding="utf-8")

        hex_key = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"

        # Inputs:
        # Step 1: file 1
        # Step 2: config 1 (AES-256-CBC)
        # Step 3: key strategy 3 (Enter raw hex key)
        # -> enter hex_key
        # Step 4: default dest
        # Step 6: return
        inputs = ["1", "1", "3", hex_key, "", "3"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_encrypt_wizard()

        saved_key_file = clean_menu.DEFAULT_OUTPUT_DIR / "doc.txt.enc.key"
        assert saved_key_file.exists()
        assert saved_key_file.read_text(encoding="utf-8").strip() == hex_key

    def test_single_encrypt_round_trip_failure_raises_error(self, clean_menu, monkeypatch, capsys):
        """If in-memory round-trip decryption fails, abort and report error before output write."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "corrupt_test.txt"
        sample_file.write_text("Test Payload", encoding="utf-8")

        # Mock cipher_service.decrypt_data to return mismatched bytes
        original_decrypt = clean_menu._cipher_service.decrypt_data

        def mock_bad_decrypt(*args, **kwargs):
            return b"MismatchedBytesCorrupt"

        monkeypatch.setattr(clean_menu._cipher_service, "decrypt_data", mock_bad_decrypt)

        inputs = ["1", "1", "1", "", "3"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_encrypt_wizard()
        out = capsys.readouterr().err  # ErrorTranslator prints to stderr

        dest_file = clean_menu.DEFAULT_OUTPUT_DIR / "corrupt_test.txt.enc"
        assert not dest_file.exists()  # Did not commit output file on verify failure
        assert "Operation Failed" in out

    def test_single_encrypt_navigation_back_and_cancel(self, clean_menu, monkeypatch, capsys):
        """Verify 'b' steps back to previous prompt and 'c' cancels immediately."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "test_nav.txt"
        sample_file.write_text("Sample", encoding="utf-8")

        # Select file (1) -> at config step enter 'b' (back to file selection) -> select 1 -> 'c' (cancel)
        inputs = ["1", "b", "1", "c"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_encrypt_wizard()
        out = capsys.readouterr().out
        assert "Operation cancelled by user" in out
        dest_file = clean_menu.DEFAULT_OUTPUT_DIR / "test_nav.txt.enc"
        assert not dest_file.exists()

    def test_single_encrypt_output_conflict_handling(self, clean_menu, monkeypatch, capsys):
        """When destination file exists, prompt for overwrite or rename."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "existing.txt"
        sample_file.write_text("New content", encoding="utf-8")

        existing_dest = clean_menu.DEFAULT_OUTPUT_DIR / "existing.txt.enc"
        existing_dest.write_bytes(b"Old ciphertext")

        # Select file (1) -> config (1) -> key (1) -> dest ("") -> conflict prompt (1 = Overwrite) -> return (3)
        inputs = ["1", "1", "1", "", "1", "3"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_encrypt_wizard()
        out = capsys.readouterr().out
        assert "Conflict: Destination" in out
        assert "OPERATION SUCCESSFUL: ENCRYPTION" in out


# =============================================================================
# 3. Single-File Decryption Wizard Tests
# =============================================================================


class TestSingleDecryptWizard:
    """Verify single-file decryption wizard, sidecar auto-detection, and recovery."""

    def test_single_decrypt_with_autodetected_sidecars(self, clean_menu, monkeypatch, capsys):
        """Single decrypt automatically detects and uses companion .key and .iv sidecars."""
        cipher_path = clean_menu.DEFAULT_OUTPUT_DIR / "secret.txt.enc"
        key_path = clean_menu.DEFAULT_OUTPUT_DIR / "secret.txt.enc.key"
        iv_path = clean_menu.DEFAULT_OUTPUT_DIR / "secret.txt.enc.iv"

        key = b"\x01" * 32
        iv = b"\x02" * 16
        plaintext = b"Decrypted Secret Document 12345"

        enc_res = clean_menu._cipher_service.encrypt_data("AES", 256, "CBC", plaintext, key, iv)
        cipher_path.write_bytes(enc_res.ciphertext)
        KeyManager.save_key(key, key_path)
        KeyManager.save_iv(iv, iv_path)

        # Inputs:
        # Step 1: select ciphertext file 1
        # Step 2: use detected key 'y'
        # Step 3: select mode 1 (CBC) -> use detected IV 'y'
        # Step 4: accept default decrypted path (press Enter)
        # Step 6: next action 2 (Return to menu)
        inputs = ["1", "y", "1", "y", "", "2"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_decrypt_wizard()
        out = capsys.readouterr().out

        expected_recovered = clean_menu.DEFAULT_DECRYPTED_DIR / "secret.txt"
        assert expected_recovered.exists()
        assert expected_recovered.read_bytes() == plaintext
        assert "OPERATION SUCCESSFUL: DECRYPTION" in out
        assert "SUCCESS (Plaintext restored and verified)" in out

    def test_single_decrypt_with_manual_hex_key_and_iv(self, clean_menu, monkeypatch, capsys):
        """Single decrypt when no sidecars exist prompts for manual hex key and IV."""
        cipher_path = clean_menu.DEFAULT_OUTPUT_DIR / "manual.bin.enc"
        key = b"\xaa" * 16  # 128-bit
        iv = b"\xbb" * 16
        plaintext = b"Manual Key Decrypt Test"

        enc_res = clean_menu._cipher_service.encrypt_data("AES", 128, "CBC", plaintext, key, iv)
        cipher_path.write_bytes(enc_res.ciphertext)

        # Inputs:
        # Step 1: select file 1
        # Step 2: select manual hex key (2) -> enter key.hex()
        # Step 3: select mode 1 (CBC) -> enter iv.hex()
        # Step 4: default dest ("")
        # Step 6: return (2)
        inputs = ["1", "2", key.hex(), "1", iv.hex(), "", "2"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_decrypt_wizard()

        recovered_file = clean_menu.DEFAULT_DECRYPTED_DIR / "manual.bin"
        assert recovered_file.exists()
        assert recovered_file.read_bytes() == plaintext

    def test_single_decrypt_corrupted_padding_handled(self, clean_menu, monkeypatch, capsys):
        """Corrupted ciphertext or wrong key produces a clean 3-tier diagnostic error."""
        cipher_path = clean_menu.DEFAULT_OUTPUT_DIR / "bad.txt.enc"
        cipher_path.write_bytes(b"\xff" * 48)  # invalid ciphertext
        key_path = clean_menu.DEFAULT_OUTPUT_DIR / "bad.txt.enc.key"
        KeyManager.save_key(b"\x00" * 32, key_path)

        # Select file (1) -> use detected key (y) -> mode 1 (CBC) -> enter valid 32-hex IV -> default dest
        inputs = ["1", "y", "1", "00" * 16, ""]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_decrypt_wizard()
        err = capsys.readouterr().err

        assert "Operation Failed" in err
        assert "Decryption failed" in err


# =============================================================================
# 4. Batch Operations Wizard Tests
# =============================================================================


class TestBatchWizards:
    """Verify batch encryption and decryption wizards, preflight previews, and isolation."""

    def test_batch_encrypt_wizard_full_flow(self, clean_menu, monkeypatch, capsys):
        """Batch encrypt folder with unique keys, preflight confirmation, and CSV log."""
        src_dir = clean_menu.DEFAULT_INPUT_DIR / "batch_src"
        src_dir.mkdir()
        (src_dir / "f1.txt").write_text("File 1 content", encoding="utf-8")
        (src_dir / "f2.txt").write_text("File 2 content", encoding="utf-8")

        dst_dir = clean_menu.DEFAULT_OUTPUT_DIR / "batch_dst"

        # Inputs:
        # Step 1: enter src_dir path
        # Step 2: config 1 (AES-256-CBC) -> key strategy 1 (Unique keys)
        # Step 3: dest_dir path -> conflict policy 1 (Skip Existing)
        # Step 4: confirmation 'y'
        # Next action: return (2)
        inputs = [str(src_dir), "1", "1", str(dst_dir), "1", "y", "2"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_batch_encrypt_wizard()
        out = capsys.readouterr().out

        assert (dst_dir / "f1.txt.enc").exists()
        assert (dst_dir / "f1.txt.enc.key").exists()
        assert (dst_dir / "f1.txt.enc.iv").exists()
        assert (dst_dir / "f2.txt.enc").exists()

        assert "BATCH ENCRYPTION PRE-FLIGHT" in out
        assert "BATCH OPERATION SUMMARY" in out
        assert "Successfully Encrypted" in out

    def test_batch_encrypt_preflight_cancellation(self, clean_menu, monkeypatch, capsys):
        """User cancelling at preflight preview aborts with zero writes."""
        src_dir = clean_menu.DEFAULT_INPUT_DIR / "cancel_batch"
        src_dir.mkdir()
        (src_dir / "item.txt").write_text("Hello", encoding="utf-8")
        dst_dir = clean_menu.DEFAULT_OUTPUT_DIR / "cancel_dst"

        # Enter src -> config 1 -> key 1 -> dest -> conflict 1 -> confirm 'n' (cancel)
        inputs = [str(src_dir), "1", "1", str(dst_dir), "1", "n"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_batch_encrypt_wizard()
        out = capsys.readouterr().out

        assert "Batch encryption cancelled by user" in out
        assert not dst_dir.exists()

    def test_batch_decrypt_wizard_full_flow(self, clean_menu, monkeypatch, capsys):
        """Batch decrypt folder with companion sidecars and CSV logging."""
        src_dir = clean_menu.DEFAULT_OUTPUT_DIR / "dec_batch_src"
        src_dir.mkdir()
        dst_dir = clean_menu.DEFAULT_DECRYPTED_DIR / "dec_batch_dst"

        key = b"\x01" * 32
        iv = b"\x02" * 16
        enc1 = clean_menu._cipher_service.encrypt_data("AES", 256, "CBC", b"Batch Plaintext 1", key, iv)
        enc2 = clean_menu._cipher_service.encrypt_data("AES", 256, "CBC", b"Batch Plaintext 2", key, iv)

        (src_dir / "f1.txt.enc").write_bytes(enc1.ciphertext)
        KeyManager.save_key(key, src_dir / "f1.txt.enc.key")
        KeyManager.save_iv(iv, src_dir / "f1.txt.enc.iv")

        (src_dir / "f2.txt.enc").write_bytes(enc2.ciphertext)
        KeyManager.save_key(key, src_dir / "f2.txt.enc.key")
        KeyManager.save_iv(iv, src_dir / "f2.txt.enc.iv")

        # Inputs:
        # Step 1: src_dir
        # Step 2: mode 1 (CBC)
        # Step 3: dst_dir -> conflict 1 (Skip)
        # Step 4: confirm 'y'
        # Next action: return (2)
        inputs = [str(src_dir), "1", str(dst_dir), "1", "y", "2"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_batch_decrypt_wizard()
        out = capsys.readouterr().out

        assert (dst_dir / "f1.txt").read_bytes() == b"Batch Plaintext 1"
        assert (dst_dir / "f2.txt").read_bytes() == b"Batch Plaintext 2"
        assert "BATCH DECRYPTION SUMMARY" in out
        assert "Successfully Decrypted" in out


# =============================================================================
# 5. Benchmark & Security Wizards Tests
# =============================================================================


class TestBenchmarkAndSecurityWizards:
    """Verify Benchmark and Security Wizards integration with V1 engines and ReportGenerator."""

    def test_benchmark_wizard_execution_and_report(self, clean_menu, monkeypatch, capsys):
        """Benchmark wizard executes V1 BenchmarkService, generates HTML report, and prompts browser."""
        # Preset 1 (Quick) -> Open browser 'n'
        inputs = ["1", "n"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        with patch("src.cli_v2.report_generator.ReportGenerator.open_in_browser", return_value=True) as mock_open:
            clean_menu.run_benchmark_wizard()
            mock_open.assert_not_called()

        out = capsys.readouterr().out
        assert "Performance & Benchmark Suite" in out
        assert "Benchmark report saved" in out

    def test_benchmark_wizard_open_browser_confirmed(self, clean_menu, monkeypatch, capsys):
        """When user confirms browser open, ReportGenerator.open_in_browser is called."""
        inputs = ["1", "y"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        with patch("src.cli_v2.report_generator.ReportGenerator.open_in_browser", return_value=True) as mock_open:
            clean_menu.run_benchmark_wizard()
            mock_open.assert_called_once()

    def test_security_wizard_execution_and_report(self, clean_menu, monkeypatch, capsys):
        """Security wizard executes V1 SecurityService, generates security report, and prompts browser."""
        # Confirm run 'y' -> Open browser 'y'
        inputs = ["y", "y"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        with patch("src.cli_v2.report_generator.ReportGenerator.open_in_browser", return_value=True) as mock_open:
            clean_menu.run_security_wizard()
            mock_open.assert_called_once()

        out = capsys.readouterr().out
        assert "Security & Cryptanalysis Lab" in out
        assert "Security report saved" in out


# =============================================================================
# 6. Report Viewer & Help Wizards Tests
# =============================================================================


class TestReportViewerAndHelpWizards:
    """Verify Report Viewer and Help documentation display."""

    def test_report_viewer_no_reports_fallback(self, clean_menu, monkeypatch, capsys):
        """When no HTML reports exist in results/reports/, display notice and return."""
        clean_menu.run_report_viewer_wizard()
        out = capsys.readouterr().out
        assert "No HTML reports found in" in out

    def test_report_viewer_lists_and_opens_report(self, clean_menu, monkeypatch, capsys):
        """When HTML reports exist, user selects report and opens in browser."""
        report1 = clean_menu.DEFAULT_REPORTS_DIR / "cryptography_report_20260915_120000.html"
        report1.write_text("<html>Report Content</html>", encoding="utf-8")

        # Select report 1 -> Open in browser 'y'
        inputs = ["1"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        with patch("src.cli_v2.report_generator.ReportGenerator.open_in_browser", return_value=True) as mock_open:
            clean_menu.run_report_viewer_wizard()
            mock_open.assert_called_once_with(report1)

        out = capsys.readouterr().out
        assert "Opening 'cryptography_report_20260915_120000.html'" in out

    def test_help_wizard_displays_documentation(self, clean_menu, monkeypatch, capsys):
        """Help wizard renders full educational guide and waits for Enter."""
        monkeypatch.setattr("builtins.input", MockInput([""]))
        clean_menu.run_help_wizard()
        out = capsys.readouterr().out

        assert "CRYPTOGRAPHY TESTING LAB — V2 HELP" in out
        assert "Universal Navigation Controls" in out
        assert "Cipher Modes & Key Sizes" in out
        assert "Key Management" in out
        assert "Batch Operations" in out
        assert "HTML Reports & Benchmarks" in out


# =============================================================================
# 7. Helper Unit Tests
# =============================================================================


def test_create_minimal_bmp():
    """Verify in-memory BMP generator creates valid 24-bpp BMP bytes."""
    bmp_bytes = _create_minimal_bmp(8, 8)
    assert len(bmp_bytes) > 54
    assert bmp_bytes[:2] == b"BM"
    # DIB header bpp field is at offset 28
    bpp = int.from_bytes(bmp_bytes[28:30], "little")
    assert bpp == 24


# =============================================================================
# 8. Explorer, Presets, Shared Keys & Error Recovery Tests
# =============================================================================


class TestMenuExtendedWorkflows:
    """Verify Explorer launching, alternative presets, shared key modes, and error branches."""

    def test_single_encrypt_load_existing_key_file(self, clean_menu, monkeypatch, capsys):
        """Single encrypt can load an existing .key sidecar file from disk."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "plain_with_key.txt"
        sample_file.write_text("Plaintext for existing key", encoding="utf-8")

        key_file = clean_menu.DEFAULT_INPUT_DIR / "existing.key"
        key_bytes = b"\x33" * 32
        KeyManager.save_key(key_bytes, key_file)

        # Inputs:
        # Step 1: select file 1
        # Step 2: config 1 (AES-256-CBC)
        # Step 3: key strategy 2 (Load existing .key file) -> enter key_file path
        # Step 4: default dest ("")
        # Step 6: next action 3 (Return)
        inputs = ["1", "1", "2", str(key_file), "", "3"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_encrypt_wizard()
        out = capsys.readouterr().out

        expected_dest = clean_menu.DEFAULT_OUTPUT_DIR / "plain_with_key.txt.enc"
        assert expected_dest.exists()
        assert "PASSED" in out

    def test_single_encrypt_open_explorer_action(self, clean_menu, monkeypatch):
        """Selecting Explorer post-operation action invokes Presentation.open_explorer."""
        sample_file = clean_menu.DEFAULT_INPUT_DIR / "exp.txt"
        sample_file.write_text("Explorer Test", encoding="utf-8")

        # Select file (1) -> config (1) -> key (1) -> dest ("") -> next action 1 (Open Explorer)
        inputs = ["1", "1", "1", "", "1"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        with patch("src.cli_v2.presentation.Presentation.open_explorer", return_value=True) as mock_exp:
            clean_menu.run_single_encrypt_wizard()
            mock_exp.assert_called_once_with(clean_menu.DEFAULT_OUTPUT_DIR)

    def test_single_decrypt_open_explorer_action(self, clean_menu, monkeypatch):
        """Selecting Explorer post-operation action in decrypt invokes Presentation.open_explorer."""
        cipher_path = clean_menu.DEFAULT_OUTPUT_DIR / "exp.txt.enc"
        key_path = clean_menu.DEFAULT_OUTPUT_DIR / "exp.txt.enc.key"
        iv_path = clean_menu.DEFAULT_OUTPUT_DIR / "exp.txt.enc.iv"

        key = b"\x01" * 32
        iv = b"\x02" * 16
        enc = clean_menu._cipher_service.encrypt_data("AES", 256, "CBC", b"Exp Decrypt", key, iv)
        cipher_path.write_bytes(enc.ciphertext)
        KeyManager.save_key(key, key_path)
        KeyManager.save_iv(iv, iv_path)

        # Select file (1) -> use auto key (y) -> mode 1 (CBC) -> use auto IV (y) -> dest ("") -> action 1 (Explorer)
        inputs = ["1", "y", "1", "y", "", "1"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        with patch("src.cli_v2.presentation.Presentation.open_explorer", return_value=True) as mock_exp:
            clean_menu.run_single_decrypt_wizard()
            mock_exp.assert_called_once_with(clean_menu.DEFAULT_DECRYPTED_DIR)

    def test_single_decrypt_navigation_back(self, clean_menu, monkeypatch, capsys):
        """Single decrypt supports backing out to previous configuration step."""
        cipher_path = clean_menu.DEFAULT_OUTPUT_DIR / "nav_dec.txt.enc"
        cipher_path.write_bytes(b"\x00" * 32)
        KeyManager.save_key(b"\x00" * 32, clean_menu.DEFAULT_OUTPUT_DIR / "nav_dec.txt.enc.key")

        # File (1) -> auto key (y) -> at mode prompt enter 'b' -> auto key (y) -> mode (1) -> IV cancel ('c')
        inputs = ["1", "y", "b", "y", "1", "c"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_single_decrypt_wizard()
        out = capsys.readouterr().out
        assert "Operation cancelled by user" in out

    def test_batch_encrypt_shared_key_strategy(self, clean_menu, monkeypatch, capsys):
        """Batch encrypt in shared-key mode writes a single batch.key and unique CBC IVs."""
        src_dir = clean_menu.DEFAULT_INPUT_DIR / "shared_batch_src"
        src_dir.mkdir()
        (src_dir / "a.txt").write_text("File A", encoding="utf-8")
        (src_dir / "b.txt").write_text("File B", encoding="utf-8")
        dst_dir = clean_menu.DEFAULT_OUTPUT_DIR / "shared_batch_dst"

        # Step 1: src_dir
        # Step 2: config 1 (AES-256-CBC) -> key strategy 2 (Shared key)
        # Step 3: dst_dir -> conflict 1 (Skip)
        # Step 4: confirm 'y'
        # Next action: 2 (Return)
        inputs = [str(src_dir), "1", "2", str(dst_dir), "1", "y", "2"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_batch_encrypt_wizard()
        out = capsys.readouterr().out

        assert (dst_dir / "batch.key").exists()
        assert (dst_dir / "a.txt.enc").exists()
        assert (dst_dir / "a.txt.enc.iv").exists()
        assert not (dst_dir / "a.txt.enc.key").exists()  # Unique key not created in shared mode
        assert "Successfully Encrypted" in out

    def test_batch_decrypt_shared_key_strategy(self, clean_menu, monkeypatch, capsys):
        """Batch decrypt resolves shared batch.key in source folder."""
        src_dir = clean_menu.DEFAULT_OUTPUT_DIR / "shared_dec_src"
        src_dir.mkdir()
        dst_dir = clean_menu.DEFAULT_DECRYPTED_DIR / "shared_dec_dst"

        key = b"\x77" * 32
        KeyManager.save_key(key, src_dir / "batch.key")

        iv1 = b"\x11" * 16
        iv2 = b"\x22" * 16
        enc1 = clean_menu._cipher_service.encrypt_data("AES", 256, "CBC", b"Shared Plain 1", key, iv1)
        enc2 = clean_menu._cipher_service.encrypt_data("AES", 256, "CBC", b"Shared Plain 2", key, iv2)

        (src_dir / "f1.txt.enc").write_bytes(enc1.ciphertext)
        KeyManager.save_iv(iv1, src_dir / "f1.txt.enc.iv")
        (src_dir / "f2.txt.enc").write_bytes(enc2.ciphertext)
        KeyManager.save_iv(iv2, src_dir / "f2.txt.enc.iv")

        # Step 1: src_dir
        # Step 2: mode 1 (CBC) -> key strategy 2 (Use detected batch.key)
        # Step 3: dst_dir -> conflict 1 (Skip)
        # Step 4: confirm 'y'
        # Next action: return (2)
        inputs = [str(src_dir), "1", "2", str(dst_dir), "1", "y", "2"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_batch_decrypt_wizard()
        out = capsys.readouterr().out

        assert (dst_dir / "f1.txt").read_bytes() == b"Shared Plain 1"
        assert (dst_dir / "f2.txt").read_bytes() == b"Shared Plain 2"
        assert "BATCH DECRYPTION SUMMARY" in out

    def test_batch_encrypt_empty_source_dir(self, clean_menu, monkeypatch, capsys):
        """Batch encrypt when source folder has no files displays notice and returns."""
        empty_dir = clean_menu.DEFAULT_INPUT_DIR / "empty_dir"
        empty_dir.mkdir()

        # Step 1: enter empty_dir -> config 1 -> key 1 -> dest -> conflict 1
        inputs = [str(empty_dir), "1", "1", "", "1"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_batch_encrypt_wizard()
        out = capsys.readouterr().out
        assert "No candidate plaintext files discovered" in out

    def test_batch_decrypt_empty_source_dir(self, clean_menu, monkeypatch, capsys):
        """Batch decrypt when source folder has no .enc files displays notice and returns."""
        empty_dir = clean_menu.DEFAULT_OUTPUT_DIR / "empty_dec_dir"
        empty_dir.mkdir()

        # Step 1: enter empty_dir -> mode 1 -> dest -> conflict 1
        inputs = [str(empty_dir), "1", "", "1"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_batch_decrypt_wizard()
        out = capsys.readouterr().out
        assert "No candidate *.enc ciphertext files discovered" in out

    def test_benchmark_standard_preset(self, clean_menu, monkeypatch, capsys):
        """Benchmark Standard Preset (preset 2) runs successfully."""
        # Preset 2 (Standard) -> Open browser 'n'
        inputs = ["2", "n"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_benchmark_wizard()
        out = capsys.readouterr().out
        assert "Performance & Benchmark Suite" in out
        assert "Benchmark report saved" in out

    def test_benchmark_cancel_preset(self, clean_menu, monkeypatch, capsys):
        """Cancelling at benchmark preset selection returns cleanly."""
        inputs = ["c"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_benchmark_wizard()
        out = capsys.readouterr().out
        assert "Executing benchmark suite" not in out

    def test_security_cancel_confirmation(self, clean_menu, monkeypatch, capsys):
        """Declining security suite confirmation returns cleanly without executing."""
        inputs = ["n"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_security_wizard()
        out = capsys.readouterr().out
        assert "Executing security evaluations" not in out

    def test_report_viewer_cancel_selection(self, clean_menu, monkeypatch, capsys):
        """Cancelling report selection returns cleanly."""
        report = clean_menu.DEFAULT_REPORTS_DIR / "cryptography_report_20260915_150000.html"
        report.write_text("<html></html>", encoding="utf-8")

        inputs = ["c"]
        monkeypatch.setattr("builtins.input", MockInput(inputs))

        clean_menu.run_report_viewer_wizard()
        out = capsys.readouterr().out
        assert "Opening" not in out
