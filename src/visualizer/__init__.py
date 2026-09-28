"""
Live Cryptography Workflow Visualizer Package.

Provides a decoupled, zero-dependency presentation and telemetry layer for the
Cryptography Testing Lab, exposing real-time execution events from the frozen
V1 and V2 backends to an interactive, air-gapped web interface.
"""

from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["VisualizerServer", "TelemetryBridge"]

from src.visualizer.server import VisualizerServer
from src.visualizer.telemetry_bridge import TelemetryBridge
