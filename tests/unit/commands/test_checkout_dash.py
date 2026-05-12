"""Tests for 'autowt -' (switch to previous worktree)."""

from pathlib import Path
from unittest.mock import patch

from autowt.commands.checkout import checkout_branch
from autowt.models import SwitchCommand, TerminalMode, WorktreeInfo


class TestDashSwitchesToPrevious:
    def setup_method(self):
        self.repo_path = Path("/repo")
        self.worktree_a = Path("/worktrees/branch-a")
        self.worktree_b = Path("/worktrees/branch-b")

    def test_dash_resolves_to_previous_branch(self, mock_services):
        mock_services.git.repo_root = self.repo_path
        mock_services.git.current_branch = "branch-a"
        mock_services.git.worktrees = [
            WorktreeInfo(branch="main", path=self.repo_path, is_primary=True),
            WorktreeInfo(branch="branch-a", path=self.worktree_a),
            WorktreeInfo(branch="branch-b", path=self.worktree_b),
        ]
        mock_services.terminal.switch_success = True
        mock_services.state.set_previous_worktree_branch(self.repo_path, "branch-b")

        switch_cmd = SwitchCommand(branch="-", terminal_mode=TerminalMode.ECHO)

        with patch("autowt.commands.checkout.Path.cwd", return_value=self.worktree_a):
            checkout_branch(switch_cmd, mock_services)

        assert mock_services.terminal.switch_calls
        call = mock_services.terminal.switch_calls[0]
        assert call[0] == self.worktree_b

    def test_dash_with_no_previous_prints_error(self, mock_services, capsys):
        mock_services.git.repo_root = self.repo_path
        mock_services.git.current_branch = "branch-a"

        switch_cmd = SwitchCommand(branch="-", terminal_mode=TerminalMode.ECHO)
        checkout_branch(switch_cmd, mock_services)

        # No switch should have happened
        assert not mock_services.terminal.switch_calls

    def test_switching_records_previous(self, mock_services):
        mock_services.git.repo_root = self.repo_path
        mock_services.git.current_branch = "branch-a"
        mock_services.git.worktrees = [
            WorktreeInfo(branch="main", path=self.repo_path, is_primary=True),
            WorktreeInfo(branch="branch-a", path=self.worktree_a),
            WorktreeInfo(branch="branch-b", path=self.worktree_b),
        ]
        mock_services.terminal.switch_success = True

        switch_cmd = SwitchCommand(branch="branch-b", terminal_mode=TerminalMode.ECHO)

        with patch("autowt.commands.checkout.Path.cwd", return_value=self.worktree_a):
            checkout_branch(switch_cmd, mock_services)

        assert (
            mock_services.state.get_previous_worktree_branch(self.repo_path)
            == "branch-a"
        )
