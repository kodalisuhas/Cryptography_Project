"""
Static architectural documentation metadata for Explain Mode.

Contains descriptive metadata for visualizer nodes to educate users on the
underlying cryptographic components, contracts, timing boundaries, and mathematical
formulations without altering or redefining any cryptographic contracts.
"""

from __future__ import annotations

from typing import Any

EXPLAIN_NODES: dict[str, dict[str, Any]] = {
    "node_aes_cipher": {
        "title": "AES Core Engine",
        "module": "src.core.aes.AESCipher",
        "role": "Low-level cryptographic primitive implementing NIST FIPS 197 standard.",
        "invariants": [
            "Fixed block size of strictly 16 bytes (128 bits).",
            "Supported key lengths: 128, 192, and 256 bits.",
            "CBC mode requires a cryptographically secure 16-byte random IV.",
            "ECB mode forbids IV usage and operates on independent 16-byte blocks.",
        ],
        "timing_boundary": "PerformanceTimer strictly isolates the core encrypt/decrypt method, excluding I/O and key expansion.",
        "formula": None,
        "freeze_reference": "Frozen in V1.0 baseline release.",
    },
    "node_pkcs7": {
        "title": "PKCS#7 Padding Engine",
        "module": "src.core.padding.PKCS7",
        "role": "Applies standard block padding to align variable-length plaintexts to 16-byte boundaries.",
        "invariants": [
            "Always appends between 1 and 16 padding bytes.",
            "Pad value equals the number of padding bytes added (e.g. 0x01 or 16x 0x10).",
            "Constant-time padding removal validation prevents padding oracle vulnerabilities.",
        ],
        "timing_boundary": "Excluded from microbenchmark core timing loop.",
        "formula": "PadLength = 16 - (PlaintextLength mod 16)",
        "freeze_reference": "Frozen in V1.0 baseline release.",
    },
    "node_cipher_service": {
        "title": "Cipher Service Orchestrator",
        "module": "src.engines.cipher_service.CipherService",
        "role": "High-level coordination service for single-file and in-memory cryptographic operations.",
        "invariants": [
            "Instantiates ciphers via CipherFactory.",
            "Enforces contract separation between CBC (IV required) and ECB (no IV).",
            "Returns immutable EncryptionResult(ciphertext, iv).",
        ],
        "timing_boundary": "Wraps end-to-end operation; wall-time measured at wizard boundary.",
        "formula": None,
        "freeze_reference": "Frozen in V1.0 / V2.0 baseline releases.",
    },
    "node_metric_collector": {
        "title": "MetricCollector & Statistical Engine",
        "module": "src.analyzers.metric_collector.MetricCollector",
        "role": "Synthesizes raw microbenchmark observations into robust statistical aggregates.",
        "invariants": [
            "Sample size must equal exactly 30 observations.",
            "Warmup iterations (5 loops) are strictly excluded from statistical calculation.",
            "Sample variance uses Bessel's correction (ddof=1).",
            "Identifies empirical outliers via Tukey Interquartile Range (IQR) fences.",
        ],
        "timing_boundary": "Operates strictly post-execution on in-memory float arrays.",
        "formula": "IQR = Q3 - Q1; Lower Fence = Q1 - 1.5*IQR; Upper Fence = Q3 + 1.5*IQR",
        "freeze_reference": "Frozen in V1.0 baseline release.",
    },
    "node_performance_timer": {
        "title": "PerformanceTimer Decorator",
        "module": "src.analyzers.performance_timer.PerformanceTimer",
        "role": "Hardware-accurate timing loop wrapper using time.perf_counter().",
        "invariants": [
            "Executes 5 warmup iterations to prime instruction cache and CPU frequency.",
            "Collects exactly 30 consecutive execution timings.",
            "Runs timing loop uninterrupted without per-iteration telemetry interruptions.",
        ],
        "timing_boundary": "Strictly encloses the callable cryptographic operation only.",
        "formula": "Throughput (MB/s) = (PayloadBytes / 1048576) / (MeanTimeSeconds)",
        "freeze_reference": "Frozen in V1.0 baseline release.",
    },
    "node_security_evaluator": {
        "title": "Security & Diffusion Evaluator",
        "module": "src.analyzers.security_evaluator.SecurityEvaluator",
        "role": "Calculates cryptographic diffusion properties and visual cryptanalysis.",
        "invariants": [
            "Avalanche effect requires exactly 1-bit difference between plaintexts.",
            "Key sensitivity requires exactly 1-bit difference between cryptographic keys.",
            "Bitwise difference is computed via strict Hamming Distance across all ciphertext bits.",
            "Approximately 50% diffusion indicates strong one-bit avalanche behavior (descriptive reference).",
        ],
        "timing_boundary": "Analytical verification; not timing-benchmarked.",
        "formula": "Avalanche (%) = (HammingDistance(C1, C2) / (TotalBytes * 8)) * 100",
        "freeze_reference": "Frozen in V1.0 baseline release.",
    },
    "node_batch_orchestrator": {
        "title": "Batch Operations Orchestrator",
        "module": "src.cli_v2.batch_orchestrator.BatchOrchestrator",
        "role": "Manages batch directory discovery, collision preflight, and sequential file processing.",
        "invariants": [
            "Per-file error isolation ensures a failure in one file does not halt the batch.",
            "Atomic file replacement using temporary staging prevents partial file corruption.",
            "Reports real-time progress via progress_callback(current, total, filename).",
        ],
        "timing_boundary": "Tracks per-file elapsed milliseconds and aggregate batch duration.",
        "formula": None,
        "freeze_reference": "Frozen in V2.0 baseline release.",
    },
    "node_file_analysis_runner": {
        "title": "File-Specific Analysis Lab Runner",
        "module": "src.analysis_lab.runner.FileAnalysisRunner",
        "role": "Automated microbenchmarking matrix evaluating a single target file across all 6 AES configurations.",
        "invariants": [
            "Evaluates AES-128, AES-192, and AES-256 in both CBC and ECB modes.",
            "Ingests file into memory once to isolate storage latency from cryptographic timing.",
            "Determines fastest observed configuration without universal ranking or winner claims.",
        ],
        "timing_boundary": "Dual MetricCollector instances isolate encryption from decryption performance.",
        "formula": None,
        "freeze_reference": "Frozen in File-Specific Analysis Lab release (commit 6ce9fc0).",
    },
}
