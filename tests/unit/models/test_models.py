"""Tests for data models."""

from pathlib import Path

from autowt.models import (
    BranchStatus,
    CleanupMode,
    ProjectScriptsConfig,
    SwitchCommand,
    TerminalMode,
    WorktreeInfo,
)


class TestWorktreeInfo:
    """Tests for WorktreeInfo model."""

    def test_worktree_info_creation(self):
        """Test creating WorktreeInfo instance."""
        path = Path("/test/path")
        worktree = WorktreeInfo(branch="test-branch", path=path, is_current=True)

        assert worktree.branch == "test-branch"
        assert worktree.path == path
        assert worktree.is_current is True

    def test_worktree_info_defaults(self):
        """Test WorktreeInfo default values."""
        worktree = WorktreeInfo(branch="test", path=Path("/test"))

        assert worktree.is_current is False


class TestBranchStatus:
    """Tests for BranchStatus model."""

    def test_branch_status_creation(self):
        """Test creating BranchStatus instance."""
        path = Path("/test/path")
        status = BranchStatus(
            branch="test-branch",
            has_remote=True,
            is_merged=False,
            is_identical=False,
            path=path,
        )

        assert status.branch == "test-branch"
        assert status.has_remote is True
        assert status.is_merged is False
        assert status.is_identical is False
        assert status.path == path


class TestSwitchCommand:
    """Tests for SwitchCommand model."""

    def test_switch_command_creation(self):
        """Test creating SwitchCommand instance."""
        cmd = SwitchCommand(
            branch="test-branch", terminal_mode=TerminalMode.TAB, from_branch="main"
        )

        assert cmd.branch == "test-branch"
        assert cmd.terminal_mode == TerminalMode.TAB
        assert cmd.from_branch == "main"

    def test_switch_command_defaults(self):
        """Test SwitchCommand default values."""
        cmd = SwitchCommand(branch="test-branch")

        assert cmd.branch == "test-branch"
        assert cmd.terminal_mode is None
        assert cmd.init_script is None
        assert cmd.after_init is None
        assert cmd.ignore_same_session is False
        assert cmd.auto_confirm is False
        assert cmd.debug is False
        assert cmd.from_branch is None


class TestEnums:
    """Tests for enum values."""

    def test_terminal_mode_values(self):
        """Test TerminalMode enum values."""
        assert TerminalMode.TAB.value == "tab"
        assert TerminalMode.WINDOW.value == "window"
        assert TerminalMode.INPLACE.value == "inplace"

    def test_cleanup_mode_values(self):
        """Test CleanupMode enum values."""
        assert CleanupMode.ALL.value == "all"
        assert CleanupMode.REMOTELESS.value == "remoteless"
        assert CleanupMode.MERGED.value == "merged"
        assert CleanupMode.INTERACTIVE.value == "interactive"


class TestProjectScriptsConfig:
    """Tests for ProjectScriptsConfig backward compatibility."""

    def test_from_dict_with_session_init_only(self):
        """Test creating config with only session_init specified."""
        data = {"session_init": "npm install", "custom": {"test": "npm test"}}
        config = ProjectScriptsConfig.from_dict(data)

        assert config.session_init == "npm install"
        assert config.custom == {"test": "npm test"}

    def test_from_dict_with_init_only_maps_to_session_init(self):
        """Test creating config with only init maps to session_init."""
        data = {"init": "make setup", "custom": {"build": "make build"}}
        config = ProjectScriptsConfig.from_dict(data)

        assert config.session_init == "make setup"
        assert config.custom == {"build": "make build"}

    def test_from_dict_with_both_init_and_session_init_prefers_session_init(self):
        """Test that session_init is preferred when both are specified."""
        data = {
            "init": "old command",
            "session_init": "new command",
            "custom": {"deploy": "make deploy"},
        }

        config = ProjectScriptsConfig.from_dict(data)

        assert config.session_init == "new command"  # session_init takes precedence
        assert config.custom == {"deploy": "make deploy"}

    def test_from_dict_with_empty_dict(self):
        """Test creating config from empty dictionary."""
        config = ProjectScriptsConfig.from_dict({})

        assert config.session_init is None
        assert config.custom is None

    def test_to_dict_includes_session_init(self):
        """Test that to_dict outputs session_init, not init."""
        config = ProjectScriptsConfig(
            session_init="python setup.py", custom={"test": "pytest", "lint": "ruff"}
        )

        result = config.to_dict()

        assert result == {
            "session_init": "python setup.py",
            "custom": {"test": "pytest", "lint": "ruff"},
        }
        assert "init" not in result  # Should not output deprecated key

    def test_to_dict_with_none_values(self):
        """Test that to_dict excludes None values."""
        config = ProjectScriptsConfig(session_init=None, custom=None)

        result = config.to_dict()

        assert result == {}  # Empty dict when all values are None
