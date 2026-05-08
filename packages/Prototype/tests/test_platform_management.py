"""
Unit tests for platform_management.py.

Covers:
- load_platforms: reads and parses the JSON
- get_platform_by_package: lookup by package name
- is_known_platform: boolean wrapper around the lookup
- get_foreground_package: parses ADB dumpsys output
- get_active_platform: ties detection + lookup together

ADB is always mocked. We never touch a real device in unit tests.
"""

import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest

import platform_management


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_platforms_data():
    """
    Minimal platforms.json content covering all currently configured platforms.

    Keep this in sync with platforms.json when adding new platforms — or
    accept that adding a platform requires a fixture update as part of the PR.
    """
    return {
        "platforms": [
            {
                "name": "Snapchat",
                "package_name": "com.snapchat.android",
                "remote_folder": "/storage/emulated/0/Android/data/com.snapchat.android/files/Camera1/",
                "photo_mode": "vcam",
                "gallery_path": None,
                "photo": {
                    "width": 1080, "height": 1920, "rotate": 90,
                    "mirror": False, "resize_mode": "fill", "filename": "1000.bmp"
                },
                "video": {
                    "width": 1080, "height": 1920, "rotate": 180,
                    "mirror": False, "resize_mode": "fill",
                    "max_duration": 60, "filename": "virtual.mp4"
                }
            },
            {
                "name": "WhatsApp",
                "package_name": "com.whatsapp",
                "remote_folder": "/storage/emulated/0/Android/data/com.whatsapp/files/Camera1/",
                "photo_mode": "gallery",
                "gallery_path": "/storage/emulated/0/DCIM/Camera/",
                "photo": {
                    "width": 4032, "height": 3024, "rotate": None,
                    "mirror": None, "resize_mode": "contain",
                    "filename": "virtual_photo.jpg"
                },
                "video": {
                    "width": 1920, "height": 1080, "rotate": None,
                    "mirror": None, "resize_mode": "contain",
                    "max_duration": 60, "filename": "virtual.mp4"
                }
            },
            {
                "name": "Discord",
                "package_name": "com.discord",
                "remote_folder": "/storage/emulated/0/Android/data/com.discord/files/Camera1/",
                "photo_mode": "gallery",
                "gallery_path": "/storage/emulated/0/DCIM/Camera/",
                "photo": {
                    "width": 4032, "height": 3024, "rotate": None,
                    "mirror": None, "resize_mode": "contain",
                    "filename": "virtual_photo.jpg"
                },
                "video": {
                    "width": 1920, "height": 1080, "rotate": None,
                    "mirror": None, "resize_mode": "contain",
                    "max_duration": 60, "filename": "virtual.mp4"
                }
            }
        ]
    }


@pytest.fixture
def platforms_file(tmp_path, sample_platforms_data):
    """Write sample platforms data to a temp file and return the path."""
    file_path = tmp_path / "platforms.json"
    file_path.write_text(json.dumps(sample_platforms_data), encoding="utf-8")
    return str(file_path)


@pytest.fixture
def patched_platforms_file(monkeypatch, platforms_file):
    """Patch get_platforms_file so load_platforms reads our fixture."""
    monkeypatch.setattr(platform_management, "get_platforms_file", lambda: platforms_file)
    return platforms_file


# ---------------------------------------------------------------------------
# load_platforms
# ---------------------------------------------------------------------------

class TestLoadPlatforms:

    def test_returns_list_of_platforms(self, patched_platforms_file):
        result = platform_management.load_platforms()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_loads_snapchat_config(self, patched_platforms_file):
        result = platform_management.load_platforms()
        snapchat = next(p for p in result if p["name"] == "Snapchat")
        assert snapchat["package_name"] == "com.snapchat.android"
        assert snapchat["photo_mode"] == "vcam"
        assert snapchat["photo"]["rotate"] == 90

    def test_loads_whatsapp_config(self, patched_platforms_file):
        result = platform_management.load_platforms()
        whatsapp = next(p for p in result if p["name"] == "WhatsApp")
        assert whatsapp["package_name"] == "com.whatsapp"
        assert whatsapp["photo_mode"] == "gallery"
        assert whatsapp["gallery_path"] == "/storage/emulated/0/DCIM/Camera/"

    def test_loads_discord_config(self, patched_platforms_file):
        result = platform_management.load_platforms()
        discord = next(p for p in result if p["name"] == "Discord")
        assert discord["package_name"] == "com.discord"
        assert discord["photo_mode"] == "gallery"
        assert discord["gallery_path"] == "/storage/emulated/0/DCIM/Camera/"

    def test_returns_empty_list_when_file_not_found(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_platforms_file", lambda: None)
        result = platform_management.load_platforms()
        assert result == []

    def test_handles_utf8_bom(self, tmp_path, monkeypatch, sample_platforms_data):
        # Windows tooling sometimes writes UTF-8 BOM; load_platforms uses utf-8-sig
        file_path = tmp_path / "platforms.json"
        file_path.write_bytes(b"\xef\xbb\xbf" + json.dumps(sample_platforms_data).encode("utf-8"))
        monkeypatch.setattr(platform_management, "get_platforms_file", lambda: str(file_path))
        result = platform_management.load_platforms()
        assert len(result) == 3


# ---------------------------------------------------------------------------
# get_platform_by_package
# ---------------------------------------------------------------------------

class TestGetPlatformByPackage:

    def test_returns_snapchat_for_snapchat_package(self, patched_platforms_file):
        result = platform_management.get_platform_by_package("com.snapchat.android")
        assert result is not None
        assert result["name"] == "Snapchat"

    def test_returns_whatsapp_for_whatsapp_package(self, patched_platforms_file):
        result = platform_management.get_platform_by_package("com.whatsapp")
        assert result is not None
        assert result["name"] == "WhatsApp"

    def test_returns_discord_for_discord_package(self, patched_platforms_file):
        result = platform_management.get_platform_by_package("com.discord")
        assert result is not None
        assert result["name"] == "Discord"

    def test_returns_none_for_unknown_package(self, patched_platforms_file):
        result = platform_management.get_platform_by_package("com.unknown.app")
        assert result is None

    def test_returns_none_for_empty_string(self, patched_platforms_file):
        result = platform_management.get_platform_by_package("")
        assert result is None

    def test_is_case_sensitive(self, patched_platforms_file):
        # Package names on Android are case-sensitive — we should not match uppercase variants
        result = platform_management.get_platform_by_package("com.Snapchat.Android")
        assert result is None


# ---------------------------------------------------------------------------
# is_known_platform
# ---------------------------------------------------------------------------

class TestIsKnownPlatform:

    def test_true_for_known_platform(self, patched_platforms_file):
        assert platform_management.is_known_platform("com.snapchat.android") is True

    def test_true_for_discord(self, patched_platforms_file):
        assert platform_management.is_known_platform("com.discord") is True

    def test_false_for_unknown_platform(self, patched_platforms_file):
        assert platform_management.is_known_platform("com.facebook.katana") is False

    def test_false_for_empty_string(self, patched_platforms_file):
        assert platform_management.is_known_platform("") is False


# ---------------------------------------------------------------------------
# get_foreground_package
# ---------------------------------------------------------------------------

class TestGetForegroundPackage:

    def _mock_adb_result(self, stdout: str, returncode: int = 0):
        mock = MagicMock()
        mock.stdout = stdout
        mock.returncode = returncode
        return mock

    def test_returns_none_when_adb_not_found(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_adb_path", lambda: None)
        assert platform_management.get_foreground_package() is None

    def test_parses_snapchat_from_dumpsys(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_adb_path", lambda: "/fake/adb")
        dumpsys_output = (
            "  ResumedActivity: ActivityRecord{abc123 u0 "
            "com.snapchat.android/.LandingPageActivity t42}\n"
        )
        with patch.object(subprocess, "run", return_value=self._mock_adb_result(dumpsys_output)):
            assert platform_management.get_foreground_package() == "com.snapchat.android"

    def test_parses_whatsapp_from_dumpsys(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_adb_path", lambda: "/fake/adb")
        dumpsys_output = (
            "  ResumedActivity: ActivityRecord{def456 u0 "
            "com.whatsapp/.HomeActivity t99}\n"
        )
        with patch.object(subprocess, "run", return_value=self._mock_adb_result(dumpsys_output)):
            assert platform_management.get_foreground_package() == "com.whatsapp"

    def test_parses_discord_from_dumpsys(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_adb_path", lambda: "/fake/adb")
        dumpsys_output = (
            "  ResumedActivity: ActivityRecord{ghi789 u0 "
            "com.discord/.main.MainActivity t55}\n"
        )
        with patch.object(subprocess, "run", return_value=self._mock_adb_result(dumpsys_output)):
            assert platform_management.get_foreground_package() == "com.discord"

    def test_returns_none_on_empty_output(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_adb_path", lambda: "/fake/adb")
        with patch.object(subprocess, "run", return_value=self._mock_adb_result("")):
            assert platform_management.get_foreground_package() is None

    def test_returns_none_when_no_resumed_activity(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_adb_path", lambda: "/fake/adb")
        output = "mDisplayId=0\n  mFocusedApp=null\n  Some other junk\n"
        with patch.object(subprocess, "run", return_value=self._mock_adb_result(output)):
            assert platform_management.get_foreground_package() is None

    def test_handles_adb_timeout(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_adb_path", lambda: "/fake/adb")
        with patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("adb", 12)):
            assert platform_management.get_foreground_package() is None

    def test_handles_adb_not_found_at_runtime(self, monkeypatch):
        monkeypatch.setattr(platform_management, "get_adb_path", lambda: "/fake/adb")
        with patch.object(subprocess, "run", side_effect=FileNotFoundError()):
            assert platform_management.get_foreground_package() is None


# ---------------------------------------------------------------------------
# get_active_platform
# ---------------------------------------------------------------------------

class TestGetActivePlatform:

    def test_returns_platform_when_foreground_is_known(self, patched_platforms_file, monkeypatch):
        monkeypatch.setattr(
            platform_management, "get_foreground_package", lambda: "com.snapchat.android"
        )
        result = platform_management.get_active_platform()
        assert result is not None
        assert result["name"] == "Snapchat"

    def test_returns_discord_when_foreground_is_discord(self, patched_platforms_file, monkeypatch):
        monkeypatch.setattr(
            platform_management, "get_foreground_package", lambda: "com.discord"
        )
        result = platform_management.get_active_platform()
        assert result is not None
        assert result["name"] == "Discord"

    def test_returns_none_when_foreground_is_unknown(self, patched_platforms_file, monkeypatch):
        monkeypatch.setattr(
            platform_management, "get_foreground_package", lambda: "com.some.random.app"
        )
        assert platform_management.get_active_platform() is None

    def test_returns_none_when_detection_fails(self, patched_platforms_file, monkeypatch):
        monkeypatch.setattr(platform_management, "get_foreground_package", lambda: None)
        assert platform_management.get_active_platform() is None