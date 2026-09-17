"""V2 Usability Layer for Cryptography Testing Lab.

This package provides an additive usability layer on top of the frozen V1
cryptographic core, introducing guided workflows, key management, batch
operations, and standalone HTML reporting.
"""

from __future__ import annotations

__all__ = [
    "main_v2",
    "menu_v2",
    "navigation",
    "file_picker",
    "key_manager",
    "batch_orchestrator",
    "report_generator",
    "presentation",
    "error_translator",
]

__version__ = "2.0.0"