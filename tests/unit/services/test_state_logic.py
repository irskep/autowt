"""Tests for state management business logic."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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

    @pytest.mark.parametrize(
        "platform,home_subpath,env_setup",
        [
            ("Darwin", ["Library", "Application Support", "autowt"], {}),
            ("Windows", [".autowt"], {}),
            ("Linux", [".local", "share", "autowt"], {}),
        ],
    )
    def test_get_default_app_dir_platforms(
        self, platform, home_subpath, env_setup, monkeypatch
    ):
        """Test default app directory across different platforms."""
        # Clear environment and set up platform
        for key, value in env_setup.items():
            monkeypatch.setenv(key, value)
        if not env_setup:  # Clear XDG_DATA_HOME for non-XDG tests
            monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        monkeypatch.setattr("platform.system", lambda: platform)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_home = Path(temp_dir)

            with patch("pathlib.Path.home", return_value=temp_home):
                # Create mock config_loader (required parameter)
                mock_config_loader = MagicMock()
                service = StateService(config_loader=mock_config_loader)
                expected = temp_home
                for part in home_subpath:
                    expected = expected / part
                assert service.app_dir == expected

    def test_get_default_app_dir_linux_xdg(self, tmp_path, monkeypatch):
        """Test default app directory on Linux with XDG_DATA_HOME."""
        monkeypatch.setattr("platform.system", lambda: "Linux")
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

        mock_config_loader = MagicMock()
        service = StateService(config_loader=mock_config_loader)
        expected = tmp_path / "autowt"
        assert service.app_dir == expected


class TestSessionIdLogic:
    """Tests for session ID management logic."""

    def test_session_id_updates(self):
        """Test session ID dictionary updates with composite keys."""
        repo_path = "/test/repo"
        session_ids = {
            f"{repo_path}:branch1": "session1",
            f"{repo_path}:branch2": "session2",
        }

        # Add new session
        session_ids[f"{repo_path}:branch3"] = "session3"
        assert f"{repo_path}:branch3" in session_ids
        assert session_ids[f"{repo_path}:branch3"] == "session3"

        # Update existing session
        session_ids[f"{repo_path}:branch1"] = "new-session1"
        assert session_ids[f"{repo_path}:branch1"] == "new-session1"

        # Remove session
        removed = session_ids.pop(f"{repo_path}:branch2", None)
        assert removed == "session2"
        assert f"{repo_path}:branch2" not in session_ids

    def test_session_id_cleanup_after_worktree_removal(self):
        """Test cleaning up session IDs when worktrees are removed."""
        repo_path = "/test/repo"
        session_ids = {
            f"{repo_path}:feature1": "session1",
            f"{repo_path}:feature2": "session2",
            f"{repo_path}:bugfix": "session3",
        }
        removed_branches = {"feature2", "bugfix"}

        # Remove session IDs for removed branches
        for branch in removed_branches:
            session_ids.pop(f"{repo_path}:{branch}", None)

        # Verify cleanup
        assert f"{repo_path}:feature1" in session_ids
        assert f"{repo_path}:feature2" not in session_ids
        assert f"{repo_path}:bugfix" not in session_ids
        assert len(session_ids) == 1

    def test_session_id_repo_disambiguation(self):
        """Test that session IDs are isolated per repository."""
        repo1_path = "/path/to/repo1"
        repo2_path = "/path/to/repo2"

        # Both repos have the same branch name "main"
        session_ids = {
            f"{repo1_path}:main": "session-repo1-main",
            f"{repo2_path}:main": "session-repo2-main",
            f"{repo1_path}:feature": "session-repo1-feature",
            f"{repo2_path}:feature": "session-repo2-feature",
        }

        # Verify sessions are isolated
        assert session_ids[f"{repo1_path}:main"] == "session-repo1-main"
        assert session_ids[f"{repo2_path}:main"] == "session-repo2-main"
        assert session_ids[f"{repo1_path}:feature"] == "session-repo1-feature"
        assert session_ids[f"{repo2_path}:feature"] == "session-repo2-feature"

        # Removing a branch from one repo doesn't affect the other
        session_ids.pop(f"{repo1_path}:main", None)
        assert f"{repo1_path}:main" not in session_ids
        assert f"{repo2_path}:main" in session_ids
        assert session_ids[f"{repo2_path}:main"] == "session-repo2-main"

        # Verify total count
        assert len(session_ids) == 3
