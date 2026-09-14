"""Tests for the interactive menu: dispatch, loop, and error recovery.

Convention: pytest, monkeypatch for builtins.input and getpass.getpass,
unittest.mock for command handlers.  Menu is a thin wrapper reusing handlers.
"""

import argparse
import pytest
from unittest.mock import patch, MagicMock, call

from src.cli.menu import run_menu


# ── Helpers ──────────────────────────────────────────────────────────


def _mock_args(verbose=False):
    return argparse.Namespace(verbose=verbose)


# ── Menu exit ───────────────────────────────────────────────────────


class TestMenuExit:
    def test_choice_5_exits(self, monkeypatch):
        """Typing '5' should exit the loop cleanly."""
        inputs = iter(["5"])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
        run_menu(_mock_args())  # should not raise

    def test_eof_exits(self, monkeypatch):
        """EOFError (Ctrl-D) should exit cleanly."""
        monkeypatch.setattr("builtins.input", lambda _="": (_ for _ in ()).throw(EOFError))
        run_menu(_mock_args())  # should not raise


# ── Invalid choice ──────────────────────────────────────────────────


class TestInvalidChoice:
    def test_invalid_then_exit(self, monkeypatch, capsys):
        """Invalid input followed by exit should print error and exit."""
        inputs = iter(["99", "5"])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))
        run_menu(_mock_args())
        out = capsys.readouterr().out
        assert "Invalid choice" in out or "1-5" in out


# ── Encrypt menu choice ─────────────────────────────────────────────


class TestMenuEncrypt:
    def test_encrypt_dispatches_handler(self, monkeypatch, capsys):
        """Choice '1' should build a Namespace and call run_encrypt."""
        # Sequence: menu choice, then key_size, mode, plaintext, fmt, key_mode, key, exit
        inputs = iter(["1", "128", "ECB", "hello", "text", "1", "ab" * 16, "5"])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_encrypt") as mock_encrypt:
            mock_encrypt.side_effect = lambda ns: None  # simulate success
            run_menu(_mock_args())

        mock_encrypt.assert_called_once()
        ns = mock_encrypt.call_args[0][0]
        assert ns.algorithm == "AES"
        assert ns.key_size == 128
        assert ns.mode == "ECB"
        assert ns.input == "hello"
        assert ns.key == "ab" * 16

    def test_encrypt_generate_key(self, monkeypatch, capsys):
        """Choice '2' for key_mode sets generate_key=True."""
        inputs = iter(["1", "256", "CBC", "secret", "text", "2", "ff" * 16, "5"])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_encrypt") as mock_encrypt:
            run_menu(_mock_args())

        ns = mock_encrypt.call_args[0][0]
        assert ns.generate_key is True
        assert ns.key is None
        assert ns.iv == "ff" * 16

    def test_encrypt_masked_key_fallback(self, monkeypatch):
        """Choice '3' for key_mode leaves key=None → handler falls back to getpass."""
        inputs = iter(["1", "128", "ECB", "hi", "text", "3", "5"])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_encrypt") as mock_encrypt:
            run_menu(_mock_args())

        ns = mock_encrypt.call_args[0][0]
        assert ns.key is None
        assert ns.generate_key is False


# ── Decrypt menu choice ─────────────────────────────────────────────


class TestMenuDecrypt:
    def test_decrypt_dispatches_handler(self, monkeypatch):
        """Choice '2' should build a Namespace and call run_decrypt."""
        inputs = iter([
            "2",       # menu choice
            "128",     # key_size
            "ECB",     # mode
            "ab" * 16, # key
            "cafe" * 16,  # ciphertext
            "5",       # exit
        ])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_decrypt") as mock_decrypt:
            run_menu(_mock_args())

        mock_decrypt.assert_called_once()
        ns = mock_decrypt.call_args[0][0]
        assert ns.algorithm == "AES"
        assert ns.key == "ab" * 16

    def test_decrypt_cbc_with_iv(self, monkeypatch):
        """CBC decrypt should prompt for IV."""
        inputs = iter([
            "2",       # menu choice
            "128",     # key_size
            "CBC",     # mode
            "ab" * 16, # key
            "cafe" * 16,  # ciphertext
            "11" * 16,  # iv
            "5",       # exit
        ])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_decrypt") as mock_decrypt:
            run_menu(_mock_args())

        ns = mock_decrypt.call_args[0][0]
        assert ns.iv == "11" * 16

    def test_decrypt_cbc_no_iv_prints_warning(self, monkeypatch, capsys):
        """CBC decrypt with empty IV should print warning."""
        inputs = iter([
            "2",       # menu choice
            "128",     # key_size
            "CBC",     # mode
            "ab" * 16, # key
            "cafe" * 16,  # ciphertext
            "",        # empty IV → None
            "5",       # exit
        ])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_decrypt") as mock_decrypt:
            run_menu(_mock_args())

        out = capsys.readouterr().out
        assert "requires an IV" in out


# ── Benchmark menu choice ───────────────────────────────────────────


class TestMenuBenchmark:
    def test_benchmark_uses_defaults(self, monkeypatch):
        """Choice '3' with empty inputs should use defaults."""
        inputs = iter(["3", "", "", "", "5"])  # 3, then 3 empty defaults, then exit
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_benchmark") as mock_bench:
            run_menu(_mock_args())

        mock_bench.assert_called_once()
        ns = mock_bench.call_args[0][0]
        assert ns.key_sizes == "128,192,256"
        assert ns.modes == "ECB,CBC"
        assert ns.payload_sizes == "1048576"

    def test_benchmark_custom_inputs(self, monkeypatch):
        """Choice '3' with custom values."""
        inputs = iter(["3", "128,256", "CBC", "512", "5"])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_benchmark") as mock_bench:
            run_menu(_mock_args())

        ns = mock_bench.call_args[0][0]
        assert ns.key_sizes == "128,256"
        assert ns.modes == "CBC"
        assert ns.payload_sizes == "512"


# ── Security menu choice ────────────────────────────────────────────


class TestMenuSecurity:
    def test_security_dispatches_handler(self, monkeypatch):
        """Choice '4' should build a Namespace and call run_security."""
        inputs = iter([
            "4",       # menu choice
            "ECB",     # mode
            "ab" * 16, # key
            "",        # plaintext (empty = default)
            "",        # iv (empty = auto-generate)
            "4",       # bmp width
            "4",       # bmp height
            "5",       # exit
        ])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_security") as mock_sec:
            run_menu(_mock_args())

        mock_sec.assert_called_once()
        ns = mock_sec.call_args[0][0]
        assert ns.mode == "ECB"
        assert ns.key == "ab" * 16


# ── Error recovery ──────────────────────────────────────────────────


class TestMenuErrorRecovery:
    def test_error_in_handler_returns_to_menu(self, monkeypatch, capsys):
        """An error in a handler should be caught, message shown, loop continues."""
        inputs = iter([
            "1",       # encrypt
            "128", "ECB", "hello", "text", "1", "ab" * 16,  # encrypt prompts
            "5",       # exit
        ])
        monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

        with patch("src.cli.menu.commands.run_encrypt") as mock_encrypt:
            mock_encrypt.side_effect = ValueError("something went wrong")
            run_menu(_mock_args())

        out = capsys.readouterr().out
        assert "something went wrong" in out
        assert "Returning to menu" in out

    def test_keyboard_interrupt_exits_menu(self, monkeypatch):
        """KeyboardInterrupt should propagate (caught by main)."""
        call_count = 0

        def fake_input(_=""):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "1"
            raise KeyboardInterrupt()

        monkeypatch.setattr("builtins.input", fake_input)
        # KeyboardInterrupt is NOT caught by the menu loop's per-choice handler —
        # it propagates to the caller (main), which is the intended design.
        with pytest.raises(KeyboardInterrupt):
            run_menu(_mock_args())


# ── No global state mutation ─────────────────────────────────────────


class TestMenuNoGlobalState:
    def test_services_not_imported_at_module_level(self):
        """The menu module imports 'commands' but doesn't import Services directly."""
        import src.cli.menu as menu_module
        import inspect
        source = inspect.getsource(menu_module)
        # Menu should not directly import CipherService, BenchmarkService, SecurityService
        assert "CipherService" not in source
        assert "BenchmarkService" not in source
        assert "SecurityService" not in source