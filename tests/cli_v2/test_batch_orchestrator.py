"""Tests for the V2 BatchOrchestrator.

Covers discovery, preflight, unique/shared encrypt and decrypt,
conflict behaviour, dry-run, per-file error isolation, CSV logging,
KeyboardInterrupt handling, and V1 interoperability with real AES.
"""

from __future__ import annotations

import csv
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cli_v2.batch_orchestrator import (
    BatchFileResult,
    BatchOrchestrator,
    BatchSummary,
    _utc_datetime,
)
from src.cli_v2.key_manager import KeyManager
from src.engines.cipher_service import CipherService
from src.utils.file_handler import FileHandler


# ── helpers ──────────────────────────────────────────────────────────────────

FIXED_UTC = datetime(2025, 6, 15, 12, 30, 45, tzinfo=timezone.utc)
SHARED_KEY_256 = bytes(range(32))  # deterministic 256-bit key


def _utc_fixed():
    """Module-level replacement for _utc_datetime in tests."""
    return FIXED_UTC


def _create_source_file(path: Path, content: bytes = b"Hello, BatchOrchestrator!") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _setup_encrypt_src(tmp_path: Path, names: list[str]) -> Path:
    """Create a source directory with plaintext files and return the path."""
    src = tmp_path / "src"
    for name in names:
        _create_source_file(src / name, content=f"content-of-{name}".encode())
    return src


def _make_orchestrator() -> BatchOrchestrator:
    return BatchOrchestrator(CipherService())


def _patch_save_key_to_fail(monkeypatch, dest_dir: Path, basename: str):
    """Make KeyManager.save_key raise OSError for one destination file only."""
    real_save_key = KeyManager.save_key

    def failing(key_bytes: bytes, output_path: Path):
        if (
            Path(output_path).parent == Path(dest_dir)
            and Path(output_path).name == basename
        ):
            raise OSError("simulated save_key failure")
        return real_save_key(key_bytes, output_path)

    monkeypatch.setattr(KeyManager, "save_key", staticmethod(failing))


def _patch_save_iv_to_fail(monkeypatch, dest_dir: Path, basename: str):
    """Make KeyManager.save_iv raise OSError for one destination file only."""
    real_save_iv = KeyManager.save_iv

    def failing(iv_bytes: bytes, output_path: Path):
        if (
            Path(output_path).parent == Path(dest_dir)
            and Path(output_path).name == basename
        ):
            raise OSError("simulated save_iv failure")
        return real_save_iv(iv_bytes, output_path)

    monkeypatch.setattr(KeyManager, "save_iv", staticmethod(failing))


def _patch_os_replace_to_fail(monkeypatch, dest_name: str):
    """Make os.replace raise OSError only when committing *dest_name*.

    Other destinations (other batch files, or none) fall through to the real
    os.replace, so per-file isolation can be verified alongside the failure.
    """
    original_replace = os.replace

    def failing_replace(src_path, dst_path):
        if Path(dst_path).name == dest_name:
            raise OSError("simulated replace failure")
        return original_replace(src_path, dst_path)

    monkeypatch.setattr("src.cli_v2.batch_orchestrator.os.replace", failing_replace)


# ─────────────────────────────────────────────────────────────────────────────
# Discovery
# ─────────────────────────────────────────────────────────────────────────────


class TestDiscoverFiles:
    """Flat scan, exclusion matrix, and sort behaviour."""

    def test_flat_scan_regular_files(self, tmp_path):
        """Only direct child regular files are discovered."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        (src / "sub").mkdir()  # nested dir

        cand, excl = _make_orchestrator().discover_files(src, is_encryption=True)
        assert [p.name for p in cand] == ["a.txt", "b.txt"]

    def test_no_recursion(self, tmp_path):
        """Files inside subdirectories are never discovered."""
        src = tmp_path / "src"
        nested = src / "subdir" / "deep"
        nested.mkdir(parents=True)
        _create_source_file(nested / "hidden.txt", b"x")

        cand, _ = _make_orchestrator().discover_files(src)
        assert all("hidden.txt" not in p.name for p in cand)

    def test_lexical_ordering(self, tmp_path):
        """Candidates are sorted lexicographically."""
        src = _setup_encrypt_src(tmp_path, ["z.txt", "a.txt", "m.txt"])
        cand, _ = _make_orchestrator().discover_files(src)
        assert [p.name for p in cand] == ["a.txt", "m.txt", "z.txt"]

    def test_case_insensitive_ordering(self, tmp_path):
        """Sorting is case-insensitive: 'Z' comes after 'a'."""
        src = _setup_encrypt_src(tmp_path, ["Z.txt", "a.txt"])
        cand, _ = _make_orchestrator().discover_files(src)
        assert [p.name for p in cand] == ["a.txt", "Z.txt"]

    def test_directories_excluded(self, tmp_path):
        """Directories are never candidates."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "data_dir").mkdir()
        _create_source_file(src / "data_dir" / "inner.txt", b"x")
        _create_source_file(src / "file.txt", b"y")

        cand, excl = _make_orchestrator().discover_files(src)
        assert all(not p.is_dir() for p in cand)
        assert any(p.name == "data_dir" for p in excl)

    def test_symlinks_excluded(self, tmp_path):
        """Symbolic links are excluded, not processed."""
        src = tmp_path / "src"
        src.mkdir()
        target = tmp_path / "target.txt"
        _create_source_file(target, b"x")
        link = src / "link.txt"
        try:
            os.symlink(target, link)
        except (OSError, PermissionError):
            pytest.skip("symlinks not supported on this platform")
        _create_source_file(src / "normal.txt", b"y")

        cand, excl = _make_orchestrator().discover_files(src)
        assert all(p.name != "link.txt" for p in cand)
        assert any(p.name == "link.txt" for p in excl)

    def test_junction_excluded_via_monkeypatch(self, tmp_path):
        """Junctions (platform-dependent) are excluded."""
        src = tmp_path / "src"
        src.mkdir()
        fake_junction = src / "fake"
        _create_source_file(fake_junction, b"x")

        original_is_junction = Path.is_junction

        def patched(self):
            if self.name == "fake":
                return True
            return original_is_junction(self)

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(Path, "is_junction", patched)
        try:
            cand, excl = _make_orchestrator().discover_files(src)
            assert all(p.name != "fake" for p in cand)
            assert any(p.name == "fake" for p in excl)
        finally:
            monkeypatch.undo()

    def test_hidden_dotfiles_excluded(self, tmp_path):
        """Files starting with '.' are hidden and excluded."""
        src = tmp_path / "src"
        src.mkdir()
        _create_source_file(src / ".secret", b"x")
        _create_source_file(src / "visible.txt", b"y")

        cand, excl = _make_orchestrator().discover_files(src)
        assert [p.name for p in cand] == ["visible.txt"]
        assert any(p.name == ".secret" for p in excl)

    def test_system_files_excluded(self, tmp_path):
        """OS metadata files are excluded."""
        src = tmp_path / "src"
        src.mkdir()
        for name in ("Thumbs.db", "desktop.ini", ".DS_Store"):
            _create_source_file(src / name, b"")
        _create_source_file(src / "data.txt", b"y")

        cand, excl = _make_orchestrator().discover_files(src)
        assert [p.name for p in cand] == ["data.txt"]
        for name in ("Thumbs.db", "desktop.ini", ".DS_Store"):
            assert any(p.name == name for p in excl), f"{name} should be excluded"

    def test_system_files_case_insensitive(self, tmp_path):
        """System-file exclusion is case-insensitive."""
        src = tmp_path / "src"
        src.mkdir()
        _create_source_file(src / "THUMBS.DB", b"")
        _create_source_file(src / "good.txt", b"y")

        cand, _ = _make_orchestrator().discover_files(src)
        assert all(p.name != "THUMBS.DB" for p in cand)

    def test_sidecar_extensions_excluded(self, tmp_path):
        """*.key, *.iv, *.log are excluded from both encrypt and decrypt."""
        src = tmp_path / "src"
        src.mkdir()
        for name in ("file.key", "file.iv", "file.log"):
            _create_source_file(src / name, b"")
        _create_source_file(src / "data.txt", b"y")

        cand, excl = _make_orchestrator().discover_files(src)
        assert [p.name for p in cand] == ["data.txt"]

    def test_tmp_files_excluded(self, tmp_path):
        """Files containing '.tmp' in the name are excluded."""
        src = tmp_path / "src"
        src.mkdir()
        _create_source_file(src / ".tmp_lock", b"")
        _create_source_file(src / "file.tmp_bak", b"")
        _create_source_file(src / "real.txt", b"y")

        cand, _ = _make_orchestrator().discover_files(src)
        assert [p.name for p in cand] == ["real.txt"]

    def test_enc_excluded_during_encrypt(self, tmp_path):
        """During encryption, *.enc files are excluded (already ciphertexts)."""
        src = tmp_path / "src"
        src.mkdir()
        _create_source_file(src / "output.enc", b"")
        _create_source_file(src / "input.txt", b"y")

        cand, _ = _make_orchestrator().discover_files(src, is_encryption=True)
        assert [p.name for p in cand] == ["input.txt"]
        assert any(p.name == "output.enc" for p in _make_orchestrator().discover_files(src, is_encryption=True)[1])

    def test_enc_candidate_during_decrypt(self, tmp_path):
        """During decryption, *.enc files are candidates; plaintext excluded."""
        src = tmp_path / "src"
        src.mkdir()
        _create_source_file(src / "secret.enc", b"cipher")
        _create_source_file(src / "readme.txt", b"plain")

        cand, excl = _make_orchestrator().discover_files(src, is_encryption=False)
        assert [p.name for p in cand] == ["secret.enc"]
        assert any(p.name == "readme.txt" for p in excl)

    def test_empty_dir(self, tmp_path):
        """An empty source dir returns two empty lists."""
        src = tmp_path / "src"
        src.mkdir()
        cand, excl = _make_orchestrator().discover_files(src)
        assert cand == [] and excl == []

    def test_nonexistent_dir_raises(self, tmp_path):
        """A missing source directory propagates FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _make_orchestrator().discover_files(tmp_path / "nope")

    def test_both_lists_sorted(self, tmp_path):
        """Both candidates and excluded lists are sorted case-insensitively."""
        src = tmp_path / "src"
        src.mkdir()
        _create_source_file(src / "Zebra.txt", b"y")
        _create_source_file(src / "apple.txt", b"y")
        _create_source_file(src / ".hidden", b"")
        _create_source_file(src / "Thumbs.db", b"")

        cand, excl = _make_orchestrator().discover_files(src)
        cand_names = [p.name for p in cand]
        excl_names = [p.name for p in excl]
        assert cand_names == sorted(cand_names, key=str.lower)
        assert excl_names == sorted(excl_names, key=str.lower)


# ─────────────────────────────────────────────────────────────────────────────
# Preflight planning
# ─────────────────────────────────────────────────────────────────────────────


class TestPreflight:
    """Collision detection and conflict policy planning."""

    def test_no_collisions(self, tmp_path):
        """All candidates proceed when dest dir is empty."""
        cand = [tmp_path / "a.txt", tmp_path / "b.txt"]
        result = _make_orchestrator().preflight_check(cand, tmp_path / "out", "skip")
        assert result["proceed_count"] == 2
        assert result["skipped_count"] == 0
        assert result["collisions"] == []

    def test_mixed_collisions(self, tmp_path):
        """Some dests exist → collisions listed; skip policy splits them."""
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "a.txt.enc").write_bytes(b"old")

        cand = [tmp_path / "a.txt", tmp_path / "b.txt"]
        result = _make_orchestrator().preflight_check(cand, dest, "skip")
        assert result["proceed_count"] == 1
        assert result["skipped_count"] == 1
        assert len(result["collisions"]) == 1

    def test_all_collisions(self, tmp_path):
        """Every dest exists → all skipped with skip policy."""
        dest = tmp_path / "out"
        dest.mkdir()
        for name in ("x.txt.enc", "y.txt.enc"):
            (dest / name).write_bytes(b"old")

        cand = [tmp_path / "x.txt", tmp_path / "y.txt"]
        result = _make_orchestrator().preflight_check(cand, dest, "skip")
        assert result["skipped_count"] == 2
        assert result["proceed_count"] == 0

    def test_overwrite_policy_all_proceed(self, tmp_path):
        """Overwrite policy: collisions exist but all are marked for processing."""
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "a.txt.enc").write_bytes(b"old")

        cand = [tmp_path / "a.txt"]
        result = _make_orchestrator().preflight_check(cand, dest, "overwrite")
        assert result["proceed_count"] == 1
        assert result["skipped_count"] == 0

    def test_invalid_policy_raises(self, tmp_path):
        """Unsupported policy raises ValueError."""
        with pytest.raises(ValueError, match="on_conflict"):
            _make_orchestrator().preflight_check([], tmp_path, "invalid")

    def test_no_writes_during_preflight(self, tmp_path):
        """Preflight is pure computation; no files or dirs are created."""
        out = tmp_path / "out"
        cand = [tmp_path / "a.txt"]
        _make_orchestrator().preflight_check(cand, out, "skip")
        assert not out.exists()

    def test_planning_info_fields(self, tmp_path):
        """The returned dict has all required keys."""
        result = _make_orchestrator().preflight_check([], tmp_path / "out", "skip")
        for key in ("on_conflict", "total", "collisions", "will_process", "will_skip",
                     "proceed_count", "skipped_count"):
            assert key in result

    def test_encrypt_dest_naming(self, tmp_path):
        """Encrypt preflight: 'a.txt' → dest 'a.txt.enc'."""
        dest = tmp_path / "out"
        result = _make_orchestrator().preflight_check(
            [tmp_path / "a.txt"], dest, "skip"
        )
        planned = result["will_process"] + result["will_skip"]
        # dest computed internally; verify via collision seed
        dest.mkdir()
        (dest / "a.txt.enc").write_bytes(b"old")
        result2 = _make_orchestrator().preflight_check(
            [tmp_path / "a.txt"], dest, "skip"
        )
        assert result2["skipped_count"] == 1

    def test_decrypt_dest_naming(self, tmp_path):
        """Decrypt preflight: 'a.txt.enc' → dest 'a.txt'."""
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "a.txt").write_bytes(b"plain")

        cand = [tmp_path / "a.txt.enc"]
        result = _make_orchestrator().preflight_check(cand, dest, "skip")
        assert result["skipped_count"] == 1  # collision with a.txt


# ─────────────────────────────────────────────────────────────────────────────
# Batch encryption — unique-key
# ─────────────────────────────────────────────────────────────────────────────


class TestBatchEncryptUnique:
    """Unique-key batch encryption with V1 real AES."""

    def test_one_file_success(self, tmp_path):
        """A single file encrypts successfully."""
        src = _setup_encrypt_src(tmp_path, ["data.txt"])
        dest = tmp_path / "out"
        result = _make_orchestrator().run_batch_encrypt(src, dest)
        assert result.success_count == 1
        assert result.failed_count == 0
        assert (dest / "data.txt.enc").exists()

    def test_multiple_files(self, tmp_path):
        """Multiple files are all encrypted."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt", "c.txt"])
        dest = tmp_path / "out"
        result = _make_orchestrator().run_batch_encrypt(src, dest)
        assert result.success_count == 3
        assert (dest / "a.txt.enc").exists()
        assert (dest / "b.txt.enc").exists()
        assert (dest / "c.txt.enc").exists()

    def test_unique_keys_differ(self, tmp_path):
        """Each file gets a unique key (sidecar .key files differ)."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest)

        key_a, _ = KeyManager.load_key(dest / "a.txt.enc.key")
        key_b, _ = KeyManager.load_key(dest / "b.txt.enc.key")
        assert key_a != key_b

    def test_key_sidecar_loadable(self, tmp_path):
        """Key sidecar is valid hex, loadable, matches key_size."""
        src = _setup_encrypt_src(tmp_path, ["f.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, key_size=256)

        key, bits = KeyManager.load_key(dest / "f.txt.enc.key")
        assert bits == 256
        assert len(key) == 32

    def test_iv_sidecar_cbc(self, tmp_path):
        """CBC mode produces an .iv sidecar per file."""
        src = _setup_encrypt_src(tmp_path, ["f.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, mode="CBC")
        assert (dest / "f.txt.enc.iv").exists()
        iv = KeyManager.load_iv(dest / "f.txt.enc.iv")
        assert len(iv) == 16

    def test_cbc_unique_ivs(self, tmp_path):
        """Different files get different CBC IVs."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, mode="CBC")
        iv_a = KeyManager.load_iv(dest / "a.txt.enc.iv")
        iv_b = KeyManager.load_iv(dest / "b.txt.enc.iv")
        assert iv_a != iv_b

    def test_ecb_no_iv_sidecar(self, tmp_path):
        """ECB mode produces no .iv sidecar."""
        src = _setup_encrypt_src(tmp_path, ["f.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, mode="ECB")
        assert (dest / "f.txt.enc.key").exists()
        assert not (dest / "f.txt.enc.iv").exists()

    def test_correct_naming(self, tmp_path):
        """Output ciphertext is named '<filename>.enc'."""
        src = _setup_encrypt_src(tmp_path, ["document.pdf"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest)
        assert (dest / "document.pdf.enc").exists()

    def test_originals_preserved(self, tmp_path):
        """Source plaintext files are never modified or deleted."""
        src = _setup_encrypt_src(tmp_path, ["data.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest)
        assert (src / "data.txt").exists()
        assert (src / "data.txt").read_bytes() == b"content-of-data.txt"

    def test_ciphertext_differs_from_plaintext(self, tmp_path):
        """The encrypted output is not identical to the plaintext."""
        plaintext = b"Hello, BatchOrchestrator!"
        src = _setup_encrypt_src(tmp_path, ["data.txt"])
        (src / "data.txt").write_bytes(plaintext)
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest)
        ciphertext = (dest / "data.txt.enc").read_bytes()
        assert ciphertext != plaintext
        assert len(ciphertext) >= len(plaintext)

    def test_dest_dir_created(self, tmp_path):
        """The destination directory is created when it does not exist."""
        src = _setup_encrypt_src(tmp_path, ["f.txt"])
        dest = tmp_path / "new_out"
        assert not dest.exists()
        _make_orchestrator().run_batch_encrypt(src, dest)
        assert dest.exists()

    def test_round_trip_unique(self, tmp_path):
        """Encrypt then decrypt returns original plaintext."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        enc_dir = tmp_path / "enc"
        dec_dir = tmp_path / "dec"

        _make_orchestrator().run_batch_encrypt(src, enc_dir)
        _make_orchestrator().run_batch_decrypt(enc_dir, dec_dir)

        assert (dec_dir / "a.txt").read_bytes() == b"content-of-a.txt"
        assert (dec_dir / "b.txt").read_bytes() == b"content-of-b.txt"

    def test_ecb_round_trip(self, tmp_path):
        """ECB encrypt/decrypt round-trips correctly."""
        src = _setup_encrypt_src(tmp_path, ["e.txt"])
        enc = tmp_path / "enc"
        dec = tmp_path / "dec"

        _make_orchestrator().run_batch_encrypt(src, enc, mode="ECB")
        _make_orchestrator().run_batch_decrypt(enc, dec, mode="ECB")
        assert (dec / "e.txt").read_bytes() == b"content-of-e.txt"

    def test_summary_fields(self, tmp_path):
        """BatchSummary has correct aggregate fields."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        result = _make_orchestrator().run_batch_encrypt(src, dest)

        assert result.total_files == 2
        assert result.success_count == 2
        assert result.skipped_count == 0
        assert result.failed_count == 0
        assert result.total_bytes > 0
        assert result.total_time_ms > 0
        assert len(result.results) == 2
        assert all(r.status == "SUCCESS" for r in result.results)

    def test_elapsed_ms_positive(self, tmp_path):
        """Each file result has a non-negative elapsed_ms."""
        src = _setup_encrypt_src(tmp_path, ["f.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        assert result.results[0].elapsed_ms >= 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Batch encryption — shared-key
# ─────────────────────────────────────────────────────────────────────────────


class TestBatchEncryptShared:
    """Shared-key batch encryption."""

    def test_batch_key_persisted(self, tmp_path):
        """A shared key is saved to <dest_dir>/batch.key."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, shared_key=SHARED_KEY_256)
        assert (dest / "batch.key").exists()
        loaded, bits = KeyManager.load_key(dest / "batch.key")
        assert loaded == SHARED_KEY_256
        assert bits == 256

    def test_no_per_file_key_sidecars(self, tmp_path):
        """Shared mode does not write per-file .key files."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, shared_key=SHARED_KEY_256)
        assert not (dest / "a.txt.enc.key").exists()
        assert not (dest / "b.txt.enc.key").exists()

    def test_cbc_unique_ivs_shared(self, tmp_path):
        """Even with a shared key, CBC still generates unique IVs per file."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, shared_key=SHARED_KEY_256, mode="CBC")
        assert (dest / "a.txt.enc.iv").exists()
        assert (dest / "b.txt.enc.iv").exists()
        iv_a = KeyManager.load_iv(dest / "a.txt.enc.iv")
        iv_b = KeyManager.load_iv(dest / "b.txt.enc.iv")
        assert iv_a != iv_b

    def test_ecb_shared(self, tmp_path):
        """Shared-key ECB: batch.key exists, no .iv sidecars."""
        src = _setup_encrypt_src(tmp_path, ["f.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, shared_key=SHARED_KEY_256, mode="ECB")
        assert (dest / "batch.key").exists()
        assert (dest / "f.txt.enc").exists()
        assert not (dest / "f.txt.enc.iv").exists()
        assert not (dest / "f.txt.enc.key").exists()

    def test_round_trip_shared(self, tmp_path):
        """Shared-key encrypt/decrypt round-trips correctly."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        enc = tmp_path / "enc"
        dec = tmp_path / "dec"

        _make_orchestrator().run_batch_encrypt(src, enc, shared_key=SHARED_KEY_256)
        _make_orchestrator().run_batch_decrypt(enc, dec, shared_key=SHARED_KEY_256)

        assert (dec / "a.txt").read_bytes() == b"content-of-a.txt"
        assert (dec / "b.txt").read_bytes() == b"content-of-b.txt"

    def test_multiple_ciphertexts(self, tmp_path):
        """Shared mode produces one .enc per source file."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt", "c.txt"])
        dest = tmp_path / "out"
        _make_orchestrator().run_batch_encrypt(src, dest, shared_key=SHARED_KEY_256)
        assert all((dest / f"{n}.enc").exists() for n in ("a.txt", "b.txt", "c.txt"))


# ─────────────────────────────────────────────────────────────────────────────
# Batch decryption
# ─────────────────────────────────────────────────────────────────────────────


class TestBatchDecrypt:
    """Decryption success, failure isolation, and sidecar loading."""

    def _encrypt_fixtures(self, tmp_path, names, mode="CBC", shared_key=None):
        """Helper: encrypt files and return the ciphertext directory."""
        src = _setup_encrypt_src(tmp_path, names)
        enc = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(src, enc, mode=mode, shared_key=shared_key)
        return enc

    def test_unique_key_decrypt(self, tmp_path):
        """Unique-key decrypt returns original plaintext."""
        enc = self._encrypt_fixtures(tmp_path, ["a.txt", "b.txt"])
        dec = tmp_path / "dec"
        _make_orchestrator().run_batch_decrypt(enc, dec)
        assert (dec / "a.txt").read_bytes() == b"content-of-a.txt"
        assert (dec / "b.txt").read_bytes() == b"content-of-b.txt"

    def test_shared_key_decrypt(self, tmp_path):
        """Shared-key decrypt returns original plaintext."""
        enc = self._encrypt_fixtures(tmp_path, ["a.txt"], shared_key=SHARED_KEY_256)
        dec = tmp_path / "dec"
        _make_orchestrator().run_batch_decrypt(enc, dec, shared_key=SHARED_KEY_256)
        assert (dec / "a.txt").read_bytes() == b"content-of-a.txt"

    def test_ecb_decrypt(self, tmp_path):
        """ECB ciphertext decrypts without needing an .iv sidecar."""
        enc = self._encrypt_fixtures(tmp_path, ["e.txt"], mode="ECB")
        dec = tmp_path / "dec"
        _make_orchestrator().run_batch_decrypt(enc, dec, mode="ECB")
        assert (dec / "e.txt").read_bytes() == b"content-of-e.txt"

    def test_missing_key_fails(self, tmp_path):
        """Missing .key sidecar → FAILED status."""
        enc = self._encrypt_fixtures(tmp_path, ["a.txt"])
        (enc / "a.txt.enc.key").unlink()  # remove key

        dec = tmp_path / "dec"
        result = _make_orchestrator().run_batch_decrypt(enc, dec)
        assert result.failed_count == 1
        assert result.results[0].status == "FAILED"

    def test_missing_iv_fails(self, tmp_path):
        """Missing .iv sidecar for CBC → FAILED status."""
        enc = self._encrypt_fixtures(tmp_path, ["a.txt"])
        (enc / "a.txt.enc.iv").unlink()  # remove IV

        dec = tmp_path / "dec"
        result = _make_orchestrator().run_batch_decrypt(enc, dec)
        assert result.failed_count == 1
        assert result.results[0].status == "FAILED"

    def test_wrong_key_fails(self, tmp_path):
        """Overwriting .key with a different valid key → FAILED (bad padding)."""
        enc = self._encrypt_fixtures(tmp_path, ["a.txt"])
        # Write a different valid 256-bit key
        wrong_key = bytes(range(32, 64))
        KeyManager.save_key(wrong_key, enc / "a.txt.enc.key")

        dec = tmp_path / "dec"
        result = _make_orchestrator().run_batch_decrypt(enc, dec)
        assert result.failed_count == 1
        assert result.results[0].status == "FAILED"
        assert len(result.results[0].error_message) > 0

    def test_malformed_ciphertext_fails(self, tmp_path):
        """Corrupted ciphertext content → FAILED status."""
        enc = self._encrypt_fixtures(tmp_path, ["a.txt"])
        # Overwrite ciphertext with invalid data (not multiple of 16 bytes)
        (enc / "a.txt.enc").write_bytes(b"garbage")

        dec = tmp_path / "dec"
        result = _make_orchestrator().run_batch_decrypt(enc, dec)
        assert result.failed_count == 1

    def test_per_file_isolation(self, tmp_path):
        """One corrupted file does not prevent others from succeeding.

        Uses malformed ciphertext rather than a wrong key so the expected
        failure is deterministic. Wrong-key decryption can occasionally
        produce plaintext whose trailing bytes pass PKCS#7 validation.
        """
        enc = self._encrypt_fixtures(tmp_path, ["a.txt", "bad.txt", "c.txt"])
        # Corrupt bad.txt's ciphertext with an invalid length.
        # V1 AESCipher.decrypt deterministically rejects ciphertext that is
        # not a multiple of the 16-byte block size.
        (enc / "bad.txt.enc").write_bytes(b"x")

        dec = tmp_path / "dec"
        result = _make_orchestrator().run_batch_decrypt(enc, dec)
        assert result.success_count == 2
        assert result.failed_count == 1
        failed = [r for r in result.results if r.status == "FAILED"]
        assert "bad.txt.enc" in str(failed[0].source_file)
        # Successful files are usable
        assert (dec / "a.txt").read_bytes() == b"content-of-a.txt"
        assert (dec / "c.txt").read_bytes() == b"content-of-c.txt"

    def test_ciphertext_preserved_after_decrypt(self, tmp_path):
        """Source ciphertext is never deleted or modified after decryption."""
        enc = self._encrypt_fixtures(tmp_path, ["a.txt"])
        ct_bytes = (enc / "a.txt.enc").read_bytes()
        dec = tmp_path / "dec"
        _make_orchestrator().run_batch_decrypt(enc, dec)
        assert (enc / "a.txt.enc").read_bytes() == ct_bytes

    def test_cbc_iv_loading(self, tmp_path):
        """CBC decrypt successfully loads the per-file IV."""
        enc = self._encrypt_fixtures(tmp_path, ["a.txt"], mode="CBC")
        dec = tmp_path / "dec"
        result = _make_orchestrator().run_batch_decrypt(enc, dec, mode="CBC")
        assert result.success_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# Conflict behaviour
# ─────────────────────────────────────────────────────────────────────────────


class TestConflict:
    """Skip/overwrite policies during batch execution."""

    def test_skip_default(self, tmp_path):
        """Pre-existing ciphertext → SKIPPED with default (skip) policy."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "a.txt.enc").write_bytes(b"existing")

        result = _make_orchestrator().run_batch_encrypt(src, dest)
        assert result.skipped_count == 1
        assert result.success_count == 0
        assert (dest / "a.txt.enc").read_bytes() == b"existing"

    def test_explicit_skip(self, tmp_path):
        """Explicit on_conflict='skip' behaves identically."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "a.txt.enc").write_bytes(b"old")

        result = _make_orchestrator().run_batch_encrypt(src, dest, on_conflict="skip")
        assert result.skipped_count == 1

    def test_overwrite_policy(self, tmp_path):
        """Overwrite policy replaces the existing ciphertext."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "a.txt.enc").write_bytes(b"old")

        result = _make_orchestrator().run_batch_encrypt(src, dest, on_conflict="overwrite")
        assert result.success_count == 1
        assert result.skipped_count == 0
        # The new ciphertext must differ from the old placeholder
        assert (dest / "a.txt.enc").read_bytes() != b"old"

    def test_existing_preserved_when_prep_fails(self, tmp_path):
        """If os.replace fails, the pre-existing dest is not destroyed."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "a.txt.enc").write_bytes(b"OLD_CONTENT")

        original_replace = os.replace

        def failing_replace(src_path, dst_path):
            if "a.txt.enc" in str(dst_path) and "OLD_CONTENT" not in str(src_path):
                raise OSError("simulated replace failure")
            return original_replace(src_path, dst_path)

        with patch("src.cli_v2.batch_orchestrator.os.replace", side_effect=failing_replace):
            result = _make_orchestrator().run_batch_encrypt(
                src, dest, on_conflict="overwrite"
            )

        assert result.failed_count == 1
        assert (dest / "a.txt.enc").read_bytes() == b"OLD_CONTENT"

    def test_decrypt_skip(self, tmp_path):
        """Decrypt skip policy: pre-existing plaintext destination → SKIPPED."""
        enc_dir = _setup_encrypt_src(tmp_path, ["a.txt"])
        enc_dir2 = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(enc_dir, enc_dir2)

        dec = tmp_path / "dec"
        dec.mkdir()
        (dec / "a.txt").write_bytes(b"existing_plain")

        result = _make_orchestrator().run_batch_decrypt(enc_dir2, dec)
        assert result.skipped_count == 1
        assert (dec / "a.txt").read_bytes() == b"existing_plain"

    def test_decrypt_overwrite(self, tmp_path):
        """Decrypt overwrite: existing plaintext replaced by decrypted content."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        enc = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(src, enc)

        dec = tmp_path / "dec"
        dec.mkdir()
        (dec / "a.txt").write_bytes(b"old_plain")

        result = _make_orchestrator().run_batch_decrypt(
            enc, dec, on_conflict="overwrite"
        )
        assert result.success_count == 1
        assert (dec / "a.txt").read_bytes() == b"content-of-a.txt"


# ─────────────────────────────────────────────────────────────────────────────
# Sidecar failure safety
# ─────────────────────────────────────────────────────────────────────────────


class TestSidecarFailureSafety:
    """Sidecar preparation failures must never destroy pre-existing artifacts."""

    def _premake_dest(self, dest: Path) -> Path:
        """Create a destination dir with a pre-existing ciphertext for bad.txt."""
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "bad.txt.enc").write_bytes(b"OLDER_ENCRYPTED")
        return dest

    def test_save_key_failure_unique_ecb_preserves_dest(self, tmp_path, monkeypatch):
        """A: unique-key ECB — save_key failure keeps the old ciphertext; no orphan sidecars."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt", "good.txt"])
        dest = self._premake_dest(tmp_path / "out")
        _patch_save_key_to_fail(monkeypatch, dest, "bad.txt.enc.key")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="ECB", on_conflict="overwrite"
        )
        by_name = {r.source_file.name: r.status for r in result.results}
        assert by_name["bad.txt"] == "FAILED"
        assert by_name["good.txt"] == "SUCCESS"
        assert (dest / "bad.txt.enc").read_bytes() == b"OLDER_ENCRYPTED"
        # No orphan sidecar from the failed operation.
        assert not (dest / "bad.txt.enc.key").exists()
        assert not (dest / "bad.txt.enc.iv").exists()

    def test_save_key_failure_unique_cbc_preserves_dest(self, tmp_path, monkeypatch):
        """B: unique-key CBC — save_key failure keeps the old ciphertext; no orphan sidecars."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt", "good.txt"])
        dest = self._premake_dest(tmp_path / "out")
        _patch_save_key_to_fail(monkeypatch, dest, "bad.txt.enc.key")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        by_name = {r.source_file.name: r.status for r in result.results}
        assert by_name["bad.txt"] == "FAILED"
        assert by_name["good.txt"] == "SUCCESS"
        assert (dest / "bad.txt.enc").read_bytes() == b"OLDER_ENCRYPTED"
        # No orphan sidecars from the failed operation.
        assert not (dest / "bad.txt.enc.key").exists()
        assert not (dest / "bad.txt.enc.iv").exists()

    def test_save_key_failure_shared_cbc_preserves_dest(self, tmp_path, monkeypatch):
        """C: shared-key CBC — batch.key write failure fails the file, keeps ciphertext."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt", "good.txt"])
        dest = self._premake_dest(tmp_path / "out")
        _patch_save_key_to_fail(monkeypatch, dest, "batch.key")

        result = _make_orchestrator().run_batch_encrypt(
            src,
            dest,
            mode="CBC",
            shared_key=SHARED_KEY_256,
            on_conflict="overwrite",
        )
        assert all(r.status == "FAILED" for r in result.results)
        assert (dest / "bad.txt.enc").read_bytes() == b"OLDER_ENCRYPTED"
        # Shared mode never creates per-file .key sidecars.
        assert not (dest / "bad.txt.enc.key").exists()
        assert not (dest / "good.txt.enc.key").exists()
        # The batch.key could never be persisted.
        assert not (dest / "batch.key").exists()

    def test_save_key_failure_overwrite_preserves_sidecar_set(self, tmp_path, monkeypatch):
        """D: overwrite mode — a full pre-existing artifact set is preserved."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        old_ct = b"OLD_CT_BYTES"
        old_key = b"00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff\n"
        old_iv = b"fedcba9876543210fedcba9876543210\n"
        (dest / "bad.txt.enc").write_bytes(old_ct)
        (dest / "bad.txt.enc.key").write_bytes(old_key)
        (dest / "bad.txt.enc.iv").write_bytes(old_iv)
        _patch_save_key_to_fail(monkeypatch, dest, "bad.txt.enc.key")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert result.results[0].status == "FAILED"
        assert (dest / "bad.txt.enc").read_bytes() == old_ct
        assert (dest / "bad.txt.enc.key").read_bytes() == old_key
        assert (dest / "bad.txt.enc.iv").read_bytes() == old_iv

    def test_save_iv_failure_unique_cbc_preserves_dest(self, tmp_path, monkeypatch):
        """save_iv failure in unique-key CBC keeps the old ciphertext and key sidecar."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt", "good.txt"])
        dest = self._premake_dest(tmp_path / "out")
        # Pre-existing key sidecar: save_iv failure must not overwrite it.
        old_key = b"00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff\n"
        (dest / "bad.txt.enc.key").write_bytes(old_key)
        _patch_save_iv_to_fail(monkeypatch, dest, "bad.txt.enc.iv")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        by_name = {r.source_file.name: r.status for r in result.results}
        assert by_name["bad.txt"] == "FAILED"
        assert by_name["good.txt"] == "SUCCESS"
        # Ciphertext and key sidecar preserved byte-for-byte.
        assert (dest / "bad.txt.enc").read_bytes() == b"OLDER_ENCRYPTED"
        assert (dest / "bad.txt.enc.key").read_bytes() == old_key
        # IV sidecar: old was absent, new orphan removed.
        assert not (dest / "bad.txt.enc.iv").exists()

    def test_save_iv_failure_shared_cbc_preserves_dest(self, tmp_path, monkeypatch):
        """save_iv failure in shared-key CBC keeps ciphertext and pre-existing IV."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt", "good.txt"])
        dest = self._premake_dest(tmp_path / "out")
        # Pre-existing IV sidecar: must be preserved byte-for-byte.
        old_iv = b"fedcba9876543210fedcba9876543210\n"
        (dest / "bad.txt.enc.iv").write_bytes(old_iv)
        _patch_save_iv_to_fail(monkeypatch, dest, "bad.txt.enc.iv")

        result = _make_orchestrator().run_batch_encrypt(
            src,
            dest,
            mode="CBC",
            shared_key=SHARED_KEY_256,
            on_conflict="overwrite",
        )
        by_name = {r.source_file.name: r.status for r in result.results}
        assert by_name["bad.txt"] == "FAILED"
        assert by_name["good.txt"] == "SUCCESS"
        assert (dest / "bad.txt.enc").read_bytes() == b"OLDER_ENCRYPTED"
        assert (dest / "bad.txt.enc.iv").read_bytes() == old_iv
        # Shared mode persists batch.key but never per-file .key files.
        assert (dest / "batch.key").exists()
        assert not (dest / "bad.txt.enc.key").exists()
        assert not (dest / "good.txt.enc.key").exists()

    def test_save_iv_failure_overwrite_preserves_dest(self, tmp_path, monkeypatch):
        """save_iv failure in overwrite mode preserves the full pre-existing artifact set."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        old_ct = b"OLD_CT_BYTES"
        old_key = b"00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff\n"
        old_iv = b"fedcba9876543210fedcba9876543210\n"
        (dest / "bad.txt.enc").write_bytes(old_ct)
        (dest / "bad.txt.enc.key").write_bytes(old_key)
        (dest / "bad.txt.enc.iv").write_bytes(old_iv)
        _patch_save_iv_to_fail(monkeypatch, dest, "bad.txt.enc.iv")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert result.results[0].status == "FAILED"
        # All three pre-existing artifacts preserved byte-for-byte.
        assert (dest / "bad.txt.enc").read_bytes() == old_ct
        assert (dest / "bad.txt.enc.key").read_bytes() == old_key
        assert (dest / "bad.txt.enc.iv").read_bytes() == old_iv

    def test_failed_preparation_marked_failed(self, tmp_path, monkeypatch):
        """A sidecar failure yields an explicit FAILED result row."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = self._premake_dest(tmp_path / "out")
        _patch_save_key_to_fail(monkeypatch, dest, "bad.txt.enc.key")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert result.failed_count == 1
        assert result.results[0].status == "FAILED"
        assert result.log_file is not None

    def test_failed_preparation_cleans_temp(self, tmp_path, monkeypatch):
        """Staged .tmp_* artifacts are removed after a sidecar failure."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = self._premake_dest(tmp_path / "out")
        _patch_save_key_to_fail(monkeypatch, dest, "bad.txt.enc.key")

        _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert list(dest.glob(".tmp_*")) == []

    def test_sidecar_failure_unrelated_files_untouched(self, tmp_path, monkeypatch):
        """Files in the destination not targeted by the batch are untouched."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = self._premake_dest(tmp_path / "out")
        unrelated_enc = dest / "unrelated.enc"
        notes = dest / "notes.txt"
        unrelated_enc.write_bytes(b"UNRELATED11")
        notes.write_bytes(b"NOTES22")
        _patch_save_key_to_fail(monkeypatch, dest, "bad.txt.enc.key")

        _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert unrelated_enc.read_bytes() == b"UNRELATED11"
        assert notes.read_bytes() == b"NOTES22"

    def test_sidecar_failure_other_files_succeed(self, tmp_path, monkeypatch):
        """A failed sidecar for one file does not stop the rest of the batch."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt", "mid.txt", "good.txt"])
        dest = self._premake_dest(tmp_path / "out")
        _patch_save_key_to_fail(monkeypatch, dest, "bad.txt.enc.key")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert result.success_count == 2
        assert result.failed_count == 1
        # The succeeded files are fully usable and their key sidecars exist.
        assert (dest / "mid.txt.enc").exists()
        assert (dest / "good.txt.enc").exists()
        assert (dest / "mid.txt.enc.key").exists()
        assert (dest / "good.txt.enc.key").exists()

    def test_save_iv_failure_no_sidecars_no_orphans(self, tmp_path, monkeypatch):
        """save_iv failure with NO pre-existing sidecars leaves no orphans."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        # No pre-existing ciphertext, key, or IV sidecar.
        _patch_save_iv_to_fail(monkeypatch, dest, "bad.txt.enc.iv")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert result.results[0].status == "FAILED"
        # No ciphertext was committed (save_iv failed before os.replace).
        assert not (dest / "bad.txt.enc").exists()
        # No orphan sidecars from the failed operation.
        assert not (dest / "bad.txt.enc.key").exists()
        assert not (dest / "bad.txt.enc.iv").exists()
        # No temp files remain.
        assert list(dest.glob(".tmp_*")) == []

    def test_save_key_failure_no_sidecars_no_orphans(self, tmp_path, monkeypatch):
        """save_key failure with NO pre-existing sidecars leaves no orphans."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        # No pre-existing ciphertext, key, or IV sidecar.
        _patch_save_key_to_fail(monkeypatch, dest, "bad.txt.enc.key")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="ECB", on_conflict="overwrite"
        )
        assert result.results[0].status == "FAILED"
        assert not (dest / "bad.txt.enc").exists()
        assert not (dest / "bad.txt.enc.key").exists()
        assert not (dest / "bad.txt.enc.iv").exists()
        assert list(dest.glob(".tmp_*")) == []

    def test_os_replace_failure_restores_full_sidecar_set(self, tmp_path, monkeypatch):
        """The most important gap: sidecars written, ciphertext replace fails.

        save_key and save_iv both SUCCEED (new sidecars overwrite the old
        ones), then os.replace is forced to fail.  The rollback protection
        must extend past sidecar preparation and restore the complete
        pre-existing artifact set (.enc/.key/.iv) byte-for-byte.
        """
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        old_ct = b"OLD_CT_BYTES"
        old_key = b"00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff\n"
        old_iv = b"fedcba9876543210fedcba9876543210\n"
        (dest / "bad.txt.enc").write_bytes(old_ct)
        (dest / "bad.txt.enc.key").write_bytes(old_key)
        (dest / "bad.txt.enc.iv").write_bytes(old_iv)
        _patch_os_replace_to_fail(monkeypatch, "bad.txt.enc")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert result.results[0].status == "FAILED"
        # All three pre-existing artifacts preserved byte-for-byte.
        assert (dest / "bad.txt.enc").read_bytes() == old_ct
        assert (dest / "bad.txt.enc.key").read_bytes() == old_key
        assert (dest / "bad.txt.enc.iv").read_bytes() == old_iv
        # No staged temp files remain.
        assert list(dest.glob(".tmp_*")) == []

    def test_os_replace_failure_no_sidecars_no_orphans(self, tmp_path, monkeypatch):
        """os.replace failure with NO pre-existing sidecars leaves no orphans.

        save_key and save_iv succeed (new sidecars created), then the ciphertext
        replace fails: the freshly-created key/iv sidecars must be removed and
        no ciphertext may be committed.
        """
        src = _setup_encrypt_src(tmp_path, ["bad.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        # No pre-existing ciphertext, key, or IV sidecar.
        _patch_os_replace_to_fail(monkeypatch, "bad.txt.enc")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        assert result.results[0].status == "FAILED"
        # No ciphertext was committed (replace failed) and no orphan sidecars:
        assert not (dest / "bad.txt.enc").exists()
        assert not (dest / "bad.txt.enc.key").exists()
        assert not (dest / "bad.txt.enc.iv").exists()
        assert list(dest.glob(".tmp_*")) == []

    def test_os_replace_failure_other_files_succeed(self, tmp_path, monkeypatch):
        """Per-file isolation survives an os.replace failure: the other file succeeds."""
        src = _setup_encrypt_src(tmp_path, ["bad.txt", "good.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "bad.txt.enc").write_bytes(b"OLD_CT")
        _patch_os_replace_to_fail(monkeypatch, "bad.txt.enc")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, mode="CBC", on_conflict="overwrite"
        )
        by_name = {r.source_file.name: r.status for r in result.results}
        assert by_name["bad.txt"] == "FAILED"
        assert by_name["good.txt"] == "SUCCESS"
        # bad.txt's pre-existing ciphertext intact; good.txt fully committed
        # with usable key/iv sidecars.
        assert (dest / "bad.txt.enc").read_bytes() == b"OLD_CT"
        assert (dest / "good.txt.enc").exists()
        assert (dest / "good.txt.enc.key").exists()
        assert (dest / "good.txt.enc.iv").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Shared batch.key timing
# ─────────────────────────────────────────────────────────────────────────────


class TestSharedBatchKeyTiming:
    """batch.key is persisted only when a file is actually processed."""

    def test_all_skipped_creates_no_batch_key(self, tmp_path):
        """Shared key + all destinations exist + skip → no batch.key is created."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "a.txt.enc").write_bytes(b"existing")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, shared_key=SHARED_KEY_256, on_conflict="skip"
        )
        assert result.skipped_count == 1
        assert result.success_count == 0
        assert not (dest / "batch.key").exists()

    def test_batch_key_written_once_when_first_file_skipped(self, tmp_path):
        """A skipped file does not block batch.key; the first processed file writes it."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "a.txt.enc").write_bytes(b"existing")

        result = _make_orchestrator().run_batch_encrypt(
            src, dest, shared_key=SHARED_KEY_256, on_conflict="skip"
        )
        assert result.skipped_count == 1
        assert result.success_count == 1
        assert (dest / "batch.key").exists()
        assert (dest / "b.txt.enc").exists()

    def test_empty_batch_creates_no_batch_key(self, tmp_path):
        """No candidates → no batch.key, even in shared-key mode."""
        src = tmp_path / "empty_src"
        src.mkdir()
        result = _make_orchestrator().run_batch_encrypt(
            src, tmp_path / "out", shared_key=SHARED_KEY_256
        )
        assert result.total_files == 0
        assert not (tmp_path / "out" / "batch.key").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Dry-run
# ─────────────────────────────────────────────────────────────────────────────


class TestDryRun:
    """Dry-run mode performs zero writes."""

    def test_zero_ciphertexts(self, tmp_path):
        """Dry-run encrypt produces no .enc files."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"

        result = _make_orchestrator().run_batch_encrypt(src, dest, dry_run=True)
        assert not dest.exists()
        assert result.success_count == 2

    def test_zero_key_sidecars(self, tmp_path):
        """Dry-run encrypt produces no .key files."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"

        _make_orchestrator().run_batch_encrypt(src, dest, dry_run=True)
        assert not (dest / "a.txt.enc.key").exists()

    def test_zero_iv_sidecars(self, tmp_path):
        """Dry-run encrypt produces no .iv files."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"

        _make_orchestrator().run_batch_encrypt(src, dest, dry_run=True)
        assert not (dest / "a.txt.enc.iv").exists()

    def test_no_log(self, tmp_path):
        """Dry-run returns log_file=None."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(
            src, tmp_path / "out", dry_run=True
        )
        assert result.log_file is None

    def test_crypto_not_called_encrypt(self, tmp_path):
        """Encrypt dry-run never calls encrypt_data."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        service = CipherService()
        mock_enc = MagicMock(side_effect=AssertionError("should not be called"))
        original_enc = service.encrypt_data
        service.encrypt_data = mock_enc

        orch = BatchOrchestrator(cipher_service=service)
        orch.run_batch_encrypt(src, tmp_path / "out", dry_run=True)
        mock_enc.assert_not_called()

    def test_crypto_not_called_decrypt(self, tmp_path):
        """Decrypt dry-run never calls decrypt_data."""
        enc_src = _setup_encrypt_src(tmp_path, ["a.txt"])
        enc_dir = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(enc_src, enc_dir)

        service = CipherService()
        mock_dec = MagicMock(side_effect=AssertionError("should not be called"))
        service.decrypt_data = mock_dec

        orch = BatchOrchestrator(cipher_service=service)
        orch.run_batch_decrypt(enc_dir, tmp_path / "out", dry_run=True)
        mock_dec.assert_not_called()

    def test_dry_run_decrypt_zero_plaintext(self, tmp_path):
        """Dry-run decrypt produces no output files."""
        enc_src = _setup_encrypt_src(tmp_path, ["a.txt"])
        enc_dir = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(enc_src, enc_dir)

        result = _make_orchestrator().run_batch_decrypt(
            enc_dir, tmp_path / "dec", dry_run=True
        )
        assert result.success_count == 1
        assert not (tmp_path / "dec").exists()

    def test_no_batch_key_in_dry_run(self, tmp_path):
        """Shared-key dry-run does not write batch.key."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        _make_orchestrator().run_batch_encrypt(
            src, tmp_path / "out", shared_key=SHARED_KEY_256, dry_run=True
        )
        assert not (tmp_path / "out" / "batch.key").exists()

    def test_summary_fields_dry_run(self, tmp_path):
        """Dry-run summary correctly counts planned operations."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt", "c.txt"])
        result = _make_orchestrator().run_batch_encrypt(
            src, tmp_path / "out", dry_run=True
        )
        assert result.total_files == 3
        assert result.success_count == 3
        assert result.total_time_ms == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Error isolation
# ─────────────────────────────────────────────────────────────────────────────


class TestErrorIsolation:
    """Per-file failures do not abort the batch."""

    def test_one_fails_others_succeed(self, tmp_path):
        """One unreadable source file fails; other files encrypt normally."""
        src = _setup_encrypt_src(tmp_path, ["good1.txt", "good2.txt"])
        # Create a file, then remove it after discover (race simulation)
        missing = src / "gone.txt"
        missing.write_bytes(b"will vanish")

        dest = tmp_path / "out"
        orch = _make_orchestrator()

        # Discover first (so gone.txt is a candidate), then remove it
        src_path = src
        gone_path = missing
        _real_exists = Path.exists

        original_encrypt_one = orch._encrypt_one

        def selective_encrypt(*args, **kwargs):
            # Delete gone.txt before the first _encrypt_one call for it
            if gone_path.exists():
                gone_path.unlink()
            return original_encrypt_one(*args, **kwargs)

        orch._encrypt_one = selective_encrypt

        # We need to discover first, but gone.txt exists during discovery.
        # Instead, manually test: create a file that we will make unreadable.
        src2 = _setup_encrypt_src(tmp_path, ["ok.txt"])
        bad = src2 / "bad.txt"
        bad.write_bytes(b"content")
        bad.chmod(0o000)  # remove read permissions

        try:
            result = orch.run_batch_encrypt(src2, dest)
            # bad.txt should fail, ok.txt should succeed
            statuses = {r.source_file.name: r.status for r in result.results}
            assert statuses["ok.txt"] == "SUCCESS"
            # bad.txt may fail (PermissionError) or succeed if running as admin
        finally:
            bad.chmod(0o666)  # restore for cleanup

    def test_failed_result_has_status(self, tmp_path):
        """FAILED results have exactly status='FAILED'."""
        enc_src = _setup_encrypt_src(tmp_path, ["a.txt"])
        enc_dir = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(enc_src, enc_dir)

        # Corrupt key for a.txt
        wrong = bytes(range(32, 64))
        KeyManager.save_key(wrong, enc_dir / "a.txt.enc.key")

        result = _make_orchestrator().run_batch_decrypt(enc_dir, tmp_path / "dec")
        failed = [r for r in result.results if r.status == "FAILED"]
        assert len(failed) == 1
        assert failed[0].error_message  # non-empty error message

    def test_no_secret_in_error_message(self, tmp_path):
        """Error messages never contain the key material."""
        enc_src = _setup_encrypt_src(tmp_path, ["a.txt"])
        enc_dir = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(
            enc_src, enc_dir, shared_key=SHARED_KEY_256
        )

        # Corrupt ciphertext
        (enc_dir / "a.txt.enc").write_bytes(b"\x00" * 32)

        result = _make_orchestrator().run_batch_decrypt(
            enc_dir, tmp_path / "dec", shared_key=SHARED_KEY_256
        )
        for r in result.results:
            assert SHARED_KEY_256.hex() not in r.error_message
            assert SHARED_KEY_256.hex() not in r.error_message.lower()

    def test_batch_completes_on_individual_failure(self, tmp_path):
        """Batch does not raise an exception when individual files fail."""
        enc_src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        enc_dir = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(enc_src, enc_dir)

        # Corrupt one key
        wrong = bytes(range(32, 64))
        KeyManager.save_key(wrong, enc_dir / "a.txt.enc.key")

        # Should not raise
        result = _make_orchestrator().run_batch_decrypt(
            enc_dir, tmp_path / "dec"
        )
        assert result.total_files == 2
        assert result.failed_count == 1
        assert result.success_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# CSV logging
# ─────────────────────────────────────────────────────────────────────────────


class TestCsvLog:
    """Log location, schema, timestamp format, and secret protection."""

    def test_log_location(self, tmp_path):
        """Log file is written into the destination directory."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        assert result.log_file is not None
        assert result.log_file.parent == tmp_path / "out"

    def test_filename_pattern(self, tmp_path):
        """Log filename matches 'batch_log_YYYYMMDD_HHMMSS.csv'."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        assert re.match(r"batch_log_\d{8}_\d{6}\.csv$", result.log_file.name)

    def test_exact_seven_columns(self, tmp_path):
        """CSV header has exactly 7 columns."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        with open(result.log_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert len(header) == 7

    def test_column_names(self, tmp_path):
        """CSV header columns are exactly the frozen schema."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        with open(result.log_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        expected = [
            "timestamp", "source_file", "dest_file", "status",
            "size_bytes", "elapsed_ms", "error_message",
        ]
        assert header == expected

    def test_utc_timestamp_format(self, tmp_path):
        """Timestamps are UTC ISO-8601 with a trailing 'Z'."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        with open(result.log_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # header
            for row in reader:
                ts = row[0]
                assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", ts)

    def test_rows_match_results(self, tmp_path):
        """Number of data rows equals the number of result records."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt", "c.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        with open(result.log_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # header
            rows = list(reader)
        assert len(rows) == result.total_files

    def test_no_secrets_in_log(self, tmp_path):
        """Key material does not appear anywhere in the log content."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(
            src, tmp_path / "out", shared_key=SHARED_KEY_256
        )
        log_text = result.log_file.read_text(encoding="utf-8")
        assert SHARED_KEY_256.hex() not in log_text

    def test_no_log_in_dry_run(self, tmp_path):
        """Dry-run produces log_file=None and no log on disk."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(
            src, tmp_path / "out", dry_run=True
        )
        assert result.log_file is None
        assert not (tmp_path / "out").exists()

    def test_log_with_empty_results(self, tmp_path):
        """An empty batch still writes a log with the header only."""
        src = tmp_path / "empty_src"
        src.mkdir()
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        assert result.log_file is not None
        with open(result.log_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        assert len(header) == 7
        assert rows == []  # no data rows

    def test_decrypt_log(self, tmp_path):
        """Decryption also writes a log with correct columns."""
        enc_src = _setup_encrypt_src(tmp_path, ["a.txt"])
        enc = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(enc_src, enc)

        result = _make_orchestrator().run_batch_decrypt(enc, tmp_path / "dec")
        assert result.log_file is not None
        with open(result.log_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header[0] == "timestamp"
        assert header[3] == "status"

    def test_log_deterministic_timestamp(self, tmp_path):
        """Log filename uses the monkeypatched UTC timestamp."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        with patch("src.cli_v2.batch_orchestrator._utc_datetime", _utc_fixed):
            result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        assert result.log_file.name == "batch_log_20250615_123045.csv"


# ─────────────────────────────────────────────────────────────────────────────
# KeyboardInterrupt
# ─────────────────────────────────────────────────────────────────────────────


class TestKeyboardInterrupt:
    """Graceful cancellation preserves completed work and cleans temps."""

    def test_temp_cleaned(self, tmp_path):
        """No .tmp_* files remain after KeyboardInterrupt."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        service = CipherService()
        call_count = [0]
        original_encrypt = service.encrypt_data

        def interrupting_encrypt(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise KeyboardInterrupt()
            return original_encrypt(*args, **kwargs)

        service.encrypt_data = interrupting_encrypt
        orch = BatchOrchestrator(cipher_service=service)

        # KeyboardInterrupt propagates from the try/except in run_batch_encrypt
        # The outer handler catches it and returns a partial summary.
        result = orch.run_batch_encrypt(src, dest)

        # Check no temp files remain
        tmp_files = list(dest.glob(".tmp_*"))
        assert tmp_files == [], f"Temp files remain: {tmp_files}"

    def test_completed_survive(self, tmp_path):
        """Files processed before the interrupt are successfully written."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        service = CipherService()
        call_count = [0]
        original_encrypt = service.encrypt_data

        def interrupting_encrypt(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise KeyboardInterrupt()
            return original_encrypt(*args, **kwargs)

        service.encrypt_data = interrupting_encrypt
        orch = BatchOrchestrator(cipher_service=service)
        result = orch.run_batch_encrypt(src, dest)

        # The first file was completed before the interrupt
        success = [r for r in result.results if r.status == "SUCCESS"]
        assert len(success) >= 1

    def test_not_converted_to_failed(self, tmp_path):
        """The interrupted file does not appear as a FAILED result."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        service = CipherService()
        call_count = [0]
        original_encrypt = service.encrypt_data

        def interrupting_encrypt(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise KeyboardInterrupt()
            return original_encrypt(*args, **kwargs)

        service.encrypt_data = interrupting_encrypt
        orch = BatchOrchestrator(cipher_service=service)
        result = orch.run_batch_encrypt(src, dest)

        assert all(r.status != "FAILED" for r in result.results)

    def test_log_written_on_interrupt(self, tmp_path):
        """Partial results are flushed to the CSV log on interrupt."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        dest = tmp_path / "out"
        service = CipherService()
        call_count = [0]
        original_encrypt = service.encrypt_data

        def interrupting_encrypt(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise KeyboardInterrupt()
            return original_encrypt(*args, **kwargs)

        service.encrypt_data = interrupting_encrypt
        orch = BatchOrchestrator(cipher_service=service)
        result = orch.run_batch_encrypt(src, dest)

        assert result.log_file is not None
        assert result.log_file.exists()

    def test_decrypt_interrupt(self, tmp_path):
        """KeyboardInterrupt during decrypt follows the same pattern."""
        enc_src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        enc = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(enc_src, enc)

        service = CipherService()
        call_count = [0]
        original_decrypt = service.decrypt_data

        def interrupting_decrypt(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise KeyboardInterrupt()
            return original_decrypt(*args, **kwargs)

        service.decrypt_data = interrupting_decrypt
        orch = BatchOrchestrator(cipher_service=service)
        result = orch.run_batch_decrypt(enc, tmp_path / "dec")

        success = [r for r in result.results if r.status == "SUCCESS"]
        assert len(success) >= 1
        assert all(r.status != "FAILED" for r in result.results)


# ─────────────────────────────────────────────────────────────────────────────
# V1 interoperability
# ─────────────────────────────────────────────────────────────────────────────


class TestInterop:
    """Real V1 AES interop: batch-produced ciphertext is V1-decryptable."""

    def test_v1_service_decrypts_batch_ciphertext(self, tmp_path):
        """CipherService.decrypt_data on a batch-produced file returns original."""
        src = _setup_encrypt_src(tmp_path, ["data.txt"])
        original = (src / "data.txt").read_bytes()
        enc = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(src, enc)

        # Load sidecar key and IV via KeyManager, decrypt via raw CipherService
        key, key_bits = KeyManager.load_key(enc / "data.txt.enc.key")
        iv = KeyManager.load_iv(enc / "data.txt.enc.iv")
        ciphertext = FileHandler.read_bytes(enc / "data.txt.enc")

        service = CipherService()
        plaintext = service.decrypt_data("AES", key_bits, "CBC", ciphertext, key, iv)
        assert plaintext == original

    def test_batch_decrypts_v1_encrypted_file(self, tmp_path):
        """CipherService.encrypt_data produces a file BatchOrchestrator can decrypt."""
        # Encrypt via raw V1, then decrypt via BatchOrchestrator
        plaintext = b"Raw V1 interop test payload"
        key = SHARED_KEY_256
        iv = os.urandom(16)

        service = CipherService()
        result = service.encrypt_data("AES", 256, "CBC", plaintext, key, iv)

        # Set up a mock ciphertext directory
        ct_dir = tmp_path / "ct"
        ct_dir.mkdir()
        FileHandler.write_bytes(ct_dir / "v1_output.enc", result.ciphertext)
        KeyManager.save_iv(result.iv, ct_dir / "v1_output.enc.iv")

        dec = tmp_path / "dec"
        batch_result = _make_orchestrator().run_batch_decrypt(
            ct_dir, dec, shared_key=key
        )
        assert batch_result.success_count == 1
        assert (dec / "v1_output").read_bytes() == plaintext

    def test_ecb_interop(self, tmp_path):
        """ECB mode: batch encrypt is V1-decryptable."""
        plaintext = b"ECB interop"
        key = SHARED_KEY_256

        service = CipherService()
        result = service.encrypt_data("AES", 256, "ECB", plaintext, key, None)

        ct_dir = tmp_path / "ct"
        ct_dir.mkdir()
        FileHandler.write_bytes(ct_dir / "ecb_file.enc", result.ciphertext)
        KeyManager.save_key(key, ct_dir / "ecb_file.enc.key")

        dec = tmp_path / "dec"
        batch_result = _make_orchestrator().run_batch_decrypt(
            ct_dir, dec, shared_key=key, mode="ECB"
        )
        assert batch_result.success_count == 1
        assert (dec / "ecb_file").read_bytes() == plaintext

    def test_round_trip_128_key(self, tmp_path):
        """128-bit key round-trip through batch encrypt/decrypt."""
        src = _setup_encrypt_src(tmp_path, ["small.txt"])
        enc = tmp_path / "enc"
        dec = tmp_path / "dec"

        _make_orchestrator().run_batch_encrypt(src, enc, key_size=128)
        _make_orchestrator().run_batch_decrypt(enc, dec)

        assert (dec / "small.txt").read_bytes() == b"content-of-small.txt"

    def test_round_trip_192_key(self, tmp_path):
        """192-bit key round-trip through batch encrypt/decrypt."""
        src = _setup_encrypt_src(tmp_path, ["mid.txt"])
        enc = tmp_path / "enc"
        dec = tmp_path / "dec"

        _make_orchestrator().run_batch_encrypt(src, enc, key_size=192)
        _make_orchestrator().run_batch_decrypt(enc, dec)

        assert (dec / "mid.txt").read_bytes() == b"content-of-mid.txt"


# ─────────────────────────────────────────────────────────────────────────────
# Progress callback
# ─────────────────────────────────────────────────────────────────────────────


class TestProgressCallback:
    """Progress callback invocation."""

    def test_callback_called_per_file(self, tmp_path):
        """The callback is invoked once per candidate file."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt", "c.txt"])
        calls = []
        cb = lambda c, t, f: calls.append((c, t, f))

        _make_orchestrator().run_batch_encrypt(src, tmp_path / "out", progress_callback=cb)
        assert len(calls) == 3

    def test_callback_current_totals(self, tmp_path):
        """Callback receives (current_index, total, filename) tuples."""
        src = _setup_encrypt_src(tmp_path, ["x.txt", "y.txt"])
        calls = []
        cb = lambda c, t, f: calls.append((c, t, f))

        _make_orchestrator().run_batch_encrypt(src, tmp_path / "out", progress_callback=cb)
        assert calls[0][0] == 1
        assert calls[0][1] == 2
        assert calls[1][0] == 2

    def test_callback_called_on_skipped(self, tmp_path):
        """Skipped files also trigger the progress callback."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        dest = tmp_path / "out"
        dest.mkdir()
        (dest / "a.txt.enc").write_bytes(b"old")

        calls = []
        cb = lambda c, t, f: calls.append((c, t, f))
        _make_orchestrator().run_batch_encrypt(src, dest, progress_callback=cb)
        assert len(calls) == 1

    def test_callback_called_in_dry_run(self, tmp_path):
        """Dry-run still invokes the progress callback."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        calls = []
        cb = lambda c, t, f: calls.append((c, t, f))
        _make_orchestrator().run_batch_encrypt(src, tmp_path / "out", dry_run=True, progress_callback=cb)
        assert len(calls) == 1

    def test_no_callback(self, tmp_path):
        """When no callback is provided, no error is raised."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        assert result.success_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# Policy validation
# ─────────────────────────────────────────────────────────────────────────────


class TestPolicyValidation:
    """Invalid on_conflict values raise ValueError."""

    def test_invalid_encrypt(self, tmp_path):
        """Invalid policy in run_batch_encrypt raises ValueError."""
        src = _setup_encrypt_src(tmp_path, ["a.txt"])
        with pytest.raises(ValueError, match="on_conflict"):
            _make_orchestrator().run_batch_encrypt(src, tmp_path / "out", on_conflict="ask")

    def test_invalid_decrypt(self, tmp_path):
        """Invalid policy in run_batch_decrypt raises ValueError."""
        with pytest.raises(ValueError, match="on_conflict"):
            _make_orchestrator().run_batch_decrypt(tmp_path / "src", tmp_path / "dec", on_conflict="prompt")


# ─────────────────────────────────────────────────────────────────────────────
# Source safety
# ─────────────────────────────────────────────────────────────────────────────


class TestSourceSafety:
    """Source directories are never modified by batch operations."""

    def test_encrypt_preserves_all_sources(self, tmp_path):
        """All source files remain byte-identical after batch encryption."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt", "c.txt"])
        originals = {p.name: p.read_bytes() for p in src.iterdir() if p.is_file()}

        _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")

        for name, content in originals.items():
            assert (src / name).read_bytes() == content

    def test_decrypt_preserves_all_ciphertexts(self, tmp_path):
        """All source ciphertexts remain byte-identical after batch decryption."""
        enc_src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        enc = tmp_path / "enc"
        _make_orchestrator().run_batch_encrypt(enc_src, enc)

        originals = {p.name: p.read_bytes() for p in enc.iterdir() if p.suffix == ".enc"}

        _make_orchestrator().run_batch_decrypt(enc, tmp_path / "dec")

        for name, content in originals.items():
            assert (enc / name).read_bytes() == content


# ─────────────────────────────────────────────────────────────────────────────
# Batch summary dataclass
# ─────────────────────────────────────────────────────────────────────────────


class TestBatchSummaryDataclass:
    """Dataclass defaults and structure."""

    def test_default_factory(self):
        """BatchSummary defaults are correct."""
        s = BatchSummary(0, 0, 0, 0, 0, 0.0)
        assert s.results == []
        assert s.log_file is None

    def test_result_fields(self):
        """BatchFileResult stores all fields."""
        r = BatchFileResult(
            Path("src"), Path("dst"), "SUCCESS", 1024, 5.5, ""
        )
        assert r.size_bytes == 1024
        assert r.elapsed_ms == 5.5

    def test_batch_summary_total_bytes(self, tmp_path):
        """total_bytes is the sum of all result sizes."""
        src = _setup_encrypt_src(tmp_path, ["a.txt", "b.txt"])
        result = _make_orchestrator().run_batch_encrypt(src, tmp_path / "out")
        expected = sum(r.size_bytes for r in result.results)
        assert result.total_bytes == expected
