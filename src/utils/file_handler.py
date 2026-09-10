"""Thin persistence leaf: filesystem reads/writes, CSV, JSON, and figure saving.

All methods are static.  No instance state, no project-module imports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FileHandler:
    """Static-method filesystem persistence utility."""

    # ------------------------------------------------------------------
    # Binary I/O
    # ------------------------------------------------------------------

    @staticmethod
    def read_bytes(path: str | Path) -> bytes:
        """Load a binary file entirely into memory."""
        return Path(path).read_bytes()

    @staticmethod
    def write_bytes(path: str | Path, data: bytes) -> None:
        """Write binary data to disk, creating parent directories if needed."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    # ------------------------------------------------------------------
    # Text I/O
    # ------------------------------------------------------------------

    @staticmethod
    def read_text(path: str | Path, encoding: str = "utf-8") -> str:
        """Load a text file entirely into memory."""
        return Path(path).read_text(encoding=encoding)

    @staticmethod
    def write_text(path: str | Path, text: str, encoding: str = "utf-8") -> None:
        """Write text to disk, creating parent directories if needed."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding=encoding)

    # ------------------------------------------------------------------
    # Structured persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_dataframe_csv(
        df: Any, path: str | Path, *, float_format: str = "%.6f"
    ) -> None:
        """Write a pandas DataFrame to CSV via its ``.to_csv()`` method."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(p, index=False, float_format=float_format)

    @staticmethod
    def save_figure(
        fig: Any, path: str | Path, *, dpi: int = 300
    ) -> None:
        """Save a matplotlib Figure as PNG via its ``.savefig()`` method."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(p, dpi=dpi, bbox_inches="tight", format="png")

    @staticmethod
    def write_json(
        data: dict, path: str | Path, *, indent: int = 2
    ) -> None:
        """Serialize a dict to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(data, indent=indent, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def read_json(path: str | Path) -> dict:
        """Deserialize a JSON file to a dict."""
        return json.loads(Path(path).read_text(encoding="utf-8"))

    # ------------------------------------------------------------------
    # Path utilities
    # ------------------------------------------------------------------

    @staticmethod
    def exists(path: str | Path) -> bool:
        """Return ``True`` if *path* exists."""
        return Path(path).exists()

    @staticmethod
    def get_file_size(path: str | Path) -> int:
        """Return file size in bytes."""
        return Path(path).stat().st_size

    @staticmethod
    def ensure_directory(path: str | Path) -> None:
        """Create directories on demand (including parents)."""
        Path(path).mkdir(parents=True, exist_ok=True)
