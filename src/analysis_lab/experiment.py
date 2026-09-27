"""
Performance experiment runner for File-Specific Encryption Analysis Lab.

Executes microbenchmarks across supported AES configurations against a single target file,
collecting raw observation latencies and statistical aggregates via dual MetricCollectors.
"""

from __future__ import annotations

from typing import Any, Sequence

from src.analysis_lab.ciphertext_analyzer import CiphertextAnalyzer
from src.analysis_lab.models import (
    CiphertextMetrics,
    ConfigurationResult,
    PerformanceMetrics,
)
from src.analyzers.metric_collector import MetricCollector
from src.analyzers.performance_timer import PerformanceTimer
from src.engines.cipher_factory import CipherFactory


SUPPORTED_CONFIGURATIONS: tuple[dict[str, Any], ...] = (
    {"algorithm": "AES", "key_size": 128, "mode": "CBC"},
    {"algorithm": "AES", "key_size": 192, "mode": "CBC"},
    {"algorithm": "AES", "key_size": 256, "mode": "CBC"},
    {"algorithm": "AES", "key_size": 128, "mode": "ECB"},
    {"algorithm": "AES", "key_size": 192, "mode": "ECB"},
    {"algorithm": "AES", "key_size": 256, "mode": "ECB"},
)


class PerformanceExperiment:
    """
    In-memory microbenchmark experiment runner.

    Evaluates cryptographic configurations against a fixed in-memory byte buffer,
    strictly adhering to the frozen 5 warmup + 30 measured PerformanceTimer contract.
    """

    def __init__(
        self,
        payload: bytes,
        configurations: Sequence[dict[str, Any]] | None = None,
        skip_decryption: bool = False,
        cipher_factory: CipherFactory | None = None,
    ) -> None:
        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError(
                f"payload must be bytes or bytearray, got {type(payload).__name__}"
            )

        self.payload = bytes(payload)
        self.configurations = tuple(configurations or SUPPORTED_CONFIGURATIONS)
        self.skip_decryption = skip_decryption
        self.factory = cipher_factory or CipherFactory()

        self.encryption_collector = MetricCollector()
        self.decryption_collector = (
            MetricCollector() if not skip_decryption else None
        )

    def run(
        self,
    ) -> tuple[list[ConfigurationResult], MetricCollector, MetricCollector | None]:
        """
        Execute performance microbenchmarks across all configured ciphers.

        Returns:
            tuple of (results_list, encryption_collector, decryption_collector)
        """
        results: list[ConfigurationResult] = []
        is_zero_byte = len(self.payload) == 0

        for config_spec in self.configurations:
            algo = config_spec["algorithm"]
            key_size = config_spec["key_size"]
            mode = config_spec["mode"]

            enc_stats: dict[str, Any] | None = None
            dec_stats: dict[str, Any] | None = None
            ciphertext_metrics: CiphertextMetrics | None = None

            try:
                # Phase 1: Unmeasured Setup
                cipher = self.factory.create_cipher(algo, key_size, mode)
                key = cipher.generate_key()
                iv = cipher.generate_iv() if mode == "CBC" else None

                # Phase 2: Unmeasured Round-Trip Pre-Check
                initial_ciphertext = cipher.encrypt(self.payload, key, iv)
                decrypted_check = cipher.decrypt(initial_ciphertext, key, iv)
                if decrypted_check != self.payload:
                    raise RuntimeError(
                        "Pre-benchmark round-trip check failed: "
                        "restored plaintext did not match original input"
                    )

                # Phase 3: Ciphertext Derivation (exact length delta)
                ciphertext_metrics = CiphertextAnalyzer.analyze(
                    self.payload, initial_ciphertext
                )

                # Phase 4: Measured Encryption Microbenchmark (5 warmup + 30 measured)
                @PerformanceTimer.measure_time_with_warmup()
                def _timed_encrypt():
                    return cipher.encrypt(self.payload, key, iv)

                _, enc_stats = _timed_encrypt()

                # Phase 5: Measured Decryption Microbenchmark (Optional)
                if not self.skip_decryption:

                    @PerformanceTimer.measure_time_with_warmup()
                    def _timed_decrypt():
                        return cipher.decrypt(initial_ciphertext, key, iv)

                    _, dec_stats = _timed_decrypt()

            except (OSError, ValueError, RuntimeError) as exc:
                # Expected operational or cryptographic failure: isolate and record
                failure_result = ConfigurationResult(
                    algorithm=algo,
                    key_size=key_size,
                    mode=mode,
                    status="FAILED",
                    error_message=str(exc),
                )
                results.append(failure_result)
                continue

            # Phase 6: Ingest into MetricCollectors (OUTSIDE try/except)
            # Any schema error in assembled dict is an internal defect that must propagate!
            enc_dict = {
                "algorithm": algo,
                "key_size": key_size,
                "mode": mode,
                "data_size_bytes": len(self.payload),
                "raw_times_ms": enc_stats["raw_times_ms"],
            }
            self.encryption_collector.add_metric(enc_dict)
            enc_summary = self.encryption_collector._summary_data[-1]
            enc_metrics = self._build_performance_metrics(
                enc_summary, enc_stats["raw_times_ms"], is_zero_byte
            )

            dec_metrics: PerformanceMetrics | None = None
            if (
                dec_stats is not None
                and self.decryption_collector is not None
            ):
                dec_dict = {
                    "algorithm": algo,
                    "key_size": key_size,
                    "mode": mode,
                    "data_size_bytes": len(self.payload),
                    "raw_times_ms": dec_stats["raw_times_ms"],
                }
                self.decryption_collector.add_metric(dec_dict)
                dec_summary = self.decryption_collector._summary_data[-1]
                dec_metrics = self._build_performance_metrics(
                    dec_summary, dec_stats["raw_times_ms"], is_zero_byte
                )

            # Build successful result object
            success_result = ConfigurationResult(
                algorithm=algo,
                key_size=key_size,
                mode=mode,
                status="SUCCESS",
                encryption_metrics=enc_metrics,
                decryption_metrics=dec_metrics,
                ciphertext_metrics=ciphertext_metrics,
            )
            results.append(success_result)

        return results, self.encryption_collector, self.decryption_collector

    @staticmethod
    def _build_performance_metrics(
        summary_row: dict[str, Any],
        raw_times: list[float],
        is_zero_byte: bool,
    ) -> PerformanceMetrics:
        """Construct PerformanceMetrics model from MetricCollector summary dict."""
        throughput = (
            None if is_zero_byte else float(summary_row["throughput_mb_s"])
        )
        return PerformanceMetrics(
            sample_count=int(summary_row["count"]),
            mean_ms=float(summary_row["mean_time_ms"]),
            median_ms=float(summary_row["median_time_ms"]),
            std_dev_ms=float(summary_row["std_dev_time_ms"]),
            min_ms=float(summary_row["min_time_ms"]),
            max_ms=float(summary_row["max_time_ms"]),
            q1_ms=float(summary_row["q1_ms"]),
            q3_ms=float(summary_row["q3_ms"]),
            iqr_ms=float(summary_row["iqr_ms"]),
            outlier_count=int(summary_row["outlier_count"]),
            throughput_mb_s=throughput,
            raw_times_ms=tuple(float(t) for t in raw_times),
        )
