"""
Command-line interface for File-Specific Encryption Analysis Lab.

Provides:
1. Direct CLI Mode (--input / -i): Non-interactive execution for scripts and power users.
2. Interactive Wizard Mode (invoked without --input): Step-by-step guided workflow with
   file path cleaning, preflight summary, options prompt, high-volume safeguard, and
   summary card display.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence
import webbrowser

from src.analysis_lab.runner import FileAnalysisRunner
from src.cli_v2.file_picker import FilePicker
from src.cli_v2.presentation import Presentation


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser for the laboratory."""
    parser = argparse.ArgumentParser(
        prog="python -m src.analysis_lab.cli",
        description="Post-V2 File-Specific Encryption Analysis Laboratory",
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_path",
        type=str,
        default=None,
        help="Path to input target file (triggers direct CLI mode). If omitted, launches wizard.",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        type=str,
        default=None,
        help="Destination path for generated HTML report.",
    )
    parser.add_argument(
        "--skip-decryption",
        action="store_true",
        default=False,
        help="Omit decryption microbenchmarks (run encryption only).",
    )
    parser.add_argument(
        "--security",
        action="store_true",
        default=False,
        help="Run optional security diffusion analysis (Avalanche & Key Sensitivity).",
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        default=100,
        help="Operational file-size ceiling in megabytes (default: 100).",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        default=False,
        help="Do not automatically launch HTML report in web browser.",
    )
    parser.add_argument(
        "--include-absolute-path",
        action="store_true",
        default=False,
        help="Include absolute file path in report (default: masked for privacy).",
    )
    parser.add_argument(
        "--no-hash",
        action="store_true",
        default=False,
        help="Suppress SHA-256 fingerprint in report for privacy.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Override operational size warning and ceiling.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Display detailed tracebacks on errors.",
    )
    return parser


def run_direct_mode(args: argparse.Namespace) -> int:
    """Execute direct non-interactive CLI workflow."""
    runner = FileAnalysisRunner(
        file_path=args.input_path,
        output_path=args.output_path,
        skip_decryption=args.skip_decryption,
        security_enabled=args.security,
        max_size_mb=args.max_size_mb,
        no_open=args.no_open,
        include_absolute_path=args.include_absolute_path,
        no_hash=args.no_hash,
        force=args.force,
        verbose=args.verbose,
    )

    result, report_path, exit_code = runner.run()

    if exit_code == 0 and result is not None:
        meta = result.file_metadata
        fields = {
            "Target File": meta.file_name,
            "Payload Size": f"{meta.file_size_bytes:,} bytes",
            "Configurations": (
                f"{result.success_count} / {len(result.configurations)} successful "
                f"({result.failure_count} failed)"
            ),
            "Fastest Encryption": result.fastest_encryption_config or "None",
            "Fastest Decryption": (
                "N/A (Skipped)"
                if result.skip_decryption
                else (result.fastest_decryption_config or "None")
            ),
            "HTML Report": str(report_path) if report_path else "None",
        }
        card = Presentation.format_summary_card(
            title="FILE-SPECIFIC ENCRYPTION ANALYSIS",
            fields=fields,
            notice="In-memory microbenchmark with isolated timing loops.",
        )
        print(card)

    return exit_code


def run_wizard_mode(
    args: argparse.Namespace,
    input_func: Any = input,
    browser_open: Any = webbrowser.open,
) -> int:
    """Execute interactive step-by-step guided wizard."""
    print("=" * 60)
    print("FILE-SPECIFIC ENCRYPTION ANALYSIS WIZARD".center(60))
    print("=" * 60)

    # Step 1: Input File Selection
    raw_path = input_func("Enter target file path (drag-and-drop supported, 'c' to cancel): ").strip()
    if raw_path.lower() in ("c", "cancel"):
        print("[!] Analysis cancelled.")
        return 0

    target_path = FilePicker.clean_path(raw_path)
    if not target_path.exists() or target_path.is_dir():
        print(f"[!] Invalid path or file does not exist: {target_path}", file=sys.stderr)
        return 1

    # Step 2: Preflight Inspection Display
    resolved = target_path.resolve()
    size_bytes = resolved.stat().st_size
    size_mb = size_bytes / (1024.0 * 1024.0)

    print("\n[*] Preflight Inspection:")
    print(f"  Filename   : {resolved.name}")
    print(f"  Size       : {size_bytes:,} bytes ({size_mb:.2f} MB)")
    if not args.no_hash:
        sha256 = FileAnalysisRunner.compute_sha256(resolved)
        print(f"  SHA-256    : {sha256}")

    # Step 3: Scope Confirmation
    print("\n[*] Scope: Evaluating all 6 AES configurations (AES-128/192/256 in CBC/ECB modes).")

    # Step 4: Operational Options
    skip_dec_resp = input_func("Include decryption benchmarking? [Y/n]: ").strip().lower()
    skip_decryption = (skip_dec_resp == "n")

    sec_resp = input_func(
        "Include security diffusion analysis (Avalanche & Key Sensitivity)? [y/N]: "
    ).strip().lower()
    security_enabled = (sec_resp in ("y", "yes"))

    # Step 5: High-Volume Operational Warning (if file > 30 MB)
    if size_mb > 30 and not args.force:
        vol_gb = (size_bytes * 420.0) / (1024.0 * 1024.0 * 1024.0)
        print(
            f"\n[!] Warning: File is {size_mb:.1f} MB. Evaluating 6 configurations (35 cycles each) "
            f"will process ~{vol_gb:.1f} GB through AES (before ciphertext padding differences)."
        )
        proceed_resp = input_func("Proceed? [y/N]: ").strip().lower()
        if proceed_resp not in ("y", "yes"):
            print("[!] Operation cancelled by user.")
            return 0

    # Step 6: Step-by-Step Console Execution Indicators
    print("\n[*] [1/3] Benchmarking encryption and decryption microbenchmarks...")
    if security_enabled:
        print("[*] [2/3] Evaluating security diffusion metrics...")
    print("[*] [3/3] Compiling standalone HTML report...")

    runner = FileAnalysisRunner(
        file_path=resolved,
        output_path=args.output_path,
        skip_decryption=skip_decryption,
        security_enabled=security_enabled,
        max_size_mb=args.max_size_mb,
        no_open=True,  # Handle browser opening explicitly in wizard step 8
        include_absolute_path=args.include_absolute_path,
        no_hash=args.no_hash,
        force=args.force,
        verbose=args.verbose,
    )

    result, report_path, exit_code = runner.run()

    # Step 7: Post-Operation Summary Card
    if exit_code == 0 and result is not None:
        meta = result.file_metadata
        fields = {
            "Target File": meta.file_name,
            "Payload Size": f"{meta.file_size_bytes:,} bytes",
            "Configurations": (
                f"{result.success_count} / {len(result.configurations)} successful "
                f"({result.failure_count} failed)"
            ),
            "Fastest Encryption": result.fastest_encryption_config or "None",
            "Fastest Decryption": (
                "N/A (Skipped)"
                if result.skip_decryption
                else (result.fastest_decryption_config or "None")
            ),
            "HTML Report": str(report_path) if report_path else "None",
        }
        card = Presentation.format_summary_card(
            title="FILE-SPECIFIC ENCRYPTION ANALYSIS",
            fields=fields,
            notice="In-memory microbenchmark with isolated timing loops.",
        )
        print("\n" + card)

        # Step 8: Auto-Open HTML Report Prompt
        if report_path is not None and not args.no_open:
            open_resp = input_func("\nOpen HTML report in web browser? [Y/n]: ").strip().lower()
            if open_resp != "n":
                try:
                    browser_open(report_path.resolve().as_uri())
                except Exception:
                    pass

    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for command-line execution."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.input_path is not None:
        return run_direct_mode(args)
    else:
        return run_wizard_mode(args)


if __name__ == "__main__":
    sys.exit(main())
