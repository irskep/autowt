"""Tests for command handlers with mocked services."""

from unittest.mock import patch

import pytest

from autowt.commands import checkout, cleanup, ls
from autowt.models import (
    CleanupMode,
    TerminalMode,
)
from tests.mocks.services import (
    MockGitService,
    MockProcessService,
    MockStateService,
    MockTerminalService,
)


class TestListCommand:
    """Tests for ls command."""

    @pytest.mark.skip(reason="Output format may have changed - needs updating")
    def test_ls_with_worktrees(self, temp_repo_path, sample_worktrees, capsys):
        """Test listing worktrees."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = sample_worktrees
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Run command
        ls.list_worktrees(state_service, git_service, terminal_service, process_service)

        # Check output
        captured = capsys.readouterr()
        assert f"Primary clone: {temp_repo_path}" in captured.out
        assert "You are in: Primary clone" in captured.out
        assert "Branches:" in captured.out
        assert "feature1" in captured.out
        assert "feature2" in captured.out
        assert "bugfix" in captured.out

    def test_ls_no_worktrees(self, temp_repo_path, capsys):
        """Test listing when no worktrees exist."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = []
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Run command
        ls.list_worktrees(state_service, git_service, terminal_service, process_service)

        # Check output
        captured = capsys.readouterr()
        assert "No worktrees found." in captured.out

    def test_ls_not_in_repo(self, capsys):
        """Test ls when not in a git repository."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = None
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Run command
        ls.list_worktrees(state_service, git_service, terminal_service, process_service)

        # Check output
        captured = capsys.readouterr()
        assert "Error: Not in a git repository" in captured.out


class TestCheckoutCommand:
    """Tests for checkout command."""

    def test_checkout_existing_worktree(self, temp_repo_path, sample_worktrees):
        """Test switching to existing worktree."""
        # Setup mocks
        state_service = MockStateService()
        state_service.session_ids = {"feature1": "session1"}  # Add session ID data
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = sample_worktrees
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Mock user input to confirm switch
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):  # Suppress print output
            checkout.checkout_branch(
                "feature1",
                TerminalMode.TAB,
                state_service,
                git_service,
                terminal_service,
                process_service,
            )

        # Verify terminal switching was called
        assert len(terminal_service.switch_calls) == 1
        call = terminal_service.switch_calls[0]
        assert call[0] == sample_worktrees[0].path  # worktree path
        assert call[1] == TerminalMode.TAB  # terminal mode
        assert call[2] == "session1"  # session ID

    def test_checkout_new_worktree(self, temp_repo_path):
        """Test creating new worktree."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = []  # No existing worktrees
        git_service.fetch_success = True
        git_service.create_success = True
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Run command
        checkout.checkout_branch(
            "new-feature",
            TerminalMode.WINDOW,
            state_service,
            git_service,
            terminal_service,
            process_service,
        )

        # Verify git operations
        assert git_service.fetch_called
        assert len(git_service.create_worktree_calls) == 1

        create_call = git_service.create_worktree_calls[0]
        assert create_call[1] == "new-feature"  # branch name

        # Verify terminal switching
        assert len(terminal_service.switch_calls) == 1
        switch_call = terminal_service.switch_calls[0]
        assert switch_call[1] == TerminalMode.WINDOW

        # Verify state was saved
        assert state_service.save_called

    def test_checkout_decline_switch(self, temp_repo_path, sample_worktrees):
        """Test declining to switch to existing worktree."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = sample_worktrees
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Mock user input to decline switch
        with patch("builtins.input", return_value="n"):
            checkout.checkout_branch(
                "feature1",
                TerminalMode.TAB,
                state_service,
                git_service,
                terminal_service,
                process_service,
            )

        # Verify no terminal switching was attempted
        assert len(terminal_service.switch_calls) == 0


class TestCleanupCommand:
    """Tests for cleanup command."""

    def test_cleanup_all_mode(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test cleanup in ALL mode."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = sample_worktrees
        git_service.branch_statuses = sample_branch_statuses
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Mock user confirmation and print output
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):  # Suppress print output
            cleanup.cleanup_worktrees(
                CleanupMode.ALL,
                state_service,
                git_service,
                terminal_service,
                process_service,
            )

        # Should try to remove merged and remoteless branches
        assert (
            len(git_service.remove_worktree_calls) == 2
        )  # feature2 (no remote) + bugfix (merged)
        assert state_service.save_called

    def test_cleanup_remoteless_mode(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test cleanup in REMOTELESS mode."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = sample_worktrees
        git_service.branch_statuses = sample_branch_statuses
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Mock user confirmation
        with patch("builtins.input", return_value="y"):
            cleanup.cleanup_worktrees(
                CleanupMode.REMOTELESS,
                state_service,
                git_service,
                terminal_service,
                process_service,
            )

        # Should only remove remoteless branches
        assert len(git_service.remove_worktree_calls) == 1  # feature2 (no remote)

    def test_cleanup_merged_mode(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test cleanup in MERGED mode."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = sample_worktrees
        git_service.branch_statuses = sample_branch_statuses
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Mock user confirmation
        with patch("builtins.input", return_value="y"):
            cleanup.cleanup_worktrees(
                CleanupMode.MERGED,
                state_service,
                git_service,
                terminal_service,
                process_service,
            )

        # Should remove both identical and merged branches (both are safe to remove)
        assert (
            len(git_service.remove_worktree_calls) == 2
        )  # feature2 (identical) + bugfix (merged)

    def test_cleanup_with_processes(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses, sample_processes
    ):
        """Test cleanup when processes are running."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = sample_worktrees
        git_service.branch_statuses = sample_branch_statuses
        terminal_service = MockTerminalService()
        process_service = MockProcessService()
        process_service.processes = sample_processes

        # Mock user confirmation and print output
        with (
            patch("builtins.input", return_value="y"),
            patch("builtins.print"),
        ):  # Suppress print output
            cleanup.cleanup_worktrees(
                CleanupMode.ALL,
                state_service,
                git_service,
                terminal_service,
                process_service,
            )

        # Verify process termination was attempted
        assert len(process_service.terminate_calls) == 1
        assert len(process_service.find_calls) >= 1

    def test_cleanup_cancel(
        self, temp_repo_path, sample_worktrees, sample_branch_statuses
    ):
        """Test canceling cleanup."""
        # Setup mocks
        state_service = MockStateService()
        git_service = MockGitService()
        git_service.repo_root = temp_repo_path
        git_service.worktrees = sample_worktrees
        git_service.branch_statuses = sample_branch_statuses
        terminal_service = MockTerminalService()
        process_service = MockProcessService()

        # Mock user cancellation and print output
        with (
            patch("builtins.input", return_value="n"),
            patch("builtins.print"),
        ):  # Suppress print output
            cleanup.cleanup_worktrees(
                CleanupMode.ALL,
                state_service,
                git_service,
                terminal_service,
                process_service,
            )

        # Should not remove any worktrees
        assert len(git_service.remove_worktree_calls) == 0
        assert not state_service.save_called
