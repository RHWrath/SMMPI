"""
Unit tests for case_manager.py (CaseManager class).

Scope: __init__ and run_login_flow only. The GUI screens
(_show_login_screen, _show_case_selection_screen) are patched out in tests
so we never need a running Tk root.

The GUI screens themselves are covered by manual/system testing, not here.
"""

import os
from unittest.mock import MagicMock, patch
import pytest

from case_manager import CaseManager
from session import Session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_config(tmp_path):
    """Minimal config that load_config would return."""
    return {"case_root": str(tmp_path / "cases")}


@pytest.fixture
def case_manager(monkeypatch, fake_config):
    """
    CaseManager with load_config stubbed and the CTk app mocked out.
    Returned instance has both `_show_*` methods ready to be patched per test.
    """
    monkeypatch.setattr("case_manager.load_config", lambda: fake_config)
    mock_app = MagicMock()
    cm = CaseManager(mock_app)
    return cm


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestCaseManagerInit:

    def test_stores_app_reference(self, case_manager):
        assert case_manager.app is not None

    def test_loads_config_on_construction(self, case_manager, fake_config):
        assert case_manager.config == fake_config

    def test_session_starts_as_none(self, case_manager):
        assert case_manager.session is None

    def test_internal_state_starts_empty(self, case_manager):
        assert case_manager._officer_name is None
        assert case_manager._case_number is None


# ---------------------------------------------------------------------------
# run_login_flow — cancellation paths
# ---------------------------------------------------------------------------

class TestRunLoginFlowCancellation:

    def test_returns_none_when_login_cancelled(self, case_manager):
        # Login screen closes without setting officer_name
        case_manager._show_login_screen = MagicMock()
        case_manager._show_case_selection_screen = MagicMock()

        result = case_manager.run_login_flow()

        assert result is None
        # Case selection screen should never be reached
        case_manager._show_case_selection_screen.assert_not_called()

    def test_returns_none_when_case_selection_cancelled(self, case_manager):
        # Login succeeds, case selection doesn't
        def set_officer():
            case_manager._officer_name = "Jan"
        case_manager._show_login_screen = MagicMock(side_effect=set_officer)
        case_manager._show_case_selection_screen = MagicMock()

        result = case_manager.run_login_flow()

        assert result is None
        case_manager._show_case_selection_screen.assert_called_once()


# ---------------------------------------------------------------------------
# run_login_flow — happy path
# ---------------------------------------------------------------------------

class TestRunLoginFlowSuccess:

    def test_returns_session_on_full_flow(self, case_manager):
        def set_officer():
            case_manager._officer_name = "Jan"
        def set_case():
            case_manager._case_number = "2026-001"

        case_manager._show_login_screen = MagicMock(side_effect=set_officer)
        case_manager._show_case_selection_screen = MagicMock(side_effect=set_case)

        result = case_manager.run_login_flow()

        assert result is not None
        assert isinstance(result, Session)
        assert result.officer_name == "Jan"
        assert result.case_number == "2026-001"

    def test_stores_session_on_success(self, case_manager):
        def set_officer():
            case_manager._officer_name = "Jan"
        def set_case():
            case_manager._case_number = "2026-001"

        case_manager._show_login_screen = MagicMock(side_effect=set_officer)
        case_manager._show_case_selection_screen = MagicMock(side_effect=set_case)

        result = case_manager.run_login_flow()

        assert case_manager.session is result

    def test_creates_case_folder_on_success(self, case_manager, fake_config):
        def set_officer():
            case_manager._officer_name = "Jan"
        def set_case():
            case_manager._case_number = "2026-001"

        case_manager._show_login_screen = MagicMock(side_effect=set_officer)
        case_manager._show_case_selection_screen = MagicMock(side_effect=set_case)

        case_manager.run_login_flow()

        expected_path = os.path.join(fake_config["case_root"], "2026-001")
        assert os.path.isdir(expected_path)


# ---------------------------------------------------------------------------
# run_login_flow — Session construction failure safety net
# ---------------------------------------------------------------------------

class TestRunLoginFlowSessionFailure:
    """
    If anything slips past GUI validation and Session.__init__ raises,
    run_login_flow should return None instead of crashing.
    """

    def test_returns_none_when_session_raises_valueerror(self, case_manager):
        # Inject an invalid case_number that would bypass the GUI check.
        def set_officer():
            case_manager._officer_name = "Jan"
        def set_case():
            # Contains a slash — Session's regex will reject it.
            case_manager._case_number = "invalid/case"

        case_manager._show_login_screen = MagicMock(side_effect=set_officer)
        case_manager._show_case_selection_screen = MagicMock(side_effect=set_case)

        result = case_manager.run_login_flow()

        assert result is None

    def test_returns_none_when_officer_name_sanitises_to_blank(self, case_manager):
        # If officer_name somehow becomes all-unsafe chars post-login, Session raises.
        def set_officer():
            case_manager._officer_name = "<<<>>>"
        def set_case():
            case_manager._case_number = "2026-001"

        case_manager._show_login_screen = MagicMock(side_effect=set_officer)
        case_manager._show_case_selection_screen = MagicMock(side_effect=set_case)

        result = case_manager.run_login_flow()

        assert result is None

    def test_session_stays_none_after_failure(self, case_manager):
        # After a failed run, self.session should still be None, not half-set.
        def set_officer():
            case_manager._officer_name = "Jan"
        def set_case():
            case_manager._case_number = "bad/name"

        case_manager._show_login_screen = MagicMock(side_effect=set_officer)
        case_manager._show_case_selection_screen = MagicMock(side_effect=set_case)

        case_manager.run_login_flow()

        assert case_manager.session is None
