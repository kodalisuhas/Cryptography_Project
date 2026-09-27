"""
Orchestrator and execution runner for File-Specific Encryption Analysis Lab.

Coordinates:
1. Preflight file validation, streaming SHA-256 fingerprinting, and size policy enforcement.
2. In-memory microbenchmarking execution via PerformanceExperiment and SecurityExperiment.
3. Consolidated FileAnalysisResult construction.
4. Multi-tier error handling (Level B HTML assembly fallback and Level C persistence fallback).
5. Standalone report compilation via FileAnalysisReportGenerator and auto-open browser dispatch.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import sys
from typing import Any, Callable
import webbrowser

from src.analysis_lab.experiment import PerformanceExperiment
from src.analysis_lab.models import (
    ConfigurationResult,
    FileAnalysisResult,
    FileMetadata,
)
from src.analysis_lab.report import (
    FileAnalysisReportGenerator,
    ReportAssemblyError,
)
from src.analysis_lab.security_experiment import SecurityExperiment
from src.cli_v2.error_translator import ErrorTranslator
from src.utils.file_handler import FileHandler


class FileAnalysisRunner:
    """
    High-level orchestrator for file-specific cryptographic laboratory experiments.

    Coordinates preflight checks, benchmark execution, report generation, and error recovery.
    """

    WARNING_SIZE_MB = 30
    DEFAULT_CEILING_MB = 100

    def __init__(
        self,
        file_path: str | Path,
        output_path: str | Path | None = None,
        skip_decryption: bool = False,
        security_enabled: bool = False,
        max_size_mb: int = DEFAULT_CEILING_MB,
        no_open: bool = False,
        include_absolute_path: bool = False,
        no_hash: bool = False,
        force: bool = False,
        verbose: bool = False,
        file_handler: type[FileHandler] = FileHandler,
        experiment_factory: Any = PerformanceExperiment,
        security_experiment_factory: Any = SecurityExperiment,
        report_generator_factory: Any = FileAnalysisReportGenerator,
        browser_open: Callable[[str], Any] = webbrowser.open,
    ) -> None:
        self.file_path = Path(file_path)
        self.output_path = Path(output_path) if output_path is not None else None
        self.skip_decryption = skip_decryption
        self.security_enabled = security_enabled
        self.max_size_mb = max_size_mb
        self.no_open = no_open
        self.include_absolute_path = include_absolute_path
        self.no_hash = no_hash
        self.force = force
        self.verbose = verbose

        self.file_handler = file_handler
        self.experiment_factory = experiment_factory
        self.security_experiment_factory = security_experiment_factory
        self.report_generator_factory = report_generator_factory
        self.browser_open = browser_open

    @staticmethod
    def compute_sha256(path: Path, chunk_size: int = 65536) -> str:
        """Stream file contents through SHA-256 to compute a 64-char lowercase hex digest."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest().lower()

    def preflight_check(self) -> tuple[Path, int, str | None, bool]:
        """
        Validate file existence, permissions, and operational size safeguards.

        Returns:
            (resolved_path, file_size_bytes, sha256_hash, is_bmp)

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the file is not readable.
            IsADirectoryError: If the path points to a directory.
            ValueError: If file size exceeds the operational ceiling without --force.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Target file not found: {self.file_path}")

        if self.file_path.is_dir():
            raise IsADirectoryError(f"Target path is a directory, not a file: {self.file_path}")

        resolved = self.file_path.resolve()

        if not os.access(resolved, os.R_OK):
            raise PermissionError(f"Target file is not readable (permission denied): {resolved}")

        size_bytes = resolved.stat().st_size
        size_mb = size_bytes / (1024.0 * 1024.0)

        # Operational ceiling check
        if size_mb > self.max_size_mb and not self.force:
            raise ValueError(
                f"File size ({size_mb:.2f} MB) exceeds laboratory ceiling ({self.max_size_mb} MB). "
                f"The in-memory buffer lab is designed for files up to {self.max_size_mb} MB. "
                "Use --force to override if system RAM permits."
            )

        # Streaming SHA-256 fingerprinting
        sha256_hash = self.compute_sha256(resolved) if not self.no_hash else None

        # BMP signature detection
        is_bmp = False
        try:
            with open(resolved, "rb") as f:
                header = f.read(54)
                if len(header) >= 54 and header.startswith(b"BM"):
                    is_bmp = True
        except OSError:
            is_bmp = False

        return resolved, size_bytes, sha256_hash, is_bmp

    @staticmethod
    def dump_fallback_metrics(result: FileAnalysisResult, stream: Any = sys.stdout) -> None:
        """
        Dump formatted empirical benchmark metrics to terminal stream (Level B/C recovery).

        Ensures that benchmark data is never lost even if HTML assembly or disk saving fails.
        """
        lines = [
            "",
            "=" * 78,
            "FILE ANALYSIS BENCHMARK METRICS (TERMINAL FALLBACK DUMP)".center(78),
            "=" * 78,
            f"Target File : {result.file_metadata.file_name}",
            f"File Size   : {result.file_metadata.file_size_bytes:,} bytes",
            f"Timestamp   : {result.timestamp_utc}",
            "-" * 78,
            f"{'Configuration':<14} | {'Status':<7} | {'Enc Mean (ms)':<14} | {'Enc MB/s':<10} | {'Dec Mean (ms)':<14} | {'Dec MB/s':<10}",
            "-" * 78,
        ]
        for cfg in result.configurations:
            enc_m = cfg.encryption_metrics
            dec_m = cfg.decryption_metrics

            enc_mean = f"{enc_m.mean_ms:.3f}" if enc_m else "N/A"
            enc_tput = (
                f"{enc_m.throughput_mb_s:.2f}"
                if (enc_m and enc_m.throughput_mb_s is not None)
                else "N/A"
            )

            dec_mean = f"{dec_m.mean_ms:.3f}" if dec_m else "N/A"
            dec_tput = (
                f"{dec_m.throughput_mb_s:.2f}"
                if (dec_m and dec_m.throughput_mb_s is not None)
                else "N/A"
            )

            lines.append(
                f"{cfg.config_name:<14} | {cfg.status:<7} | {enc_mean:<14} | {enc_tput:<10} | {dec_mean:<14} | {dec_tput:<10}"
            )

        lines.extend([
            "-" * 78,
            f"Fastest Observed Encryption : {result.fastest_encryption_config or 'None'}",
            f"Fastest Observed Decryption : {result.fastest_decryption_config or 'N/A'}",
            "=" * 78,
            "",
        ])
        print("\n".join(lines), file=stream)

    def run(self) -> tuple[FileAnalysisResult | None, Path | None, int]:
        """
        Execute the complete laboratory analysis workflow.

        Returns:
            (result, report_path, exit_code)
            exit_code: 0 on success, 1 on failure.
        """
        # Step 1: Preflight inspection
        try:
            resolved_path, size_bytes, sha256_hash, is_bmp = self.preflight_check()
        except (OSError, ValueError) as exc:
            ErrorTranslator.display_error(exc, context="Preflight Inspection", verbose=self.verbose)
            return None, None, 1

        # Step 2: Read payload into memory
        try:
            payload = self.file_handler.read_bytes(resolved_path)
        except OSError as exc:
            ErrorTranslator.display_error(exc, context="File Ingestion", verbose=self.verbose)
            return None, None, 1

        # Step 3: Execute Performance Microbenchmarks
        perf_experiment = self.experiment_factory(
            payload=payload,
            skip_decryption=self.skip_decryption,
        )
        perf_output = perf_experiment.run()
        if isinstance(perf_output, tuple) and len(perf_output) == 3:
            perf_results, enc_collector, dec_collector = perf_output
        else:
            perf_results = perf_output
            enc_collector = getattr(perf_experiment, "encryption_collector", None)
            dec_collector = getattr(perf_experiment, "decryption_collector", None)

        # Step 4: Execute Security Diffusion Analysis (if requested)
        configurations: tuple[ConfigurationResult, ...]
        if self.security_enabled:
            sec_experiment = self.security_experiment_factory(payload=payload)
            sec_output = sec_experiment.run()

            merged = []
            if isinstance(sec_output, dict):
                for cfg in perf_results:
                    sec_m = sec_output.get(cfg.config_name)
                    merged.append(dataclasses.replace(cfg, security_metrics=sec_m))
            else:
                for cfg, sec_m in zip(perf_results, sec_output):
                    merged.append(dataclasses.replace(cfg, security_metrics=sec_m))
            configurations = tuple(merged)
        else:
            configurations = tuple(perf_results)

        # Step 5: Assemble FileMetadata and FileAnalysisResult
        try:
            display_path = str(resolved_path.relative_to(Path.cwd()))
        except ValueError:
            display_path = resolved_path.name

        meta = FileMetadata(
            file_name=resolved_path.name,
            display_path=display_path,
            absolute_path=str(resolved_path),
            file_size_bytes=size_bytes,
            sha256_hash=sha256_hash,
            is_bmp=is_bmp,
        )

        ts_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        result = FileAnalysisResult(
            file_metadata=meta,
            configurations=configurations,
            timestamp_utc=ts_utc,
            skip_decryption=self.skip_decryption,
            security_enabled=self.security_enabled,
        )

        # Step 6: Compile and Persist HTML Report
        report_generator = self.report_generator_factory(
            result=result,
            include_absolute_path=self.include_absolute_path,
            no_hash=self.no_hash,
            encryption_collector=enc_collector,
            decryption_collector=dec_collector,
            file_handler=self.file_handler,
        )

        saved_path: Path | None = None
        try:
            saved_path = report_generator.save_report(output_path=self.output_path)
        except ReportAssemblyError as exc:
            # Level B: HTML Assembly failure
            ErrorTranslator.display_error(exc, context="HTML Report Assembly", verbose=self.verbose)
            self.dump_fallback_metrics(result, stream=sys.stderr)
            return result, None, 1
        except (OSError, PermissionError) as exc:
            # Level C: Disk persistence failure
            ErrorTranslator.display_error(exc, context="Report Persistence", verbose=self.verbose)
            self.dump_fallback_metrics(result, stream=sys.stderr)
            return result, None, 1

        # Step 7: Auto-open browser dispatch
        if saved_path is not None and not self.no_open:
            try:
                self.browser_open(saved_path.resolve().as_uri())
            except Exception:
                # Browser launching failure is non-fatal
                pass

        return result, saved_path, 0
