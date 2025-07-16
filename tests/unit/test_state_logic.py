"""Tests for state management business logic."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from autowt.models import ApplicationState, Configuration, TerminalMode, WorktreeInfo
from autowt.services.state import StateService


class TestStateServiceLogic:
    """Tests for StateService business logic (not file I/O)."""

    def test_state_round_trip_conversion(self, temp_repo_path, sample_worktrees):
        """Test converting state to dict and back preserves data."""
        # Create original state
        original_state = ApplicationState(
            primary_clone=temp_repo_path,
            worktrees=sample_worktrees,
            current_worktree="feature1",
        )

        # Convert to dict and back
        state_dict = original_state.to_dict()
        restored_state = ApplicationState.from_dict(state_dict, temp_repo_path)

        # Verify data preservation
        assert restored_state.primary_clone == original_state.primary_clone
        assert restored_state.current_worktree == original_state.current_worktree
        assert len(restored_state.worktrees) == len(original_state.worktrees)

        for orig, restored in zip(original_state.worktrees, restored_state.worktrees):
            assert orig.branch == restored.branch
            assert orig.path == restored.path
            assert orig.is_current == restored.is_current
            assert orig.session_id == restored.session_id

    def test_config_round_trip_conversion(self):
        """Test converting config to dict and back preserves data."""
        # Create original config
        original_config = Configuration(
            terminal=TerminalMode.WINDOW, terminal_always_new=True
        )

        # Convert to dict and back
        config_dict = original_config.to_dict()
        restored_config = Configuration.from_dict(config_dict)

        # Verify data preservation
        assert restored_config.terminal == original_config.terminal
        assert (
            restored_config.terminal_always_new == original_config.terminal_always_new
        )

    def test_config_partial_data_handling(self):
        """Test config creation with partial data uses defaults."""
        # Test with minimal data
        config = Configuration.from_dict({})
        assert config.terminal == TerminalMode.TAB  # default
        assert config.terminal_always_new is False  # default

        # Test with partial data
        config = Configuration.from_dict({"terminal": "tab"})
        assert config.terminal == TerminalMode.TAB
        assert config.terminal_always_new is False  # default

    def test_state_empty_data_handling(self, temp_repo_path):
        """Test state creation with empty data."""
        state = ApplicationState.from_dict({}, temp_repo_path)
        assert state.primary_clone == temp_repo_path
        assert state.worktrees == []
        assert state.current_worktree is None

    def test_state_worktree_data_conversion(self, temp_repo_path):
        """Test worktree data conversion edge cases."""
        data = {
            "worktrees": [
                {
                    "branch": "test",
                    "path": "/test/path",
                    # Missing optional fields
                }
            ]
        }

        state = ApplicationState.from_dict(data, temp_repo_path)
        worktree = state.worktrees[0]

        assert worktree.branch == "test"
        assert worktree.path == Path("/test/path")
        assert worktree.is_current is False  # default
        assert worktree.session_id is None  # default


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


class TestStateUpdateLogic:
    """Tests for state update business logic."""

    def test_add_worktree_to_state(self, sample_app_state):
        """Test adding a new worktree to existing state."""
        new_worktree = WorktreeInfo(
            branch="new-feature",
            path=Path("/path/to/new-feature"),
            is_current=False,
            session_id="new-session",
        )

        # Add worktree
        original_count = len(sample_app_state.worktrees)
        sample_app_state.worktrees.append(new_worktree)

        # Verify addition
        assert len(sample_app_state.worktrees) == original_count + 1
        assert new_worktree in sample_app_state.worktrees

    def test_remove_worktree_from_state(self, sample_app_state):
        """Test removing a worktree from state."""
        # Get initial state
        original_count = len(sample_app_state.worktrees)
        branch_to_remove = "feature1"

        # Remove worktree
        sample_app_state.worktrees = [
            wt for wt in sample_app_state.worktrees if wt.branch != branch_to_remove
        ]

        # Verify removal
        assert len(sample_app_state.worktrees) == original_count - 1
        remaining_branches = [wt.branch for wt in sample_app_state.worktrees]
        assert branch_to_remove not in remaining_branches

    def test_update_current_worktree(self, sample_app_state):
        """Test updating current worktree in state."""
        original_current = sample_app_state.current_worktree
        new_current = "feature1"

        # Update current worktree
        sample_app_state.current_worktree = new_current

        # Verify change
        assert sample_app_state.current_worktree == new_current
        assert sample_app_state.current_worktree != original_current

    def test_clear_current_worktree(self, sample_app_state):
        """Test clearing current worktree."""
        assert sample_app_state.current_worktree is not None

        # Clear current worktree
        sample_app_state.current_worktree = None

        # Verify cleared
        assert sample_app_state.current_worktree is None


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
