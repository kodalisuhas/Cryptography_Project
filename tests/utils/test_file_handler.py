"""Unit tests for src.utils.file_handler.FileHandler."""

import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import pytest

from src.utils.file_handler import FileHandler


# ------------------------------------------------------------------
# Binary I/O
# ------------------------------------------------------------------

class TestReadWriteBytes:
    def test_read_write_bytes_roundtrip(self, tmp_path):
        data = b"\x00\x01\x02\xff" * 256
        path = tmp_path / "binary.dat"
        FileHandler.write_bytes(path, data)
        assert FileHandler.read_bytes(path) == data

    def test_read_missing_file_raises_filenotfound(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            FileHandler.read_bytes(tmp_path / "missing.bin")

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows raises PermissionError instead of IsADirectoryError for directory reads",
    )
    def test_read_directory_raises_isadirectoryerror(self, tmp_path):
        with pytest.raises(IsADirectoryError):
            FileHandler.read_bytes(tmp_path)

    def test_write_creates_parent_directories(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "file.bin"
        FileHandler.write_bytes(deep, b"hello")
        assert deep.exists()

    def test_write_bytes_overwrites_existing(self, tmp_path):
        path = tmp_path / "overwrite.bin"
        FileHandler.write_bytes(path, b"first")
        FileHandler.write_bytes(path, b"second")
        assert FileHandler.read_bytes(path) == b"second"


# ------------------------------------------------------------------
# Text I/O
# ------------------------------------------------------------------

class TestReadWriteText:
    def test_read_write_text_roundtrip(self, tmp_path):
        text = "Hello, persistence!\nLine two.\n"
        path = tmp_path / "text.txt"
        FileHandler.write_text(path, text)
        assert FileHandler.read_text(path) == text


# ------------------------------------------------------------------
# CSV / DataFrame
# ------------------------------------------------------------------

class TestDataFrameCSV:
    def test_save_dataframe_csv_creates_file(self, tmp_path):
        df = pd.DataFrame({"a": [1, 2], "b": [3.0, 4.0]})
        path = tmp_path / "out.csv"
        FileHandler.save_dataframe_csv(df, path)
        assert path.exists()

    def test_save_dataframe_csv_roundtrip(self, tmp_path):
        df = pd.DataFrame({"key": ["x", "y"], "val": [1.234567, 8.901234]})
        path = tmp_path / "roundtrip.csv"
        FileHandler.save_dataframe_csv(df, path)
        loaded = pd.read_csv(path)
        assert list(loaded.columns) == ["key", "val"]
        assert loaded.shape == (2, 2)
        assert loaded["val"].iloc[0] == pytest.approx(1.234567, abs=1e-6)


# ------------------------------------------------------------------
# Figure / PNG
# ------------------------------------------------------------------

class TestSaveFigure:
    def _make_figure(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        return fig

    def test_save_figure_creates_png(self, tmp_path):
        fig = self._make_figure()
        path = tmp_path / "graph.png"
        FileHandler.save_figure(fig, path)
        plt.close(fig)
        assert path.exists()
        magic = path.read_bytes()[:4]
        assert magic == b"\x89PNG"

    def test_save_figure_nontrivial_size(self, tmp_path):
        fig = self._make_figure()
        path = tmp_path / "graph.png"
        FileHandler.save_figure(fig, path)
        plt.close(fig)
        assert path.stat().st_size > 1024


# ------------------------------------------------------------------
# JSON
# ------------------------------------------------------------------

class TestJSON:
    def test_write_json_creates_file(self, tmp_path):
        path = tmp_path / "data.json"
        FileHandler.write_json({"a": 1}, path)
        assert path.exists()

    def test_write_json_roundtrip(self, tmp_path):
        original = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        path = tmp_path / "roundtrip.json"
        FileHandler.write_json(original, path)
        loaded = FileHandler.read_json(path)
        assert loaded == original

    def test_read_json_invalid_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json {{{")
        with pytest.raises(json.JSONDecodeError):
            FileHandler.read_json(path)


# ------------------------------------------------------------------
# exists / get_file_size / ensure_directory
# ------------------------------------------------------------------

class TestExists:
    def test_exists_true_false(self, tmp_path):
        existing = tmp_path / "exists.txt"
        existing.write_text("x")
        assert FileHandler.exists(existing) is True
        assert FileHandler.exists(tmp_path / "nope.txt") is False


class TestGetFileSize:
    def test_get_file_size_correct(self, tmp_path):
        path = tmp_path / "sized.bin"
        path.write_bytes(b"hello world")
        assert FileHandler.get_file_size(path) == 11

    def test_get_file_size_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            FileHandler.get_file_size(tmp_path / "missing.bin")


class TestEnsureDirectory:
    def test_ensure_directory_idempotent(self, tmp_path):
        d = tmp_path / "dir"
        FileHandler.ensure_directory(d)
        FileHandler.ensure_directory(d)  # second call must not raise
        assert d.is_dir()

    def test_ensure_directory_creates_parents(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c"
        FileHandler.ensure_directory(deep)
        assert deep.is_dir()


# ------------------------------------------------------------------
# Permission (cross-platform caveat)
# ------------------------------------------------------------------

class TestPermission:
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Windows permission semantics differ",
    )
    def test_permission_error_propagates(self, tmp_path):
        import os
        import stat

        path = tmp_path / "noperm.bin"
        path.write_bytes(b"data")
        os.chmod(path, stat.S_IRUSR)  # read-only
        try:
            with pytest.raises(PermissionError):
                FileHandler.write_bytes(path, b"overwritten")
        finally:
            os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
