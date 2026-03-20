"""Tests for duplicate hook execution bug.

When _run_hook_set receives a merged (global+project) config as the `config`
parameter — which is what _create_new_worktree always passes — and the project
config does NOT override a global hook, the global hook script appears in BOTH
global_scripts and project_scripts, causing it to execute twice.

This is because:
  1. _run_hook_set loads global config: services.config_loader.load_config(project_dir=None)
  2. The `config` param was loaded as: services.state.load_config(project_dir=repo_path)
     which merges global + project configs
  3. extract_hook_scripts extracts the same script from both configs
  4. The script runs twice
"""

from pathlib import Path

from autowt.commands.checkout import _run_hook_set
from autowt.config import Config, ScriptsConfig
from autowt.hooks import HookType


class TestDuplicateHookExecution:
    """Regression tests: global hooks must not run twice when project has no override."""

    def setup_method(self):
        self.worktree_dir = Path("/tmp/test-worktree")
        self.repo_dir = Path("/tmp/test-repo")
        self.branch_name = "feature/test"
        self.global_post_create = "echo 'running post_create hook'"

    def test_global_hook_runs_exactly_once_when_project_has_no_override(
        self, mock_services
    ):
        """A global post_create hook should run once, not twice.

        Reproduces the real-world scenario: global config defines post_create,
        project config has no post_create override. The merged config (global+project)
        inherits the global post_create, so extract_hook_scripts finds it in both
        the global config AND the merged config passed as "project" config.
        """
        # Global config: has a post_create hook
        global_config = Config(
            scripts=ScriptsConfig(post_create=self.global_post_create)
        )

        # Merged config (global + project): project didn't override post_create,
        # so merged config still has the global post_create.
        # This is what services.state.load_config(project_dir=repo_path) returns.
        merged_config = Config(
            scripts=ScriptsConfig(post_create=self.global_post_create)
        )

        # Wire up: config_loader.load_config(project_dir=None) returns global config
        mock_services.config_loader.configs["default"] = global_config
        mock_services.hooks.run_hooks_success = True

        # Call _run_hook_set with the merged config (as checkout.py does)
        _run_hook_set(
            mock_services,
            HookType.POST_CREATE,
            self.worktree_dir,
            self.repo_dir,
            merged_config,  # This is the merged config, same as real usage
            self.branch_name,
            abort_on_failure=True,
        )

        # The hook script should run exactly ONCE
        assert len(mock_services.hooks.run_hook_calls) == 1, (
            f"Expected hook to run exactly 1 time, but it ran "
            f"{len(mock_services.hooks.run_hook_calls)} times. "
            f"Scripts executed: {[c[0] for c in mock_services.hooks.run_hook_calls]}"
        )

    def test_global_hook_runs_exactly_once_when_no_project_config_exists(
        self, mock_services
    ):
        """Same bug triggers even with no project config file at all.

        When there's no project .autowt.toml, the merged config IS the global config.
        extract_hook_scripts still finds the hook in both parameters.
        """
        global_config = Config(
            scripts=ScriptsConfig(post_create=self.global_post_create)
        )

        # No project config means merged config == global config
        merged_config = global_config

        mock_services.config_loader.configs["default"] = global_config
        mock_services.hooks.run_hooks_success = True

        _run_hook_set(
            mock_services,
            HookType.POST_CREATE,
            self.worktree_dir,
            self.repo_dir,
            merged_config,
            self.branch_name,
            abort_on_failure=True,
        )

        assert len(mock_services.hooks.run_hook_calls) == 1, (
            f"Expected hook to run exactly 1 time, but it ran "
            f"{len(mock_services.hooks.run_hook_calls)} times"
        )

    def test_distinct_global_and_project_hooks_both_run(self, mock_services):
        """When global and project have DIFFERENT hooks, both should run."""
        global_hook = "echo 'global hook'"
        project_hook = "echo 'project hook'"

        global_config = Config(scripts=ScriptsConfig(post_create=global_hook))

        # Project config overrides with a different hook
        merged_config = Config(scripts=ScriptsConfig(post_create=project_hook))

        mock_services.config_loader.configs["default"] = global_config
        mock_services.hooks.run_hooks_success = True

        _run_hook_set(
            mock_services,
            HookType.POST_CREATE,
            self.worktree_dir,
            self.repo_dir,
            merged_config,
            self.branch_name,
            abort_on_failure=True,
        )

        # Both distinct hooks should run
        assert len(mock_services.hooks.run_hook_calls) == 2, (
            f"Expected 2 hook calls (global + project), "
            f"got {len(mock_services.hooks.run_hook_calls)}"
        )
        scripts_run = [c[0] for c in mock_services.hooks.run_hook_calls]
        assert global_hook in scripts_run
        assert project_hook in scripts_run
