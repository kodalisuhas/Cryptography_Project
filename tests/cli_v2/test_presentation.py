"""Tests for the V2 presentation layer.

Behavioral coverage for summary cards, progress tickers, diagnostic
boxes, and OS file-manager launchers — all verified through capsys,
monkeypatch, and mock without invoking any real OS launcher.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.cli_v2.presentation import Presentation


# ── Summary card tests ───────────────────────────────────────────────────────

class TestFormatSummaryCard:
    """Summary card rendering behavior."""

    def test_title_appears(self):
        """The card title appears in the output."""
        card = Presentation.format_summary_card("Encrypt Complete", {})
        assert "Encrypt Complete" in card

    def test_field_appears(self):
        """A single field key-value pair appears in the output."""
        card = Presentation.format_summary_card("Title", {"Mode": "CBC"})
        assert "Mode" in card
        assert "CBC" in card

    def test_multiple_fields(self):
        """All fields appear in order with their values."""
        fields = {"Mode": "CBC", "Size": "256", "Status": "OK"}
        card = Presentation.format_summary_card("T", fields)
        assert "Mode" in card and "CBC" in card
        assert "Size" in card and "256" in card
        assert "Status" in card and "OK" in card
        keys = list(fields.keys())
        for i in range(len(keys) - 1):
            assert card.index(keys[i]) < card.index(keys[i + 1])

    def test_border_is_60_chars(self):
        """The top border is exactly 60 '=' characters."""
        card = Presentation.format_summary_card("T", {})
        top_line = card.split("\n")[0]
        assert top_line == "=" * 60

    def test_all_borders_are_60_chars(self):
        """Every border line in the card is exactly 60 '=' characters."""
        card = Presentation.format_summary_card("T", {})
        for line in card.split("\n"):
            stripped = line.strip()
            if stripped and all(c == "=" for c in stripped):
                assert len(stripped) == 60

    def test_title_centered(self):
        """The title line is centered within the 60-char border."""
        card = Presentation.format_summary_card("Test", {})
        title_line = card.split("\n")[1]
        assert title_line == "Test".center(60)

    def test_field_alignment(self):
        """Field keys are left-aligned in a 16-char column."""
        card = Presentation.format_summary_card("T", {"Key": "Val"})
        field_line = [l for l in card.split("\n") if "Key" in l][0]
        # Field line format: "  Key             : Val"
        assert field_line.startswith("  Key")
        assert ": Val" in field_line

    def test_value_converted_to_string(self):
        """Non-string values are rendered as their str() representation."""
        card = Presentation.format_summary_card("T", {"Num": 42, "Flag": True})
        assert "42" in card
        assert "True" in card

    def test_empty_fields(self):
        """An empty fields dict still produces a valid card."""
        card = Presentation.format_summary_card("Empty", {})
        assert "=" * 60 in card
        assert "Empty" in card
        # No field lines (other than borders and title)
        field_lines = [
            l for l in card.split("\n")
            if l.strip() and not all(c == "=" for c in l.strip())
            and l.strip() != "Empty"
        ]
        assert field_lines == []

    def test_notice_present(self):
        """A notice string appears in the card after the field section."""
        card = Presentation.format_summary_card("T", {}, notice="Lab notice")
        assert "Lab notice" in card
        # Notice is between two border lines
        lines = card.split("\n")
        notice_idx = next(i for i, l in enumerate(lines) if "Lab notice" in l)
        # Line above is a border
        above = lines[notice_idx - 1]
        assert all(c == "=" for c in above.strip()) if above.strip() else True
        # Line below is a border
        below = lines[notice_idx + 1]
        assert all(c == "=" for c in below.strip()) if below.strip() else True

    def test_notice_absent(self):
        """When notice is None, no notice block appears."""
        card = Presentation.format_summary_card("T", {}, notice=None)
        lines = card.split("\n")
        # Three borders with no notice: top, post-title, bottom.
        border_count = sum(
            1 for l in lines
            if l.strip() and all(c == "=" for c in l.strip())
        )
        assert border_count == 3
        # No standalone notice text (nothing between the post-title and bottom borders).
        content = [
            l.strip() for l in lines
            if l.strip() and not all(c == "=" for c in l.strip())
        ]
        assert content == ["T"]

    def test_special_character_values(self):
        """Values with special characters are rendered without corruption."""
        special = "hello world! @#$%^&*()"
        card = Presentation.format_summary_card("T", {"V": special})
        assert special in card

    def test_no_printing(self):
        """format_summary_card does not print anything to stdout/stderr."""
        with patch("builtins.print") as mock_print:
            Presentation.format_summary_card("T", {"K": "V"})
            mock_print.assert_not_called()

    def test_returns_string(self, capsys):
        """The returned value is a complete string, not None."""
        card = Presentation.format_summary_card("Title", {"A": "1"})
        assert isinstance(card, str)
        captured = capsys.readouterr()
        assert captured.out == ""


# ── Progress ticker tests ───────────────────────────────────────────────────

class TestUpdateProgress:
    """Progress ticker rendering behavior."""

    def test_starts_with_carriage_return(self, capsys):
        """Incomplete progress output begins with \\r."""
        Presentation.update_progress(5, 10, "file.txt")
        out = capsys.readouterr().out
        assert out.startswith("\r")

    def test_counter_format(self, capsys):
        """Progress counter is formatted as zero-padded [NNN/NNN]."""
        Presentation.update_progress(42, 150, "file.txt")
        out = capsys.readouterr().out
        assert "[042/150]" in out

    def test_percentage(self, capsys):
        """Percentage is displayed for the current progress."""
        Presentation.update_progress(50, 100, "file.txt")
        out = capsys.readouterr().out
        assert "50%" in out

    def test_status_appears(self, capsys):
        """The status value renders as the colon label before the filename."""
        Presentation.update_progress(1, 10, "file.txt", status="ACTIVE")
        out = capsys.readouterr().out
        assert "ACTIVE: file.txt" in out

    def test_default_status(self, capsys):
        """The default status label is PROCESSING."""
        Presentation.update_progress(1, 10, "file.txt")
        out = capsys.readouterr().out
        assert "PROCESSING: file.txt" in out

    def test_filename_appears(self, capsys):
        """The filename appears in the status portion."""
        Presentation.update_progress(1, 10, "data.csv")
        out = capsys.readouterr().out
        assert "data.csv" in out

    def test_long_filename_truncated(self, capsys):
        """A filename longer than 20 chars is truncated."""
        long_name = "a" * 25 + ".txt"
        Presentation.update_progress(1, 10, long_name)
        out = capsys.readouterr().out
        # The filename should be truncated, so the original full name must not appear
        assert long_name not in out
        # Truncated form ends with '...'
        assert "..." in out

    def test_total_zero_no_division_error(self, capsys):
        """total == 0 is callable without ZeroDivisionError."""
        Presentation.update_progress(0, 0, "file.txt")
        out = capsys.readouterr().out  # no exception raised

    def test_total_zero_renders_dashes(self, capsys):
        """total == 0 renders ---/--- and ---%, never claiming 100%."""
        Presentation.update_progress(0, 0, "file.txt")
        out = capsys.readouterr().out
        assert "---/---" in out
        assert "---%" in out
        assert "100%" not in out

    def test_completed_ends_with_newline(self, capsys):
        """When current == total the completed line ends with \\n."""
        Presentation.update_progress(10, 10, "done.txt")
        out = capsys.readouterr().out
        assert out.endswith("\n")

    def test_incomplete_no_newline(self, capsys):
        """When current < total the line does NOT end with \\n."""
        Presentation.update_progress(5, 10, "file.txt")
        out = capsys.readouterr().out
        assert not out.endswith("\n")

    def test_progress_bar_is_40_chars(self, capsys):
        """The progress bar between brackets is exactly 40 characters."""
        Presentation.update_progress(3, 10, "f")
        out = capsys.readouterr().out
        # Split off the counter section, then extract the bar between '[' and ']'.
        bar_section = out.split("]")[1]
        bar_content = bar_section.split("[")[1].split("]")[0]
        assert len(bar_content) == 40

    def test_bar_half_filled(self, capsys):
        """At 50%: 20 '=' fill, one '>' head indicator, 19 remaining spaces."""
        Presentation.update_progress(50, 100, "f")
        out = capsys.readouterr().out
        # Extract bar content between the bar brackets
        parts = out.split("]")[1:]  # after counter
        bar_section = parts[0]  # this contains " [bar..."
        bar_content = bar_section.split("[")[1].split("]")[0]
        assert len(bar_content) == 40
        assert bar_content.count("=") == 20
        assert bar_content.count(">") == 1
        assert bar_content.count(" ") == 19
        assert bar_content == "=" * 20 + ">" + " " * 19

    def test_bar_empty_at_zero(self, capsys):
        """At 0% the bar is 40 spaces (no completed portion)."""
        Presentation.update_progress(0, 10, "f")
        out = capsys.readouterr().out
        parts = out.split("]")[1:]
        bar_section = parts[0]
        bar_content = bar_section.split("[")[1].split("]")[0]
        assert bar_content == " " * 40

    def test_bar_partial_uses_head_indicator(self, capsys):
        """A partial fill shows '=' completed, a '>' head, then spaces."""
        Presentation.update_progress(1, 4, "f")  # 25% -> 10 filled
        out = capsys.readouterr().out
        parts = out.split("]")[1:]
        bar_section = parts[0]
        bar_content = bar_section.split("[")[1].split("]")[0]
        assert bar_content == "=" * 10 + ">" + " " * 29

    def test_bar_full_at_completion(self, capsys):
        """At 100% the bar is exactly 40 '=' characters."""
        Presentation.update_progress(100, 100, "f")
        out = capsys.readouterr().out
        parts = out.split("]")[1:]
        bar_section = parts[0]
        bar_content = bar_section.split("[")[1].split("]")[0]
        assert bar_content == "=" * 40

    def test_ascii_only(self, capsys):
        """All output characters are pure ASCII."""
        Presentation.update_progress(1, 10, "file.txt")
        out = capsys.readouterr().out
        out.encode("ascii")  # raises UnicodeEncodeError if non-ASCII

    def test_stdout_flush_called(self, capsys):
        """sys.stdout.flush() is called after writing."""
        with patch("sys.stdout") as mock_stdout:
            Presentation.update_progress(1, 10, "f.txt")
            mock_stdout.write.assert_called_once()
            mock_stdout.flush.assert_called_once()

    def test_no_stderr_output(self, capsys):
        """No output is written to stderr."""
        Presentation.update_progress(5, 10, "file.txt")
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_returns_none(self, capsys):
        """update_progress returns None."""
        result = Presentation.update_progress(1, 10, "f")
        assert result is None


# ── Diagnostic box tests ─────────────────────────────────────────────────────

class TestFormatDiagnosticBox:
    """Diagnostic box rendering behavior."""

    def test_header(self):
        """The header line contains [!] Operation Failed."""
        box = Presentation.format_diagnostic_box("Bad", "reason", [])
        assert "[!] Operation Failed: Bad" in box

    def test_what_failed(self):
        """The What Failed line is present with the correct value."""
        box = Presentation.format_diagnostic_box("X", "Y", [])
        assert "What Failed    : X" in box

    def test_probable_cause(self):
        """The Probable Cause line is present with the correct value."""
        box = Presentation.format_diagnostic_box("X", "because", [])
        assert "Probable Cause : because" in box

    def test_action_steps_header(self):
        """The Action Steps line is present."""
        box = Presentation.format_diagnostic_box("X", "Y", ["do A"])
        assert "Action Steps   :" in box

    def test_numbered_actions(self):
        """Actions are numbered starting from 1."""
        box = Presentation.format_diagnostic_box("X", "Y", ["Fix this", "Check that"])
        assert "1. Fix this" in box
        assert "2. Check that" in box

    def test_multiple_actions(self):
        """Three actions appear in order with correct numbering."""
        actions = ["Step one", "Step two", "Step three"]
        box = Presentation.format_diagnostic_box("X", "Y", actions)
        for i, a in enumerate(actions, 1):
            assert f"{i}. {a}" in box
        # Actions are in order
        for i in range(len(actions) - 1):
            assert box.index(f"{i+1}.") < box.index(f"{i+2}.")

    def test_empty_actions(self):
        """An empty action list produces a valid box with no numbered steps."""
        box = Presentation.format_diagnostic_box("X", "Y", [])
        assert "Action Steps   :" in box
        # No lines that look like numbered steps
        step_lines = [l for l in box.split("\n") if "1." in l.split(":")[-1]]
        # More reliably: the Action Steps line is the last line
        lines = box.strip().split("\n")
        assert lines[-1].strip() == "Action Steps   :"

    def test_divider_is_60_chars(self):
        """The divider line is exactly 60 '-' characters."""
        box = Presentation.format_diagnostic_box("X", "Y", [])
        lines = box.split("\n")
        divider = lines[1]
        assert divider == "-" * 60

    def test_no_printing(self):
        """format_diagnostic_box returns a string without printing."""
        with patch("builtins.print") as mock_print:
            result = Presentation.format_diagnostic_box("W", "C", ["A"])
            mock_print.assert_not_called()
            assert isinstance(result, str)

    def test_no_stderr_output(self, capsys):
        """No output is written to stderr."""
        Presentation.format_diagnostic_box("W", "C", ["A"])
        captured = capsys.readouterr()
        assert captured.err == ""


# ── Explorer tests ───────────────────────────────────────────────────────────

class TestOpenExplorer:
    """OS file-manager launcher behavior."""

    def test_nonexistent_target_returns_false(self, tmp_path):
        """A nonexistent path returns False."""
        assert Presentation.open_explorer(tmp_path / "nope") is False

    def test_invalid_path_returns_false(self):
        """A non-Path or deeply invalid path returns False."""
        assert Presentation.open_explorer(Path("/nonexistent/fake/path")) is False

    def test_valid_directory_success(self, tmp_path):
        """A valid existing path on Windows returns True (mocked os.startfile)."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch("sys.platform", "win32"):
            with patch("os.startfile") as mock_sf:
                result = Presentation.open_explorer(subdir)
                assert result is True
                mock_sf.assert_called_once_with(str(subdir))

    def test_windows_failure_returns_false(self, tmp_path):
        """When os.startfile raises, open_explorer returns False."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch("sys.platform", "win32"):
            with patch("os.startfile", side_effect=OSError("denied")):
                result = Presentation.open_explorer(subdir)
                assert result is False

    def test_macos_subprocess_called(self, tmp_path):
        """On macOS subprocess.Popen(['open', ...]) is called."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch("sys.platform", "darwin"):
            with patch("subprocess.Popen") as mock_popen:
                result = Presentation.open_explorer(subdir)
                assert result is True
                mock_popen.assert_called_once_with(["open", str(subdir)])

    def test_linux_subprocess_called(self, tmp_path):
        """On Linux subprocess.Popen(['xdg-open', ...]) is called."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch("sys.platform", "linux"):
            with patch("subprocess.Popen") as mock_popen:
                result = Presentation.open_explorer(subdir)
                assert result is True
                mock_popen.assert_called_once_with(["xdg-open", str(subdir)])

    def test_subprocess_failure_returns_false(self, tmp_path):
        """When subprocess.Popen raises, open_explorer returns False."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch("sys.platform", "linux"):
            with patch("subprocess.Popen", side_effect=FileNotFoundError("no")):
                result = Presentation.open_explorer(subdir)
                assert result is False

    def test_no_output(self, tmp_path, capsys):
        """open_explorer produces no stdout/stderr output."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch("sys.platform", "win32"):
            with patch("os.startfile"):
                Presentation.open_explorer(subdir)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_returns_boolean(self, tmp_path):
        """Return value is always a bool."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        with patch("sys.platform", "win32"):
            with patch("os.startfile"):
                result = Presentation.open_explorer(subdir)
                assert isinstance(result, bool)
