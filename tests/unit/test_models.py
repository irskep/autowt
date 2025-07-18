"""Tests for data models."""

from pathlib import Path

from autowt.models import (
    BranchStatus,
    CleanupMode,
    Configuration,
    ProcessInfo,
    TerminalMode,
    WorktreeInfo,
)


class TestConfiguration:
    """Tests for Configuration model."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = Configuration()
        assert config.terminal == TerminalMode.TAB
        assert config.terminal_always_new is False

    def test_configuration_from_dict(self):
        """Test creating configuration from dictionary."""
        data = {"terminal": "tab", "terminal_always_new": True}
        config = Configuration.from_dict(data)
        assert config.terminal == TerminalMode.TAB
        assert config.terminal_always_new is True

    def test_configuration_from_dict_partial(self):
        """Test creating configuration from partial dictionary."""
        data = {"terminal": "window"}
        config = Configuration.from_dict(data)
        assert config.terminal == TerminalMode.WINDOW
        assert config.terminal_always_new is False  # default

    def test_configuration_to_dict(self):
        """Test converting configuration to dictionary."""
        config = Configuration(terminal=TerminalMode.INPLACE, terminal_always_new=True)
        data = config.to_dict()
        expected = {
            "terminal": "inplace",
            "terminal_always_new": True,
            "cleanup": {"kill_processes": True},
        }
        assert data == expected


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


class TestProcessInfo:
    """Tests for ProcessInfo model."""

    def test_process_info_creation(self):
        """Test creating ProcessInfo instance."""
        working_dir = Path("/test/dir")
        process = ProcessInfo(
            pid=1234, command="python server.py", working_dir=working_dir
        )

        assert process.pid == 1234
        assert process.command == "python server.py"
        assert process.working_dir == working_dir


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
