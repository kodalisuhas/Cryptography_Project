"""Presentation layer for V2 guided wizards.

Renders pure-ASCII summary cards, in-place progress tickers, structured
3-tier diagnostic boxes, and OS file-manager launchers — all without
introducing business logic, encryption, or V1 dependencies.

Security: this module only renders text supplied by the caller. It never
accesses key material, never logs or echoes secrets, and never performs
any I/O beyond writing to stdout for the progress ticker.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class Presentation:
    """Static-method formatting and display utilities for the V2 UI layer."""

    _BORDER_WIDTH = 60
    _BAR_WIDTH = 40

    @staticmethod
    def format_summary_card(
        title: str,
        fields: dict[str, Any],
        notice: str | None = None,
    ) -> str:
        """Return a bordered ASCII summary card string.

        Renders the title centered within 60-character ``=`` borders,
        followed by key/value pairs with consistent alignment.  An optional
        notice block is appended after the main fields, separated by its
        own border.  No output is printed — the raw string is returned.

        Args:
            title: Card heading rendered centered between the top borders.
            fields: Ordered mapping of label/value pairs.  Values are
                converted via ``str()`` before rendering.
            notice: Optional plaintext notice appended after the fields
                (e.g. a laboratory security reminder).  ``None`` suppresses
                the notice block entirely.

        Returns:
            The fully-formatted summary card as a single string.
        """
        border = "=" * Presentation._BORDER_WIDTH
        lines: list[str] = [
            border,
            title.center(Presentation._BORDER_WIDTH),
            border,
        ]

        for key, value in fields.items():
            lines.append(f"  {key:<16s}: {value}")

        if notice:
            lines.append(border)
            lines.append(notice)

        lines.append(border)
        return "\n".join(lines) + "\n"

    @staticmethod
    def update_progress(
        current: int,
        total: int,
        filename: str,
        status: str = "PROCESSING",
    ) -> None:
        """Render a single-line in-place progress ticker via ``sys.stdout``.

        Writes the progress line with a leading ``\\r`` so successive
        calls overwrite the same terminal line.  When ``current == total``
        the completed line is terminated with ``\\n``.

        Args:
            current: Number of items processed so far.
            total: Total number of items expected.
            filename: Basename of the file currently being processed
                (truncated if longer than 20 characters).
            status: Short status label rendered after the progress bar.
        """
        if total <= 0:
            # Graceful "no items" representation — does not claim completion.
            count_str = "---/---"
            pct_str = "---%"
            filled = 0
        else:
            safe_current = min(max(current, 0), total)
            pct = safe_current * 100 // total
            count_str = f"{current:03d}/{total:03d}"
            pct_str = f"{pct}%"
            filled = round(safe_current * Presentation._BAR_WIDTH / total)

        filled = min(max(filled, 0), Presentation._BAR_WIDTH)

        # Completed '=' fill, a single '>' head indicator at the boundary,
        # then remaining spaces.  Empty shows 40 spaces; full shows 40 '='.
        if filled <= 0:
            bar = " " * Presentation._BAR_WIDTH
        elif filled >= Presentation._BAR_WIDTH:
            bar = "=" * Presentation._BAR_WIDTH
        else:
            bar = "=" * filled + ">" + " " * (Presentation._BAR_WIDTH - filled - 1)

        # Truncate long filenames to 20 chars (17 + '...').
        short_name = filename[:17] + "..." if len(filename) > 20 else filename

        line = "\r" + (
            f"[{count_str}] ({pct_str:>4s})"
            f" [{bar}] {status}: {short_name}"
        )

        is_complete = (total > 0 and current >= total) or (
            total <= 0 and current == 0
        )

        sys.stdout.write(line + ("\n" if is_complete else ""))
        sys.stdout.flush()

    @staticmethod
    def format_diagnostic_box(
        what: str,
        why: str,
        actions: list[str],
    ) -> str:
        """Return a structured 3-tier diagnostic string.

        Renders the ``[!] Operation Failed`` header, the ``What Failed``
        and ``Probable Cause`` lines, and a numbered list of
        ``Action Steps``.  The string is returned — never printed.

        Args:
            what: Short title describing the failure.
            why: Probable cause of the failure.
            actions: Ordered list of actionable recovery steps.  An empty
                list still produces a valid diagnostic (the Action Steps
                section simply contains no numbered entries).

        Returns:
            The fully-formatted diagnostic as a single string.
        """
        divider = "-" * Presentation._BORDER_WIDTH
        lines: list[str] = [
            f"[!] Operation Failed: {what}",
            divider,
            f"What Failed    : {what}",
            f"Probable Cause : {why}",
            "Action Steps   :",
        ]

        for i, action in enumerate(actions, 1):
            lines.append(f"                {i}. {action}")

        return "\n".join(lines)

    @staticmethod
    def open_explorer(target_path: Path) -> bool:
        """Open the operating-system file manager at ``target_path``.

        Dispatches to ``os.startfile`` on Windows, ``open`` on macOS, and
        ``xdg-open`` on Linux/other POSIX.  Returns ``True`` when the
        launcher is successfully invoked, ``False`` if the target is
        invalid or the invocation fails.

        Args:
            target_path: Directory or file to reveal in the file manager.

        Returns:
            ``True`` if the file manager launch command was dispatched,
            ``False`` otherwise.
        """
        if not isinstance(target_path, Path) or not target_path.exists():
            return False

        try:
            if sys.platform == "win32":
                os.startfile(str(target_path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target_path)])
            else:
                subprocess.Popen(["xdg-open", str(target_path)])
            return True
        except Exception:
            return False
