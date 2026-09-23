"""Tests for the V2 file picker utilities."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.cli_v2.file_picker import FilePicker


class TestCleanPath:
    """Tests for path cleaning from drag-and-drop input."""

    def test_clean_path_no_quotes(self):
        """Test path without quotes passes through unchanged."""
        result = FilePicker.clean_path("C:\\Users\\test\\file.txt")
        assert result == Path("C:\\Users\\test\\file.txt")

    def test_clean_path_double_quotes(self):
        """Test path with double quotes gets stripped."""
        result = FilePicker.clean_path('"C:\\Users\\test\\file.txt"')
        assert result == Path("C:\\Users\\test\\file.txt")

    def test_clean_path_single_quotes(self):
        """Test path with single quotes gets stripped."""
        result = FilePicker.clean_path("'C:\\Users\\test\\file.txt'")
        assert result == Path("C:\\Users\\test\\file.txt")

    def test_clean_path_whitespace(self):
        """Test surrounding whitespace gets stripped."""
        result = FilePicker.clean_path("  C:\\file.txt  ")
        assert result == Path("C:\\file.txt")

    def test_clean_path_quotes_and_whitespace(self):
        """Test both quotes and whitespace get stripped."""
        result = FilePicker.clean_path('  "C:\\file.txt"  ')
        assert result == Path("C:\\file.txt")


class TestListFiles:
    """Tests for directory listing and filtering."""

    def test_list_files_basic(self, tmp_path: Path):
        """Test basic file listing with sizes."""
        (tmp_path / "a.txt").write_text("hello")
        (tmp_path / "b.txt").write_text("world")

        files = FilePicker.list_files(tmp_path)

        assert len(files) == 2
        assert files[0][0].name == "a.txt"
        assert files[1][0].name == "b.txt"
        assert files[0][1] == 5
        assert files[1][1] == 5

    def test_list_files_sorted_alphabetically(self, tmp_path: Path):
        """Test files are sorted case-insensitively by name."""
        (tmp_path / "Zebra.txt").write_text("z")
        (tmp_path / "apple.txt").write_text("a")
        (tmp_path / "Banana.txt").write_text("b")

        files = FilePicker.list_files(tmp_path)

        assert [f[0].name for f in files] == ["apple.txt", "Banana.txt", "Zebra.txt"]

    def test_list_files_excludes_extensions(self, tmp_path: Path):
        """Test exclusion of specified extensions."""
        (tmp_path / "keep.txt").write_text("keep")
        (tmp_path / "exclude.key").write_text("secret")
        (tmp_path / "exclude.iv").write_text("vector")

        files = FilePicker.list_files(tmp_path, exclude_extensions={".key", ".iv"})

        assert len(files) == 1
        assert files[0][0].name == "keep.txt"

    def test_list_files_excludes_hidden_by_default(self, tmp_path: Path):
        """Test hidden files are excluded by default."""
        (tmp_path / "visible.txt").write_text("vis")
        (tmp_path / ".hidden").write_text("hid")

        files = FilePicker.list_files(tmp_path)

        assert len(files) == 1
        assert files[0][0].name == "visible.txt"

    def test_list_files_include_hidden_option(self, tmp_path: Path):
        """Test hidden files can be included with flag."""
        (tmp_path / "visible.txt").write_text("vis")
        (tmp_path / ".hidden").write_text("hid")

        files = FilePicker.list_files(tmp_path, include_hidden=True)

        assert len(files) == 2

    def test_list_files_excludes_os_metadata(self, tmp_path: Path):
        """Test OS metadata files are always excluded."""
        (tmp_path / "normal.txt").write_text("n")
        (tmp_path / ".DS_Store").write_text("mac")
        (tmp_path / "Thumbs.db").write_text("win")
        (tmp_path / "desktop.ini").write_text("win")

        files = FilePicker.list_files(tmp_path)

        assert len(files) == 1
        assert files[0][0].name == "normal.txt"

    def test_list_files_excludes_directories(self, tmp_path: Path):
        """Test subdirectories are not included."""
        (tmp_path / "file.txt").write_text("f")
        (tmp_path / "subdir").mkdir()

        files = FilePicker.list_files(tmp_path)

        assert len(files) == 1
        assert files[0][0].name == "file.txt"

    def test_list_files_empty_directory(self, tmp_path: Path):
        """Test empty directory returns empty list."""
        files = FilePicker.list_files(tmp_path)
        assert files == []

    def test_list_files_nonexistent_directory(self, tmp_path: Path):
        """Test nonexistent directory returns empty list."""
        files = FilePicker.list_files(tmp_path / "nonexistent")
        assert files == []

    def test_list_files_custom_pattern(self, tmp_path: Path):
        """Test custom glob pattern filtering."""
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.log").write_text("b")

        files = FilePicker.list_files(tmp_path, pattern="*.txt")

        assert len(files) == 1
        assert files[0][0].name == "a.txt"


class TestFormatSize:
    """Tests for human-readable size formatting."""

    def test_format_bytes(self):
        assert FilePicker.format_size(0) == "0 B"
        assert FilePicker.format_size(512) == "512 B"
        assert FilePicker.format_size(1023) == "1023 B"

    def test_format_kilobytes(self):
        assert FilePicker.format_size(1024) == "1.0 KB"
        assert FilePicker.format_size(1536) == "1.5 KB"
        assert FilePicker.format_size(1024 * 1024 - 1) == "1024.0 KB"

    def test_format_megabytes(self):
        assert FilePicker.format_size(1024 * 1024) == "1.0 MB"
        assert FilePicker.format_size(1024 * 1024 * 1.5) == "1.5 MB"

    def test_format_gigabytes(self):
        assert FilePicker.format_size(1024 * 1024 * 1024) == "1.0 GB"
        assert FilePicker.format_size(1024 * 1024 * 1024 * 2.5) == "2.5 GB"


class TestDisplayFileList:
    """Tests for file list display (output captured via capsys)."""

    def test_display_empty_list(self, capsys):
        """Test display of empty file list."""
        FilePicker.display_file_list([], "Test Files")
        captured = capsys.readouterr()
        assert "Test Files: (none)" in captured.out

    def test_display_files_with_sizes(self, capsys):
        """Test display shows numbered list with sizes."""
        files = [
            (Path("a.txt"), 1024),
            (Path("b.txt"), 1024 * 1024),
        ]
        FilePicker.display_file_list(files, "Available")
        captured = capsys.readouterr()
        assert "1. a.txt (1.0 KB)" in captured.out
        assert "2. b.txt (1.0 MB)" in captured.out


class TestPromptFileSelection:
    """Tests for interactive file selection prompt."""

    def test_prompt_selection_valid(self, tmp_path: Path):
        """Test valid numeric selection returns correct path."""
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")

        files = FilePicker.list_files(tmp_path)

        with patch("builtins.input", return_value="1"):
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result == tmp_path / "a.txt"

    def test_prompt_selection_custom_path(self, tmp_path: Path):
        """Test custom path entry via numeric custom option."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        # custom_option_index = len(files) + 1 = 2
        # First input: "2" to select custom option
        # Second input: "custom.txt" as the custom path
        with patch("builtins.input", side_effect=["2", "custom.txt"]):
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result == Path("custom.txt")

    def test_prompt_selection_invalid_then_valid(self, tmp_path: Path):
        """Test retry on invalid input."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        with patch("builtins.input", side_effect=["5", "abc", "1"]):
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result == tmp_path / "a.txt"

    def test_prompt_selection_cancel_eof(self, tmp_path: Path):
        """Test EOF returns None."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        with patch("builtins.input", side_effect=EOFError()):
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result is None

    def test_prompt_selection_no_files_no_custom(self, capsys):
        """Test behavior with no files and custom disabled."""
        with patch("builtins.input", return_value=""):
            result = FilePicker.prompt_file_selection([], "Select:", allow_custom=False)

        assert result is None
        captured = capsys.readouterr()
        assert "No files available" in captured.out

    def test_prompt_selection_c_token_cancels_not_custom(self, tmp_path: Path):
        """Regression: universal 'c' token cancels and never prompts for a custom path."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        with patch("builtins.input", return_value="c") as mock_input:
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result is None
        # Cancellation consumes exactly one input - no custom-path re-prompt.
        assert mock_input.call_count == 1

    def test_prompt_selection_cancel_word_cancels(self, tmp_path: Path):
        """Regression: 'cancel' cancels rather than entering custom-path mode."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        with patch("builtins.input", return_value="cancel") as mock_input:
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result is None
        assert mock_input.call_count == 1

    def test_prompt_selection_custom_keyword_enters_custom(self, tmp_path: Path):
        """Regression: 'custom' still enters custom-path mode."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        with patch("builtins.input", side_effect=["custom", "custom.txt"]):
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result == Path("custom.txt")

    def test_prompt_selection_custom_subprompt_c_cancels(self, tmp_path: Path):
        """Regression: 'c' in the custom-path subprompt cancels (numeric branch)."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        # Numeric custom option (option 2), then cancel at the subprompt.
        with patch("builtins.input", side_effect=["2", "c"]) as mocked_input:
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result is None
        # Main prompt + subprompt only; no spurious third input.
        assert mocked_input.call_count == 2

    def test_prompt_selection_custom_subprompt_cancel_cancels(self, tmp_path: Path):
        """Regression: 'cancel' in the custom-path subprompt cancels (numeric branch)."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        with patch("builtins.input", side_effect=["2", "cancel"]) as mocked_input:
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result is None
        assert mocked_input.call_count == 2

    def test_prompt_selection_custom_keyword_subprompt_c_cancels(self, tmp_path: Path):
        """Regression: 'c' in the custom-path subprompt cancels (keyword branch)."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        # "custom" keyword enters custom mode, then cancel at the subprompt.
        with patch("builtins.input", side_effect=["custom", "c"]) as mocked_input:
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result is None
        assert mocked_input.call_count == 2

    def test_prompt_selection_custom_subprompt_accepts_path(self, tmp_path: Path):
        """Regression: a real path in the subprompt is NOT cancelled (numeric branch)."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        with patch("builtins.input", side_effect=["2", "custom.txt"]):
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result == Path("custom.txt")

    def test_prompt_selection_custom_subprompt_empty_reprompts_choice(self, tmp_path: Path):
        """Behavioral lock: empty subprompt re-prompts the selection, not cancelled."""
        (tmp_path / "a.txt").write_text("a")

        files = FilePicker.list_files(tmp_path)

        # Empty custom path, then a fresh valid choice (option 1).
        with patch("builtins.input", side_effect=["2", "", "1"]) as mocked_input:
            result = FilePicker.prompt_file_selection(files, "Select:")

        assert result == (tmp_path / "a.txt")
        assert mocked_input.call_count == 3


class TestResolveInputPath:
    """Tests for input path resolution workflow."""

    def test_resolve_input_path_numeric(self, tmp_path: Path):
        """Test numeric selection from listed files."""
        (tmp_path / "input.txt").write_text("content")

        with patch("builtins.input", return_value="1"):
            result = FilePicker.resolve_input_path(tmp_path, "data/input")

        assert result == tmp_path / "input.txt"

    def test_resolve_input_path_custom(self, tmp_path: Path):
        """Test custom path entry."""
        (tmp_path / "input.txt").write_text("content")

        with patch("builtins.input", side_effect=["2", "custom.txt"]):
            result = FilePicker.resolve_input_path(tmp_path, "data/input")

        assert result == Path("custom.txt")

    def test_resolve_input_path_c_token_cancels(self, tmp_path: Path):
        """Regression: universal 'c' token propagates cancellation (KeyboardInterrupt)."""
        (tmp_path / "input.txt").write_text("content")

        with patch("builtins.input", return_value="c"):
            with pytest.raises(KeyboardInterrupt):
                FilePicker.resolve_input_path(tmp_path, "data/input")

    def test_resolve_input_path_cancel_word_cancels(self, tmp_path: Path):
        """Regression: 'cancel' token propagates cancellation (KeyboardInterrupt)."""
        (tmp_path / "input.txt").write_text("content")

        with patch("builtins.input", return_value="cancel"):
            with pytest.raises(KeyboardInterrupt):
                FilePicker.resolve_input_path(tmp_path, "data/input")

    def test_resolve_input_path_full_path_not_a_cancel(self, tmp_path: Path):
        """Regression: a real filesystem path is never treated as the 'c' token."""
        custom = f"C:\\Users\\someone\\file.txt"

        with patch("builtins.input", return_value=custom):
            result = FilePicker.resolve_input_path(tmp_path, "data/input")

        assert result == Path("C:\\Users\\someone\\file.txt")

    def test_resolve_input_path_creates_directory(self, tmp_path: Path):
        """Test that directory is created if missing."""
        new_dir = tmp_path / "new_input"
        fake_file = new_dir / "input.txt"

        # ensure_directory is mocked (does not create the dir), so list_files is
        # stubbed to report a selectable file, letting the selection loop exit.
        with patch("builtins.input", return_value="1"):
            with patch(
                "src.cli_v2.file_picker.FilePicker.list_files",
                return_value=[(fake_file, 0)],
            ):
                with patch(
                    "src.utils.file_handler.FileHandler.ensure_directory"
                ) as mock_ensure:
                    result = FilePicker.resolve_input_path(new_dir, "data/input")
                    mock_ensure.assert_called_once_with(new_dir)
                    assert result == fake_file


class TestResolveOutputPath:
    """Tests for output path resolution with conflict handling."""

    def test_resolve_output_path_new_file(self, tmp_path: Path):
        """Test new file path returned directly."""
        result = FilePicker.resolve_output_path(tmp_path, "output.enc", "data/output")
        assert result == tmp_path / "output.enc"

    def test_resolve_output_path_overwrite(self, tmp_path: Path):
        """Test overwrite choice returns existing path."""
        (tmp_path / "output.enc").write_text("existing")

        with patch("builtins.input", return_value="1"):
            result = FilePicker.resolve_output_path(tmp_path, "output.enc", "data/output")

        assert result == tmp_path / "output.enc"

    def test_resolve_output_path_new_name(self, tmp_path: Path):
        """Test entering new name returns new path."""
        (tmp_path / "output.enc").write_text("existing")

        with patch("builtins.input", side_effect=["2", "new.enc"]):
            result = FilePicker.resolve_output_path(tmp_path, "output.enc", "data/output")

        assert result == tmp_path / "new.enc"

    def test_resolve_output_path_cancel(self, tmp_path: Path):
        """Test cancel raises KeyboardInterrupt."""
        (tmp_path / "output.enc").write_text("existing")

        with patch("builtins.input", return_value="3"):
            with pytest.raises(KeyboardInterrupt):
                FilePicker.resolve_output_path(tmp_path, "output.enc", "data/output")


class TestExcludeExtensionsDefault:
    """Tests for default exclusion behavior."""

    def test_default_excludes_key_iv_log_enc(self, tmp_path: Path):
        """Test default excludes .key, .iv, .log, .enc extensions."""
        (tmp_path / "keep.txt").write_text("k")
        (tmp_path / "keyfile.key").write_text("k")
        (tmp_path / "ivfile.iv").write_text("i")
        (tmp_path / "logfile.log").write_text("l")
        (tmp_path / "encfile.enc").write_text("e")
        (tmp_path / "tmpfile.tmp").write_text("t")

        files = FilePicker.list_files(tmp_path)

        assert len(files) == 1
        assert files[0][0].name == "keep.txt"

    def test_custom_exclude_overrides_default(self, tmp_path: Path):
        """Test custom exclude set replaces default."""
        (tmp_path / "keep.txt").write_text("k")
        (tmp_path / "keyfile.key").write_text("k")

        # Only exclude .log, not .key
        files = FilePicker.list_files(tmp_path, exclude_extensions={".log"})

        assert len(files) == 2
        names = {f[0].name for f in files}
        assert names == {"keep.txt", "keyfile.key"}