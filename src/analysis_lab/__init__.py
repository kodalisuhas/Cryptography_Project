"""
Post-V2 File-Specific Encryption Analysis Lab.

Additive laboratory package providing empirical evaluation of supported encryption
configurations against individual files.
"""

from src.analysis_lab.ciphertext_analyzer import CiphertextAnalyzer
from src.analysis_lab.experiment import (
    SUPPORTED_CONFIGURATIONS,
    PerformanceExperiment,
)
from src.analysis_lab.models import (
    CiphertextMetrics,
    ConfigurationResult,
    FileAnalysisResult,
    FileMetadata,
    PerformanceMetrics,
    SecurityMetrics,
)
from src.analysis_lab.report import (
    FileAnalysisReportGenerator,
    ReportAssemblyError,
)
from src.analysis_lab.runner import FileAnalysisRunner
from src.analysis_lab.security_experiment import SecurityExperiment

__all__ = [
    "CiphertextAnalyzer",
    "CiphertextMetrics",
    "ConfigurationResult",
    "FileAnalysisReportGenerator",
    "FileAnalysisResult",
    "FileAnalysisRunner",
    "FileMetadata",
    "PerformanceExperiment",
    "PerformanceMetrics",
    "ReportAssemblyError",
    "SecurityExperiment",
    "SecurityMetrics",
    "SUPPORTED_CONFIGURATIONS",
]
