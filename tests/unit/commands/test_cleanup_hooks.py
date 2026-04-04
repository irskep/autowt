"""Tests for cleanup command hook execution."""

from autowt.commands.cleanup import cleanup_worktrees
from autowt.config import Config, HookConfig, ScriptsConfig
from autowt.models import BranchStatus, CleanupCommand, CleanupMode, WorktreeInfo


class TestCleanupHookConfigSelection:
    """Regression tests for separating merged and project-only cleanup hook config."""

    def test_cleanup_does_not_duplicate_inherited_global_hooks(
        self, mock_services, temp_repo_path
    ):
        repo_dir = temp_repo_path
        worktree_dir = temp_repo_path.parent / "test-repo-worktrees" / "feature-test"
        global_hook = "echo 'global pre_cleanup'"

        mock_services.git.repo_root = repo_dir
        mock_services.git.worktrees = [
            WorktreeInfo(branch="main", path=repo_dir, is_primary=True),
            WorktreeInfo(branch="feature/test", path=worktree_dir),
        ]
        mock_services.git.branch_statuses = [
            BranchStatus(
                branch="feature/test",
                has_remote=False,
                is_merged=True,
                is_identical=False,
                path=worktree_dir,
            )
        ]
        mock_services.state.global_hook_config = HookConfig(pre_cleanup=global_hook)
        mock_services.state.configs["default"] = Config(
            scripts=ScriptsConfig(pre_cleanup=global_hook)
        )
        mock_services.state.project_hook_configs[str(repo_dir)] = HookConfig()

        cleanup_worktrees(
            CleanupCommand(
                mode=CleanupMode.MERGED,
                auto_confirm=True,
            ),
            mock_services,
        )

        assert len(mock_services.hooks.run_hooks_calls) == 1
        global_scripts, project_scripts, *_ = mock_services.hooks.run_hooks_calls[0]
        assert global_scripts == [global_hook]
        assert project_scripts == []
