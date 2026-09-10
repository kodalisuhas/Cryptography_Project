"""CLI command handlers: input construction, Service invocation, result formatting.

The CLI is a thin presentation layer over the frozen Service layer.  It owns:

* argument / input conversion to ``bytes``
* key acquisition (explicit hex, generated via Core, or masked ``getpass``)
* IV parsing and validation
* benchmark configuration / payload construction
* in-memory 24-bpp BMP construction for the ECB weakness demo
* Service invocation
* result formatting and printing
* persistence orchestration (file I/O via FileHandler; the CLI owns base64
  conversion, graph generation, figure lifecycle, and overwrite checks)

It does NOT own crypto, timing, statistics, or security math.
"""

from __future__ import annotations

import base64
import getpass
import struct
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from tabulate import tabulate

from src.analyzers.graph_generator import GraphGenerator
from src.engines import CipherFactory, CipherService, BenchmarkService, SecurityService
from src.utils.file_handler import FileHandler

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AES_KEY_SIZES = (128, 192, 256)
_ECB_CBC = ("ECB", "CBC")

# Default plaintext used when --plaintext is omitted (≥ 1 byte).
_DEFAULT_SECURITY_PLAINTEXT = b"AES diffusion and sensitivity evaluation plaintext (base)."

# BMP pixel data uses deterministic bytes for reproducibility.
_BMP_ROW_FILL = b"\x5a"  # single byte repeated to fill pixel data


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _parse_hex(value: str, name: str) -> bytes:
    """Decode a hex string or raise ``ValueError`` with a clear message."""
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError(f"Invalid hex for {name}") from exc


def _decode_input(value: str, fmt: str) -> bytes:
    """Convert a CLI input string to bytes depending on format."""
    if fmt == "hex":
        return _parse_hex(value, "--input")
    # "text" — UTF-8 encode
    return value.encode("utf-8")


def _format_plaintext(data: bytes) -> str:
    """Best-effort UTF-8 display with hex fallback."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return f"(hex) {data.hex()}"


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _timestamp() -> str:
    """Return the frozen timestamp format: ``YYYYMMDD_HHMMSS``."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _check_overwrite(path: str | Path, force: bool) -> None:
    """Raise ``FileExistsError`` if *path* exists and ``--force`` is not set."""
    if FileHandler.exists(path) and not force:
        raise FileExistsError(f"Output file already exists: {path}")


def _save_benchmark_graphs(summary_df, save_graphs: str, ts: str) -> None:
    """Generate and persist the three frozen benchmark graphs.

    ``generate_key_size_comparison`` / ``generate_mode_comparison`` require a
    single ``data_size_bytes`` value.  If multiple payload sizes were
    benchmarked, filter the summary to the smallest data size for those two
    graphs (frozen Selection §39 orchestration rule).  ``throughput_analysis``
    supports multiple sizes natively and uses the full summary.
    """
    compare_df = summary_df
    if summary_df["data_size_bytes"].nunique() > 1:
        first_size = summary_df["data_size_bytes"].min()
        compare_df = summary_df[summary_df["data_size_bytes"] == first_size]

    for name, fig_df in (
        ("key_size_comparison", compare_df),
        ("mode_comparison", compare_df),
        ("throughput_analysis", summary_df),
    ):
        generator = getattr(GraphGenerator, f"generate_{name}")
        fig = generator(fig_df)
        path = f"{save_graphs}/{name}_{ts}.png"
        FileHandler.save_figure(fig, path)
        plt.close(fig)
        print(f"Saved: {path}")


_ECB_WEAKNESS_BASE64_FIELDS = (
    "original_header",
    "original_pixel_data",
    "ecb_ciphertext",
    "cbc_ciphertext",
    "bmp_trailing_data",
)


def _build_security_report(
    results: dict, algorithm: str, key_size: int, mode: str, ts: str
) -> dict:
    """Build the JSON-serializable security report, base64-encoding binary fields.

    Base64 conversion is a CLI concern.  FileHandler receives only an already
    serializable dictionary.  The frozen ``ecb_weakness`` binary fields become
    ASCII base64 strings; numeric results are preserved unchanged.
    """
    report_results = {}
    for conf, metrics in results.items():
        conf_out = dict(metrics)
        if "ecb_weakness" in metrics:
            ecb = dict(metrics["ecb_weakness"])
            for field in _ECB_WEAKNESS_BASE64_FIELDS:
                value = ecb.get(field)
                if isinstance(value, (bytes, bytearray)):
                    ecb[field] = base64.b64encode(bytes(value)).decode("ascii")
            conf_out["ecb_weakness"] = ecb
        report_results[conf] = conf_out

    return {
        "metadata": {
            "algorithm": algorithm,
            "key_size": key_size,
            "mode": mode,
            "timestamp": ts,
        },
        "results": report_results,
    }


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def _generate_key_bytes(algorithm: str, key_size: int, mode: str) -> bytes:
    """Generate a random key via the public Core factory path."""
    cipher = CipherFactory().create_cipher(algorithm, key_size, mode)
    return cipher.generate_key()


def _prompt_key_masked(key_size: int) -> bytes:
    """Read a hex-encoded key from stdin with masking."""
    hex_input = getpass.getpass(f"Enter AES-{key_size} key (hex): ")
    return _parse_hex(hex_input.strip(), "key (masked)")


def _resolve_encrypt_key(args, key_size: int) -> bytes:
    """Obtain the encryption key from --key, --generate-key, or getpass."""
    if args.key is not None:
        return _parse_hex(args.key, "--key")
    if args.generate_key:
        return _generate_key_bytes(args.algorithm, key_size, args.mode)
    # Fallback: masked interactive prompt (non-TTY will raise naturally).
    return _prompt_key_masked(key_size)


# ---------------------------------------------------------------------------
# IV helpers
# ---------------------------------------------------------------------------


def _resolve_encrypt_iv(args, mode: str):
    """Return the IV for encrypt: explicit hex, ``None`` for CBC auto-gen, or error for ECB."""
    if mode.upper() == "ECB":
        if args.iv is not None:
            raise ValueError("ECB mode does not use an IV; remove --iv")
        return None
    # CBC — explicit or auto-generated by Service
    if args.iv is None:
        return None
    return _parse_hex(args.iv, "--iv")


def _resolve_decrypt_iv(args, mode: str):
    """Return the IV for decrypt: explicit hex for CBC, ``None`` for ECB."""
    if mode.upper() == "ECB":
        if args.iv is not None:
            raise ValueError("ECB mode does not use an IV; remove --iv")
        return None
    if args.iv is None:
        raise ValueError("CBC decryption requires --iv (the IV used during encryption)")
    return _parse_hex(args.iv, "--iv")


def _resolve_security_iv(args, key_size: int) -> bytes:
    """Return a 16-byte IV for the security suite.

    If ``--iv`` is given, use it.  Otherwise obtain a controlled IV from Core
    via the public CBC cipher factory path.  The *mode* argument is irrelevant
    here because ``SecurityService`` routes the IV internally.
    """
    if args.iv is not None:
        return _parse_hex(args.iv, "--iv")
    # Public Core path — same as key generation.  Use CBC to get a valid IV.
    cipher = CipherFactory().create_cipher("AES", key_size, "CBC")
    return cipher.generate_iv()


# ---------------------------------------------------------------------------
# 1-bit pair helpers (input construction, not crypto math)
# ---------------------------------------------------------------------------


def _one_bit_partner(data: bytes) -> bytes:
    """Return a copy of *data* with exactly one bit flipped (bit 0 of first byte)."""
    if not data:
        raise ValueError("Cannot derive a 1-bit-different input from empty data")
    partner = bytearray(data)
    partner[0] ^= 0x01
    return bytes(partner)


def _key_size_from_key(key: bytes) -> int:
    """Derive AES key size in bits from key length, or raise ``ValueError``."""
    key_size = len(key) * 8
    if key_size not in _AES_KEY_SIZES:
        raise ValueError(
            f"Key length {len(key)} bytes does not match any AES key size "
            f"(need 16, 24, or 32 bytes for 128/192/256 bits)"
        )
    return key_size


# ---------------------------------------------------------------------------
# BMP builder
# ---------------------------------------------------------------------------


def _build_bmp_bytes(width: int, height: int) -> bytes:
    """Construct a minimal valid 24-bpp BMP entirely in memory.

    The resulting bytes are accepted by
    ``SecurityEvaluator.test_ecb_weakness``.  No external image libraries
    required.
    """
    if width <= 0 or height <= 0:
        raise ValueError("BMP width and height must be positive integers")
    row_bytes = width * 3
    row_stride = ((row_bytes + 3) // 4) * 4  # 4-byte row alignment
    pixel_bytes = row_stride * height
    header_size = 54
    file_size = header_size + pixel_bytes

    bmp = bytearray(header_size + pixel_bytes)

    # --- BMP file header (14 bytes) ---
    bmp[0:2] = b"BM"
    struct.pack_into("<I", bmp, 0x02, file_size)       # file size
    # bytes 0x06–0x09 reserved zeros (default)
    struct.pack_into("<I", bmp, 0x0A, header_size)     # pixel data offset

    # --- DIB (BITMAPINFOHEADER) header (40 bytes) ---
    struct.pack_into("<I", bmp, 0x0E, 40)              # header size
    struct.pack_into("<i", bmp, 0x12, width)            # width (signed)
    struct.pack_into("<i", bmp, 0x16, height)           # height (signed)
    struct.pack_into("<H", bmp, 0x1A, 1)               # colour planes
    struct.pack_into("<H", bmp, 0x1C, 24)              # bits-per-pixel
    struct.pack_into("<I", bmp, 0x1E, 0)               # compression (BI_RGB)
    struct.pack_into("<I", bmp, 0x22, pixel_bytes)     # image size field
    # bytes 0x26–0x35: X/Y resolution and palette — leave as zeros

    # --- Pixel data (deterministic fill) ---
    fill = _BMP_ROW_FILL * (row_bytes + 1)  # ensure enough bytes
    for row in range(height):
        offset = header_size + row * row_stride
        bmp[offset : offset + row_bytes] = fill[:row_bytes]

    return bytes(bmp)


# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------


def _parse_comma_separated_ints(text: str, name: str) -> list[int]:
    """Parse a comma-separated list of integers."""
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        raise ValueError(f"Invalid {name}: no values provided")
    try:
        return [int(p) for p in parts]
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: expected comma-separated integers") from exc


def _parse_benchmark_lists(args) -> tuple[list[int], list[str], list[int]]:
    """Validate and parse the benchmark comma-separated arguments."""
    key_sizes = _parse_comma_separated_ints(args.key_sizes, "key-sizes")
    modes_raw = [m.strip().upper() for m in args.modes.split(",") if m.strip()]
    payload_sizes = _parse_comma_separated_ints(args.payload_sizes, "payload-sizes")

    if not modes_raw:
        raise ValueError("Invalid modes: no values provided")
    for ks in key_sizes:
        if ks not in _AES_KEY_SIZES:
            raise ValueError(f"Invalid key size: {ks} (must be 128, 192, or 256)")
    for m in modes_raw:
        if m not in _ECB_CBC:
            raise ValueError(f"Invalid mode: {m} (must be ECB or CBC)")
    for ps in payload_sizes:
        if ps <= 0:
            raise ValueError(f"Payload size must be positive, got {ps}")

    return key_sizes, modes_raw, payload_sizes


def _build_payload(size: int) -> bytes:
    """Build a deterministic bytes payload of exactly *size* bytes."""
    pattern = b"AES-benchmark-payload-0123456789"
    reps = size // len(pattern) + 1
    return (pattern * reps)[:size]


# ---------------------------------------------------------------------------
# Security result formatting
# ---------------------------------------------------------------------------


def _print_security_results(results: dict, iv: bytes) -> None:
    """Pretty-print the security suite results."""
    print(f"Security suite IV: {iv.hex()}")
    for conf, metrics in results.items():
        print(f"\nConfiguration: {conf}")
        print(f"  Avalanche effect : {metrics['avalanche_effect']:.2f}%")
        print(f"  Key sensitivity  : {metrics['key_sensitivity']:.2f}%")
        if "ecb_weakness" in metrics:
            ecb = metrics["ecb_weakness"]
            print(
                f"  ECB weakness     : {len(ecb['ecb_ciphertext'])} bytes ECB ciphertext, "
                f"{len(ecb['cbc_ciphertext'])} bytes CBC baseline"
            )


# ===================================================================
# Public command handlers
# ===================================================================


def run_encrypt(args) -> None:
    """Execute the ``encrypt`` subcommand."""
    key = _resolve_encrypt_key(args, args.key_size)
    iv = _resolve_encrypt_iv(args, args.mode)

    input_file = getattr(args, "input_file", None)
    output_file = getattr(args, "output_file", None)
    force = getattr(args, "force", False)

    if input_file is not None:
        # File input: raw binary plaintext, read verbatim.
        plaintext = FileHandler.read_bytes(args.input_file)
    else:
        plaintext = _decode_input(args.input, args.input_format)

    service = CipherService()
    result = service.encrypt_data(
        args.algorithm, args.key_size, args.mode, plaintext, key, iv
    )

    print(f"Ciphertext: {result.ciphertext.hex()}")
    if result.iv is not None:
        print(f"IV: {result.iv.hex()}")
    if args.generate_key:
        print(f"Key (generated): {key.hex()}")

    if output_file is not None:
        _check_overwrite(output_file, force)
        FileHandler.ensure_directory(Path(output_file).parent)
        FileHandler.write_bytes(output_file, result.ciphertext)
        print(f"Saved: {output_file}")
        # CBC only: persist the IV in a .iv sidecar (hex text, one line).
        if args.mode.upper() == "CBC" and result.iv is not None:
            FileHandler.write_text(output_file + ".iv", result.iv.hex() + "\n")
            print(f"Saved: {output_file}.iv")


def run_decrypt(args) -> None:
    """Execute the ``decrypt`` subcommand."""
    key = _parse_hex(args.key, "--key")

    input_file = getattr(args, "input_file", None)
    output_file = getattr(args, "output_file", None)
    force = getattr(args, "force", False)

    if input_file is not None:
        # File input: raw ciphertext bytes. CBC reads the .iv sidecar.
        ciphertext = FileHandler.read_bytes(input_file)
        if args.mode.upper() == "CBC":
            iv_hex = FileHandler.read_text(input_file + ".iv")
            iv = bytes.fromhex(iv_hex.strip())
        else:
            # ECB never reads or expects a .iv file — still reject --iv.
            iv = _resolve_decrypt_iv(args, args.mode)
    else:
        ciphertext = _parse_hex(args.input, "--input")
        iv = _resolve_decrypt_iv(args, args.mode)

    service = CipherService()
    plaintext = service.decrypt_data(
        args.algorithm, args.key_size, args.mode, ciphertext, key, iv
    )

    print(f"Plaintext: {_format_plaintext(plaintext)}")

    if output_file is not None:
        _check_overwrite(output_file, force)
        FileHandler.ensure_directory(Path(output_file).parent)
        FileHandler.write_bytes(output_file, plaintext)
        print(f"Saved: {output_file}")


def run_benchmark(args) -> None:
    """Execute the ``benchmark`` subcommand."""
    key_sizes, modes, payload_sizes = _parse_benchmark_lists(args)

    configs = []
    for ks in key_sizes:
        for mode in modes:
            configs.append({"algorithm": args.algorithm, "key_size": ks, "mode": mode})

    data_payloads = [_build_payload(ps) for ps in payload_sizes]

    # Status line — printed outside any measured block (Service runs the loop).
    print(
        f"Running benchmark: {len(configs)} configuration(s) "
        f"x {len(data_payloads)} payload(s) ..."
    )

    service = BenchmarkService()
    collector = service.run_performance_suite(configs, data_payloads)

    df = collector.get_summary_dataframe()
    if df.empty:
        raise ValueError("Benchmark produced no results")

    display_cols = [
        "key_size",
        "mode",
        "data_size_bytes",
        "mean_time_ms",
        "median_time_ms",
        "std_dev_time_ms",
        "outlier_count",
        "throughput_mb_s",
    ]
    present = [c for c in display_cols if c in df.columns]
    print(tabulate(df[present], headers="keys", tablefmt="grid", floatfmt=".4f"))

    save_csv = getattr(args, "save_csv", None)
    save_graphs = getattr(args, "save_graphs", None)

    ts = _timestamp()
    if save_csv is not None:
        FileHandler.ensure_directory(save_csv)
        summary_csv = f"{save_csv}/benchmark_summary_{ts}.csv"
        raw_csv = f"{save_csv}/benchmark_raw_{ts}.csv"
        FileHandler.save_dataframe_csv(df, summary_csv)
        FileHandler.save_dataframe_csv(collector.get_raw_dataframe(), raw_csv)
        print(f"Saved: {summary_csv}")
        print(f"Saved: {raw_csv}")
    if save_graphs is not None:
        FileHandler.ensure_directory(save_graphs)
        _save_benchmark_graphs(df, save_graphs, ts)


def run_security(args) -> None:
    """Execute the ``security`` subcommand."""
    key1 = _parse_hex(args.key, "--key")
    key_size = _key_size_from_key(key1)
    key2 = _one_bit_partner(key1)

    plaintext1 = _decode_input(args.plaintext, args.plaintext_format) if args.plaintext else _DEFAULT_SECURITY_PLAINTEXT
    plaintext2 = _one_bit_partner(plaintext1)

    iv = _resolve_security_iv(args, key_size)

    image_bytes = _build_bmp_bytes(args.bmp_width, args.bmp_height)

    configs = [{"algorithm": args.algorithm, "key_size": key_size, "mode": args.mode}]

    service = SecurityService()
    results = service.run_security_suite(
        configs, plaintext1, plaintext2, key1, key2, image_bytes, iv
    )

    _print_security_results(results, iv)

    save_report = getattr(args, "save_report", None)
    if save_report is not None:
        ts = _timestamp()
        FileHandler.ensure_directory(save_report)
        output_dict = _build_security_report(
            results, args.algorithm, key_size, args.mode, ts
        )
        report_path = f"{save_report}/security_report_{args.mode}_{ts}.json"
        FileHandler.write_json(output_dict, report_path)
        print(f"Saved: {report_path}")