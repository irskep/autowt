"""Tests for state management business logic."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from autowt.config import Config, TerminalConfig
from autowt.models import TerminalMode
from autowt.services.state import StateService


class TestStateServiceLogic:
    """Tests for StateService business logic (not file I/O)."""

    def test_config_round_trip_conversion(self):
        """Test converting config to dict and back preserves data."""
        # Create original config
        original_config = Config(
            terminal=TerminalConfig(mode=TerminalMode.WINDOW, always_new=True)
        )

        # Convert to dict and back
        config_dict = original_config.to_dict()
        restored_config = Config.from_dict(config_dict)

        # Verify data preservation
        assert restored_config.terminal.mode == original_config.terminal.mode
        assert (
            restored_config.terminal.always_new == original_config.terminal.always_new
        )

    def test_config_partial_data_handling(self):
        """Test config creation with partial data uses defaults."""
        # Test with minimal data
        config = Config.from_dict({})
        assert config.terminal.mode == TerminalMode.TAB  # default
        assert config.terminal.always_new is False  # default

        # Test with partial data
        config = Config.from_dict({"terminal": {"mode": "tab"}})
        assert config.terminal.mode == TerminalMode.TAB
        assert config.terminal.always_new is False  # default


class TestStateServicePlatformLogic:
    """Tests for platform-specific state service logic."""

    @patch("platform.system")
    def test_get_default_app_dir_macos(self, mock_system):
        """Test default app directory on macOS."""
        mock_system.return_value = "Darwin"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_home = Path(temp_dir)

            with patch("pathlib.Path.home", return_value=temp_home):
                service = StateService()
                expected = temp_home / "Library" / "Application Support" / "autowt"
                assert service.app_dir == expected

    @patch("platform.system")
    @patch.dict("os.environ", {"XDG_DATA_HOME": "/custom/xdg"})
    def test_get_default_app_dir_linux_xdg(self, mock_system, tmp_path):
        """Test default app directory on Linux with XDG_DATA_HOME."""
        mock_system.return_value = "Linux"

        # Use a temporary directory for the test
        with patch.dict("os.environ", {"XDG_DATA_HOME": str(tmp_path)}):
            service = StateService()
            expected = tmp_path / "autowt"
            assert service.app_dir == expected

    @patch("platform.system")
    @patch.dict("os.environ", {}, clear=True)
    def test_get_default_app_dir_linux_default(self, mock_system):
        """Test default app directory on Linux without XDG_DATA_HOME."""
        mock_system.return_value = "Linux"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_home = Path(temp_dir)

            with patch("pathlib.Path.home", return_value=temp_home):
                service = StateService()
                expected = temp_home / ".local" / "share" / "autowt"
                assert service.app_dir == expected

    @patch("platform.system")
    def test_get_default_app_dir_windows(self, mock_system):
        """Test default app directory on Windows."""
        mock_system.return_value = "Windows"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_home = Path(temp_dir)

            with patch("pathlib.Path.home", return_value=temp_home):
                service = StateService()
                expected = temp_home / ".autowt"
                assert service.app_dir == expected


class TestSessionIdLogic:
    """Tests for session ID management logic."""

    def test_session_id_updates(self):
        """Test session ID dictionary updates."""
        session_ids = {"branch1": "session1", "branch2": "session2"}

        # Add new session
        session_ids["branch3"] = "session3"
        assert "branch3" in session_ids
        assert session_ids["branch3"] == "session3"

        # Update existing session
        session_ids["branch1"] = "new-session1"
        assert session_ids["branch1"] == "new-session1"

        # Remove session
        removed = session_ids.pop("branch2", None)
        assert removed == "session2"
        assert "branch2" not in session_ids

    def test_session_id_cleanup_after_worktree_removal(self):
        """Test cleaning up session IDs when worktrees are removed."""
        session_ids = {
            "feature1": "session1",
            "feature2": "session2",
            "bugfix": "session3",
        }
        removed_branches = {"feature2", "bugfix"}

        # Remove session IDs for removed branches
        for branch in removed_branches:
            session_ids.pop(branch, None)

        # Verify cleanup
        assert "feature1" in session_ids
        assert "feature2" not in session_ids
        assert "bugfix" not in session_ids
        assert len(session_ids) == 1
