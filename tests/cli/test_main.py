"""Tests for main dispatch, exit-code mapping, and error handling.

Convention: pytest, function-based tests, monkeypatch for sys.argv.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.cli.main import main, EXIT_SUCCESS, EXIT_RUNTIME, EXIT_USAGE


# ── Dispatch tests (mocked handlers) ────────────────────────────────


class TestDispatch:
    """Verify that main() routes to the correct handler for each command."""

    @pytest.mark.parametrize(
        "command, handler_attr",
        [
            ("encrypt", "commands.run_encrypt"),
            ("decrypt", "commands.run_decrypt"),
            ("benchmark", "commands.run_benchmark"),
            ("security", "commands.run_security"),
        ],
    )
    def test_dispatches_to_handler(self, command, handler_attr, monkeypatch):
        called = []
        fake_handler = lambda args: called.append(command)

        # Patch the handler at its source module location
        with patch(f"src.cli.main.{handler_attr.split('.')[0]}", autospec=False) as mock_mod:
            setattr(mock_mod, handler_attr.split(".")[1], fake_handler)
            argv = self._base_args(command)
            monkeypatch.setattr("sys.argv", ["cli"] + argv)
            exit_code = main(argv)

        assert exit_code == EXIT_SUCCESS
        assert called == [command]

    def test_dispatches_menu(self, monkeypatch):
        called = []
        fake_menu = lambda args: called.append("menu")
        with patch("src.cli.main.menu") as mock_menu:
            mock_menu.run_menu = fake_menu
            monkeypatch.setattr("sys.argv", ["cli", "menu"])
            exit_code = main(["menu"])
        assert exit_code == EXIT_SUCCESS
        assert called == ["menu"]

    @staticmethod
    def _base_args(command):
        if command == "encrypt":
            return [
                "encrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "hello",
            ]
        elif command == "decrypt":
            return [
                "decrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "cafe" * 16,
            ]
        elif command == "benchmark":
            return ["benchmark", "--key-sizes", "128", "--modes", "ECB"]
        elif command == "security":
            return ["security", "--mode", "ECB", "--key", "ab" * 16]
        return []


# ── Error mapping ───────────────────────────────────────────────────


class TestErrorMapping:
    """Verify that exceptions from handlers map to the correct exit codes."""

    def test_value_error_exit_1(self, monkeypatch):
        def bad_handler(args):
            raise ValueError("bad input")

        with patch("src.cli.main.commands") as mock_mod:
            mock_mod.run_encrypt = bad_handler
            monkeypatch.setattr("sys.argv", ["cli"])
            exit_code = main([
                "encrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "hi",
            ])
        assert exit_code == EXIT_RUNTIME

    def test_type_error_exit_1(self, monkeypatch):
        def bad_handler(args):
            raise TypeError("wrong type")

        with patch("src.cli.main.commands") as mock_mod:
            mock_mod.run_encrypt = bad_handler
            exit_code = main([
                "encrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "hi",
            ])
        assert exit_code == EXIT_RUNTIME

    def test_key_error_exit_1(self, monkeypatch):
        def bad_handler(args):
            raise KeyError("missing key")

        with patch("src.cli.main.commands") as mock_mod:
            mock_mod.run_encrypt = bad_handler
            exit_code = main([
                "encrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "hi",
            ])
        assert exit_code == EXIT_RUNTIME

    def test_value_error_prints_message(self, monkeypatch, capsys):
        def bad_handler(args):
            raise ValueError("something broke")

        with patch("src.cli.main.commands") as mock_mod:
            mock_mod.run_encrypt = bad_handler
            main([
                "encrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "hi",
            ])
        captured = capsys.readouterr()
        assert "something broke" in captured.out

    def test_keyboard_interrupt_exit_0(self, monkeypatch, capsys):
        def bad_handler(args):
            raise KeyboardInterrupt()

        with patch("src.cli.main.commands") as mock_mod:
            mock_mod.run_encrypt = bad_handler
            exit_code = main([
                "encrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "hi",
            ])
        assert exit_code == EXIT_SUCCESS
        captured = capsys.readouterr()
        assert "Cancelled" in captured.out

    def test_unexpected_exception_exit_1(self, monkeypatch, capsys):
        def bad_handler(args):
            raise RuntimeError("unexpected")

        with patch("src.cli.main.commands") as mock_mod:
            mock_mod.run_encrypt = bad_handler
            exit_code = main([
                "encrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "hi",
            ])
        assert exit_code == EXIT_RUNTIME
        captured = capsys.readouterr()
        assert "Unexpected error" in captured.out

    def test_unexpected_exception_verbose_traceback(self, monkeypatch, capsys):
        def bad_handler(args):
            raise RuntimeError("boom")

        with patch("src.cli.main.commands") as mock_mod:
            mock_mod.run_encrypt = bad_handler
            # --verbose = True triggers traceback printing
            exit_code = main([
                "--verbose", "encrypt", "--key-size", "128", "--mode", "ECB",
                "--key", "ab" * 16, "--input", "hi",
            ])
        assert exit_code == EXIT_RUNTIME
        captured = capsys.readouterr()
        assert "boom" in captured.err  # traceback goes to stderr


# ── Unknown command → exit 2 ────────────────────────────────────────


class TestUnknownCommand:
    def test_unknown_subcommand(self, monkeypatch):
        with pytest.raises(SystemExit) as exc_info:
            main(["nonexistent"])
        assert exc_info.value.code == 2