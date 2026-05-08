"""
Unit tests for config_manager.py.

Covers:
- get_config_path: resolves the config file location in dev and bundled modes
- load_config: reads JSON, merges with defaults, returns defaults on error
- save_config: writes JSON to disk, returns True on success / False on failure

Tests write to tmp_path so nothing touches the real filesystem.

Note on current quirks (see chat for context, not test concerns):
- load_config catches all exceptions and returns defaults — this test file
  covers the common failure cases (missing file, malformed JSON) rather
  than every possible failure mode.
"""

import json
import os
import sys
import pytest

import config_manager


# ---------------------------------------------------------------------------
# get_config_path
# ---------------------------------------------------------------------------

class TestGetConfigPath:

    def test_returns_script_dir_path_in_dev_mode(self, monkeypatch):
        # Dev mode = sys.frozen not set. Path ends in "config.json" next to config_manager.py
        monkeypatch.delattr(sys, "frozen", raising=False)
        result = config_manager.get_config_path()
        expected_dir = os.path.dirname(os.path.abspath(config_manager.__file__))
        assert result == os.path.join(expected_dir, "config.json")

    def test_returns_exe_dir_path_when_frozen(self, monkeypatch):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", "/fake/bundle/app.exe")
        result = config_manager.get_config_path()
        assert result == os.path.join("/fake/bundle", "config.json")


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:

    def test_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        # Point config_path at a non-existent file
        fake_path = str(tmp_path / "config.json")
        monkeypatch.setattr(config_manager, "get_config_path", lambda: fake_path)

        result = config_manager.load_config()

        assert "case_root" in result
        # Default case_root is ~/SMMPI_Cases
        assert result["case_root"] == os.path.join(os.path.expanduser("~"), "SMMPI_Cases")

    def test_loads_existing_config(self, tmp_path, monkeypatch):
        fake_path = tmp_path / "config.json"
        fake_path.write_text(json.dumps({"case_root": "C:/custom/path"}))
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        result = config_manager.load_config()

        assert result["case_root"] == "C:/custom/path"

    def test_merges_defaults_into_partial_config(self, tmp_path, monkeypatch):
        # If the config is missing a key that exists in defaults, the default is filled in.
        # Right now `case_root` is the only default, so we simulate by saving an empty dict.
        fake_path = tmp_path / "config.json"
        fake_path.write_text(json.dumps({}))
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        result = config_manager.load_config()

        assert "case_root" in result
        assert result["case_root"] == os.path.join(os.path.expanduser("~"), "SMMPI_Cases")

    def test_keeps_user_value_over_default(self, tmp_path, monkeypatch):
        fake_path = tmp_path / "config.json"
        fake_path.write_text(json.dumps({"case_root": "D:/my_cases"}))
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        result = config_manager.load_config()

        assert result["case_root"] == "D:/my_cases"

    def test_preserves_extra_user_keys(self, tmp_path, monkeypatch):
        # If the user has keys in their config that aren't in defaults, they're preserved.
        fake_path = tmp_path / "config.json"
        fake_path.write_text(json.dumps({
            "case_root": "D:/my_cases",
            "future_setting": "some_value"
        }))
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        result = config_manager.load_config()

        assert result["future_setting"] == "some_value"

    def test_returns_defaults_on_malformed_json(self, tmp_path, monkeypatch):
        # load_config has a bare except — any parse error means defaults.
        fake_path = tmp_path / "config.json"
        fake_path.write_text("{not valid json")
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        result = config_manager.load_config()

        assert result["case_root"] == os.path.join(os.path.expanduser("~"), "SMMPI_Cases")


# ---------------------------------------------------------------------------
# save_config
# ---------------------------------------------------------------------------

class TestSaveConfig:

    def test_writes_config_to_disk(self, tmp_path, monkeypatch):
        fake_path = tmp_path / "config.json"
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        result = config_manager.save_config({"case_root": "C:/test"})

        assert result is True
        assert fake_path.exists()
        loaded = json.loads(fake_path.read_text())
        assert loaded == {"case_root": "C:/test"}

    def test_overwrites_existing_config(self, tmp_path, monkeypatch):
        fake_path = tmp_path / "config.json"
        fake_path.write_text(json.dumps({"case_root": "old/value"}))
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        result = config_manager.save_config({"case_root": "new/value"})

        assert result is True
        loaded = json.loads(fake_path.read_text())
        assert loaded["case_root"] == "new/value"

    def test_writes_indented_json(self, tmp_path, monkeypatch):
        # save_config uses indent=2 — readable on disk. Worth locking in so
        # a reformatter doesn't silently produce unreadable single-line files.
        fake_path = tmp_path / "config.json"
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        config_manager.save_config({"case_root": "C:/test", "other": "value"})

        content = fake_path.read_text()
        assert "\n" in content
        assert "  " in content  # 2-space indent

    def test_returns_false_on_write_failure(self, monkeypatch):
        # save_config catches exceptions and returns False instead of crashing.
        monkeypatch.setattr(
            config_manager, "get_config_path",
            lambda: "/nonexistent_dir/cannot_write/config.json"
        )

        result = config_manager.save_config({"case_root": "C:/test"})

        assert result is False


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """What gets saved comes back unchanged from load."""

    def test_save_then_load(self, tmp_path, monkeypatch):
        fake_path = tmp_path / "config.json"
        monkeypatch.setattr(config_manager, "get_config_path", lambda: str(fake_path))

        original = {"case_root": "D:/evidence", "extra_setting": 42}
        config_manager.save_config(original)
        loaded = config_manager.load_config()

        assert loaded["case_root"] == "D:/evidence"
        assert loaded["extra_setting"] == 42
