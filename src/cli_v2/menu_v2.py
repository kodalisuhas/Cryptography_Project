"""Guided menu and wizard orchestration engine for V2 usability layer.

Provides a task-centric terminal menu, 6 guided workflows (Single-File Encrypt,
Single-File Decrypt, Batch Encrypt, Batch Decrypt, Performance Benchmark,
Security Analysis), supporting views (Report Viewer, Help), universal step
navigation (Back, Cancel, Help), automatic in-memory round-trip verification,
3-tier error diagnostics, and laboratory key visibility.

This module owns interactive UI orchestration only.  Cryptographic execution,
benchmarking, and cryptanalysis are delegated to the frozen V1 services
(CipherService, BenchmarkService, SecurityService).  Key persistence and
validation are delegated to KeyManager; file enumeration and path cleaning are
delegated to FilePicker; terminal formatting and Explorer launching are
delegated to Presentation; HTML reports and browser dispatch are delegated to
ReportGenerator; exception translation is delegated to ErrorTranslator.
"""

from __future__ import annotations

import os
from pathlib import Path
import time
from typing import Any, Callable

from src.analyzers.metric_collector import MetricCollector
from src.cli_v2.batch_orchestrator import BatchOrchestrator, BatchSummary
from src.cli_v2.error_translator import ErrorTranslator
from src.cli_v2.file_picker import FilePicker
from src.cli_v2.key_manager import KeyManager
from src.cli_v2.navigation import NavigationEngine, StepResult, WizardStep
from src.cli_v2.presentation import Presentation
from src.cli_v2.report_generator import ReportGenerator
from src.engines.benchmark_service import BenchmarkService
from src.engines.cipher_service import CipherService
from src.engines.security_service import SecurityService
from src.utils.file_handler import FileHandler


def _create_minimal_bmp(width: int = 16, height: int = 16) -> bytes:
    """Create a minimal valid 24-bpp uncompressed BMP image in memory."""
    row_bytes = width * 3
    row_stride = ((row_bytes + 3) // 4) * 4
    pixel_size = row_stride * height
    file_size = 54 + pixel_size

    header = bytearray(54)
    header[0:2] = b"BM"
    header[2:6] = file_size.to_bytes(4, "little")
    header[10:14] = (54).to_bytes(4, "little")
    header[14:18] = (40).to_bytes(4, "little")
    header[18:22] = width.to_bytes(4, "little", signed=True)
    header[22:26] = height.to_bytes(4, "little", signed=True)
    header[26:28] = (1).to_bytes(2, "little")  # planes
    header[28:30] = (24).to_bytes(2, "little")  # 24 bpp
    header[30:34] = (0).to_bytes(4, "little")   # uncompressed
    header[34:38] = pixel_size.to_bytes(4, "little")

    # Alternate pixel colors for pattern demonstration
    pixels = bytearray(pixel_size)
    for i in range(len(pixels)):
        pixels[i] = (i % 256)

    return bytes(header) + bytes(pixels)


class MenuV2:
    """Task-centric guided wizard engine for the V2 usability layer."""

    DEFAULT_INPUT_DIR = Path("data/input")
    DEFAULT_OUTPUT_DIR = Path("data/output")
    DEFAULT_DECRYPTED_DIR = Path("data/decrypted")
    DEFAULT_REPORTS_DIR = Path("results/reports")

    def __init__(
        self,
        cipher_service: CipherService | None = None,
        benchmark_service: BenchmarkService | None = None,
        security_service: SecurityService | None = None,
        navigation: NavigationEngine | None = None,
        batch_orchestrator: BatchOrchestrator | None = None,
        verbose: bool = False,
    ):
        self._cipher_service = cipher_service or CipherService()
        self._benchmark_service = benchmark_service or BenchmarkService()
        self._security_service = security_service or SecurityService()
        self._nav = navigation or NavigationEngine()
        self._batch_orchestrator = batch_orchestrator or BatchOrchestrator(self._cipher_service)
        self._verbose = verbose

    # =========================================================================
    # Main Menu Loop
    # =========================================================================

    def display_main_menu(self) -> None:
        """Display the task-centric V2 main menu and route user choices."""
        while True:
            print("\n============================================================")
            print("              CRYPTOGRAPHY TESTING LAB — V2")
            print("============================================================")
            print("  1. Single-File Operations (Encrypt, Decrypt, Verify)")
            print("  2. Batch Operations (Folder Encrypt, Folder Decrypt)")
            print("  3. Benchmark & Performance Suite")
            print("  4. Security & Cryptanalysis Lab")
            print("  5. View & Generate HTML Reports")
            print("  6. Help & Documentation")
            print("  7. File-Specific Encryption Analysis")
            print("  8. Exit")
            print("============================================================")

            try:
                raw = input("Select an option [1-8]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting Cryptography Testing Lab. Goodbye!")
                break

            if not raw:
                continue

            token = raw.lower()
            if token in ("8", "exit", "quit", "q", "c", "cancel"):
                print("\nExiting Cryptography Testing Lab. Goodbye!")
                break
            elif token in ("?", "help"):
                self.run_help_wizard()
                continue
            elif token in ("b", "back"):
                print("  (Already at main menu)")
                continue

            if raw == "1":
                self._handle_single_file_menu()
            elif raw == "2":
                self._handle_batch_menu()
            elif raw == "3":
                self.run_benchmark_wizard()
            elif raw == "4":
                self.run_security_wizard()
            elif raw == "5":
                self.run_report_viewer_wizard()
            elif raw == "6":
                self.run_help_wizard()
            elif raw == "7":
                self.run_file_analysis_wizard()
            else:
                print("  Invalid option. Please enter a number between 1 and 8 (or '?' for help).")

    def _handle_single_file_menu(self) -> None:
        """Sub-menu for Single-File operations."""
        res = self._nav.prompt_choice(
            "Single-File Operations:",
            [
                "Encrypt a File (with auto sidecar key & round-trip verification)",
                "Decrypt a File (with auto sidecar detection)",
                "Return to Main Menu",
            ],
            default=1,
            help_text="Select whether to encrypt a plaintext file or decrypt an existing ciphertext.",
        )
        if res.action in ("CANCEL", "BACK") or res.value == 2 or res.value is None:
            return
        if res.value == 0:
            self.run_single_encrypt_wizard()
        elif res.value == 1:
            self.run_single_decrypt_wizard()

    def _handle_batch_menu(self) -> None:
        """Sub-menu for Batch Operations."""
        res = self._nav.prompt_choice(
            "Batch Operations:",
            [
                "Encrypt a Folder (multi-file directory encryption with error isolation)",
                "Decrypt a Folder (multi-file directory decryption with error isolation)",
                "Return to Main Menu",
            ],
            default=1,
            help_text="Batch process an entire directory of files with per-file error isolation and CSV logging.",
        )
        if res.action in ("CANCEL", "BACK") or res.value == 2 or res.value is None:
            return
        if res.value == 0:
            self.run_batch_encrypt_wizard()
        elif res.value == 1:
            self.run_batch_decrypt_wizard()

    # =========================================================================
    # 1. Single-File Encryption Wizard
    # =========================================================================

    def run_single_encrypt_wizard(self, input_path: Path | None = None) -> None:
        """Run the single-file encryption wizard with automatic round-trip verify."""
        print("\n--- Single-File Encryption Wizard ---")

        try:
            step = 1
            chosen_input: Path | None = input_path
            algorithm: str = "AES"
            key_size: int = 256
            mode: str = "CBC"
            key: bytes | None = None
            output_path: Path | None = None

            while True:
                if step == 1:
                    if input_path is not None:
                        chosen_input = input_path
                        step = 2
                        continue

                    # Select input file
                    FileHandler.ensure_directory(self.DEFAULT_INPUT_DIR)
                    files = FilePicker.list_files(self.DEFAULT_INPUT_DIR)
                    options = [f"{p.name} ({FilePicker.format_size(s)})" for p, s in files]
                    options.append("Enter custom file path...")

                    res = self._nav.prompt_choice(
                        f"Select input file to encrypt from '{self.DEFAULT_INPUT_DIR}/':",
                        options,
                        default=1 if files else len(options),
                        help_text="Select a file from the default input folder, or enter a custom path.",
                    )
                    if res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if res.action == "BACK":
                        return

                    if res.value == len(options) - 1:
                        # Custom path
                        custom_res = self._nav.prompt_step(
                            WizardStep(
                                name="custom_input",
                                prompt_text="Enter path to plaintext file",
                                help_text="Provide an absolute or relative path to the file you want to encrypt.",
                                validator=lambda s: FilePicker.clean_path(s),
                            )
                        )
                        if custom_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if custom_res.action == "BACK":
                            continue
                        chosen_input = custom_res.value
                    else:
                        chosen_input = files[res.value][0]

                    if not chosen_input.exists() or not chosen_input.is_file():
                        print(f"  Error: File '{chosen_input}' not found or is not a regular file.")
                        continue

                    step = 2

                elif step == 2:
                    # Select Algorithm & Mode & Key Size
                    mode_options = [
                        "AES-256-CBC (Recommended default — Maximum key size with CBC mode)",
                        "AES-128-CBC (Standard 128-bit key with CBC mode)",
                        "AES-192-CBC (Standard 192-bit key with CBC mode)",
                        "AES-256-ECB (Demonstration only — Leaks data patterns!)",
                        "AES-128-ECB (Demonstration only — Leaks data patterns!)",
                        "AES-192-ECB (Demonstration only — Leaks data patterns!)",
                    ]
                    res = self._nav.prompt_choice(
                        "Select Cipher Configuration:",
                        mode_options,
                        default=1,
                        help_text="CBC provides block chaining with a unique IV; ECB encrypts blocks independently and is insecure for structured data.",
                    )
                    if res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if res.action == "BACK":
                        if input_path is not None:
                            return
                        step = 1
                        continue

                    config_map = {
                        0: ("AES", 256, "CBC"),
                        1: ("AES", 128, "CBC"),
                        2: ("AES", 192, "CBC"),
                        3: ("AES", 256, "ECB"),
                        4: ("AES", 128, "ECB"),
                        5: ("AES", 192, "ECB"),
                    }
                    algorithm, key_size, mode = config_map[res.value]
                    if mode == "ECB":
                        print("\n  [!] Security Notice: ECB mode does NOT hide data patterns. Provided for educational comparison only.\n")

                    step = 3

                elif step == 3:
                    # Key Strategy
                    key_options = [
                        "Generate New Key & Save Sidecar (.key) (Recommended default)",
                        "Load existing .key sidecar file",
                        "Enter raw hexadecimal key string",
                    ]
                    res = self._nav.prompt_choice(
                        "Select Key Strategy:",
                        key_options,
                        default=1,
                        help_text="Choose whether to generate a fresh random key or supply an existing key.",
                    )
                    if res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if res.action == "BACK":
                        step = 2
                        continue

                    if res.value == 0:
                        # Generate new key via V1 cipher
                        cipher = self._cipher_service.factory.create_cipher(algorithm, key_size, mode)
                        key = cipher.generate_key()
                    elif res.value == 1:
                        # Load existing key file
                        key_step_res = self._nav.prompt_step(
                            WizardStep(
                                name="key_file_path",
                                prompt_text="Enter path to .key file",
                                help_text="Path to an existing .key sidecar file.",
                                validator=lambda s: FilePicker.clean_path(s),
                            )
                        )
                        if key_step_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if key_step_res.action == "BACK":
                            continue
                        loaded_key, loaded_bits = KeyManager.load_key(key_step_res.value)
                        key = loaded_key
                        key_size = loaded_bits
                    elif res.value == 2:
                        # Enter raw hex
                        hex_res = self._nav.prompt_step(
                            WizardStep(
                                name="raw_hex_key",
                                prompt_text=f"Enter {key_size // 8}-byte hex key ({key_size // 4} chars)",
                                help_text=f"Hexadecimal string of {key_size // 4} characters for AES-{key_size}.",
                                validator=lambda s: bytes.fromhex(KeyManager.normalize_hex(s)),
                            )
                        )
                        if hex_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if hex_res.action == "BACK":
                            continue
                        key = hex_res.value
                        KeyManager.validate_key_hex(key.hex())

                    step = 4

                elif step == 4:
                    # Destination resolution
                    default_dest = self.DEFAULT_OUTPUT_DIR / f"{chosen_input.name}.enc"
                    dest_res = self._nav.prompt_step(
                        WizardStep(
                            name="output_destination",
                            prompt_text=f"Destination ciphertext path [default: {default_dest}]",
                            help_text="Path where the encrypted ciphertext file should be written.",
                            validator=lambda s: FilePicker.clean_path(s) if s else default_dest,
                        )
                    )
                    if dest_res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if dest_res.action == "BACK":
                        step = 3
                        continue

                    output_path = dest_res.value
                    if output_path.exists():
                        conflict_res = self._nav.prompt_choice(
                            f"[!] Conflict: Destination '{output_path}' already exists:",
                            ["Overwrite existing file", "Choose another name", "Cancel"],
                            default=1,
                            help_text="Choose whether to overwrite the existing destination file.",
                        )
                        if conflict_res.action == "CANCEL" or conflict_res.value == 2:
                            print("\n[!] Operation cancelled by user.")
                            return
                        if conflict_res.action == "BACK":
                            continue
                        if conflict_res.value == 1:
                            continue  # Re-prompt for destination

                    step = 5

                elif step == 5:
                    # Execution & In-Memory Round-Trip Verification
                    start_time = time.perf_counter()
                    plaintext = FileHandler.read_bytes(chosen_input)

                    # 1. Encrypt via V1 CipherService
                    enc_result = self._cipher_service.encrypt_data(
                        algorithm, key_size, mode, plaintext, key, iv=None
                    )
                    ciphertext = enc_result.ciphertext
                    iv = enc_result.iv

                    # 2. In-Memory Round-Trip Verification (Assert decrypt(encrypt(P)) == P)
                    decrypted_plaintext = self._cipher_service.decrypt_data(
                        algorithm, key_size, mode, ciphertext, key, iv
                    )
                    if decrypted_plaintext != plaintext:
                        raise ValueError(
                            "In-memory round-trip verification failed: decrypted bytes do not match original plaintext."
                        )

                    # 3. Commit output files
                    FileHandler.ensure_directory(output_path.parent)
                    FileHandler.write_bytes(output_path, ciphertext)

                    # 4. Save Key & IV sidecars
                    key_sidecar = Path(str(output_path) + ".key")
                    KeyManager.save_key(key, key_sidecar)

                    if mode == "CBC" and iv is not None:
                        iv_sidecar = Path(str(output_path) + ".iv")
                        KeyManager.save_iv(iv, iv_sidecar)
                    else:
                        iv_sidecar = None

                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                    # 5. Render Structured Summary Card
                    fields = {
                        "Operation": "Single-File Encryption",
                        "Input File": f"{chosen_input} ({FilePicker.format_size(len(plaintext))})",
                        "Ciphertext Output": f"{output_path} ({FilePicker.format_size(len(ciphertext))})",
                        "Algorithm / Mode": f"AES-{key_size}-{mode}",
                        "Key Location": str(key_sidecar),
                        "IV Location": str(iv_sidecar) if iv_sidecar else "None (ECB Mode)",
                        "Execution Time": f"{elapsed_ms:.2f} ms",
                        "Round-Trip Verify": "PASSED (In-memory decrypt matches original)",
                        "Laboratory Key": key.hex(),
                    }
                    notice = (
                        "[!] Laboratory Notice: The full encryption key is displayed above for\n"
                        "    laboratory and testing verification. Plaintext key storage is provided\n"
                        "    for lab convenience. In production, store keys in secure key vaults."
                    )
                    print("\n" + Presentation.format_summary_card("OPERATION SUCCESSFUL: ENCRYPTION", fields, notice))

                    # 6. Post-Operation Actions
                    next_res = self._nav.prompt_choice(
                        "Next Action:",
                        [
                            "Open output folder in File Explorer",
                            "Test decrypt this file now",
                            "Return to Main Menu",
                        ],
                        default=3,
                        help_text="Choose a follow-up action or return to the main menu.",
                    )
                    if next_res.value == 0:
                        Presentation.open_explorer(output_path.parent)
                    elif next_res.value == 1:
                        self.run_single_decrypt_wizard(ciphertext_path=output_path)

                    return

        except KeyboardInterrupt:
            print("\n[!] Operation cancelled by user.")
            return
        except Exception as exc:
            ErrorTranslator.display_error(exc, context="Single-File Encryption", verbose=self._verbose)
            return

    # =========================================================================
    # 2. Single-File Decryption Wizard
    # =========================================================================

    def run_single_decrypt_wizard(self, ciphertext_path: Path | None = None) -> None:
        """Run the single-file decryption wizard with auto-detection of sidecars."""
        print("\n--- Single-File Decryption Wizard ---")

        try:
            step = 1
            chosen_cipher: Path | None = ciphertext_path
            key: bytes | None = None
            key_size: int = 256
            mode: str = "CBC"
            iv: bytes | None = None
            output_path: Path | None = None

            while True:
                if step == 1:
                    if ciphertext_path is not None:
                        chosen_cipher = ciphertext_path
                        step = 2
                        continue

                    # Select ciphertext file
                    FileHandler.ensure_directory(self.DEFAULT_OUTPUT_DIR)
                    files = FilePicker.list_files(self.DEFAULT_OUTPUT_DIR, exclude_extensions={".key", ".iv", ".log", ".tmp"})
                    options = [f"{p.name} ({FilePicker.format_size(s)})" for p, s in files]
                    options.append("Enter custom ciphertext path...")

                    res = self._nav.prompt_choice(
                        f"Select ciphertext file from '{self.DEFAULT_OUTPUT_DIR}/':",
                        options,
                        default=1 if files else len(options),
                        help_text="Select an encrypted file to decrypt, or specify a custom path.",
                    )
                    if res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if res.action == "BACK":
                        return

                    if res.value == len(options) - 1:
                        custom_res = self._nav.prompt_step(
                            WizardStep(
                                name="custom_ciphertext",
                                prompt_text="Enter path to ciphertext file",
                                help_text="Provide path to the encrypted file.",
                                validator=lambda s: FilePicker.clean_path(s),
                            )
                        )
                        if custom_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if custom_res.action == "BACK":
                            continue
                        chosen_cipher = custom_res.value
                    else:
                        chosen_cipher = files[res.value][0]

                    if not chosen_cipher.exists() or not chosen_cipher.is_file():
                        print(f"  Error: File '{chosen_cipher}' not found or is not a regular file.")
                        continue

                    step = 2

                elif step == 2:
                    # Key Acquisition (Auto-detect companion sidecar)
                    detected_key, detected_iv = KeyManager.auto_detect_sidecars(chosen_cipher)

                    if detected_key is not None:
                        use_auto = self._nav.prompt_yes_no(
                            f"Detected key sidecar '{detected_key.name}'. Use this key?",
                            default_yes=True,
                            help_text="Automatically load the encryption key from the companion .key sidecar file.",
                        )
                        if use_auto.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if use_auto.action == "BACK":
                            if ciphertext_path is not None:
                                return
                            step = 1
                            continue

                        if use_auto.value:
                            key, key_size = KeyManager.load_key(detected_key)
                            step = 3
                            continue

                    # Manual key selection
                    key_opts = [
                        "Select .key file from disk",
                        "Enter raw hexadecimal key string",
                    ]
                    key_choice = self._nav.prompt_choice(
                        "How would you like to provide the decryption key?",
                        key_opts,
                        default=1,
                        help_text="Choose to browse for a .key file or paste raw hexadecimal characters.",
                    )
                    if key_choice.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if key_choice.action == "BACK":
                        if ciphertext_path is not None:
                            return
                        step = 1
                        continue

                    if key_choice.value == 0:
                        path_res = self._nav.prompt_step(
                            WizardStep(
                                name="key_path_manual",
                                prompt_text="Enter path to .key file",
                                help_text="Path to the .key sidecar file.",
                                validator=lambda s: FilePicker.clean_path(s),
                            )
                        )
                        if path_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if path_res.action == "BACK":
                            continue
                        key, key_size = KeyManager.load_key(path_res.value)
                    else:
                        hex_res = self._nav.prompt_step(
                            WizardStep(
                                name="raw_hex_key_decrypt",
                                prompt_text="Enter hex key string (32/48/64 characters)",
                                help_text="Raw hexadecimal key string (128, 192, or 256 bits).",
                                validator=lambda s: bytes.fromhex(KeyManager.normalize_hex(s)),
                            )
                        )
                        if hex_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if hex_res.action == "BACK":
                            continue
                        key = hex_res.value
                        key_size = KeyManager.validate_key_hex(key.hex())

                    step = 3

                elif step == 3:
                    # Mode & IV Acquisition
                    detected_key, detected_iv = KeyManager.auto_detect_sidecars(chosen_cipher)

                    mode_res = self._nav.prompt_choice(
                        "Select Cipher Mode:",
                        [
                            "CBC (Cipher Block Chaining — Requires IV) [Default]",
                            "ECB (Electronic Codebook — No IV)",
                        ],
                        default=1 if detected_iv else 1,
                        help_text="Select the mode that was used during encryption.",
                    )
                    if mode_res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if mode_res.action == "BACK":
                        step = 2
                        continue

                    mode = "CBC" if mode_res.value == 0 else "ECB"

                    if mode == "CBC":
                        if detected_iv is not None:
                            use_iv_res = self._nav.prompt_yes_no(
                                f"Detected IV sidecar '{detected_iv.name}'. Use this IV?",
                                default_yes=True,
                                help_text="Automatically load the Initialization Vector from the companion .iv sidecar file.",
                            )
                            if use_iv_res.action == "CANCEL":
                                print("\n[!] Operation cancelled by user.")
                                return
                            if use_iv_res.action == "BACK":
                                continue
                            if use_iv_res.value:
                                iv = KeyManager.load_iv(detected_iv)
                                step = 4
                                continue

                        # Manual IV input
                        iv_res = self._nav.prompt_step(
                            WizardStep(
                                name="manual_iv_input",
                                prompt_text="Enter 32-character hex IV (16 bytes)",
                                help_text="Hexadecimal Initialization Vector used during CBC encryption.",
                                validator=lambda s: KeyManager.validate_iv_hex(KeyManager.normalize_hex(s)),
                            )
                        )
                        if iv_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if iv_res.action == "BACK":
                            continue
                        iv = iv_res.value
                    else:
                        iv = None

                    step = 4

                elif step == 4:
                    # Output destination
                    suggested_name = chosen_cipher.name[:-4] if chosen_cipher.name.lower().endswith(".enc") else f"{chosen_cipher.name}.dec"
                    default_dest = self.DEFAULT_DECRYPTED_DIR / suggested_name

                    dest_res = self._nav.prompt_step(
                        WizardStep(
                            name="decrypt_dest_path",
                            prompt_text=f"Destination plaintext path [default: {default_dest}]",
                            help_text="Path where the recovered plaintext should be saved.",
                            validator=lambda s: FilePicker.clean_path(s) if s else default_dest,
                        )
                    )
                    if dest_res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if dest_res.action == "BACK":
                        step = 3
                        continue

                    output_path = dest_res.value
                    if output_path.exists():
                        conflict_res = self._nav.prompt_choice(
                            f"[!] Conflict: Destination '{output_path}' already exists:",
                            ["Overwrite existing file", "Choose another name", "Cancel"],
                            default=1,
                            help_text="Choose whether to overwrite the existing destination file.",
                        )
                        if conflict_res.action == "CANCEL" or conflict_res.value == 2:
                            print("\n[!] Operation cancelled by user.")
                            return
                        if conflict_res.action == "BACK":
                            continue
                        if conflict_res.value == 1:
                            continue

                    step = 5

                elif step == 5:
                    # Execution
                    start_time = time.perf_counter()
                    ciphertext = FileHandler.read_bytes(chosen_cipher)

                    plaintext = self._cipher_service.decrypt_data(
                        "AES", key_size, mode, ciphertext, key, iv
                    )

                    FileHandler.ensure_directory(output_path.parent)
                    FileHandler.write_bytes(output_path, plaintext)

                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                    fields = {
                        "Operation": "Single-File Decryption",
                        "Ciphertext File": f"{chosen_cipher} ({FilePicker.format_size(len(ciphertext))})",
                        "Restored Output": f"{output_path} ({FilePicker.format_size(len(plaintext))})",
                        "Algorithm / Mode": f"AES-{key_size}-{mode}",
                        "Execution Time": f"{elapsed_ms:.2f} ms",
                        "Status": "SUCCESS (Plaintext restored and verified)",
                    }
                    print("\n" + Presentation.format_summary_card("OPERATION SUCCESSFUL: DECRYPTION", fields))

                    next_res = self._nav.prompt_choice(
                        "Next Action:",
                        [
                            "Open output folder in File Explorer",
                            "Return to Main Menu",
                        ],
                        default=2,
                        help_text="Choose a follow-up action or return to the main menu.",
                    )
                    if next_res.value == 0:
                        Presentation.open_explorer(output_path.parent)

                    return

        except KeyboardInterrupt:
            print("\n[!] Operation cancelled by user.")
            return
        except Exception as exc:
            ErrorTranslator.display_error(exc, context="Single-File Decryption", verbose=self._verbose)
            return

    # =========================================================================
    # 3. Batch Folder Encryption Wizard
    # =========================================================================

    def run_batch_encrypt_wizard(
        self,
        source_dir: Path | None = None,
        dest_dir: Path | None = None,
    ) -> None:
        """Run the batch folder encryption wizard with preflight preview and error isolation."""
        print("\n--- Batch Folder Encryption Wizard ---")

        try:
            step = 1
            src_path: Path = source_dir or self.DEFAULT_INPUT_DIR
            dst_path: Path = dest_dir or self.DEFAULT_OUTPUT_DIR
            algorithm: str = "AES"
            key_size: int = 256
            mode: str = "CBC"
            shared_key: bytes | None = None
            on_conflict: str = "skip"

            while True:
                if step == 1:
                    if source_dir is not None:
                        src_path = source_dir
                        step = 2
                        continue

                    src_res = self._nav.prompt_step(
                        WizardStep(
                            name="batch_src_dir",
                            prompt_text=f"Source directory containing plaintext files [default: {self.DEFAULT_INPUT_DIR}]",
                            help_text="Directory to scan for candidate plaintext files to encrypt.",
                            validator=lambda s: FilePicker.clean_path(s) if s else self.DEFAULT_INPUT_DIR,
                        )
                    )
                    if src_res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if src_res.action == "BACK":
                        return

                    src_path = src_res.value
                    if not src_path.exists() or not src_path.is_dir():
                        print(f"  Error: Directory '{src_path}' not found.")
                        continue

                    step = 2

                elif step == 2:
                    # Config & Key Strategy
                    cfg_res = self._nav.prompt_choice(
                        "Select Cipher Configuration:",
                        [
                            "AES-256-CBC (Recommended default)",
                            "AES-128-CBC",
                            "AES-256-ECB (Demonstration only)",
                            "AES-128-ECB (Demonstration only)",
                        ],
                        default=1,
                        help_text="Select cipher mode and key size for the batch operation.",
                    )
                    if cfg_res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if cfg_res.action == "BACK":
                        if source_dir is not None:
                            return
                        step = 1
                        continue

                    mode_map = {
                        0: ("AES", 256, "CBC"),
                        1: ("AES", 128, "CBC"),
                        2: ("AES", 256, "ECB"),
                        3: ("AES", 128, "ECB"),
                    }
                    algorithm, key_size, mode = mode_map[cfg_res.value]

                    key_strat = self._nav.prompt_choice(
                        "Select Batch Key Strategy:",
                        [
                            "Unique per-file keys (.enc.key for each file) [Default / Secure]",
                            "Shared batch key (single batch.key for entire folder)",
                        ],
                        default=1,
                        help_text="Unique keys minimize blast radius; shared key uses one key for all files with unique random IVs in CBC mode.",
                    )
                    if key_strat.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if key_strat.action == "BACK":
                        continue

                    if key_strat.value == 1:
                        cipher = self._cipher_service.factory.create_cipher(algorithm, key_size, mode)
                        shared_key = cipher.generate_key()
                    else:
                        shared_key = None

                    step = 3

                elif step == 3:
                    # Destination & Conflict Policy
                    if dest_dir is None:
                        dst_res = self._nav.prompt_step(
                            WizardStep(
                                name="batch_dest_dir",
                                prompt_text=f"Destination output directory [default: {self.DEFAULT_OUTPUT_DIR}]",
                                help_text="Directory where encrypted ciphertexts and sidecars will be stored.",
                                validator=lambda s: FilePicker.clean_path(s) if s else self.DEFAULT_OUTPUT_DIR,
                            )
                        )
                        if dst_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if dst_res.action == "BACK":
                            step = 2
                            continue
                        dst_path = dst_res.value

                    conflict_res = self._nav.prompt_choice(
                        "File Conflict / Overwrite Policy:",
                        [
                            "Skip Existing (Recommended default — Safe non-destructive resumption)",
                            "Overwrite All (Replace existing ciphertexts)",
                        ],
                        default=1,
                        help_text="Skip Existing enables non-destructive retry/resumption by bypassing existing ciphertexts.",
                    )
                    if conflict_res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if conflict_res.action == "BACK":
                        if dest_dir is not None:
                            step = 2
                        continue

                    on_conflict = "skip" if conflict_res.value == 0 else "overwrite"
                    step = 4

                elif step == 4:
                    # Preflight discovery & preview
                    candidates, excluded = self._batch_orchestrator.discover_files(src_path, is_encryption=True)
                    preflight = self._batch_orchestrator.preflight_check(candidates, dst_path, on_conflict)

                    print("\n============================================================")
                    print("               BATCH ENCRYPTION PRE-FLIGHT")
                    print("============================================================")
                    print(f"  Source Directory : {src_path}")
                    print(f"  Destination Dir  : {dst_path}")
                    print(f"  Candidate Files  : {len(candidates)}")
                    print(f"  Excluded Entries : {len(excluded)}")
                    print(f"  Collisions Found : {len(preflight['collisions'])}")
                    print(f"  Will Process     : {preflight['proceed_count']}")
                    print(f"  Will Skip        : {preflight['skipped_count']}")
                    print(f"  Algorithm / Mode : AES-{key_size}-{mode}")
                    print(f"  Key Strategy     : {'Shared batch.key' if shared_key is not None else 'Unique per-file keys'}")
                    print(f"  Conflict Policy  : {on_conflict.capitalize()}")
                    print("============================================================")

                    if not candidates:
                        print("\n[!] No candidate plaintext files discovered in source directory.\n")
                        return

                    confirm_res = self._nav.prompt_yes_no(
                        "Proceed with batch encryption?",
                        default_yes=True,
                        help_text="Confirm execution of the planned batch encryption operation.",
                    )
                    if confirm_res.action == "CANCEL" or not confirm_res.value:
                        print("\n[!] Batch encryption cancelled by user.")
                        return
                    if confirm_res.action == "BACK":
                        step = 3
                        continue

                    step = 5

                elif step == 5:
                    # Execution
                    print("\nEncrypting files...")
                    summary = self._batch_orchestrator.run_batch_encrypt(
                        source_dir=src_path,
                        dest_dir=dst_path,
                        algorithm=algorithm,
                        key_size=key_size,
                        mode=mode,
                        shared_key=shared_key,
                        on_conflict=on_conflict,
                        progress_callback=Presentation.update_progress,
                    )

                    fields = {
                        "Operation": "Batch Folder Encryption",
                        "Source Directory": str(src_path),
                        "Destination Dir": str(dst_path),
                        "Total Discovered": summary.total_files,
                        "Successfully Encrypted": summary.success_count,
                        "Skipped (Existing)": summary.skipped_count,
                        "Failed Files": summary.failed_count,
                        "Total Data Processed": f"{summary.total_bytes:,} bytes",
                        "Total Elapsed Time": f"{summary.total_time_ms:.2f} ms",
                        "Batch Log File": str(summary.log_file) if summary.log_file else "None",
                    }
                    notice = (
                        "[!] Laboratory Notice: Batch encryption complete. Keys saved to companion\n"
                        "    sidecars in the destination directory. Log written to batch_log_*.csv."
                    )
                    print("\n" + Presentation.format_summary_card("BATCH OPERATION SUMMARY", fields, notice))

                    if summary.failed_count > 0:
                        print("\n[!] Failed Files:")
                        for r in summary.results:
                            if r.status == "FAILED":
                                print(f"  - {r.source_file.name}: {r.error_message}")

                    next_res = self._nav.prompt_choice(
                        "Next Action:",
                        [
                            "Open output folder in File Explorer",
                            "Return to Main Menu",
                        ],
                        default=2,
                        help_text="Choose a follow-up action or return to the main menu.",
                    )
                    if next_res.value == 0:
                        Presentation.open_explorer(dst_path)

                    return

        except KeyboardInterrupt:
            print("\n[!] Operation cancelled by user.")
            return
        except Exception as exc:
            ErrorTranslator.display_error(exc, context="Batch Encryption", verbose=self._verbose)
            return

    # =========================================================================
    # 4. Batch Folder Decryption Wizard
    # =========================================================================

    def run_batch_decrypt_wizard(
        self,
        source_dir: Path | None = None,
        dest_dir: Path | None = None,
    ) -> None:
        """Run the batch folder decryption wizard with error isolation and sidecar resolution."""
        print("\n--- Batch Folder Decryption Wizard ---")

        try:
            step = 1
            src_path: Path = source_dir or self.DEFAULT_OUTPUT_DIR
            dst_path: Path = dest_dir or self.DEFAULT_DECRYPTED_DIR
            algorithm: str = "AES"
            key_size: int = 256
            mode: str = "CBC"
            shared_key: bytes | None = None
            on_conflict: str = "skip"

            while True:
                if step == 1:
                    if source_dir is not None:
                        src_path = source_dir
                        step = 2
                        continue

                    src_res = self._nav.prompt_step(
                        WizardStep(
                            name="batch_decrypt_src",
                            prompt_text=f"Source directory containing .enc files [default: {self.DEFAULT_OUTPUT_DIR}]",
                            help_text="Directory containing *.enc ciphertext files to decrypt.",
                            validator=lambda s: FilePicker.clean_path(s) if s else self.DEFAULT_OUTPUT_DIR,
                        )
                    )
                    if src_res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if src_res.action == "BACK":
                        return

                    src_path = src_res.value
                    if not src_path.exists() or not src_path.is_dir():
                        print(f"  Error: Directory '{src_path}' not found.")
                        continue

                    step = 2

                elif step == 2:
                    # Key Strategy & Mode
                    mode_choice = self._nav.prompt_choice(
                        "Select Cipher Mode for Batch Decryption:",
                        [
                            "CBC (Cipher Block Chaining — Requires .iv sidecars) [Default]",
                            "ECB (Electronic Codebook)",
                        ],
                        default=1,
                        help_text="Cipher mode used when encrypting the batch files.",
                    )
                    if mode_choice.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if mode_choice.action == "BACK":
                        if source_dir is not None:
                            return
                        step = 1
                        continue

                    mode = "CBC" if mode_choice.value == 0 else "ECB"

                    batch_key_file = src_path / "batch.key"
                    if batch_key_file.exists():
                        key_opt = self._nav.prompt_choice(
                            f"Key Strategy (Detected '{batch_key_file.name}'):",
                            [
                                "Use per-file companion .key sidecars (Default)",
                                f"Use detected shared '{batch_key_file.name}' for all files",
                            ],
                            default=1,
                            help_text="Choose whether to load individual .key sidecars per file or use a shared batch key.",
                        )
                        if key_opt.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if key_opt.action == "BACK":
                            continue
                        if key_opt.value == 1:
                            shared_key, key_size = KeyManager.load_key(batch_key_file)
                        else:
                            shared_key = None
                    else:
                        shared_key = None

                    step = 3

                elif step == 3:
                    # Destination & Conflict
                    if dest_dir is None:
                        dst_res = self._nav.prompt_step(
                            WizardStep(
                                name="batch_decrypt_dest",
                                prompt_text=f"Destination directory for recovered files [default: {self.DEFAULT_DECRYPTED_DIR}]",
                                help_text="Directory where decrypted plaintexts will be stored.",
                                validator=lambda s: FilePicker.clean_path(s) if s else self.DEFAULT_DECRYPTED_DIR,
                            )
                        )
                        if dst_res.action == "CANCEL":
                            print("\n[!] Operation cancelled by user.")
                            return
                        if dst_res.action == "BACK":
                            step = 2
                            continue
                        dst_path = dst_res.value

                    conflict_res = self._nav.prompt_choice(
                        "File Conflict / Overwrite Policy:",
                        [
                            "Skip Existing (Recommended default — Safe non-destructive resumption)",
                            "Overwrite All (Replace existing plaintexts)",
                        ],
                        default=1,
                        help_text="Skip Existing enables non-destructive retry/resumption by bypassing existing restored files.",
                    )
                    if conflict_res.action == "CANCEL":
                        print("\n[!] Operation cancelled by user.")
                        return
                    if conflict_res.action == "BACK":
                        if dest_dir is not None:
                            step = 2
                        continue

                    on_conflict = "skip" if conflict_res.value == 0 else "overwrite"
                    step = 4

                elif step == 4:
                    # Preflight
                    candidates, excluded = self._batch_orchestrator.discover_files(src_path, is_encryption=False)
                    preflight = self._batch_orchestrator.preflight_check(candidates, dst_path, on_conflict)

                    print("\n============================================================")
                    print("               BATCH DECRYPTION PRE-FLIGHT")
                    print("============================================================")
                    print(f"  Source Directory : {src_path}")
                    print(f"  Destination Dir  : {dst_path}")
                    print(f"  Ciphertext Files : {len(candidates)}")
                    print(f"  Excluded Entries : {len(excluded)}")
                    print(f"  Collisions Found : {len(preflight['collisions'])}")
                    print(f"  Will Process     : {preflight['proceed_count']}")
                    print(f"  Will Skip        : {preflight['skipped_count']}")
                    print(f"  Algorithm / Mode : AES-{key_size}-{mode}")
                    print(f"  Key Strategy     : {'Shared batch.key' if shared_key is not None else 'Individual per-file .key sidecars'}")
                    print(f"  Conflict Policy  : {on_conflict.capitalize()}")
                    print("============================================================")

                    if not candidates:
                        print("\n[!] No candidate *.enc ciphertext files discovered in source directory.\n")
                        return

                    confirm_res = self._nav.prompt_yes_no(
                        "Proceed with batch decryption?",
                        default_yes=True,
                        help_text="Confirm execution of the planned batch decryption operation.",
                    )
                    if confirm_res.action == "CANCEL" or not confirm_res.value:
                        print("\n[!] Batch decryption cancelled by user.")
                        return
                    if confirm_res.action == "BACK":
                        step = 3
                        continue

                    step = 5

                elif step == 5:
                    # Execution
                    print("\nDecrypting files...")
                    summary = self._batch_orchestrator.run_batch_decrypt(
                        source_dir=src_path,
                        dest_dir=dst_path,
                        algorithm=algorithm,
                        key_size=key_size,
                        mode=mode,
                        shared_key=shared_key,
                        on_conflict=on_conflict,
                        progress_callback=Presentation.update_progress,
                    )

                    fields = {
                        "Operation": "Batch Folder Decryption",
                        "Source Directory": str(src_path),
                        "Destination Dir": str(dst_path),
                        "Total Ciphertexts": summary.total_files,
                        "Successfully Decrypted": summary.success_count,
                        "Skipped (Existing)": summary.skipped_count,
                        "Failed Files": summary.failed_count,
                        "Total Data Processed": f"{summary.total_bytes:,} bytes",
                        "Total Elapsed Time": f"{summary.total_time_ms:.2f} ms",
                        "Batch Log File": str(summary.log_file) if summary.log_file else "None",
                    }
                    print("\n" + Presentation.format_summary_card("BATCH DECRYPTION SUMMARY", fields))

                    if summary.failed_count > 0:
                        print("\n[!] Failed Files:")
                        for r in summary.results:
                            if r.status == "FAILED":
                                print(f"  - {r.source_file.name}: {r.error_message}")

                    next_res = self._nav.prompt_choice(
                        "Next Action:",
                        [
                            "Open output folder in File Explorer",
                            "Return to Main Menu",
                        ],
                        default=2,
                        help_text="Choose a follow-up action or return to the main menu.",
                    )
                    if next_res.value == 0:
                        Presentation.open_explorer(dst_path)

                    return

        except KeyboardInterrupt:
            print("\n[!] Operation cancelled by user.")
            return
        except Exception as exc:
            ErrorTranslator.display_error(exc, context="Batch Decryption", verbose=self._verbose)
            return

    # =========================================================================
    # 5. Performance Benchmark Wizard
    # =========================================================================

    def run_benchmark_wizard(self) -> None:
        """Run performance benchmark suite and generate standalone HTML report."""
        print("\n--- Performance & Benchmark Suite ---")

        try:
            preset_choice = self._nav.prompt_choice(
                "Select Benchmark Preset:",
                [
                    "Quick Benchmark (AES 128/256-bit, CBC/ECB, 1KB & 1MB payloads) [Default]",
                    "Standard Benchmark (AES 128/192/256-bit, CBC/ECB, 1KB, 64KB, 1MB payloads)",
                    "Full Matrix Benchmark (All key sizes, CBC/ECB, 1KB, 64KB, 1MB, 10MB payloads)",
                ],
                default=1,
                help_text="Presets execute 5 warmup cycles and 30 sample iterations per configuration per the frozen V1 methodology.",
            )
            if preset_choice.action in ("CANCEL", "BACK") or preset_choice.value is None:
                return

            if preset_choice.value == 0:
                configs = [
                    {"algorithm": "AES", "key_size": 128, "mode": "CBC"},
                    {"algorithm": "AES", "key_size": 256, "mode": "CBC"},
                    {"algorithm": "AES", "key_size": 128, "mode": "ECB"},
                    {"algorithm": "AES", "key_size": 256, "mode": "ECB"},
                ]
                payloads = [b"\x00" * 1024, b"\x00" * (1024 * 1024)]
            elif preset_choice.value == 1:
                configs = [
                    {"algorithm": "AES", "key_size": 128, "mode": "CBC"},
                    {"algorithm": "AES", "key_size": 192, "mode": "CBC"},
                    {"algorithm": "AES", "key_size": 256, "mode": "CBC"},
                    {"algorithm": "AES", "key_size": 128, "mode": "ECB"},
                    {"algorithm": "AES", "key_size": 192, "mode": "ECB"},
                    {"algorithm": "AES", "key_size": 256, "mode": "ECB"},
                ]
                payloads = [b"\x00" * 1024, b"\x00" * (64 * 1024), b"\x00" * (1024 * 1024)]
            else:
                configs = [
                    {"algorithm": "AES", "key_size": 128, "mode": "CBC"},
                    {"algorithm": "AES", "key_size": 192, "mode": "CBC"},
                    {"algorithm": "AES", "key_size": 256, "mode": "CBC"},
                    {"algorithm": "AES", "key_size": 128, "mode": "ECB"},
                    {"algorithm": "AES", "key_size": 192, "mode": "ECB"},
                    {"algorithm": "AES", "key_size": 256, "mode": "ECB"},
                ]
                payloads = [b"\x00" * 1024, b"\x00" * (64 * 1024), b"\x00" * (1024 * 1024), b"\x00" * (10 * 1024 * 1024)]

            print("\nExecuting benchmark suite (5 warmup iterations, 30 sample iterations)...")
            collector: MetricCollector = self._benchmark_service.run_performance_suite(configs, payloads)

            # Build HTML report
            print("Compiling standalone HTML performance report...")
            report_path = ReportGenerator.build_benchmark_report(collector)
            print(f"[+] Benchmark report saved: '{report_path}'")

            # Browser auto-open prompt (D4)
            open_res = self._nav.prompt_yes_no(
                "Open HTML report in web browser?",
                default_yes=True,
                help_text="Launch default web browser to view interactive report with embedded charts.",
            )
            if open_res.value:
                ReportGenerator.open_in_browser(report_path)

        except KeyboardInterrupt:
            print("\n[!] Benchmark operation cancelled by user.")
            return
        except Exception as exc:
            ErrorTranslator.display_error(exc, context="Benchmark Suite", verbose=self._verbose)
            return

    # =========================================================================
    # 6. Security & Cryptanalysis Lab Wizard
    # =========================================================================

    def run_security_wizard(self) -> None:
        """Run security evaluation suite and generate standalone HTML report."""
        print("\n--- Security & Cryptanalysis Lab ---")

        try:
            print("\nThis suite evaluates:")
            print("  1. Avalanche Effect (Plaintext 1-bit flip diffusion)")
            print("  2. Key Sensitivity (Key 1-bit flip diffusion)")
            print("  3. ECB vs CBC Bitmap Pattern Leakage Analysis")

            confirm = self._nav.prompt_yes_no(
                "Run security analysis suite?",
                default_yes=True,
                help_text="Run the security evaluation across AES-256 in CBC and ECB modes.",
            )
            if confirm.action in ("CANCEL", "BACK") or not confirm.value:
                return

            configs = [
                {"algorithm": "AES", "key_size": 256, "mode": "CBC"},
                {"algorithm": "AES", "key_size": 256, "mode": "ECB"},
            ]

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

            print("\nExecuting security evaluations via V1 SecurityService...")
            results = self._security_service.run_security_suite(
                configs=configs,
                plaintext1=p1,
                plaintext2=plaintext2,
                key1=k1,
                key2=key2,
                image_bytes=image_bytes,
                iv=iv,
            )

            # Build HTML Security Report
            print("Compiling standalone HTML security report...")
            report_path = ReportGenerator.build_security_report(results)
            print(f"[+] Security report saved: '{report_path}'")

            # Browser auto-open prompt (D4)
            open_res = self._nav.prompt_yes_no(
                "Open HTML report in web browser?",
                default_yes=True,
                help_text="Launch default web browser to view diffusion metrics and ECB structural comparisons.",
            )
            if open_res.value:
                ReportGenerator.open_in_browser(report_path)

        except KeyboardInterrupt:
            print("\n[!] Security analysis cancelled by user.")
            return
        except Exception as exc:
            ErrorTranslator.display_error(exc, context="Security Analysis", verbose=self._verbose)
            return

    # =========================================================================
    # 7. Report Viewer Wizard
    # =========================================================================

    def run_report_viewer_wizard(self) -> None:
        """Browse existing HTML reports and open them in the default browser."""
        print("\n--- HTML Report Viewer ---")

        try:
            FileHandler.ensure_directory(self.DEFAULT_REPORTS_DIR)
            report_files = FilePicker.list_files(self.DEFAULT_REPORTS_DIR, pattern="*.html")

            if not report_files:
                print(f"\n[!] No HTML reports found in '{self.DEFAULT_REPORTS_DIR}/'.")
                print("    Run a Performance Benchmark or Security Analysis to generate a report.\n")
                return

            options = [f"{p.name} ({FilePicker.format_size(s)})" for p, s in report_files]
            res = self._nav.prompt_choice(
                f"Select an HTML report to open from '{self.DEFAULT_REPORTS_DIR}/':",
                options,
                default=1,
                help_text="Select a generated standalone report to view in your web browser.",
            )
            if res.action in ("CANCEL", "BACK") or res.value is None:
                return

            chosen_report = report_files[res.value][0]
            print(f"\nOpening '{chosen_report.name}' in default browser...")
            opened = ReportGenerator.open_in_browser(chosen_report)
            if not opened:
                print(f"  (Browser dispatch failed or non-GUI environment. Report path: {chosen_report.resolve()})")

        except KeyboardInterrupt:
            print("\n[!] Report viewing cancelled by user.")
            return
        except Exception as exc:
            ErrorTranslator.display_error(exc, context="Report Viewer", verbose=self._verbose)
            return

    # =========================================================================
    # 8. Help Wizard
    # =========================================================================

    def run_help_wizard(self) -> None:
        """Display comprehensive educational help and documentation."""
        help_text = """
============================================================
            CRYPTOGRAPHY TESTING LAB — V2 HELP
============================================================

1. Overview:
   The Cryptography Testing Lab provides a guided, interactive
   environment for evaluating AES encryption, performance benchmarking,
   and cryptanalysis.

2. Universal Navigation Controls:
   At any interactive prompt:
     • 'b' or 'back'   : Return to previous configuration step.
     • 'c' or 'cancel' : Abort current operation and return to main menu.
     • '?' or 'help'   : Display in-place contextual guidance.

3. Cipher Modes & Key Sizes:
   • AES-128 / AES-192 / AES-256: Supported key lengths (16, 24, 32 bytes).
   • CBC Mode (Cipher Block Chaining): Recommended default. Each block is
     chained with the previous ciphertext block. Requires a unique random
     IV (Initialization Vector) per file. Provides confidentiality only
     (not authentication or integrity).
   • ECB Mode (Electronic Codebook): Insecure! Identical plaintext blocks
     produce identical ciphertext blocks, leaking structural patterns.
     Use ONLY for educational comparison.

4. Key Management:
   • Keys and IVs are saved as raw hexadecimal text sidecars (.key / .iv).
   • Single-file encryption creates '<output>.key' and '<output>.iv'.
   • In laboratory mode, full keys are displayed on screen for inspection.
   • Never use plaintext .key sidecars in production environments.

5. Batch Operations:
   • Encrypt or decrypt entire directories in a flat scan.
   • Per-file error isolation ensures one bad file does not stop the batch.
   • Default conflict policy is 'Skip Existing' for safe resumption.
   • A detailed CSV execution log is written to 'batch_log_*.csv'.

6. HTML Reports & Benchmarks:
   • Benchmarks execute 5 warmup cycles and 30 measured iterations.
   • Single-document HTML reports with embedded charts are saved to
     'results/reports/' and can be opened in your default browser.
============================================================
"""
        print(help_text)
        try:
            input("Press Enter to return to Main Menu...")
        except (EOFError, KeyboardInterrupt):
            pass

    # =========================================================================
    # 9. File-Specific Encryption Analysis Wizard
    # =========================================================================

    def run_file_analysis_wizard(self) -> None:
        """Run the File-Specific Encryption Analysis wizard.

        Routes user into the frozen post-V2 Analysis Lab interactive wizard
        (src.analysis_lab.cli.run_wizard_mode), providing comprehensive 6-config
        evaluation against an individual file payload with standalone HTML reporting.
        """
        print("\n--- File-Specific Encryption Analysis Lab ---")
        try:
            from src.analysis_lab.cli import build_parser, run_wizard_mode

            parser = build_parser()
            args = parser.parse_args([])
            args.verbose = self._verbose
            run_wizard_mode(args)
        except KeyboardInterrupt:
            print("\n[!] Analysis cancelled by user.")
            return
        except (OSError, ValueError, RuntimeError) as exc:
            ErrorTranslator.display_error(exc, context="File-Specific Analysis", verbose=self._verbose)
            return
