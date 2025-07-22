"""Tests for command handlers with mocked services."""

from unittest.mock import patch

from autowt.commands import checkout, cleanup, ls
from autowt.models import (
    CleanupCommand,
    CleanupMode,
    SwitchCommand,
    TerminalMode,
)
from tests.fixtures.service_builders import (
    MockServices,
)


class TestListCommand:
    """Tests for ls command."""

    def test_ls_with_worktrees(self, temp_repo_path, sample_worktrees, capsys):
        """Test listing worktrees."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees

        # Run command
        ls.list_worktrees(services)

        # Check output
        captured = capsys.readouterr()
        assert "Worktrees:" in captured.out
        assert "feature1" in captured.out
        assert "feature2" in captured.out
        assert "bugfix" in captured.out
        assert "autowt <branch>" in captured.out

    def test_ls_no_worktrees(self, temp_repo_path, capsys):
        """Test listing when no worktrees exist."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = []

        # Run command
        ls.list_worktrees(services)

        # Check output
        captured = capsys.readouterr()
        assert "No worktrees found." in captured.out

    def test_ls_not_in_repo(self, capsys):
        """Test ls when not in a git repository."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = None

        # Run command
        ls.list_worktrees(services)

        # Check output
        captured = capsys.readouterr()
        assert "Error: Not in a git repository" in captured.out


class TestCheckoutCommand:
    """Tests for checkout command."""

    def test_checkout_existing_worktree(self, temp_repo_path, sample_worktrees):
        """Test switching to existing worktree."""
        # Setup mocks
        services = MockServices()
        # Add session ID data using composite key format
        composite_key = f"{temp_repo_path.resolve()}:feature1"
        services.state.session_ids = {composite_key: "session1"}  # Add session ID data
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees

        # Create SwitchCommand
        switch_cmd = SwitchCommand(branch="feature1", terminal_mode=TerminalMode.TAB)

        # Mock user input to confirm switch
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):  # Suppress print output
            checkout.checkout_branch(switch_cmd, services)

        # Verify terminal switching was called
        assert len(services.terminal.switch_calls) == 1
        call = services.terminal.switch_calls[0]
        assert call[0] == sample_worktrees[0].path  # worktree path
        assert call[1] == TerminalMode.TAB  # terminal mode
        assert call[2] == "session1"  # session ID
        assert call[3] is None  # init script

    def test_checkout_already_in_worktree(
        self, temp_repo_path, sample_worktrees, capsys
    ):
        """Test trying to switch to a worktree you're already in."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees

        # Create SwitchCommand for feature1
        switch_cmd = SwitchCommand(branch="feature1", terminal_mode=TerminalMode.TAB)

        # Mock current working directory to be inside the feature1 worktree
        target_worktree = sample_worktrees[0]  # feature1 worktree
        with patch("pathlib.Path.cwd", return_value=target_worktree.path / "subdir"):
            checkout.checkout_branch(switch_cmd, services)

        # Verify no terminal switching was attempted
        assert len(services.terminal.switch_calls) == 0

        # Check that appropriate message was printed
        captured = capsys.readouterr()
        assert "Already in feature1 worktree" in captured.out

    def test_checkout_new_worktree(self, temp_repo_path):
        """Test creating new worktree."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = []  # No existing worktrees
        services.git.fetch_success = True
        services.git.create_success = True

        # Create SwitchCommand
        switch_cmd = SwitchCommand(
            branch="new-feature", terminal_mode=TerminalMode.WINDOW
        )

        # Run command
        checkout.checkout_branch(switch_cmd, services)

        # Verify git operations
        assert services.git.fetch_called
        assert len(services.git.create_worktree_calls) == 1

        create_call = services.git.create_worktree_calls[0]
        assert create_call[1] == "new-feature"  # branch name

        # Verify terminal switching
        assert len(services.terminal.switch_calls) == 1
        switch_call = services.terminal.switch_calls[0]
        assert switch_call[1] == TerminalMode.WINDOW
        assert switch_call[3] is None  # init script

        # State is no longer saved - worktree info is derived from git

    def test_checkout_decline_switch(self, temp_repo_path, sample_worktrees):
        """Test declining to switch to existing worktree."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees
        services.terminal.switch_success = (
            False  # Simulate user declining/switch failure
        )

        # Create SwitchCommand
        switch_cmd = SwitchCommand(branch="feature1", terminal_mode=TerminalMode.TAB)

        checkout.checkout_branch(switch_cmd, services)

        # Verify terminal service was called but returned False (declined/failed)
        assert len(services.terminal.switch_calls) == 1
        assert services.terminal.switch_calls[0][5] == "feature1"  # branch_name
        assert not services.terminal.switch_calls[0][6]  # auto_confirm

    def test_checkout_existing_worktree_with_init_script(
        self, temp_repo_path, sample_worktrees
    ):
        """Test switching to existing worktree with init script."""
        # Setup mocks
        services = MockServices()
        # Add session ID data using composite key format
        composite_key = f"{temp_repo_path.resolve()}:feature1"
        services.state.session_ids = {composite_key: "session1"}
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees

        # Create SwitchCommand
        switch_cmd = SwitchCommand(
            branch="feature1", terminal_mode=TerminalMode.TAB, init_script="setup.sh"
        )

        # Mock user input to confirm switch
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):
            checkout.checkout_branch(switch_cmd, services)

        # Verify terminal switching was called WITHOUT init script (existing worktree)
        assert len(services.terminal.switch_calls) == 1
        call = services.terminal.switch_calls[0]
        assert call[0] == sample_worktrees[0].path  # worktree path
        assert call[1] == TerminalMode.TAB  # terminal mode
        assert call[2] == "session1"  # session ID
        assert call[3] is None  # no init script for existing worktrees
        assert call[4] is None  # no after_init for existing worktrees
        assert call[5] == "feature1"  # branch name

    def test_checkout_new_worktree_with_init_script(self, temp_repo_path):
        """Test creating new worktree with init script."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = []  # No existing worktrees
        services.git.fetch_success = True
        services.git.create_success = True

        # Create SwitchCommand
        switch_cmd = SwitchCommand(
            branch="feature-with-init",
            terminal_mode=TerminalMode.TAB,
            init_script="npm install",
        )

        # Run command
        checkout.checkout_branch(switch_cmd, services)

        # Verify terminal switching was called WITH init script (new worktree)
        assert len(services.terminal.switch_calls) == 1
        call = services.terminal.switch_calls[0]
        assert call[1] == TerminalMode.TAB  # terminal mode
        assert call[3] == "npm install"  # init script
        assert call[5] == "feature-with-init"  # branch name

    def test_checkout_with_complex_init_script(self, temp_repo_path):
        """Test creating worktree with complex init script."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = []
        services.git.fetch_success = True
        services.git.create_success = True

        # Create SwitchCommand
        switch_cmd = SwitchCommand(
            branch="feature-complex",
            terminal_mode=TerminalMode.WINDOW,
            init_script="echo 'Setting up...' && npm install && npm run build",
        )

        # Run command
        checkout.checkout_branch(switch_cmd, services)

        # Verify the complex init script was passed correctly
        assert len(services.terminal.switch_calls) == 1
        call = services.terminal.switch_calls[0]
        assert call[3] == "echo 'Setting up...' && npm install && npm run build"


class TestCleanupCommand:
    """Tests for cleanup command."""

    def test_cleanup_all_mode(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test cleanup in all mode."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees
        services.git.branch_statuses = sample_branch_statuses

        # Mock user confirmation and print output
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):  # Suppress print output
            cleanup_cmd = CleanupCommand(mode=CleanupMode.ALL)
            cleanup.cleanup_worktrees(cleanup_cmd, services)

        # Verify git operations
        assert services.git.fetch_called
        assert len(services.git.remove_worktree_calls) == len(sample_branch_statuses)

    def test_cleanup_remoteless_mode(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test cleanup in remoteless mode."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees
        services.git.branch_statuses = sample_branch_statuses

        # Mock user confirmation and print output
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):  # Suppress print output
            cleanup_cmd = CleanupCommand(mode=CleanupMode.REMOTELESS)
            cleanup.cleanup_worktrees(cleanup_cmd, services)

        # Verify git operations
        assert services.git.fetch_called

    def test_cleanup_merged_mode(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test cleanup in merged mode."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees
        services.git.branch_statuses = sample_branch_statuses

        # Mock user confirmation and print output
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):  # Suppress print output
            cleanup_cmd = CleanupCommand(mode=CleanupMode.MERGED)
            cleanup.cleanup_worktrees(cleanup_cmd, services)

        # Verify git operations
        assert services.git.fetch_called

    def test_cleanup_with_processes(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test cleanup with running processes."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees
        services.git.branch_statuses = sample_branch_statuses
        # Add mock processes to terminate (empty for now)
        services.process.processes = []

        # Mock user confirmation and print output
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):  # Suppress print output
            cleanup_cmd = CleanupCommand(mode=CleanupMode.ALL)
            cleanup.cleanup_worktrees(cleanup_cmd, services)

        # Verify operations
        assert services.git.fetch_called

    def test_cleanup_cancel(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test canceling cleanup."""
        # Setup mocks
        services = MockServices()
        services.git.repo_root = temp_repo_path
        services.git.worktrees = sample_worktrees
        services.git.branch_statuses = sample_branch_statuses

        # Mock user cancellation and print output
        with (
            patch("builtins.input", return_value="n"),
            patch("builtins.print"),
        ):  # Suppress print output
            cleanup_cmd = CleanupCommand(mode=CleanupMode.ALL)
            cleanup.cleanup_worktrees(cleanup_cmd, services)

        # Verify no removal calls were made
        assert len(services.git.remove_worktree_calls) == 0
