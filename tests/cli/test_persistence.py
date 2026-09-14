"""CLI persistence integration tests for the frozen Task 9 design.

Configures the Matplotlib ``Agg`` backend before any import that touches
``pyplot``/``GraphGenerator`` (mirrors ``src/cli/main.py``).  Each test drives
the real CLI entry point (``src.cli.main.main``) end to end: argument parsing
→ ``validate_persistence_args`` → handler dispatch → error mapping.
"""

import base64
import json

import matplotlib

matplotlib.use("Agg")

import pytest
from pandas import read_csv

from src.cli.commands import _build_security_report
from src.cli.main import EXIT_RUNTIME, EXIT_SUCCESS, main

# 32 hex chars = 16 bytes → AES-128.
_KEY_128 = "ab" * 16


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encrypt_file(tmp_path, mode, data, name="plain.bin", *, extra_flags=()):
    """Encrypt *data* from a file via the CLI. Returns (exit_code, ct_path)."""
    src = tmp_path / name
    src.write_bytes(data)
    ct = tmp_path / (name + ".ct")
    argv = [
        "encrypt",
        "--algorithm", "AES",
        "--key-size", "128",
        "--mode", mode,
        "--key", _KEY_128,
        "--input-file", str(src),
        "--output-file", str(ct),
        *extra_flags,
    ]
    return main(argv), ct


def _decrypt_file(tmp_path, mode, ct, name="out.bin", *, extra_flags=()):
    """Decrypt *ct* to a file via the CLI. Returns (exit_code, out_path)."""
    out = tmp_path / name
    argv = [
        "decrypt",
        "--algorithm", "AES",
        "--key-size", "128",
        "--mode", mode,
        "--key", _KEY_128,
        "--input-file", str(ct),
        "--output-file", str(out),
        *extra_flags,
    ]
    return main(argv), out


# ---------------------------------------------------------------------------
# File round-trips
# ---------------------------------------------------------------------------


class TestFileRoundtrip:
    def test_encrypt_file_roundtrip_ecb(self, tmp_path):
        data = b"round-trip ECB payload \x01\x02\xff" * 4
        code, ct = _encrypt_file(tmp_path, "ECB", data)
        assert code == EXIT_SUCCESS
        assert ct.exists()
        code, out = _decrypt_file(tmp_path, "ECB", ct)
        assert code == EXIT_SUCCESS
        assert out.read_bytes() == data

    def test_encrypt_file_roundtrip_cbc(self, tmp_path):
        data = b"round-trip CBC payload \x00\x01\x02\xfe" * 5
        code, ct = _encrypt_file(tmp_path, "CBC", data)
        assert code == EXIT_SUCCESS
        assert ct.exists()
        assert (tmp_path / "plain.bin.ct.iv").exists()
        code, out = _decrypt_file(tmp_path, "CBC", ct)
        assert code == EXIT_SUCCESS
        assert out.read_bytes() == data


class TestIvSidecar:
    def test_encrypt_creates_iv_sidecar_cbc(self, tmp_path):
        code, _ = _encrypt_file(tmp_path, "CBC", b"sidecar check")
        assert code == EXIT_SUCCESS
        assert (tmp_path / "plain.bin.ct.iv").exists()

    def test_encrypt_no_iv_sidecar_ecb(self, tmp_path):
        code, _ = _encrypt_file(tmp_path, "ECB", b"no sidecar")
        assert code == EXIT_SUCCESS
        assert not (tmp_path / "plain.bin.ct.iv").exists()

    def test_no_iv_file_for_ecb(self, tmp_path):
        code, _ = _encrypt_file(tmp_path, "ECB", b"again, no .iv")
        assert code == EXIT_SUCCESS
        assert not list(tmp_path.glob("*.iv"))

    def test_iv_sidecar_format(self, tmp_path):
        # Frozen format: 32 hex chars (16-byte IV) + trailing newline.
        code, ct = _encrypt_file(tmp_path, "CBC", b"iv format")
        assert code == EXIT_SUCCESS
        iv_text = (tmp_path / "plain.bin.ct.iv").read_text("utf-8")
        assert iv_text.endswith("\n")
        stripped = iv_text.strip()
        assert len(stripped) == 32
        int(stripped, 16)  # must be valid hex


class TestDecryptErrors:
    def test_decrypt_missing_iv_errors(self, tmp_path, capsys):
        ct = tmp_path / "no_iv.ct"
        ct.write_bytes(b"\x00" * 32)
        out = tmp_path / "out.bin"
        code, _ = _decrypt_file(tmp_path, "CBC", ct, name="out.bin")
        assert code == EXIT_RUNTIME
        assert "No such file" in capsys.readouterr().out
        assert not out.exists()


class TestOverwrite:
    def test_overwrite_refused_without_force(self, tmp_path, capsys):
        code, ct = _encrypt_file(tmp_path, "ECB", b"original")
        assert code == EXIT_SUCCESS
        original = ct.read_bytes()

        code2, _ = _encrypt_file(tmp_path, "ECB", b"replacement", name="plain.bin")
        assert code2 == EXIT_RUNTIME
        assert "already exists" in capsys.readouterr().out
        assert ct.read_bytes() == original  # untouched

    def test_overwrite_succeeds_with_force(self, tmp_path):
        code, ct = _encrypt_file(tmp_path, "ECB", b"first")
        assert code == EXIT_SUCCESS
        code2, _ = _encrypt_file(
            tmp_path, "ECB", b"second", name="plain.bin", extra_flags=("--force",)
        )
        assert code2 == EXIT_SUCCESS
        assert ct.read_bytes() != b"first"


class TestInputErrors:
    def test_input_file_missing_errors(self, tmp_path, capsys):
        missing = tmp_path / "does_not_exist.bin"
        code = main([
            "encrypt", "--key-size", "128", "--mode", "ECB",
            "--key", _KEY_128, "--input-file", str(missing),
            "--output-file", str(tmp_path / "out.ct"),
        ])
        assert code == EXIT_RUNTIME
        assert "No such file" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Benchmark persistence
# ---------------------------------------------------------------------------


class TestBenchmarkPersistence:
    def _benchmark_args(self, tmp_path, save_csv=None, save_graphs=None):
        argv = [
            "benchmark",
            "--key-sizes", "128",
            "--modes", "ECB",
            "--payload-sizes", "262144",
        ]
        if save_csv:
            argv += ["--save-csv", str(save_csv)]
        if save_graphs:
            argv += ["--save-graphs", str(save_graphs)]
        return argv

    def test_benchmark_save_csv_creates_files(self, tmp_path):
        code = main(self._benchmark_args(tmp_path, save_csv=tmp_path))
        assert code == EXIT_SUCCESS
        csvs = sorted(tmp_path.glob("benchmark_*.csv"))
        assert len(csvs) == 2
        names = {p.name.split("_")[1] for p in csvs}
        assert names == {"summary", "raw"}

    def test_benchmark_csv_columns_match(self, tmp_path):
        code = main(self._benchmark_args(tmp_path, save_csv=tmp_path))
        assert code == EXIT_SUCCESS
        summary = read_csv(next(tmp_path.glob("benchmark_summary_*.csv")))
        raw = read_csv(next(tmp_path.glob("benchmark_raw_*.csv")))
        assert list(summary.columns) == [
            "algorithm", "key_size", "mode", "data_size_bytes", "count",
            "mean_time_ms", "median_time_ms", "std_dev_time_ms", "min_time_ms",
            "max_time_ms", "q1_ms", "q3_ms", "iqr_ms", "outlier_count",
            "throughput_mb_s", "memory_delta_mb",
        ]
        assert list(raw.columns) == [
            "algorithm", "key_size", "mode", "data_size_bytes",
            "iteration_index", "elapsed_time_ms", "is_outlier",
        ]

    def test_benchmark_save_graphs_creates_pngs(self, tmp_path):
        code = main(self._benchmark_args(tmp_path, save_graphs=tmp_path))
        assert code == EXIT_SUCCESS
        pngs = sorted(tmp_path.glob("*.png"))
        assert len(pngs) == 3
        assert any(p.name.startswith("key_size_comparison_") for p in pngs)
        assert any(p.name.startswith("mode_comparison_") for p in pngs)
        assert any(p.name.startswith("throughput_analysis_") for p in pngs)

    def test_benchmark_graphs_valid_pngs(self, tmp_path):
        code = main(self._benchmark_args(tmp_path, save_graphs=tmp_path))
        assert code == EXIT_SUCCESS
        for png in tmp_path.glob("*.png"):
            assert png.read_bytes()[:4] == b"\x89PNG"


# ---------------------------------------------------------------------------
# Security report persistence
# ---------------------------------------------------------------------------


class TestSecurityPersistence:
    def _security_args(self, tmp_path):
        return [
            "security", "--mode", "ECB", "--key", _KEY_128,
            "--bmp-width", "4", "--bmp-height", "4",
            "--save-report", str(tmp_path),
        ]

    def test_security_save_json_creates_file(self, tmp_path):
        code = main(self._security_args(tmp_path))
        assert code == EXIT_SUCCESS
        reports = list(tmp_path.glob("security_report_*.json"))
        assert len(reports) == 1

    def test_security_json_structure_valid(self, tmp_path):
        code = main(self._security_args(tmp_path))
        assert code == EXIT_SUCCESS
        report = json.loads(
            next(tmp_path.glob("security_report_*.json")).read_text("utf-8")
        )
        assert set(report) == {"metadata", "results"}
        assert report["metadata"]["algorithm"] == "AES"
        assert report["metadata"]["key_size"] == 128
        assert report["metadata"]["mode"] == "ECB"
        assert "timestamp" in report["metadata"]
        conf = report["results"]["AES-128-ECB"]
        assert "avalanche_effect" in conf
        assert "key_sensitivity" in conf
        ecb = conf["ecb_weakness"]
        for field in (
            "original_header", "original_pixel_data", "ecb_ciphertext",
            "cbc_ciphertext", "bmp_trailing_data",
        ):
            assert isinstance(ecb[field], str)  # base64-encoded

    def test_json_base64_roundtrip(self):
        fabricated = {
            "AES-128-ECB": {
                "avalanche_effect": 11.25,
                "key_sensitivity": 49.0,
                "ecb_weakness": {
                    "original_header": b"\x42\x4d\x00" * 3,
                    "original_pixel_data": b"\x5a" * 96,
                    "ecb_ciphertext": b"\xde\xad\xbe\xef" * 4,
                    "cbc_ciphertext": b"\x01\x02\x03\x04" * 4,
                    "bmp_trailing_data": b"",
                },
            }
        }
        report = _build_security_report(
            fabricated, "AES", 128, "ECB", "20260910_000000"
        )
        # FileHandler contract: dict must already be JSON-serializable.
        roundtripped = json.loads(json.dumps(report))
        ecb = roundtripped["results"]["AES-128-ECB"]["ecb_weakness"]
        for field, expected in fabricated["AES-128-ECB"]["ecb_weakness"].items():
            assert base64.b64decode(ecb[field]) == expected
        assert (
            roundtripped["results"]["AES-128-ECB"]["avalanche_effect"] == 11.25
        )


class TestBackwardCompat:
    def test_backward_compat_no_flags(self, tmp_path, capsys):
        # Encrypt without any persistence flags → existing in-memory terminal
        # behavior, and (importantly) no files are written.
        code = main([
            "encrypt", "--key-size", "128", "--mode", "ECB",
            "--key", _KEY_128, "--input", "hello",
        ])
        assert code == EXIT_SUCCESS
        out = capsys.readouterr().out
        assert "Ciphertext:" in out
        assert not list(tmp_path.iterdir())


# ---------------------------------------------------------------------------
# Path handling
# ---------------------------------------------------------------------------


class TestPaths:
    def test_path_with_spaces(self, tmp_path):
        spaced = tmp_path / "my folder with spaces"
        spaced.mkdir()
        src = spaced / "plain text file.bin"
        src.write_bytes(b"path with spaces round-trip \xff\x00")
        ct = spaced / "cipher out.bin"
        out = spaced / "recovered data.bin"

        code = main([
            "encrypt", "--key-size", "128", "--mode", "CBC",
            "--key", _KEY_128, "--input-file", str(src),
            "--output-file", str(ct),
        ])
        assert code == EXIT_SUCCESS
        code = main([
            "decrypt", "--key-size", "128", "--mode", "CBC",
            "--key", _KEY_128, "--input-file", str(ct),
            "--output-file", str(out),
        ])
        assert code == EXIT_SUCCESS
        assert out.read_bytes() == src.read_bytes()


# ---------------------------------------------------------------------------
# Edge cases: plaintext sizes on file round-trips
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_encrypt_empty_file(self, tmp_path):
        code, ct = _encrypt_file(tmp_path, "ECB", b"", name="empty.bin")
        assert code == EXIT_SUCCESS
        assert ct.read_bytes() != b""  # PKCS#7 always yields >= 1 block
        code, out = _decrypt_file(tmp_path, "ECB", ct, name="empty.out")
        assert code == EXIT_SUCCESS
        assert out.read_bytes() == b""

    def test_encrypt_one_byte(self, tmp_path):
        code, ct = _encrypt_file(tmp_path, "ECB", b"\x41", name="one.bin")
        assert code == EXIT_SUCCESS
        code, out = _decrypt_file(tmp_path, "ECB", ct, name="one.out")
        assert code == EXIT_SUCCESS
        assert out.read_bytes() == b"\x41"

    def test_encrypt_block_exact(self, tmp_path):
        data = b"0123456789abcdef"  # exactly 16 bytes
        code, ct = _encrypt_file(tmp_path, "ECB", data, name="block.bin")
        assert code == EXIT_SUCCESS
        assert len(ct.read_bytes()) == 32  # full second PKCS#7 block
        code, out = _decrypt_file(tmp_path, "ECB", ct, name="block.out")
        assert code == EXIT_SUCCESS
        assert out.read_bytes() == data

    def test_encrypt_over_block(self, tmp_path):
        data = b"A" * 17  # one byte past a block -> 32-byte ciphertext
        code, ct = _encrypt_file(tmp_path, "ECB", data, name="over.bin")
        assert code == EXIT_SUCCESS
        assert len(ct.read_bytes()) == 32
        code, out = _decrypt_file(tmp_path, "ECB", ct, name="over.out")
        assert code == EXIT_SUCCESS
        assert out.read_bytes() == data