"""Tests for checkout command hook execution."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from autowt.commands.checkout import _run_hook_set
from autowt.hooks import HookType
from autowt.models import TerminalMode
from tests.helpers import assert_hook_called_with, assert_hooks_not_called


class TestCheckoutHooks:
    """Tests for hook execution during checkout."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worktree_dir = Path("/tmp/test-worktree")
        self.repo_dir = Path("/tmp/test-repo")
        self.branch_name = "feature/test-branch"

    def test_run_pre_create_hooks_with_scripts(self, mock_services):
        """Test that pre_create hooks are executed when scripts are present."""
        # Set up mock configuration
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config
        mock_services.hooks.run_hooks_success = True

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["echo 'global pre_create'"]
        project_scripts = ["echo 'project pre_create'"]

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ) as mock_extract:
            result = _run_hook_set(
                mock_services,
                HookType.PRE_CREATE,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=True,
            )

            assert result is True

            # Verify extract_hook_scripts was called correctly
            mock_extract.assert_called_once_with(
                mock_global_config, mock_project_config, HookType.PRE_CREATE
            )

            # Verify hooks were called with correct parameters
            assert_hook_called_with(
                mock_services,
                global_scripts,
                project_scripts,
                HookType.PRE_CREATE,
                self.worktree_dir,
                self.repo_dir,
                self.branch_name,
            )

    def test_run_pre_create_hooks_no_scripts(self, mock_services):
        """Test that function returns True when no pre_create scripts are present."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config

        # Mock extract_hook_scripts to return empty scripts
        with patch(
            "autowt.commands.checkout.extract_hook_scripts", return_value=([], [])
        ):
            result = _run_hook_set(
                mock_services,
                HookType.PRE_CREATE,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=True,
            )

            assert result is True
            assert_hooks_not_called(mock_services)

    def test_run_pre_create_hooks_failure(self, mock_services):
        """Test that function returns False when hooks fail."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config
        mock_services.hooks.run_hooks_success = False  # Simulate failure

        global_scripts = ["exit 1"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            result = _run_hook_set(
                mock_services,
                HookType.PRE_CREATE,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=True,
            )

            assert result is False
            # Verify hooks were attempted
            assert len(mock_services.hooks.run_hooks_calls) == 1

    def test_run_post_create_hooks_with_scripts(self, mock_services):
        """Test that post_create hooks are executed when scripts are present."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config
        mock_services.hooks.run_hooks_success = True

        global_scripts = ["echo 'global post_create'"]
        project_scripts = ["echo 'project post_create'"]

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ) as mock_extract:
            result = _run_hook_set(
                mock_services,
                HookType.POST_CREATE,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=True,
            )

            assert result is True

            mock_extract.assert_called_once_with(
                mock_global_config, mock_project_config, HookType.POST_CREATE
            )

            assert_hook_called_with(
                mock_services,
                global_scripts,
                project_scripts,
                HookType.POST_CREATE,
                self.worktree_dir,
                self.repo_dir,
                self.branch_name,
            )

    def test_run_post_create_hooks_no_scripts(self, mock_services):
        """Test that function returns True when no post_create scripts are present."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config

        with patch(
            "autowt.commands.checkout.extract_hook_scripts", return_value=([], [])
        ):
            result = _run_hook_set(
                mock_services,
                HookType.POST_CREATE,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=True,
            )

            assert result is True
            assert_hooks_not_called(mock_services)

    def test_run_post_create_hooks_failure(self, mock_services):
        """Test that function returns False when hooks fail."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config
        mock_services.hooks.run_hooks_success = False

        global_scripts = ["exit 1"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            result = _run_hook_set(
                mock_services,
                HookType.POST_CREATE,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=True,
            )

            assert result is False
            assert len(mock_services.hooks.run_hooks_calls) == 1

    def test_post_create_hooks_working_directory(self, mock_services):
        """Test that post_create hooks run in the worktree directory."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config
        mock_services.hooks.run_hooks_success = True

        global_scripts = ["pwd > working_dir.txt"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            _run_hook_set(
                mock_services,
                HookType.POST_CREATE,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=True,
            )

            # Verify the working directory passed to hooks is the worktree directory
            call_args = mock_services.hooks.run_hooks_calls[0]
            assert call_args[3] == self.worktree_dir


class TestPostCreateAsyncHooks:
    """Tests for post_create_async hook execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worktree_dir = Path("/tmp/test-worktree")
        self.repo_dir = Path("/tmp/test-repo")
        self.branch_name = "feature/test-branch"

    def test_run_post_create_async_hooks_with_scripts(self, mock_services):
        """Test that post_create_async hooks are executed when scripts are present."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config
        mock_services.hooks.run_hooks_success = True

        global_scripts = ["npm install"]
        project_scripts = ["poetry install"]

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            _run_hook_set(
                mock_services,
                HookType.POST_CREATE_ASYNC,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=False,
            )

            # Verify hooks were called
            assert_hook_called_with(
                mock_services,
                global_scripts,
                project_scripts,
                HookType.POST_CREATE_ASYNC,
                self.worktree_dir,
                self.repo_dir,
                self.branch_name,
            )

    def test_run_post_create_async_hooks_no_scripts(self, mock_services):
        """Test that function does nothing when no post_create_async scripts are present."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config

        with patch(
            "autowt.commands.checkout.extract_hook_scripts", return_value=([], [])
        ):
            _run_hook_set(
                mock_services,
                HookType.POST_CREATE_ASYNC,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=False,
            )

            assert_hooks_not_called(mock_services)

    def test_run_post_create_async_hooks_failure_shows_warning(
        self, mock_services, capsys
    ):
        """Test that function shows warning but continues when hooks fail."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config
        mock_services.hooks.run_hooks_success = False  # Simulate failure

        global_scripts = ["exit 1"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            # Should not raise exception
            _run_hook_set(
                mock_services,
                HookType.POST_CREATE_ASYNC,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=False,
            )

            # Verify hooks were called despite failure
            assert len(mock_services.hooks.run_hooks_calls) == 1

            # Verify warning message was printed
            captured = capsys.readouterr()
            assert "Warning" in captured.out or "Warning" in captured.err

    def test_post_create_async_hooks_working_directory(self, mock_services):
        """Test that post_create_async hooks run in the worktree directory."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()
        mock_services.config_loader.configs["default"] = mock_global_config
        mock_services.hooks.run_hooks_success = True

        global_scripts = ["pwd"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            _run_hook_set(
                mock_services,
                HookType.POST_CREATE_ASYNC,
                self.worktree_dir,
                self.repo_dir,
                mock_project_config,
                self.branch_name,
                abort_on_failure=False,
            )

            # Verify the working directory passed to hooks is the worktree directory
            call_args = mock_services.hooks.run_hooks_calls[0]
            assert call_args[3] == self.worktree_dir


class TestPostCreateAsyncTiming:
    """Integration tests for post_create_async hook timing in checkout flow."""

    def test_echo_mode_runs_async_before_switch(self):
        """Test that ECHO mode is categorized to run async hooks before switch."""
        # ECHO mode should run post_create_async before switch
        assert TerminalMode.ECHO in (TerminalMode.ECHO, TerminalMode.INPLACE)

    def test_tab_mode_runs_async_after_switch(self):
        """Test that TAB mode is categorized to run async hooks after switch."""
        # TAB mode should run post_create_async after switch
        assert TerminalMode.TAB not in (TerminalMode.ECHO, TerminalMode.INPLACE)

    def test_inplace_mode_runs_async_before_switch(self):
        """Test that INPLACE mode is categorized to run async hooks before switch."""
        # INPLACE mode should run post_create_async before switch
        assert TerminalMode.INPLACE in (TerminalMode.ECHO, TerminalMode.INPLACE)
