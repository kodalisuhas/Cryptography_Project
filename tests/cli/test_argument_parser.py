"""Tests for the argument parser: subcommand structure, choices, and error handling.

Convention: pytest, function-based tests, argparse.SystemExit for usage errors.
"""

import pytest
from src.cli.argument_parser import create_parser


# ── Helpers ──────────────────────────────────────────────────────────


def _parse(args_list: list[str]):
    """Parse arguments and return the Namespace (raises SystemExit on usage error)."""
    return create_parser().parse_args(args_list)


# ── create_parser existence ──────────────────────────────────────────


class TestParserExists:
    def test_create_parser_returns_argument_parser(self):
        import argparse

        assert isinstance(create_parser(), argparse.ArgumentParser)

    def test_all_subcommands_registered(self):
        import argparse

        parser = create_parser()
        # Locate the subparsers action via its choices dictionary.
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1, "expected exactly one subparsers action"
        choices = subparsers_actions[0].choices
        for cmd in ("encrypt", "decrypt", "benchmark", "security", "menu"):
            assert cmd in choices


# ── --help exits cleanly ─────────────────────────────────────────────


class TestHelp:
    def test_top_level_help(self):
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(["--help"])
        assert exc_info.value.code == 0

    @pytest.mark.parametrize("cmd", ["encrypt", "decrypt", "benchmark", "security", "menu"])
    def test_subcommand_help(self, cmd):
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args([cmd, "--help"])
        assert exc_info.value.code == 0


# ── Missing command → exit 2 ────────────────────────────────────────


class TestMissingCommand:
    def test_no_args_exits_2(self):
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args([])
        assert exc_info.value.code == 2


# ── Forbidden optional arguments → exit 2 ───────────────────────────


class TestForbiddenOptionalArgs:
    @pytest.mark.parametrize("flag", ["--iterations", "--warmup", "--runs"])
    def test_forbidden_args_rejected(self, flag):
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(["encrypt", flag, "30", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16, "--input", "hello"])
        assert exc_info.value.code == 2


# ── --verbose parsing ───────────────────────────────────────────────


class TestVerboseParsing:
    def test_verbose_before_subcommand(self):
        ns = _parse(["--verbose", "encrypt", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16, "--input", "hi"])
        assert ns.verbose is True

    def test_verbose_after_subcommand(self):
        ns = _parse(["encrypt", "--verbose", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16, "--input", "hi"])
        assert ns.verbose is True

    def test_no_verbose_defaults_false(self):
        ns = _parse(["encrypt", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16, "--input", "hi"])
        assert ns.verbose is False


# ── encrypt parsing ─────────────────────────────────────────────────


class TestEncryptParsing:
    def _base(self, extras=None):
        args = ["encrypt", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16, "--input", "hello"]
        if extras:
            args.extend(extras)
        return _parse(args)

    def test_command(self):
        ns = self._base()
        assert ns.command == "encrypt"

    def test_defaults(self):
        ns = self._base()
        assert ns.algorithm == "AES"
        assert ns.input_format == "text"

    def test_key_size_int(self):
        ns = self._base()
        assert ns.key_size == 128
        assert isinstance(ns.key_size, int)

    def test_mode_upper(self):
        ns = self._base()
        assert ns.mode == "ECB"

    def test_key_hex(self):
        ns = self._base()
        assert ns.key == "ab" * 16

    def test_generate_key(self):
        args = ["encrypt", "--key-size", "128", "--mode", "ECB", "--generate-key", "--input", "hi"]
        ns = _parse(args)
        assert ns.generate_key is True
        assert ns.key is None

    def test_hex_input(self):
        ns = self._base(["--input-format", "hex", "--input", "48656c6c6f"])
        assert ns.input_format == "hex"
        assert ns.input == "48656c6c6f"

    def test_iv_optional(self):
        ns = self._base(["--iv", "00" * 16])
        assert ns.iv == "00" * 16

    def test_iv_defaults_none(self):
        ns = self._base()
        assert ns.iv is None

    def test_key_and_generate_mutually_exclusive(self):
        args = ["encrypt", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16, "--generate-key", "--input", "hi"]
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(args)
        assert exc_info.value.code == 2

    def test_missing_key_size(self):
        args = ["encrypt", "--mode", "ECB", "--key", "ab" * 16, "--input", "hi"]
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(args)
        assert exc_info.value.code == 2

    def test_missing_mode(self):
        args = ["encrypt", "--key-size", "128", "--key", "ab" * 16, "--input", "hi"]
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(args)
        assert exc_info.value.code == 2

    def test_missing_input(self):
        # Frozen persistence contract: --input is optional at parse time; the
        # conditional requirement (--input XOR --input-file) is enforced by
        # validate_persistence_args() inside main(), still a usage error (2).
        from src.cli.main import main

        args = ["encrypt", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16]
        with pytest.raises(SystemExit) as exc_info:
            main(args)
        assert exc_info.value.code == 2

    def test_invalid_key_size(self):
        args = ["encrypt", "--key-size", "512", "--mode", "ECB", "--key", "ab" * 16, "--input", "hi"]
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(args)
        assert exc_info.value.code == 2

    def test_invalid_mode(self):
        args = ["encrypt", "--key-size", "128", "--mode", "GCM", "--key", "ab" * 16, "--input", "hi"]
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(args)
        assert exc_info.value.code == 2

    def test_invalid_algorithm(self):
        args = ["encrypt", "--algorithm", "RSA", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16, "--input", "hi"]
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(args)
        assert exc_info.value.code == 2


# ── decrypt parsing ─────────────────────────────────────────────────


class TestDecryptParsing:
    def _base(self, extras=None):
        args = ["decrypt", "--key-size", "128", "--mode", "ECB", "--key", "ab" * 16, "--input", "cafe" * 16]
        if extras:
            args.extend(extras)
        return _parse(args)

    def test_command(self):
        ns = self._base()
        assert ns.command == "decrypt"

    def test_key_required(self):
        args = ["decrypt", "--key-size", "128", "--mode", "ECB", "--input", "cafe" * 16]
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(args)
        assert exc_info.value.code == 2

    def test_iv_optional_for_decrypt(self):
        ns = self._base()
        assert ns.iv is None

    def test_iv_can_be_set(self):
        ns = self._base(["--iv", "00" * 16])
        assert ns.iv == "00" * 16


# ── benchmark parsing ───────────────────────────────────────────────


class TestBenchmarkParsing:
    def _base(self, extras=None):
        args = ["benchmark"]
        if extras:
            args.extend(extras)
        return _parse(args)

    def test_defaults(self):
        ns = self._base()
        assert ns.algorithm == "AES"
        assert ns.key_sizes == "128,192,256"
        assert ns.modes == "ECB,CBC"
        assert ns.payload_sizes == "1048576"

    def test_custom_lists(self):
        ns = self._base(["--key-sizes", "128,256", "--modes", "CBC", "--payload-sizes", "512,1024"])
        assert ns.key_sizes == "128,256"
        assert ns.modes == "CBC"
        assert ns.payload_sizes == "512,1024"

    def test_benchmark_has_no_key_size(self):
        """Benchmark uses --key-sizes (list), not --key-size (single)."""
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(["benchmark", "--key-size", "128"])
        assert exc_info.value.code == 2


# ── security parsing ────────────────────────────────────────────────


class TestSecurityParsing:
    def _base(self, extras=None):
        args = ["security", "--mode", "CBC", "--key", "ab" * 16]
        if extras:
            args.extend(extras)
        return _parse(args)

    def test_command(self):
        ns = self._base()
        assert ns.command == "security"
        assert ns.algorithm == "AES"

    def test_defaults(self):
        ns = self._base()
        assert ns.plaintext == ""
        assert ns.plaintext_format == "text"
        assert ns.bmp_width == 64
        assert ns.bmp_height == 64
        assert ns.iv is None

    def test_key_required(self):
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(["security", "--mode", "CBC"])
        assert exc_info.value.code == 2

    def test_mode_required(self):
        with pytest.raises(SystemExit) as exc_info:
            create_parser().parse_args(["security", "--key", "ab" * 16])
        assert exc_info.value.code == 2

    def test_custom_bmp(self):
        ns = self._base(["--bmp-width", "32", "--bmp-height", "16"])
        assert ns.bmp_width == 32
        assert ns.bmp_height == 16

    def test_plaintext_format(self):
        ns = self._base(["--plaintext", "deadbeef", "--plaintext-format", "hex"])
        assert ns.plaintext_format == "hex"
        assert ns.plaintext == "deadbeef"


# ── menu parsing ────────────────────────────────────────────────────


class TestMenuParsing:
    def test_menu_command(self):
        ns = _parse(["menu"])
        assert ns.command == "menu"
        assert ns.verbose is False

    def test_menu_verbose(self):
        ns = _parse(["--verbose", "menu"])
        assert ns.command == "menu"
        assert ns.verbose is True