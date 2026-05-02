"""
Unit tests for utils.py.

Covers the path-resolution helpers plus debug_log.

The path-resolution functions follow the same pattern: build a list of
candidate paths, return the first one that exists. Tests mock filesystem
checks and sys.frozen / sys.executable so we don't need a real bundle.

Note on current quirks (see chat for context, not test concerns):
- debug_log duplicates get_base_path logic instead of calling it.
These tests verify current behavior, not intended behavior.
"""

import os
import sys
from unittest.mock import patch, MagicMock
import pytest

import utils


# ---------------------------------------------------------------------------
# get_base_path
# ---------------------------------------------------------------------------

class TestGetBasePath:

    def test_returns_script_dir_in_dev_mode(self, monkeypatch):
        # Dev mode = sys.frozen is not set
        monkeypatch.delattr(sys, "frozen", raising=False)
        result = utils.get_base_path()
        # In dev mode, this returns the directory of utils.py itself
        assert result == os.path.dirname(os.path.abspath(utils.__file__))

    def test_returns_exe_dir_when_frozen(self, monkeypatch):
        # Simulate PyInstaller bundle
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", "/fake/bundled/app.exe")
        result = utils.get_base_path()
        assert result == "/fake/bundled"


# ---------------------------------------------------------------------------
# Shared helper for path-resolution tests
# ---------------------------------------------------------------------------

class _PathResolutionBase:
    """
    Shared setup for testing get_platforms_file, get_adb_path,
    get_scrcpy_server_path, get_ffmpeg_path, get_ffprobe_path.

    Each subclass overrides `function_under_test` and `expected_candidates`
    to describe the behavior being checked.
    """

    FAKE_BASE = "/fake/base"

    @pytest.fixture(autouse=True)
    def _fake_base_path(self, monkeypatch):
        monkeypatch.setattr(utils, "get_base_path", lambda: self.FAKE_BASE)


# ---------------------------------------------------------------------------
# get_platforms_file
# ---------------------------------------------------------------------------

class TestGetPlatformsFile(_PathResolutionBase):

    def test_finds_file_in_base_path(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "platforms.json")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        assert utils.get_platforms_file() == expected

    def test_finds_file_in_internal_folder_when_base_missing(self, monkeypatch):
        # Simulate a PyInstaller layout where the file lives under _internal/
        expected = os.path.join(self.FAKE_BASE, "_internal", "platforms.json")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        assert utils.get_platforms_file() == expected

    def test_finds_file_next_to_utils_when_other_paths_missing(self, monkeypatch):
        # Third candidate: next to utils.py itself
        utils_dir = os.path.dirname(os.path.abspath(utils.__file__))
        expected = os.path.join(utils_dir, "platforms.json")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        assert utils.get_platforms_file() == expected

    def test_returns_none_when_no_candidate_exists(self, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        assert utils.get_platforms_file() is None

    def test_prefers_base_path_over_internal(self, monkeypatch):
        # When both exist, the first candidate (base path) wins
        base_path = os.path.join(self.FAKE_BASE, "platforms.json")
        internal_path = os.path.join(self.FAKE_BASE, "_internal", "platforms.json")
        monkeypatch.setattr(os.path, "exists", lambda p: p in (base_path, internal_path))
        assert utils.get_platforms_file() == base_path


# ---------------------------------------------------------------------------
# get_adb_path
# ---------------------------------------------------------------------------

class TestGetAdbPath(_PathResolutionBase):

    def test_finds_bundled_adb_in_base_path(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "platform-tools", "adb.exe")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_adb_path() == expected

    def test_finds_bundled_adb_in_internal_folder(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "_internal", "platform-tools", "adb.exe")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_adb_path() == expected

    def test_falls_back_to_path_adb(self, monkeypatch):
        path_adb = "/usr/bin/adb"
        # Only the PATH-resolved adb exists
        monkeypatch.setattr(os.path, "exists", lambda p: p == path_adb)
        monkeypatch.setattr(utils.shutil, "which", lambda name: path_adb if name == "adb" else None)
        assert utils.get_adb_path() == path_adb

    def test_returns_none_when_nothing_found(self, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_adb_path() is None

    def test_handles_shutil_which_returning_none(self, monkeypatch):
        # Regression check: the None from shutil.which must not crash os.path.exists
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        # The `path and os.path.exists(path)` short-circuit in utils.py protects us here.
        assert utils.get_adb_path() is None


# ---------------------------------------------------------------------------
# get_scrcpy_server_path
# ---------------------------------------------------------------------------

class TestGetScrcpyServerPath(_PathResolutionBase):

    def test_finds_scrcpy_server_in_base_path(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "scrcpy-server-v3.3.4")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        assert utils.get_scrcpy_server_path() == expected

    def test_finds_scrcpy_server_in_internal_folder(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "_internal", "scrcpy-server-v3.3.4")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        assert utils.get_scrcpy_server_path() == expected

    def test_returns_none_when_not_found(self, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        assert utils.get_scrcpy_server_path() is None


# ---------------------------------------------------------------------------
# get_ffmpeg_path
# ---------------------------------------------------------------------------

class TestGetFfmpegPath(_PathResolutionBase):

    def test_finds_bundled_ffmpeg(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "ffmpeg", "ffmpeg.exe")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_ffmpeg_path() == expected

    def test_finds_bundled_ffmpeg_in_internal_folder(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "_internal", "ffmpeg", "ffmpeg.exe")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_ffmpeg_path() == expected

    def test_falls_back_to_path_ffmpeg(self, monkeypatch):
        path_ffmpeg = "/usr/bin/ffmpeg"
        monkeypatch.setattr(os.path, "exists", lambda p: p == path_ffmpeg)
        monkeypatch.setattr(utils.shutil, "which", lambda name: path_ffmpeg if name == "ffmpeg" else None)
        assert utils.get_ffmpeg_path() == path_ffmpeg

    def test_returns_none_when_nothing_found(self, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_ffmpeg_path() is None


# ---------------------------------------------------------------------------
# get_ffprobe_path
# ---------------------------------------------------------------------------

class TestGetFfprobePath(_PathResolutionBase):

    def test_finds_bundled_ffprobe(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "ffmpeg", "ffprobe.exe")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_ffprobe_path() == expected

    def test_finds_bundled_ffprobe_in_internal_folder(self, monkeypatch):
        expected = os.path.join(self.FAKE_BASE, "_internal", "ffmpeg", "ffprobe.exe")
        monkeypatch.setattr(os.path, "exists", lambda p: p == expected)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_ffprobe_path() == expected

    def test_falls_back_to_path_ffprobe(self, monkeypatch):
        path_ffprobe = "/usr/bin/ffprobe"
        monkeypatch.setattr(os.path, "exists", lambda p: p == path_ffprobe)
        monkeypatch.setattr(utils.shutil, "which", lambda name: path_ffprobe if name == "ffprobe" else None)
        assert utils.get_ffprobe_path() == path_ffprobe

    def test_returns_none_when_nothing_found(self, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        monkeypatch.setattr(utils.shutil, "which", lambda name: None)
        assert utils.get_ffprobe_path() is None


# ---------------------------------------------------------------------------
# debug_log
# ---------------------------------------------------------------------------

class TestDebugLog:

    def test_writes_message_to_log_file(self, tmp_path, monkeypatch):
        # Point __file__ resolution at our tmp_path by patching sys.frozen off
        # and monkeypatching the module-level __file__ attribute indirectly
        # via os.path.abspath on the import path.
        monkeypatch.delattr(sys, "frozen", raising=False)

        # Simplest way to control where debug_log writes: patch os.path
        # calls that debug_log uses to locate the log file.
        fake_base = str(tmp_path)
        monkeypatch.setattr(os.path, "dirname", lambda p: fake_base)

        utils.debug_log("hello test")

        log_path = tmp_path / "debug_log.txt"
        assert log_path.exists()
        assert "hello test" in log_path.read_text(encoding="utf-8")

    def test_appends_on_second_call(self, tmp_path, monkeypatch):
        monkeypatch.delattr(sys, "frozen", raising=False)
        fake_base = str(tmp_path)
        monkeypatch.setattr(os.path, "dirname", lambda p: fake_base)

        utils.debug_log("first line")
        utils.debug_log("second line")

        log_path = tmp_path / "debug_log.txt"
        content = log_path.read_text(encoding="utf-8")
        assert "first line" in content
        assert "second line" in content

    def test_swallows_exceptions_silently(self, monkeypatch):
        # debug_log wraps everything in try/except — if writing fails, it must not raise.
        # We force an error by making open() raise.
        def _boom(*args, **kwargs):
            raise PermissionError("no write for you")
        monkeypatch.setattr("builtins.open", _boom)

        # Should not raise
        utils.debug_log("this will fail to write")

    def test_uses_exe_dir_when_frozen(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", str(tmp_path / "app.exe"))

        utils.debug_log("frozen mode")

        log_path = tmp_path / "debug_log.txt"
        assert log_path.exists()
        assert "frozen mode" in log_path.read_text(encoding="utf-8")