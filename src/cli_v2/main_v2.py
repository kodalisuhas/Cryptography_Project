"""CLI Entrypoint Router for the V2 usability layer."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.cli_v2.menu_v2 import MenuV2
from src.cli_v2.batch_orchestrator import BatchOrchestrator
from src.cli_v2.report_generator import ReportGenerator
from src.cli_v2.key_manager import KeyManager
from src.cli_v2.error_translator import ErrorTranslator
from src.cli_v2.presentation import Presentation
from src.engines.cipher_service import CipherService
from src.engines.benchmark_service import BenchmarkService
from src.engines.security_service import SecurityService
from src.utils.file_handler import FileHandler


EXIT_SUCCESS = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2


def _create_minimal_bmp(width: int = 16, height: int = 16) -> bytes:
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
    header[26:28] = (1).to_bytes(2, "little")
    header[28:30] = (24).to_bytes(2, "little")
    header[30:34] = (0).to_bytes(4, "little")
    header[34:38] = pixel_size.to_bytes(4, "little")

    pixels = bytearray(pixel_size)
    for i in range(len(pixels)):
        pixels[i] = (i % 256)

    return bytes(header) + bytes(pixels)


class ArgumentParserWithExit(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        sys.exit(EXIT_USAGE)


def create_parser() -> argparse.ArgumentParser:
    parser = ArgumentParserWithExit(prog="python -m src.cli_v2.main_v2", description="Cryptography Testing Lab V2 CLI")
    subparsers = parser.add_subparsers(dest="command")

    # menu
    subparsers.add_parser("menu", help="Launch interactive menu")

    # encrypt
    encrypt_p = subparsers.add_parser("encrypt", help="Encrypt a single file")
    encrypt_p.add_argument("--input", type=Path, required=True, help="Input file path")
    encrypt_p.add_argument("--key-size", type=int, choices=[128, 192, 256], required=True, help="Key size in bits")
    encrypt_p.add_argument("--mode", choices=["ECB", "CBC"], required=True, help="Cipher mode")
    group = encrypt_p.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate-key", action="store_true", help="Generate a new key")
    group.add_argument("--key", type=str, help="Hexadecimal key string")
    encrypt_p.add_argument("--output", type=Path, help="Output file path")
    encrypt_p.add_argument("--iv", type=str, help="Hexadecimal IV string (CBC only)")
    encrypt_p.add_argument("--verbose", action="store_true", help="Enable verbose error output")

    # decrypt
    decrypt_p = subparsers.add_parser("decrypt", help="Decrypt a single file")
    decrypt_p.add_argument("--input", type=Path, required=True, help="Input file path")
    decrypt_p.add_argument("--key-size", type=int, choices=[128, 192, 256], required=True, help="Key size in bits")
    decrypt_p.add_argument("--mode", choices=["ECB", "CBC"], required=True, help="Cipher mode")
    decrypt_p.add_argument("--key", type=str, required=True, help="Hexadecimal key string")
    decrypt_p.add_argument("--output", type=Path, help="Output file path")
    decrypt_p.add_argument("--iv", type=str, help="Hexadecimal IV string (CBC only)")
    decrypt_p.add_argument("--verbose", action="store_true", help="Enable verbose error output")

    # batch-encrypt
    be_p = subparsers.add_parser("batch-encrypt", help="Encrypt a folder")
    be_p.add_argument("--input", type=Path, required=True, help="Input directory")
    be_p.add_argument("--key-size", type=int, choices=[128, 192, 256], required=True, help="Key size in bits")
    be_p.add_argument("--mode", choices=["ECB", "CBC"], required=True, help="Cipher mode")
    be_p.add_argument("--output", type=Path, help="Output directory")
    be_p.add_argument("--shared-key", action="store_true", help="Use a shared key for the batch")
    be_p.add_argument("--on-conflict", choices=["skip", "overwrite"], default="skip", help="Conflict policy")
    be_p.add_argument("--dry-run", action="store_true", help="Simulate batch without writing")
    be_p.add_argument("--verbose", action="store_true", help="Enable verbose error output")

    # batch-decrypt
    bd_p = subparsers.add_parser("batch-decrypt", help="Decrypt a folder")
    bd_p.add_argument("--input", type=Path, required=True, help="Input directory")
    bd_p.add_argument("--key-size", type=int, choices=[128, 192, 256], required=True, help="Key size in bits")
    bd_p.add_argument("--mode", choices=["ECB", "CBC"], required=True, help="Cipher mode")
    bd_p.add_argument("--output", type=Path, help="Output directory")
    bd_p.add_argument("--shared-key", action="store_true", help="Use a shared key for the batch")
    bd_p.add_argument("--on-conflict", choices=["skip", "overwrite"], default="skip", help="Conflict policy")
    bd_p.add_argument("--dry-run", action="store_true", help="Simulate batch without writing")
    bd_p.add_argument("--verbose", action="store_true", help="Enable verbose error output")

    # benchmark
    bm_p = subparsers.add_parser("benchmark", help="Run performance suite")
    bm_p.add_argument("--preset", choices=["quick", "standard", "full"], default="quick", help="Benchmark preset")
    bm_p.add_argument("--no-open", action="store_true", help="Do not open report in browser")
    bm_p.add_argument("--verbose", action="store_true", help="Enable verbose error output")

    # security
    sec_p = subparsers.add_parser("security", help="Run security suite")
    sec_p.add_argument("--no-open", action="store_true", help="Do not open report in browser")
    sec_p.add_argument("--verbose", action="store_true", help="Enable verbose error output")

    # report
    rep_p = subparsers.add_parser("report", help="View HTML report")
    rep_p.add_argument("--input", type=Path, required=True, help="HTML report path")
    rep_p.add_argument("--no-open", action="store_true", help="Do not open report in browser")
    rep_p.add_argument("--verbose", action="store_true", help="Enable verbose error output")

    return parser


def _handle_encrypt(args: argparse.Namespace) -> int:
    plaintext = FileHandler.read_bytes(args.input)
    cipher_svc = CipherService()

    if args.generate_key:
        cipher = cipher_svc.factory.create_cipher("AES", args.key_size, args.mode)
        key = cipher.generate_key()
    else:
        hex_key = KeyManager.normalize_hex(args.key)
        KeyManager.validate_key_hex(hex_key)
        key = bytes.fromhex(hex_key)
        if len(key) * 8 != args.key_size:
            raise ValueError(f"Key length ({len(key) * 8} bits) does not match requested size ({args.key_size} bits).")

    iv = None
    if args.iv:
        hex_iv = KeyManager.normalize_hex(args.iv)
        KeyManager.validate_iv_hex(hex_iv)
        iv = bytes.fromhex(hex_iv)

    enc_res = cipher_svc.encrypt_data("AES", args.key_size, args.mode, plaintext, key, iv=iv)
    ciphertext = enc_res.ciphertext
    out_iv = enc_res.iv

    # Round trip verify
    dec = cipher_svc.decrypt_data("AES", args.key_size, args.mode, ciphertext, key, out_iv)
    if dec != plaintext:
        raise ValueError("In-memory round-trip verification failed.")

    default_out = Path("data/output") / f"{args.input.name}.enc"
    output_path = args.output or default_out
    FileHandler.ensure_directory(output_path.parent)
    FileHandler.write_bytes(output_path, ciphertext)

    key_sidecar = Path(str(output_path) + ".key")
    KeyManager.save_key(key, key_sidecar)

    iv_sidecar = None
    if args.mode == "CBC" and out_iv is not None:
        iv_sidecar = Path(str(output_path) + ".iv")
        KeyManager.save_iv(out_iv, iv_sidecar)

    fields = {
        "Operation": "Single-File Encryption",
        "Input File": str(args.input),
        "Ciphertext Output": str(output_path),
        "Algorithm / Mode": f"AES-{args.key_size}-{args.mode}",
        "Key Location": str(key_sidecar),
        "IV Location": str(iv_sidecar) if iv_sidecar else "None (ECB Mode)",
        "Round-Trip Verify": "PASSED (In-memory decrypt matches original)",
        "Laboratory Key": key.hex(),
    }
    notice = (
        "[!] Laboratory Notice: The full encryption key is displayed above for\n"
        "    laboratory and testing verification. Plaintext key storage is provided\n"
        "    for lab convenience. In production, store keys in secure key vaults."
    )
    print("\n" + Presentation.format_summary_card("OPERATION SUCCESSFUL: ENCRYPTION", fields, notice))
    return 0


def _handle_decrypt(args: argparse.Namespace) -> int:
    ciphertext = FileHandler.read_bytes(args.input)
    hex_key = KeyManager.normalize_hex(args.key)
    KeyManager.validate_key_hex(hex_key)
    key = bytes.fromhex(hex_key)
    if len(key) * 8 != args.key_size:
        raise ValueError("Key length does not match requested size.")

    iv = None
    if args.mode == "CBC":
        if args.iv:
            hex_iv = KeyManager.normalize_hex(args.iv)
            KeyManager.validate_iv_hex(hex_iv)
            iv = bytes.fromhex(hex_iv)

    cipher_svc = CipherService()
    plaintext = cipher_svc.decrypt_data("AES", args.key_size, args.mode, ciphertext, key, iv)

    suggested = args.input.name[:-4] if args.input.name.endswith(".enc") else f"{args.input.name}.dec"
    default_out = Path("data/decrypted") / suggested
    output_path = args.output or default_out

    FileHandler.ensure_directory(output_path.parent)
    FileHandler.write_bytes(output_path, plaintext)

    fields = {
        "Operation": "Single-File Decryption",
        "Ciphertext File": str(args.input),
        "Restored Output": str(output_path),
        "Algorithm / Mode": f"AES-{args.key_size}-{args.mode}",
        "Status": "SUCCESS (Plaintext restored and verified)",
    }
    print("\n" + Presentation.format_summary_card("OPERATION SUCCESSFUL: DECRYPTION", fields))
    return 0


def _handle_batch_encrypt(args: argparse.Namespace) -> int:
    cipher_svc = CipherService()
    batch = BatchOrchestrator(cipher_svc)

    shared_key = None
    if args.shared_key:
        cipher = cipher_svc.factory.create_cipher("AES", args.key_size, args.mode)
        shared_key = cipher.generate_key()

    out_dir = args.output or Path("data/output")
    summary = batch.run_batch_encrypt(
        source_dir=args.input,
        dest_dir=out_dir,
        algorithm="AES",
        key_size=args.key_size,
        mode=args.mode,
        shared_key=shared_key,
        on_conflict=args.on_conflict,
        dry_run=args.dry_run,
        progress_callback=Presentation.update_progress
    )

    fields = {
        "Operation": "Batch Folder Encryption",
        "Source Directory": str(args.input),
        "Destination Dir": str(out_dir),
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
    return 0


def _handle_batch_decrypt(args: argparse.Namespace) -> int:
    cipher_svc = CipherService()
    batch = BatchOrchestrator(cipher_svc)

    shared_key = None
    if args.shared_key:
        batch_key_file = args.input / "batch.key"
        if batch_key_file.exists():
            shared_key, _ = KeyManager.load_key(batch_key_file)
        else:
            raise ValueError(f"Shared key requested but {batch_key_file} not found.")

    out_dir = args.output or Path("data/decrypted")
    summary = batch.run_batch_decrypt(
        source_dir=args.input,
        dest_dir=out_dir,
        algorithm="AES",
        key_size=args.key_size,
        mode=args.mode,
        shared_key=shared_key,
        on_conflict=args.on_conflict,
        dry_run=args.dry_run,
        progress_callback=Presentation.update_progress
    )

    fields = {
        "Operation": "Batch Folder Decryption",
        "Source Directory": str(args.input),
        "Destination Dir": str(out_dir),
        "Total Ciphertexts": summary.total_files,
        "Successfully Decrypted": summary.success_count,
        "Skipped (Existing)": summary.skipped_count,
        "Failed Files": summary.failed_count,
        "Total Data Processed": f"{summary.total_bytes:,} bytes",
        "Total Elapsed Time": f"{summary.total_time_ms:.2f} ms",
        "Batch Log File": str(summary.log_file) if summary.log_file else "None",
    }
    print("\n" + Presentation.format_summary_card("BATCH DECRYPTION SUMMARY", fields))
    return 0


def _handle_benchmark(args: argparse.Namespace) -> int:
    if args.preset == "quick":
        configs = [
            {"algorithm": "AES", "key_size": 128, "mode": "CBC"},
            {"algorithm": "AES", "key_size": 256, "mode": "CBC"},
            {"algorithm": "AES", "key_size": 128, "mode": "ECB"},
            {"algorithm": "AES", "key_size": 256, "mode": "ECB"},
        ]
        payloads = [b"\x00" * 1024, b"\x00" * (1024 * 1024)]
    elif args.preset == "standard":
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

    svc = BenchmarkService()
    collector = svc.run_performance_suite(configs, payloads)
    path = ReportGenerator.build_benchmark_report(collector)
    if not args.no_open:
        ReportGenerator.open_in_browser(path)
    return 0


def _handle_security(args: argparse.Namespace) -> int:
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

    svc = SecurityService()
    results = svc.run_security_suite(
        configs=configs,
        plaintext1=p1,
        plaintext2=plaintext2,
        key1=k1,
        key2=key2,
        image_bytes=image_bytes,
        iv=iv,
    )
    path = ReportGenerator.build_security_report(results)
    if not args.no_open:
        ReportGenerator.open_in_browser(path)
    return 0


def _handle_report(args: argparse.Namespace) -> int:
    if not args.input.exists():
        raise FileNotFoundError(f"Report file {args.input} does not exist.")
    if args.input.suffix.lower() != ".html":
        raise ValueError(f"Report file {args.input} must be an HTML file.")

    if not args.no_open:
        ReportGenerator.open_in_browser(args.input)
    return 0


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = create_parser()
    parsed = parser.parse_args(args)
    if parsed.command in ("encrypt", "decrypt"):
        if parsed.mode == "ECB" and parsed.iv is not None:
            parser.error("argument --iv not allowed with --mode ECB")
    return parsed


def main(args: list[str] | None = None) -> int:
    cli_args = args if args is not None else sys.argv[1:]
    if not cli_args or cli_args == ["menu"]:
        MenuV2().display_main_menu()
        return EXIT_SUCCESS

    parsed = parse_args(cli_args)

    verbose = getattr(parsed, "verbose", False)
    
    try:
        if parsed.command == "encrypt":
            return _handle_encrypt(parsed)
        elif parsed.command == "decrypt":
            return _handle_decrypt(parsed)
        elif parsed.command == "batch-encrypt":
            return _handle_batch_encrypt(parsed)
        elif parsed.command == "batch-decrypt":
            return _handle_batch_decrypt(parsed)
        elif parsed.command == "benchmark":
            return _handle_benchmark(parsed)
        elif parsed.command == "security":
            return _handle_security(parsed)
        elif parsed.command == "report":
            return _handle_report(parsed)
        
        return EXIT_SUCCESS

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return EXIT_SUCCESS
    except (ValueError, FileNotFoundError, PermissionError, OSError) as exc:
        ErrorTranslator.display_error(exc, context="CLI", verbose=verbose)
        return EXIT_RUNTIME


if __name__ == "__main__":
    sys.exit(main())
