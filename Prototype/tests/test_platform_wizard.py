"""
Tests for platform_wizard.py — the add/edit dialogs for platforms.json.

Covers:
- Package name regex
- Form validation (happy paths, missing fields, bad values)
- Duplicate detection (add mode + edit mode self-collision)
- End-to-end file writes (append for add, replace for edit)
- Backup-before-write behavior

Run with: pytest tests/test_platform_wizard.py -v
"""

# stdlib
import json
import os
import sys
import types

# third-party
import pytest


# ---------------------------------------------------------------------------
# Module-scoped fixture: stub customtkinter only if it's not already importable
# (the real one needs tkinter, which the test environment may or may not have).
# Cleanup restores sys.modules to its original state so we don't leak fakes
# into other test files.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def _isolate_sys_modules():
    """
    Snapshot sys.modules before this test file imports anything project-local,
    and restore it afterward. This guarantees no test-time stubs (real or
    accidental) leak into other test files.

    On dev machines with tkinter, customtkinter imports normally and no stub
    is needed. On headless sandboxes without tkinter, we install a minimal
    customtkinter stub for the lifetime of this module only.
    """
    # Snapshot the keys present before we touch anything
    keys_before = set(sys.modules.keys())
    snapshot = {k: sys.modules[k] for k in keys_before}

    # Stub customtkinter only if it isn't importable as-is
    try:
        import customtkinter  # noqa: F401
    except Exception:
        fake_ctk = types.ModuleType("customtkinter")

        class _Stub:
            def __init__(self, *a, **kw): pass
            def __getattr__(self, name): return _Stub()
            def __call__(self, *a, **kw): return _Stub()

        for attr in (
            "CTkToplevel", "CTkScrollableFrame", "CTkFrame", "CTkLabel",
            "CTkEntry", "CTkButton", "CTkRadioButton", "CTkComboBox",
            "CTkTextbox", "StringVar",
        ):
            setattr(fake_ctk, attr, _Stub)

        sys.modules["customtkinter"] = fake_ctk

        # ui_setup imports tkinter directly too — stub if needed
        try:
            import tkinter  # noqa: F401
        except Exception:
            fake_tk = types.ModuleType("tkinter")
            fake_tk.Canvas = _Stub
            sys.modules["tkinter"] = fake_tk

    yield

    # Restore: drop any module that wasn't there before, and restore any that
    # was replaced. This wipes our stubs AND any project modules (utils,
    # platform_wizard, etc.) that imported our stubs, forcing clean re-imports
    # in subsequent test files.
    keys_after = set(sys.modules.keys())
    for key in keys_after - keys_before:
        sys.modules.pop(key, None)
    for key, mod in snapshot.items():
        sys.modules[key] = mod


# ---------------------------------------------------------------------------
# Lazy import — happens after the autouse fixture has set up stubs (if any)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pw():
    """The platform_wizard module, imported once per test module."""
    # Make sure project root (where platform_wizard.py lives) is on sys.path.
    # This works whether the tests live in tests/ or at the repo root.
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(here) if os.path.basename(here) == "tests" else here
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    import platform_wizard
    return platform_wizard


# ---------------------------------------------------------------------------
# Test harness — fake widgets so we can exercise validation/save without UI
# ---------------------------------------------------------------------------

class _FakeEntry:
    def __init__(self, value=""):
        self._v = str(value)
    def get(self):
        return self._v


class _FakeStringVar:
    def __init__(self, value=""):
        self._v = value
    def get(self):
        return self._v


class _FakeWindow:
    """
    Stand-in for a CTk window. Swallows any method call (.after, .destroy,
    .grab_set, etc.) so calling code that expects a real Tk window doesn't
    crash. Returns no-op lambdas for unknown attributes.
    """
    def __getattr__(self, name):
        return lambda *a, **kw: None


GOOD_PHOTO = {
    "width": "4032", "height": "3024", "rotate": "",
    "mirror": "false", "resize_mode": "contain", "filename": "virtual_photo.jpg",
}
GOOD_VIDEO = {
    "width": "1920", "height": "1080", "rotate": "",
    "mirror": "false", "resize_mode": "contain",
    "max_duration": "60", "filename": "virtual.mp4",
}
DEFAULT_EXISTING = [
    {"name": "Snapchat", "package_name": "com.snapchat.android"},
    {"name": "WhatsApp", "package_name": "com.whatsapp"},
]


def _make_harness(pw, name="Test", package="com.test.app",
                  photo_mode="gallery",
                  gallery_path="/storage/emulated/0/DCIM/Camera/",
                  remote_folder="",
                  photo_specs=None, video_specs=None,
                  existing=None, edit_index=None, mode="add",
                  on_saved=None):
    """
    Build a harness object with the same attributes _PlatformFormBase methods
    expect, but using fake widgets. Binds the right _apply_to_platforms_list
    based on mode.
    """
    h = types.SimpleNamespace()
    h.name_entry = _FakeEntry(name)
    h.package_entry = _FakeEntry(package)
    h.photo_mode_var = _FakeStringVar(photo_mode)
    h.gallery_path_entry = _FakeEntry(gallery_path)
    h.remote_folder_entry = _FakeEntry(remote_folder)
    h.photo_widgets = {k: _FakeEntry(v) for k, v in (photo_specs or GOOD_PHOTO).items()}
    h.video_widgets = {k: _FakeEntry(v) for k, v in (video_specs or GOOD_VIDEO).items()}
    h.existing_platforms = existing if existing is not None else list(DEFAULT_EXISTING)
    h._edit_index = edit_index
    h.win = _FakeWindow()
    h.parent = _FakeWindow()
    h.on_saved = on_saved
    h.result_saved = False

    base = pw._PlatformFormBase
    h._build_and_validate = lambda: base._build_and_validate(h)
    h._validate_specs = lambda widgets, label, include_max_duration: \
        base._validate_specs(h, widgets, label, include_max_duration)
    h._save = lambda: base._save(h)
    h._show_errors = lambda errors: setattr(h, "_last_errors", errors)

    if mode == "add":
        h._apply_to_platforms_list = lambda lst, cfg: pw.PlatformWizard._apply_to_platforms_list(h, lst, cfg)
    else:
        h._apply_to_platforms_list = lambda lst, cfg: pw.PlatformEditor._apply_to_platforms_list(h, lst, cfg)

    return h


# ===========================================================================
# Package name regex
# ===========================================================================

class TestPackageNameRegex:

    @pytest.mark.parametrize("package", [
        "com.instagram.android",
        "com.whatsapp",
        "org.telegram.messenger",
        "com.tiktok.app",
        "com.snapchat.android",
        "com.discord",
    ])
    def test_accepts_valid_package_names(self, pw, package):
        assert pw.PACKAGE_NAME_RE.match(package), f"Should accept {package!r}"

    @pytest.mark.parametrize("package", [
        "instagram",                  # no dots
        "Com.Instagram",              # uppercase
        "com..app",                   # double dot
        "com.instagram.",             # trailing dot
        ".com.app",                   # leading dot
        "com.app!",                   # special char
        "",                           # empty
        "com.app-name",               # hyphen
    ])
    def test_rejects_invalid_package_names(self, pw, package):
        assert not pw.PACKAGE_NAME_RE.match(package), f"Should reject {package!r}"


# ===========================================================================
# Form validation — happy paths
# ===========================================================================

class TestValidationHappyPaths:

    def test_gallery_mode_builds_correct_config(self, pw):
        h = _make_harness(pw,
            name="Instagram", package="com.instagram.android",
            photo_mode="gallery",
        )
        config, errors = h._build_and_validate()
        assert errors == []
        assert config["name"] == "Instagram"
        assert config["package_name"] == "com.instagram.android"
        assert config["photo_mode"] == "gallery"
        assert config["gallery_path"] == "/storage/emulated/0/DCIM/Camera/"
        # remote_folder is auto-built from the package name
        assert config["remote_folder"] == "/storage/emulated/0/Android/data/com.instagram.android/files/Camera1/"
        # Type coercion happened correctly
        assert config["photo"]["width"] == 4032
        assert config["photo"]["rotate"] is None
        assert config["photo"]["mirror"] is False
        assert config["video"]["max_duration"] == 60

    def test_vcam_mode_builds_correct_config(self, pw):
        h = _make_harness(pw,
            name="NewApp", package="com.newapp.test",
            photo_mode="vcam",
            remote_folder="/storage/emulated/0/Android/data/com.newapp.test/files/Camera1/",
            photo_specs={**GOOD_PHOTO, "rotate": "90"},
            video_specs={**GOOD_VIDEO, "rotate": "180"},
        )
        config, errors = h._build_and_validate()
        assert errors == []
        assert config["photo_mode"] == "vcam"
        assert config["gallery_path"] is None
        assert config["photo"]["rotate"] == 90
        assert config["video"]["rotate"] == 180


# ===========================================================================
# Form validation — bad inputs
# ===========================================================================

class TestValidationErrors:

    def test_empty_name_is_rejected(self, pw):
        h = _make_harness(pw, name="")
        _, errors = h._build_and_validate()
        assert any("name is required" in e.lower() for e in errors)

    def test_bad_package_format_is_rejected(self, pw):
        h = _make_harness(pw, package="not-a-package")
        _, errors = h._build_and_validate()
        assert any("com.example.app" in e for e in errors)

    def test_gallery_path_must_end_with_slash(self, pw):
        h = _make_harness(pw, gallery_path="/storage/emulated/0/DCIM/Camera")
        _, errors = h._build_and_validate()
        assert any("end with '/'" in e for e in errors)

    def test_gallery_path_must_be_absolute(self, pw):
        h = _make_harness(pw, gallery_path="storage/emulated/0/DCIM/Camera/")
        _, errors = h._build_and_validate()
        assert any("absolute" in e for e in errors)

    def test_vcam_requires_remote_folder(self, pw):
        h = _make_harness(pw,
            photo_mode="vcam",
            gallery_path="",
            remote_folder="",
        )
        _, errors = h._build_and_validate()
        assert any("Remote folder is required" in e for e in errors)

    def test_invalid_rotate_is_rejected(self, pw):
        h = _make_harness(pw, photo_specs={**GOOD_PHOTO, "rotate": "45"})
        _, errors = h._build_and_validate()
        assert any("rotate must be 0" in e for e in errors)

    def test_empty_width_is_rejected(self, pw):
        h = _make_harness(pw, photo_specs={**GOOD_PHOTO, "width": ""})
        _, errors = h._build_and_validate()
        assert any("width is required" in e.lower() for e in errors)

    def test_negative_width_is_rejected(self, pw):
        h = _make_harness(pw, photo_specs={**GOOD_PHOTO, "width": "-100"})
        _, errors = h._build_and_validate()
        assert any("positive integer" in e for e in errors)

    def test_filename_with_slashes_is_rejected(self, pw):
        h = _make_harness(pw, photo_specs={**GOOD_PHOTO, "filename": "sub/photo.jpg"})
        _, errors = h._build_and_validate()
        assert any("slashes" in e for e in errors)

    def test_zero_max_duration_is_rejected(self, pw):
        h = _make_harness(pw, video_specs={**GOOD_VIDEO, "max_duration": "0"})
        _, errors = h._build_and_validate()
        assert any("positive integer" in e for e in errors)

    def test_multiple_errors_are_all_returned(self, pw):
        h = _make_harness(pw, name="", package="bad", gallery_path="")
        _, errors = h._build_and_validate()
        assert len(errors) >= 3


# ===========================================================================
# Duplicate detection — add mode
# ===========================================================================

class TestDuplicateDetectionAddMode:

    def test_duplicate_name_is_blocked(self, pw):
        h = _make_harness(pw, name="Snapchat", package="com.something.else")
        _, errors = h._build_and_validate()
        assert any("'Snapchat' already exists" in e for e in errors)

    def test_duplicate_name_is_case_insensitive(self, pw):
        h = _make_harness(pw, name="SNAPCHAT", package="com.something.else")
        _, errors = h._build_and_validate()
        assert any("already exists" in e for e in errors)

    def test_duplicate_package_is_blocked(self, pw):
        h = _make_harness(pw, name="NewName", package="com.snapchat.android")
        _, errors = h._build_and_validate()
        assert any("com.snapchat.android" in e and "already exists" in e for e in errors)


# ===========================================================================
# Duplicate detection — edit mode (self-collision must be skipped)
# ===========================================================================

class TestDuplicateDetectionEditMode:

    def test_no_changes_is_allowed(self, pw):
        # Editing Snapchat without changing anything — must not flag self as duplicate
        h = _make_harness(pw,
            name="Snapchat", package="com.snapchat.android",
            photo_mode="vcam", gallery_path="", remote_folder="/some/path/",
            edit_index=0, mode="edit",
        )
        _, errors = h._build_and_validate()
        assert errors == []

    def test_typo_correction_rename_is_allowed(self, pw):
        h = _make_harness(pw,
            name="SnapChat", package="com.snapchat.android",
            photo_mode="vcam", gallery_path="", remote_folder="/some/path/",
            edit_index=0, mode="edit",
        )
        config, errors = h._build_and_validate()
        assert errors == []
        assert config["name"] == "SnapChat"

    def test_renaming_to_other_existing_platform_is_blocked(self, pw):
        h = _make_harness(pw,
            name="WhatsApp", package="com.snapchat.android",
            photo_mode="vcam", gallery_path="", remote_folder="/some/path/",
            edit_index=0, mode="edit",
        )
        _, errors = h._build_and_validate()
        assert any("WhatsApp" in e and "already exists" in e for e in errors)

    def test_changing_to_other_existing_package_is_blocked(self, pw):
        h = _make_harness(pw,
            name="Snapchat", package="com.whatsapp",
            photo_mode="vcam", gallery_path="", remote_folder="/some/path/",
            edit_index=0, mode="edit",
        )
        _, errors = h._build_and_validate()
        assert any("com.whatsapp" in e and "already exists" in e for e in errors)


# ===========================================================================
# End-to-end file writes
# ===========================================================================

@pytest.fixture
def temp_platforms_file(pw, tmp_path, monkeypatch):
    """
    Create a temp platforms.json with the standard Snapchat/WhatsApp entries
    and patch platform_wizard.get_platforms_file to point at it.
    """
    initial = {
        "platforms": [
            {
                "name": "Snapchat", "package_name": "com.snapchat.android",
                "remote_folder": "/storage/emulated/0/Android/data/com.snapchat.android/files/Camera1/",
                "photo_mode": "vcam", "gallery_path": None,
                "photo": {
                    "width": 1080, "height": 1920, "rotate": 90, "mirror": False,
                    "resize_mode": "fill", "filename": "1000.bmp",
                },
                "video": {
                    "width": 1080, "height": 1920, "rotate": 180, "mirror": False,
                    "resize_mode": "fill", "max_duration": 60, "filename": "virtual.mp4",
                },
            },
            {
                "name": "WhatsApp", "package_name": "com.whatsapp",
                "remote_folder": "/storage/emulated/0/Android/data/com.whatsapp/files/Camera1/",
                "photo_mode": "gallery", "gallery_path": "/storage/emulated/0/DCIM/Camera/",
                "photo": {
                    "width": 4032, "height": 3024, "rotate": None, "mirror": None,
                    "resize_mode": "contain", "filename": "virtual_photo.jpg",
                },
                "video": {
                    "width": 1920, "height": 1080, "rotate": None, "mirror": None,
                    "resize_mode": "contain", "max_duration": 60, "filename": "virtual.mp4",
                },
            },
        ]
    }
    path = tmp_path / "platforms.json"
    path.write_text(json.dumps(initial, indent=2), encoding="utf-8")

    # Patch the reference inside platform_wizard. monkeypatch auto-undoes
    # this when the test finishes, so other test files see the real
    # get_platforms_file again.
    monkeypatch.setattr(pw, "get_platforms_file", lambda: str(path))

    yield str(path)


def _read_platforms(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)["platforms"]


class TestEndToEndAdd:

    def test_add_appends_new_entry(self, pw, temp_platforms_file):
        existing = _read_platforms(temp_platforms_file)

        h = _make_harness(pw,
            name="Instagram", package="com.instagram.android",
            existing=existing, mode="add",
        )
        h._save()

        assert h.result_saved
        after = _read_platforms(temp_platforms_file)
        assert len(after) == len(existing) + 1
        names = [p["name"] for p in after]
        assert "Instagram" in names

    def test_add_creates_backup_file(self, pw, temp_platforms_file):
        h = _make_harness(pw,
            name="Instagram", package="com.instagram.android",
            existing=_read_platforms(temp_platforms_file), mode="add",
        )
        h._save()

        backup = temp_platforms_file + ".bak"
        assert os.path.exists(backup)

    def test_add_calls_on_saved_callback(self, pw, temp_platforms_file):
        captured = []
        h = _make_harness(pw,
            name="Instagram", package="com.instagram.android",
            existing=_read_platforms(temp_platforms_file), mode="add",
            on_saved=lambda cfg: captured.append(cfg),
        )
        h._save()
        assert len(captured) == 1
        assert captured[0]["name"] == "Instagram"


class TestEndToEndEdit:

    def test_edit_replaces_in_place(self, pw, temp_platforms_file):
        existing = _read_platforms(temp_platforms_file)
        snap_idx = next(i for i, p in enumerate(existing) if p["name"] == "Snapchat")
        snap = existing[snap_idx]

        h = _make_harness(pw,
            name=snap["name"], package=snap["package_name"],
            photo_mode=snap["photo_mode"],
            gallery_path=snap["gallery_path"] or "",
            remote_folder=snap["remote_folder"],
            photo_specs={
                "width": "720", "height": "1920", "rotate": "90",
                "mirror": "false", "resize_mode": "fill", "filename": "1000.bmp",
            },
            video_specs={
                "width": "1080", "height": "1920", "rotate": "180",
                "mirror": "false", "resize_mode": "fill",
                "max_duration": "60", "filename": "virtual.mp4",
            },
            existing=existing, edit_index=snap_idx, mode="edit",
        )
        h._save()

        assert h.result_saved
        after = _read_platforms(temp_platforms_file)
        assert len(after) == len(existing), "Edit must not change list length"
        snap_after = next(p for p in after if p["name"] == "Snapchat")
        assert snap_after["photo"]["width"] == 720

    def test_edit_rename_works(self, pw, temp_platforms_file):
        existing = _read_platforms(temp_platforms_file)
        snap_idx = next(i for i, p in enumerate(existing) if p["name"] == "Snapchat")
        snap = existing[snap_idx]

        h = _make_harness(pw,
            name="Snap", package=snap["package_name"],
            photo_mode=snap["photo_mode"],
            gallery_path=snap["gallery_path"] or "",
            remote_folder=snap["remote_folder"],
            photo_specs={
                "width": "1080", "height": "1920", "rotate": "90",
                "mirror": "false", "resize_mode": "fill", "filename": "1000.bmp",
            },
            video_specs={
                "width": "1080", "height": "1920", "rotate": "180",
                "mirror": "false", "resize_mode": "fill",
                "max_duration": "60", "filename": "virtual.mp4",
            },
            existing=existing, edit_index=snap_idx, mode="edit",
        )
        h._save()

        after = _read_platforms(temp_platforms_file)
        names = [p["name"] for p in after]
        assert "Snap" in names
        assert "Snapchat" not in names


class TestEndToEndValidationBlocksWrite:

    def test_invalid_input_does_not_touch_file(self, pw, temp_platforms_file):
        with open(temp_platforms_file, "rb") as f:
            before = f.read()

        h = _make_harness(pw,
            name="",  # invalid
            package="com.something.new",
            existing=_read_platforms(temp_platforms_file), mode="add",
        )
        h._save()

        assert not h.result_saved
        with open(temp_platforms_file, "rb") as f:
            assert f.read() == before
        assert not os.path.exists(temp_platforms_file + ".bak")