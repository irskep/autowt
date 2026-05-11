"""Tests for the hook command."""

from pathlib import Path
from unittest.mock import patch

from autowt.commands.hook import run_hook_command
from autowt.hooks import HookType
from autowt.models import WorktreeInfo


class TestRunHookCommand:
    def setup_method(self):
        self.repo_root = Path("/repo")
        self.main_repo_dir = Path("/repo-main")

    def _configure_services(self, mock_services):
        mock_services.git.repo_root = self.repo_root
        mock_services.git.current_branch = "feature/test"
        mock_services.git.worktrees = [
            WorktreeInfo(branch="main", path=self.main_repo_dir, is_primary=True),
            WorktreeInfo(branch="feature/test", path=self.repo_root, is_primary=False),
        ]

    def test_runs_global_and_project_scripts(self, mock_services):
        self._configure_services(mock_services)
        mock_services.hooks.run_hooks_success = True

        with patch(
            "autowt.commands.hook.extract_hook_scripts",
            return_value=(["echo global"], ["echo project"]),
        ):
            result = run_hook_command(HookType.SESSION_INIT, mock_services)

        assert result is True
        assert len(mock_services.hooks.run_hook_calls) == 2
        # Global script runs first
        assert mock_services.hooks.run_hook_calls[0][0] == "echo global"
        assert mock_services.hooks.run_hook_calls[0][1] == HookType.SESSION_INIT
        # Project script runs second
        assert mock_services.hooks.run_hook_calls[1][0] == "echo project"

    def test_passes_correct_paths(self, mock_services):
        self._configure_services(mock_services)
        mock_services.hooks.run_hooks_success = True

        with patch(
            "autowt.commands.hook.extract_hook_scripts",
            return_value=(["echo test"], []),
        ):
            run_hook_command(HookType.POST_CREATE, mock_services)

        call = mock_services.hooks.run_hook_calls[0]
        assert call[2] == self.repo_root  # worktree_dir
        assert call[3] == self.main_repo_dir  # main_repo_dir
        assert call[4] == "feature/test"  # branch_name

    def test_no_scripts_configured(self, mock_services):
        self._configure_services(mock_services)

        with patch(
            "autowt.commands.hook.extract_hook_scripts",
            return_value=([], []),
        ):
            result = run_hook_command(HookType.SESSION_INIT, mock_services)

        assert result is True
        assert len(mock_services.hooks.run_hook_calls) == 0

    def test_hook_failure_stops_and_returns_false(self, mock_services):
        self._configure_services(mock_services)
        mock_services.hooks.run_hooks_success = False

        with patch(
            "autowt.commands.hook.extract_hook_scripts",
            return_value=(["echo first", "echo second"], []),
        ):
            result = run_hook_command(HookType.PRE_CLEANUP, mock_services)

        assert result is False
        # Stops after first failure
        assert len(mock_services.hooks.run_hook_calls) == 1

    def test_not_in_git_repo(self, mock_services):
        mock_services.git.repo_root = None

        result = run_hook_command(HookType.SESSION_INIT, mock_services)

        assert result is False

    def test_no_current_branch(self, mock_services):
        mock_services.git.repo_root = self.repo_root
        mock_services.git.current_branch = None

        result = run_hook_command(HookType.SESSION_INIT, mock_services)

        assert result is False

    def test_falls_back_to_repo_root_when_no_primary(self, mock_services):
        mock_services.git.repo_root = self.repo_root
        mock_services.git.current_branch = "main"
        mock_services.git.worktrees = []  # No worktrees found
        mock_services.hooks.run_hooks_success = True

        with patch(
            "autowt.commands.hook.extract_hook_scripts",
            return_value=(["echo test"], []),
        ):
            run_hook_command(HookType.SESSION_INIT, mock_services)

        call = mock_services.hooks.run_hook_calls[0]
        # Both worktree_dir and main_repo_dir should be repo_root
        assert call[2] == self.repo_root
        assert call[3] == self.repo_root
