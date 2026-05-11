"""
Unit tests for session.py (Session class).

Covers:
- __init__: validates officer_name and case_number, stores state, builds case_path
- get_evidence_filename: date/time formatting, officer name sanitisation, extension handling
- get_evidence_path: combines case_path with the generated filename
- ensure_case_folder: creates the folder idempotently

officer_name is sanitised at construction (Windows-unsafe chars stripped,
blank names rejected). case_number is validated against a letters/digits/
hyphens/underscores allowlist.
"""

import os
from datetime import datetime
import pytest

from session import Session


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestSessionInit:

    def test_stores_officer_name(self, tmp_path):
        s = Session("Jan de Vries", "2026-001", str(tmp_path))
        assert s.officer_name == "Jan de Vries"

    def test_stores_case_number(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        assert s.case_number == "2026-001"

    def test_stores_case_root(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        assert s.case_root == str(tmp_path)

    def test_builds_case_path_from_root_and_number(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        assert s.case_path == os.path.join(str(tmp_path), "2026-001")

    def test_sets_started_at_to_approximately_now(self, tmp_path):
        before = datetime.now()
        s = Session("Jan", "2026-001", str(tmp_path))
        after = datetime.now()
        assert before <= s.started_at <= after


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestSessionValidation:
    """__init__ rejects invalid officer_name and case_number."""

    # officer_name

    def test_blank_officer_name_raises(self, tmp_path):
        with pytest.raises(ValueError, match="officer_name cannot be blank"):
            Session("", "2026-001", str(tmp_path))

    def test_whitespace_only_officer_name_raises(self, tmp_path):
        with pytest.raises(ValueError, match="officer_name cannot be blank"):
            Session("   ", "2026-001", str(tmp_path))

    def test_none_officer_name_raises(self, tmp_path):
        with pytest.raises(ValueError, match="officer_name cannot be blank"):
            Session(None, "2026-001", str(tmp_path))

    def test_officer_name_of_only_unsafe_chars_raises(self, tmp_path):
        # After stripping all unsafe chars, nothing usable is left
        with pytest.raises(ValueError, match="officer_name contains no usable characters"):
            Session("<<<>>>", "2026-001", str(tmp_path))

    @pytest.mark.parametrize("raw,expected", [
        ("Jan<de>Vries", "JandeVries"),
        ("Jan/de\\Vries", "JandeVries"),
        ('Jan "The Boss" de Vries', "Jan The Boss de Vries"),
        ("Jan|de?Vries*", "JandeVries"),
        ("Jan:de:Vries", "JandeVries"),
        ("Jan\x00de\x01Vries", "JandeVries"),
    ])
    def test_unsafe_chars_stripped_from_officer_name(self, tmp_path, raw, expected):
        s = Session(raw, "2026-001", str(tmp_path))
        assert s.officer_name == expected

    def test_safe_chars_preserved(self, tmp_path):
        # Apostrophes, hyphens, dots, and letters with diacritics are kept.
        s = Session("Jan-Willem O'Brien", "2026-001", str(tmp_path))
        assert s.officer_name == "Jan-Willem O'Brien"

    def test_unicode_name_preserved(self, tmp_path):
        # Dutch names with diacritics must survive.
        s = Session("Jürgen Müller", "2026-001", str(tmp_path))
        assert s.officer_name == "Jürgen Müller"

    # case_number

    def test_blank_case_number_raises(self, tmp_path):
        with pytest.raises(ValueError, match="case_number cannot be blank"):
            Session("Jan", "", str(tmp_path))

    def test_whitespace_only_case_number_raises(self, tmp_path):
        with pytest.raises(ValueError, match="case_number cannot be blank"):
            Session("Jan", "   ", str(tmp_path))

    def test_none_case_number_raises(self, tmp_path):
        with pytest.raises(ValueError, match="case_number cannot be blank"):
            Session("Jan", None, str(tmp_path))

    @pytest.mark.parametrize("bad_case", [
        "../../../etc/passwd",     # path traversal attempt
        "case 001",                # space
        "case/001",                # slash
        "case\\001",               # backslash
        "case.001",                # dot
        "case:001",                # colon
        "case#001",                # hash
    ])
    def test_invalid_case_number_raises(self, tmp_path, bad_case):
        with pytest.raises(ValueError, match="invalid characters"):
            Session("Jan", bad_case, str(tmp_path))

    @pytest.mark.parametrize("good_case", [
        "2026-001",
        "LN-2026-42",
        "case_42",
        "ABC123",
        "x",
    ])
    def test_valid_case_number_accepted(self, tmp_path, good_case):
        s = Session("Jan", good_case, str(tmp_path))
        assert s.case_number == good_case


# ---------------------------------------------------------------------------
# get_evidence_filename
# ---------------------------------------------------------------------------

class TestGetEvidenceFilename:

    def test_default_extension_is_mp4(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        assert s.get_evidence_filename().endswith(".mp4")

    def test_custom_extension_is_used(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        assert s.get_evidence_filename(".jpg").endswith(".jpg")

    def test_includes_date_in_yyyy_mm_dd_format(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        s.started_at = datetime(2026, 4, 23, 14, 30, 0)
        assert "2026-04-23" in s.get_evidence_filename()

    def test_includes_time_in_hh_mm_ss_format(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        s.started_at = datetime(2026, 4, 23, 14, 30, 5)
        filename = s.get_evidence_filename()
        assert "14-30-05" in filename

    def test_full_format(self, tmp_path):
        s = Session("Jan de Vries", "2026-001", str(tmp_path))
        s.started_at = datetime(2026, 4, 23, 14, 30, 5)
        assert s.get_evidence_filename() == "2026-04-23_14-30-05_Jan_de_Vries.mp4"

    def test_spaces_in_officer_name_replaced_with_underscores(self, tmp_path):
        s = Session("Jan de Vries", "2026-001", str(tmp_path))
        filename = s.get_evidence_filename()
        # Date/time will contain underscores too; just assert no spaces remain
        assert " " not in filename
        assert "Jan_de_Vries" in filename

    def test_leading_and_trailing_whitespace_stripped(self, tmp_path):
        s = Session("  Jan  ", "2026-001", str(tmp_path))
        s.started_at = datetime(2026, 4, 23, 14, 30, 5)
        assert s.get_evidence_filename() == "2026-04-23_14-30-05_Jan.mp4"

    def test_same_filename_on_repeated_calls(self, tmp_path):
        # started_at is fixed at construction, so the filename is stable
        # across multiple calls during the same session.
        s = Session("Jan", "2026-001", str(tmp_path))
        assert s.get_evidence_filename() == s.get_evidence_filename()


# ---------------------------------------------------------------------------
# get_evidence_path
# ---------------------------------------------------------------------------

class TestGetEvidencePath:

    def test_combines_case_path_with_filename(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        s.started_at = datetime(2026, 4, 23, 14, 30, 5)
        expected = os.path.join(str(tmp_path), "2026-001", "2026-04-23_14-30-05_Jan.mp4")
        assert s.get_evidence_path() == expected

    def test_respects_custom_extension(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        assert s.get_evidence_path(".jpg").endswith(".jpg")


# ---------------------------------------------------------------------------
# ensure_case_folder
# ---------------------------------------------------------------------------

class TestEnsureCaseFolder:

    def test_creates_case_folder(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        result = s.ensure_case_folder()
        assert os.path.isdir(result)
        assert os.path.isdir(s.case_path)

    def test_returns_case_path(self, tmp_path):
        s = Session("Jan", "2026-001", str(tmp_path))
        assert s.ensure_case_folder() == s.case_path

    def test_is_idempotent(self, tmp_path):
        # Calling twice must not raise even though folder already exists
        s = Session("Jan", "2026-001", str(tmp_path))
        s.ensure_case_folder()
        s.ensure_case_folder()  # should not raise

    def test_creates_missing_parent_directories(self, tmp_path):
        # case_root is under tmp_path but the full path includes a case number
        # that doesn't exist yet. os.makedirs handles that.
        s = Session("Jan", "case-with-subfolders", str(tmp_path / "nonexistent_root"))
        s.ensure_case_folder()
        assert os.path.isdir(os.path.join(str(tmp_path), "nonexistent_root", "case-with-subfolders"))
