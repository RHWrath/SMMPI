"""
Config contract tests.

Verifies that platforms.json is internally consistent and that every value
in it is one the code actually knows how to handle. These tests catch drift
between platforms.json and the code that reads it - the kind of bug that
surfaces only at runtime on a real device, after a long ADB push cycle.

Run with: python -m pytest tests/test_platforms_config.py -v
"""

# stdlib
import json
import os

# third-party
import pytest

# internal
from platform_management import (
    load_platforms,
    get_platform_by_package,
    is_known_platform,
)
from utils import get_platforms_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Values the code currently handles. If a new photo_mode is added to
# platforms.json without updating the code, this set must be updated too -
# which is exactly the drift these tests are designed to catch.
KNOWN_PHOTO_MODES = {"vcam", "gallery"}
KNOWN_RESIZE_MODES = {"fill", "contain"}

REQUIRED_TOP_LEVEL_KEYS = {
    "name",
    "package_name",
    "remote_folder",
    "photo_mode",
    "gallery_path",
    "photo",
    "video",
}

REQUIRED_PHOTO_KEYS = {
    "width",
    "height",
    "rotate",
    "mirror",
    "resize_mode",
    "filename",
}

REQUIRED_VIDEO_KEYS = REQUIRED_PHOTO_KEYS | {"max_duration"}


@pytest.fixture(scope="module")
def platforms():
    """Load platforms once for the whole module."""
    result = load_platforms()
    assert result, "load_platforms() returned empty - platforms.json missing or malformed"
    return result


# ---------------------------------------------------------------------------
# Structural integrity
# ---------------------------------------------------------------------------

def test_platforms_file_exists():
    """platforms.json must be findable via the utils helper."""
    path = get_platforms_file()
    assert path is not None, "get_platforms_file() returned None"
    assert os.path.exists(path), f"platforms.json not found at {path}"


def test_platforms_file_is_valid_json():
    """File must parse as JSON with a top-level 'platforms' list."""
    path = get_platforms_file()
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    assert "platforms" in data, "Top-level 'platforms' key missing"
    assert isinstance(data["platforms"], list), "'platforms' is not a list"
    assert len(data["platforms"]) > 0, "platforms list is empty"


def test_every_platform_has_required_top_level_keys(platforms):
    """Each platform entry must have the full set of expected keys."""
    for p in platforms:
        missing = REQUIRED_TOP_LEVEL_KEYS - set(p.keys())
        assert not missing, f"Platform {p.get('name', '?')} missing keys: {missing}"


def test_every_platform_has_required_photo_keys(platforms):
    for p in platforms:
        missing = REQUIRED_PHOTO_KEYS - set(p["photo"].keys())
        assert not missing, f"{p['name']} photo block missing: {missing}"


def test_every_platform_has_required_video_keys(platforms):
    for p in platforms:
        missing = REQUIRED_VIDEO_KEYS - set(p["video"].keys())
        assert not missing, f"{p['name']} video block missing: {missing}"


# ---------------------------------------------------------------------------
# Uniqueness
# ---------------------------------------------------------------------------

def test_package_names_are_unique(platforms):
    """
    Duplicate package names cause get_platform_by_package() to silently
    return only the first match, dropping the rest. This bug is invisible
    until the wrong platform handler runs.
    """
    package_names = [p["package_name"] for p in platforms]
    duplicates = {n for n in package_names if package_names.count(n) > 1}
    assert not duplicates, f"Duplicate package_name values: {duplicates}"


def test_platform_names_are_unique(platforms):
    """Display names must be unique to avoid UI confusion in the case selector."""
    names = [p["name"] for p in platforms]
    duplicates = {n for n in names if names.count(n) > 1}
    assert not duplicates, f"Duplicate platform names: {duplicates}"


# ---------------------------------------------------------------------------
# Code-config alignment (the drift catchers)
# ---------------------------------------------------------------------------

def test_every_photo_mode_is_one_the_code_handles(platforms):
    """
    If platforms.json declares photo_mode='instagram_story' but no code
    branch handles that, recording silently does nothing. Catch it here.
    """
    for p in platforms:
        mode = p["photo_mode"]
        assert mode in KNOWN_PHOTO_MODES, (
            f"{p['name']} declares photo_mode='{mode}' but code only handles "
            f"{KNOWN_PHOTO_MODES}. Either add a handler or fix the config."
        )


def test_every_resize_mode_is_one_the_code_handles(platforms):
    for p in platforms:
        for block_name in ("photo", "video"):
            mode = p[block_name]["resize_mode"]
            assert mode in KNOWN_RESIZE_MODES, (
                f"{p['name']} {block_name} resize_mode='{mode}' not in "
                f"{KNOWN_RESIZE_MODES}"
            )


def test_gallery_mode_requires_gallery_path(platforms):
    """photo_mode=gallery without gallery_path means the push has no destination."""
    for p in platforms:
        if p["photo_mode"] == "gallery":
            assert p["gallery_path"], (
                f"{p['name']} uses photo_mode=gallery but gallery_path is "
                f"null/empty - the gallery push will fail at runtime."
            )


def test_vcam_mode_uses_remote_folder(platforms):
    """photo_mode=vcam pushes to remote_folder (the VCAM watch path)."""
    for p in platforms:
        if p["photo_mode"] == "vcam":
            assert p["remote_folder"], (
                f"{p['name']} uses photo_mode=vcam but remote_folder is empty."
            )


# ---------------------------------------------------------------------------
# Behavioral checks against the lookup functions
# ---------------------------------------------------------------------------

def test_get_platform_by_package_resolves_every_configured_platform(platforms):
    """Every package_name in the config must resolve back to itself."""
    for p in platforms:
        resolved = get_platform_by_package(p["package_name"])
        assert resolved is not None, f"Lookup failed for {p['package_name']}"
        assert resolved["name"] == p["name"]


def test_get_platform_by_package_returns_none_for_unknown():
    """Unknown packages return None - no exception, no false match."""
    assert get_platform_by_package("com.nonexistent.app") is None
    assert get_platform_by_package("") is None


def test_is_known_platform_matches_lookup_behavior(platforms):
    """is_known_platform must agree with get_platform_by_package."""
    for p in platforms:
        assert is_known_platform(p["package_name"]) is True
    assert is_known_platform("com.nonexistent.app") is False


# ---------------------------------------------------------------------------
# Reasonable-bounds checks
# ---------------------------------------------------------------------------

def test_photo_dimensions_are_positive(platforms):
    for p in platforms:
        assert p["photo"]["width"] > 0
        assert p["photo"]["height"] > 0


def test_video_dimensions_are_positive(platforms):
    for p in platforms:
        assert p["video"]["width"] > 0
        assert p["video"]["height"] > 0


def test_video_max_duration_is_positive(platforms):
    """max_duration <= 0 would skip recording entirely on some code paths."""
    for p in platforms:
        assert p["video"]["max_duration"] > 0, (
            f"{p['name']} has max_duration={p['video']['max_duration']}"
        )


def test_remote_folder_paths_are_absolute(platforms):
    """All remote folders should be absolute Android paths."""
    for p in platforms:
        assert p["remote_folder"].startswith("/storage/"), (
            f"{p['name']} remote_folder doesn't look like an Android path: "
            f"{p['remote_folder']}"
        )
