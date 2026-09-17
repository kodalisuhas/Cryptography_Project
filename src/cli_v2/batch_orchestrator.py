"""Batch encryption / decryption orchestration for V2 guided wizards.

Provides flat-directory discovery, preflight collision planning, unique and
shared-key batch execution with per-file error isolation, non-destructive
``os.replace`` staging, ``batch_log_*.csv`` logging, and ``--dry-run``
simulation — per the frozen V2 Batch Operations Contract (§12).

This module owns orchestration only.  Cryptographic generation/execution is
delegated to the V1 ``CipherService``; key/IV sidecar persistence and
validation are delegated to ``KeyManager``; low-level I/O reuses
``FileHandler``.  No AES is implemented here.

Security: key material and plaintext are never written to logs or results.
Error messages come from the native exceptions, which never echo secrets.
"""

from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.cli_v2.key_manager import KeyManager
from src.engines.cipher_service import CipherService
from src.utils.file_handler import FileHandler


def _utc_datetime() -> datetime:
    """Return the current UTC datetime (monkeypatchable in tests)."""
    return datetime.now(timezone.utc)


def _iso_timestamp(dt: datetime) -> str:
    """Format a datetime as UTC ISO-8601 with a trailing ``Z``."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_timestamp(dt: datetime) -> str:
    """Format a datetime as ``YYYYMMDD_HHMMSS`` for log filenames."""
    return dt.strftime("%Y%m%d_%H%M%S")


def _is_link_like(path: Path) -> bool:
    """True when *path* is a symbolic link or a Windows junction."""
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


@dataclass
class BatchFileResult:
    """Outcome for a single source file in a batch operation."""

    source_file: Path
    dest_file: Path
    status: str  # "SUCCESS", "SKIPPED", "FAILED"
    size_bytes: int
    elapsed_ms: float
    error_message: str


@dataclass
class BatchSummary:
    """Aggregate totals for a completed batch operation."""

    total_files: int
    success_count: int
    skipped_count: int
    failed_count: int
    total_bytes: int
    total_time_ms: float
    results: list[BatchFileResult] = field(default_factory=list)
    log_file: Path | None = None


class BatchOrchestrator:
    """Flat-directory batch encryption/decryption executor with V2 semantics.

    Args:
        cipher_service: Optional V1 ``CipherService`` dialog.  Defaults to a
            fresh instance when not supplied.
    """

    # Exclusion matrix per Selection §12.1.  ``.enc`` is excluded during
    # encryption discovery only (it is a ciphertext input during decryption).
    SIDECAR_EXTENSIONS = frozenset({".key", ".iv", ".log"})
    SYSTEM_FILES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
    VALID_CONFLICT_POLICIES = ("skip", "overwrite")

    def __init__(self, cipher_service: CipherService | None = None):
        self._cipher_service = cipher_service or CipherService()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_files(
        self,
        source_dir: Path,
        is_encryption: bool = True,
    ) -> tuple[list[Path], list[Path]]:
        """Discover batch candidate files in a flat directory scan.

        Scans *source_dir* non-recursively via ``Path.iterdir()``, applies the
        frozen exclusion matrix (sidecars, ciphertexts during encryption,
        system files, hidden dotfiles, temp files, directories, links, and
        junctions), and returns candidates and excluded entries separately.

        Args:
            source_dir: Directory to scan (single level, no recursion).
            is_encryption: True for encryption discovery (candidates are
                plaintext inputs; ``*.enc`` is excluded).  False for decryption
                discovery (only ``*.enc`` ciphertexts are candidates).

        Returns:
            Tuple of ``(candidates, excluded)``.  Both lists are sorted
            case-insensitively by filename.

        Raises:
            FileNotFoundError: *source_dir* does not exist.
        """
        source_dir = Path(source_dir)
        candidates: list[Path] = []
        excluded: list[Path] = []

        for entry in source_dir.iterdir():
            name = entry.name
            lower_name = name.lower()

            if _is_link_like(entry):
                excluded.append(entry)
                continue
            if entry.is_dir():
                excluded.append(entry)
                continue
            if name.startswith("."):  # hidden dotfiles
                excluded.append(entry)
                continue
            if lower_name in {n.lower() for n in BatchOrchestrator.SYSTEM_FILES}:
                excluded.append(entry)
                continue
            if ".tmp" in lower_name:  # `*.tmp*` staging/lock files
                excluded.append(entry)
                continue

            ext = entry.suffix.lower()
            if ext in BatchOrchestrator.SIDECAR_EXTENSIONS:
                excluded.append(entry)
                continue

            if is_encryption:
                if ext == ".enc":
                    excluded.append(entry)
                else:
                    candidates.append(entry)
            else:
                if ext == ".enc":
                    candidates.append(entry)
                else:
                    excluded.append(entry)

        candidates.sort(key=lambda p: p.name.lower())
        excluded.sort(key=lambda p: p.name.lower())
        return candidates, excluded

    # ------------------------------------------------------------------
    # Preflight planning
    # ------------------------------------------------------------------

    def preflight_check(
        self,
        candidates: list[Path],
        dest_dir: Path,
        on_conflict: str,
    ) -> dict[str, Any]:
        """Plan a batch run without performing any writes.

        Computes each candidate's destination, identifies destination
        collisions, and splits candidates into those that would proceed and
        those that would be skipped, using the selected conflict policy.

        Args:
            candidates: Source paths (typically from ``discover_files``).
            dest_dir: Output directory to evaluate destinations in.
            on_conflict: ``"skip"`` or ``"overwrite"``.

        Returns:
            Planning dict with keys ``on_conflict``, ``total``,
            ``collisions`` (list of ``(source, dest)`` tuples), ``will_process``,
            ``will_skip``, ``proceed_count``, and ``skipped_count``.

        Raises:
            ValueError: *on_conflict* is not a supported policy.
        """
        if on_conflict not in BatchOrchestrator.VALID_CONFLICT_POLICIES:
            raise ValueError(
                f"on_conflict must be one of "
                f"{BatchOrchestrator.VALID_CONFLICT_POLICIES}, got {on_conflict!r}"
            )

        dest_dir = Path(dest_dir)
        collisions: list[tuple[Path, Path]] = []
        will_process: list[Path] = []
        will_skip: list[Path] = []

        for src in candidates:
            src = Path(src)
            dest = self._planned_destination(src, dest_dir)
            if dest.exists():
                collisions.append((src, dest))
                if on_conflict == "skip":
                    will_skip.append(src)
                else:
                    will_process.append(src)
            else:
                will_process.append(src)

        return {
            "on_conflict": on_conflict,
            "total": len(candidates),
            "collisions": collisions,
            "will_process": will_process,
            "will_skip": will_skip,
            "proceed_count": len(will_process),
            "skipped_count": len(will_skip),
        }

    @staticmethod
    def _planned_destination(src: Path, dest_dir: Path) -> Path:
        """Return the destination path for *src* under the V2 naming rule.

        Encryption inputs (no ``.enc`` suffix) map to ``<name>.enc``;
        decryption ciphertexts (``.enc`` suffix) map back to ``<name>``.
        """
        if src.name.lower().endswith(".enc"):
            return dest_dir / src.name[:-4]
        return dest_dir / (src.name + ".enc")

    # ------------------------------------------------------------------
    # Batch execution
    # ------------------------------------------------------------------

    def run_batch_encrypt(
        self,
        source_dir: Path,
        dest_dir: Path,
        algorithm: str = "AES",
        key_size: int = 256,
        mode: str = "CBC",
        shared_key: bytes | None = None,
        on_conflict: str = "skip",
        dry_run: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> BatchSummary:
        """Encrypt every discovered plaintext in *source_dir*.

        Each file is processed independently with per-file error isolation.
        ``shared_key`` selects shared-key mode (one key persisted as
        ``<dest_dir>/batch.key``); otherwise a fresh unique key is generated
        and persisted as ``<dest>.enc.key`` per file.  CBC mode persists a
        unique IV per file as ``<dest>.enc.iv``.

        Args:
            source_dir: Directory containing plaintext inputs.
            dest_dir: Output directory for ciphertexts and sidecars.
            algorithm: Cipher algorithm name (e.g. ``"AES"``).
            key_size: AES key size in bits (128/192/256).
            mode: Cipher mode (``"ECB"`` or ``"CBC"``).
            shared_key: When not None, use this single key for the whole batch.
            on_conflict: Destination collision policy (``"skip"`` default).
            dry_run: When True, only discover/plan — no writes of any kind.
            progress_callback: Optional ``(current, total, filename)`` callback.

        Returns:
            A ``BatchSummary`` describing the run.  ``log_file`` is ``None``
            in dry-run mode.
        """
        mode = mode.upper()
        self._validate_policy(on_conflict)
        source_dir = Path(source_dir)
        dest_dir = Path(dest_dir)

        candidates, _ = self.discover_files(source_dir, is_encryption=True)
        total = len(candidates)
        results: list[BatchFileResult] = []

        # Shared-key mode persists batch.key lazily, once, on the first file
        # that is actually processed — never for an all-SKIPPED or dry-run
        # batch.  A failure while persisting it fails only that file.
        shared_key_pending = shared_key is not None and not dry_run

        try:
            for index, src in enumerate(candidates, 1):
                if progress_callback is not None:
                    progress_callback(index, total, src.name)

                dest = dest_dir / (src.name + ".enc")
                if dest.exists() and on_conflict == "skip":
                    results.append(self._skipped_result(src, dest))
                    continue
                if dry_run:
                    results.append(self._planned_result(src, dest))
                    continue

                # Committing to process this file; persist the shared key first.
                if shared_key_pending:
                    try:
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        KeyManager.save_key(shared_key, dest_dir / "batch.key")
                        shared_key_pending = False
                    except (FileNotFoundError, PermissionError, ValueError, OSError) as exc:
                        results.append(self._failed_result(src, dest, exc))
                        continue

                results.append(
                    self._encrypt_one(
                        src,
                        dest,
                        algorithm=algorithm,
                        key_size=key_size,
                        mode=mode,
                        shared_key=shared_key,
                    )
                )
        except KeyboardInterrupt:
            # Cancellation is not a per-file failure: clean up is already done
            # inside each file handler; flush a partial log and return.
            log_file = None if dry_run else self._write_log(dest_dir, results)
            return self._build_summary(results, log_file)

        log_file = None if dry_run else self._write_log(dest_dir, results)
        return self._build_summary(results, log_file)

    def run_batch_decrypt(
        self,
        source_dir: Path,
        dest_dir: Path,
        algorithm: str = "AES",
        key_size: int = 256,
        mode: str = "CBC",
        shared_key: bytes | None = None,
        on_conflict: str = "skip",
        dry_run: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> BatchSummary:
        """Decrypt every discovered ciphertext in *source_dir*.

        Unique-key mode loads each ciphertext's ``<name>.enc.key`` sidecar
        (and ``<name>.enc.iv`` for CBC); shared-key mode uses *shared_key* with
        the same per-file CBC IV sidecar.  Missing or invalid sidecars fail
        only that file.

        Args:
            source_dir: Directory containing ``*.enc`` ciphertexts.
            dest_dir: Output directory for recovered plaintexts.
            algorithm: Cipher algorithm name (e.g. ``"AES"``).
            key_size: Fallback key size hint; the actual size is derived from
                the loaded key bytes for each file.
            mode: Cipher mode (``"ECB"`` or ``"CBC"``).
            shared_key: When not None, use this single key for the whole batch.
            on_conflict: Destination collision policy (``"skip"`` default).
            dry_run: When True, only discover/plan — no writes of any kind.
            progress_callback: Optional ``(current, total, filename)`` callback.

        Returns:
            A ``BatchSummary`` describing the run.  ``log_file`` is ``None``
            in dry-run mode.
        """
        mode = mode.upper()
        self._validate_policy(on_conflict)
        source_dir = Path(source_dir)
        dest_dir = Path(dest_dir)

        candidates, _ = self.discover_files(source_dir, is_encryption=False)
        total = len(candidates)
        results: list[BatchFileResult] = []

        try:
            for index, src in enumerate(candidates, 1):
                if progress_callback is not None:
                    progress_callback(index, total, src.name)

                dest = dest_dir / src.name[:-4]
                if dest.exists() and on_conflict == "skip":
                    results.append(self._skipped_result(src, dest))
                    continue
                if dry_run:
                    results.append(self._planned_result(src, dest))
                    continue

                results.append(
                    self._decrypt_one(
                        src,
                        dest,
                        algorithm=algorithm,
                        mode=mode,
                        shared_key=shared_key,
                    )
                )
        except KeyboardInterrupt:
            log_file = None if dry_run else self._write_log(dest_dir, results)
            return self._build_summary(results, log_file)

        log_file = None if dry_run else self._write_log(dest_dir, results)
        return self._build_summary(results, log_file)

    # ------------------------------------------------------------------
    # Per-file processors
    # ------------------------------------------------------------------

    def _encrypt_one(
        self,
        src: Path,
        dest: Path,
        *,
        algorithm: str,
        key_size: int,
        mode: str,
        shared_key: bytes | None,
    ) -> BatchFileResult:
        """Encrypt a single source file with error isolation.

        Staging: the ciphertext is written to a ``.tmp_*`` file and committed
        via ``os.replace`` so a pre-existing destination is never corrupted by
        a partial write.  Sidecars are persisted through ``KeyManager``.  On
        failure the staged file is removed and only this file is marked FAILED.

        Artifact-set preservation: before writing any sidecar, a snapshot of
        each pre-existing sidecar's content is captured.  The rollback
        protection spans sidecar preparation through the ciphertext staging
        and ``os.replace`` commit.  If ANY step fails after the snapshot is
        taken but before ``os.replace`` returns, every pre-existing sidecar is
        restored byte-for-byte, any newly-created orphan sidecars are removed,
        the staged ``.tmp_*`` file is cleaned up, and this file is marked
        FAILED — leaving the destination artifact set exactly as it was before
        this operation started.  Only a successful ``os.replace`` commits the
        artifact set.
        """
        tmp = dest.with_name(f".tmp_{dest.name}")
        key_path = Path(str(dest) + ".key")
        iv_path = Path(str(dest) + ".iv")
        _sidecar_snapshot: dict[Path, bytes] = {}
        committed = False
        try:
            start = time.perf_counter()

            if shared_key is not None:
                key = shared_key
            else:
                key = (
                    self._cipher_service.factory
                    .create_cipher(algorithm, key_size, mode)
                    .generate_key()
                )

            plaintext = FileHandler.read_bytes(src)
            encrypted = self._cipher_service.encrypt_data(
                algorithm, key_size, mode, plaintext, key, iv=None
            )

            # Snapshot pre-existing sidecars so a later failure cannot leave
            # the artifact set in an inconsistent state (e.g. new key with old
            # IV) or orphan newly-created sidecars.
            _sidecar_snapshot = {}
            for _sp in (key_path, iv_path):
                if _sp.exists():
                    _sidecar_snapshot[_sp] = _sp.read_bytes()

            # Prepare sidecars, then stage and commit the ciphertext via
            # os.replace.  The rollback scope covers the whole sequence: a
            # failure of ANY step (sidecar write, mkdir, staging, or replace)
            # restores the snapshot before the FAILED result is returned.
            if shared_key is None:
                # Unique-key mode: persist the key as <dest>.enc.key.
                # Shared-key mode persists batch.key once in the run loop.
                KeyManager.save_key(key, key_path)
            if mode == "CBC" and encrypted.iv is not None:
                KeyManager.save_iv(encrypted.iv, iv_path)

            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(encrypted.ciphertext)
            os.replace(tmp, dest)

            # The ciphertext commit succeeded; the artifact set is now
            # complete and consistent.  committed=True is what stops the
            # finally block from rolling the sidecars back.
            committed = True

            elapsed = (time.perf_counter() - start) * 1000.0
            return BatchFileResult(src, dest, "SUCCESS", src.stat().st_size, elapsed, "")
        except KeyboardInterrupt:
            tmp.unlink(missing_ok=True)
            raise
        except (FileNotFoundError, PermissionError, ValueError, OSError) as exc:
            tmp.unlink(missing_ok=True)
            return BatchFileResult(
                src,
                dest,
                "FAILED",
                src.stat().st_size if src.exists() else 0,
                0.0,
                str(exc),
            )
        finally:
            # Roll the sidecar set back unless the ciphertext was committed.
            # Runs exactly once for every exit path: on success committed is
            # True and the new sidecars stay; on any failure (incl. an
            # unexpected exception) the pre-existing sidecars are restored
            # and newly-created orphans are removed before the result or
            # exception is delivered.
            if not committed:
                self._rollback_sidecars(_sidecar_snapshot, key_path, iv_path)

    @staticmethod
    def _rollback_sidecars(
        snapshot: dict[Path, bytes],
        key_path: Path,
        iv_path: Path,
    ) -> None:
        """Restore pre-existing sidecars and remove newly-created orphans.

        For each sidecar path, a path that was present in *snapshot* is
        restored to its original bytes; a path that was not present but
        exists (a new orphan from this operation) is removed.  Best-effort:
        it never raises, so an unexpected failure cannot mask the original
        exception.
        """
        for _sp in (key_path, iv_path):
            if _sp in snapshot:
                try:
                    _sp.write_bytes(snapshot[_sp])
                except OSError:
                    pass
            else:
                try:
                    _sp.unlink(missing_ok=True)
                except OSError:
                    pass

    def _decrypt_one(
        self,
        src: Path,
        dest: Path,
        *,
        algorithm: str,
        mode: str,
        shared_key: bytes | None,
    ) -> BatchFileResult:
        """Decrypt a single ciphertext with error isolation.

        Loads the key (and IV for CBC) through ``KeyManager``, decrypts via
        ``CipherService``, and commits the recovered plaintext with staged
        ``os.replace``.  A missing sidecar or malformed payload fails only this
        file.
        """
        tmp = dest.with_name(f".tmp_{dest.name}")
        try:
            start = time.perf_counter()

            if shared_key is not None:
                key = shared_key
                key_size = len(key) * 8
            else:
                key, key_size = KeyManager.load_key(Path(str(src) + ".key"))

            iv = KeyManager.load_iv(Path(str(src) + ".iv")) if mode == "CBC" else None

            ciphertext = FileHandler.read_bytes(src)
            plaintext = self._cipher_service.decrypt_data(
                algorithm, key_size, mode, ciphertext, key, iv
            )

            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(plaintext)
            os.replace(tmp, dest)

            elapsed = (time.perf_counter() - start) * 1000.0
            return BatchFileResult(src, dest, "SUCCESS", src.stat().st_size, elapsed, "")
        except KeyboardInterrupt:
            tmp.unlink(missing_ok=True)
            raise
        except (FileNotFoundError, PermissionError, ValueError, OSError) as exc:
            tmp.unlink(missing_ok=True)
            return BatchFileResult(
                src,
                dest,
                "FAILED",
                src.stat().st_size if src.exists() else 0,
                0.0,
                str(exc),
            )

    # ------------------------------------------------------------------
    # Result helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _skipped_result(src: Path, dest: Path) -> BatchFileResult:
        """Build a SKIPPED result for an existing-destination collision."""
        return BatchFileResult(
            src,
            dest,
            "SKIPPED",
            src.stat().st_size if src.exists() else 0,
            0.0,
            "",
        )

    @staticmethod
    def _failed_result(src: Path, dest: Path, exc: Exception) -> BatchFileResult:
        """Build a FAILED result for a per-file preparation failure."""
        return BatchFileResult(
            src,
            dest,
            "FAILED",
            src.stat().st_size if src.exists() else 0,
            0.0,
            str(exc),
        )

    @staticmethod
    def _planned_result(src: Path, dest: Path) -> BatchFileResult:
        """Build a dry-run planning result (would succeed, no writes)."""
        return BatchFileResult(
            src,
            dest,
            "SUCCESS",
            src.stat().st_size if src.exists() else 0,
            0.0,
            "",
        )

    @staticmethod
    def _build_summary(
        results: list[BatchFileResult],
        log_file: Path | None,
    ) -> BatchSummary:
        """Aggregate per-file results into a ``BatchSummary``."""
        return BatchSummary(
            total_files=len(results),
            success_count=sum(1 for r in results if r.status == "SUCCESS"),
            skipped_count=sum(1 for r in results if r.status == "SKIPPED"),
            failed_count=sum(1 for r in results if r.status == "FAILED"),
            total_bytes=sum(r.size_bytes for r in results),
            total_time_ms=round(sum(r.elapsed_ms for r in results), 3),
            results=results,
            log_file=log_file,
        )

    def _write_log(self, dest_dir: Path, results: list[BatchFileResult]) -> Path:
        """Write a ``batch_log_*.csv`` into *dest_dir* and return its path."""
        now = _utc_datetime()
        log_path = dest_dir / f"batch_log_{_file_timestamp(now)}.csv"
        dest_dir.mkdir(parents=True, exist_ok=True)
        row_ts = _iso_timestamp(now)

        with open(log_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "timestamp",
                    "source_file",
                    "dest_file",
                    "status",
                    "size_bytes",
                    "elapsed_ms",
                    "error_message",
                ]
            )
            for result in results:
                writer.writerow(
                    [
                        row_ts,
                        str(result.source_file),
                        str(result.dest_file),
                        result.status,
                        result.size_bytes,
                        result.elapsed_ms,
                        result.error_message,
                    ]
                )
        return log_path

    def _validate_policy(self, on_conflict: str) -> None:
        """Raise ``ValueError`` for an unsupported conflict policy."""
        if on_conflict not in BatchOrchestrator.VALID_CONFLICT_POLICIES:
            raise ValueError(
                f"on_conflict must be one of "
                f"{BatchOrchestrator.VALID_CONFLICT_POLICIES}, got {on_conflict!r}"
            )