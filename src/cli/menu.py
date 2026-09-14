"""Interactive menu interface for the Cryptography Testing Lab CLI.

Launches a simple numbered menu.  Each choice constructs an ``argparse.Namespace``
and delegates to the same handler functions used by the subcommand path — no
duplicated logic.

No crypto logic.  No new dependencies.
"""

from __future__ import annotations

import argparse

from src.cli import commands


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

_PROMPT_TITLE = "\n=== Cryptography Testing Lab ==="

_MENU_TEXT = """
1. Encrypt
2. Decrypt
3. Benchmark
4. Security Analysis
5. Exit
"""


def _prompt_choice_int(label: str, valid: set[int], default: int | None = None) -> int:
    """Prompt for an integer from a fixed set of choices."""
    hint = "/".join(str(v) for v in sorted(valid))
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{label} ({hint}){suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
        except ValueError:
            print(f"  Enter one of: {hint}")
            continue
        if value not in valid:
            print(f"  Enter one of: {hint}")
            continue
        return value


def _prompt_choice_str(label: str, valid: set[str], default: str | None = None) -> str:
    """Prompt for a string from a fixed set of choices.

    Case-insensitive on input; returns the canonical casing from *valid* (e.g.
    ``"hex"`` for input ``"HEX"``) so downstream exact-casing comparisons work.
    """
    hint = "/".join(sorted(valid))
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"{label} ({hint}){suffix}: ").strip()
        if not raw and default is not None:
            return default
        match = next((v for v in valid if v.upper() == raw.upper()), None)
        if match is None:
            print(f"  Enter one of: {hint}")
            continue
        return match


def _prompt_non_empty(label: str) -> str:
    """Prompt for a non-empty string."""
    while True:
        raw = input(f"{label}: ").strip()
        if raw:
            return raw
        print("  Value cannot be empty.")


# ---------------------------------------------------------------------------
# Menu choice handlers — each builds a Namespace and calls a run_* handler
# ---------------------------------------------------------------------------


def _menu_encrypt(args) -> None:
    ns = argparse.Namespace()
    ns.algorithm = "AES"
    ns.verbose = getattr(args, "verbose", False)

    ns.key_size = _prompt_choice_int("Key size", {128, 192, 256})
    ns.mode = _prompt_choice_str("Mode", {"ECB", "CBC"})
    ns.input = _prompt_non_empty("Plaintext")
    ns.input_format = _prompt_choice_str("Plaintext format", {"text", "hex"}, default="text")
    ns.iv = None

    # Key strategy
    print("Key mode: 1=hex key, 2=generate random, 3=masked prompt")
    key_mode = input("Select [1/2/3]: ").strip()
    if key_mode == "2":
        ns.key = None
        ns.generate_key = True
    elif key_mode == "3":
        ns.key = None
        ns.generate_key = False
        # handler will fall back to getpass
    else:
        ns.key = _prompt_non_empty("Key (hex)")
        ns.generate_key = False

    # Optional IV for CBC
    if ns.mode == "CBC":
        raw_iv = input("IV (hex, Enter to auto-generate): ").strip()
        ns.iv = raw_iv or None

    commands.run_encrypt(ns)


def _menu_decrypt(args) -> None:
    ns = argparse.Namespace()
    ns.algorithm = "AES"
    ns.verbose = getattr(args, "verbose", False)

    ns.key_size = _prompt_choice_int("Key size", {128, 192, 256})
    ns.mode = _prompt_choice_str("Mode", {"ECB", "CBC"})
    ns.key = _prompt_non_empty("Key (hex)")
    ns.input = _prompt_non_empty("Ciphertext (hex)")
    ns.iv = None

    if ns.mode == "CBC":
        raw_iv = input("IV (hex): ").strip()
        if raw_iv:
            ns.iv = raw_iv
        else:
            print("  CBC decryption requires an IV.")
            ns.iv = None  # will raise via handler

    commands.run_decrypt(ns)


def _menu_benchmark(args) -> None:
    ns = argparse.Namespace()
    ns.algorithm = "AES"
    ns.verbose = getattr(args, "verbose", False)

    ns.key_sizes = input("Key sizes (comma-separated) [128,192,256]: ").strip() or "128,192,256"
    ns.modes = input("Modes (comma-separated) [ECB,CBC]: ").strip() or "ECB,CBC"
    ns.payload_sizes = input("Payload sizes in bytes (comma-separated) [1048576]: ").strip() or "1048576"

    commands.run_benchmark(ns)


def _menu_security(args) -> None:
    ns = argparse.Namespace()
    ns.algorithm = "AES"
    ns.verbose = getattr(args, "verbose", False)

    ns.mode = _prompt_choice_str("Mode", {"ECB", "CBC"}, default="CBC")
    ns.key = _prompt_non_empty("Base key (hex)")
    ns.plaintext = input("Base plaintext (Enter for default sample): ").strip()
    ns.plaintext_format = "text"
    if ns.plaintext:
        ns.plaintext_format = _prompt_choice_str("Plaintext format", {"text", "hex"}, default="text")

    raw_iv = input("IV (hex, Enter to auto-generate): ").strip()
    ns.iv = raw_iv or None

    ns.bmp_width = int(input("BMP width [64]: ").strip() or "64")
    ns.bmp_height = int(input("BMP height [64]: ").strip() or "64")

    commands.run_security(ns)


# ---------------------------------------------------------------------------
# Main menu loop
# ---------------------------------------------------------------------------


def run_menu(args=None) -> None:
    """Launch the interactive menu.

    Reuses the same ``commands.run_*`` handlers as the subcommand path.
    Errors are caught per-choice so the user can try again.
    """
    print(_PROMPT_TITLE)

    while True:
        print(_MENU_TEXT)
        try:
            choice = input("Select an option (1-5): ").strip()
        except EOFError:
            break

        try:
            if choice == "1":
                _menu_encrypt(args)
            elif choice == "2":
                _menu_decrypt(args)
            elif choice == "3":
                _menu_benchmark(args)
            elif choice == "4":
                _menu_security(args)
            elif choice == "5":
                break
            else:
                print("Invalid choice. Please enter 1-5.")
        except (ValueError, TypeError, KeyError) as exc:
            print(f"\nError: {exc}")
            print("Returning to menu.\n")

    print("Goodbye.")