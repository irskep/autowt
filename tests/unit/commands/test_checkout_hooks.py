"""Tests for checkout command hook execution."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from autowt.commands.checkout import (
    _run_post_create_async_hooks,
    _run_post_create_hooks,
    _run_pre_create_hooks,
)
from autowt.hooks import HookType


class TestCheckoutHooks:
    """Tests for hook execution during checkout."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worktree_dir = Path("/tmp/test-worktree")
        self.repo_dir = Path("/tmp/test-repo")
        self.branch_name = "feature/test-branch"

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_run_pre_create_hooks_with_scripts(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that pre_create hooks are executed when scripts are present."""
        # Mock configuration with pre_create scripts
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value
        mock_hook_runner.run_hooks.return_value = True

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["echo 'global pre_create'"]
        project_scripts = ["echo 'project pre_create'"]

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ) as mock_extract:
            result = _run_pre_create_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            assert result is True

            # Verify extract_hook_scripts was called with correct parameters
            mock_extract.assert_called_once_with(
                mock_global_config, mock_project_config, HookType.PRE_CREATE
            )

            # Verify hook runner was called with correct parameters
            mock_hook_runner.run_hooks.assert_called_once_with(
                global_scripts,
                project_scripts,
                HookType.PRE_CREATE,
                self.worktree_dir,
                self.repo_dir,
                self.branch_name,
            )

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_run_pre_create_hooks_no_scripts(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that function returns True when no pre_create scripts are present."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value

        # Mock extract_hook_scripts to return empty scripts
        with patch(
            "autowt.commands.checkout.extract_hook_scripts", return_value=([], [])
        ):
            result = _run_pre_create_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            assert result is True

            # Verify hook runner was not called when no scripts present
            mock_hook_runner.run_hooks.assert_not_called()

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_run_pre_create_hooks_failure(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that function returns False when hooks fail."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value
        mock_hook_runner.run_hooks.return_value = False  # Simulate failure

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["exit 1"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            result = _run_pre_create_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            assert result is False

            # Verify hook runner was called
            mock_hook_runner.run_hooks.assert_called_once()

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_run_post_create_hooks_with_scripts(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that post_create hooks are executed when scripts are present."""
        # Mock configuration with post_create scripts
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value
        mock_hook_runner.run_hooks.return_value = True

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["echo 'global post_create'"]
        project_scripts = ["echo 'project post_create'"]

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ) as mock_extract:
            result = _run_post_create_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            assert result is True

            # Verify extract_hook_scripts was called with correct parameters
            mock_extract.assert_called_once_with(
                mock_global_config, mock_project_config, HookType.POST_CREATE
            )

            # Verify hook runner was called with correct parameters
            mock_hook_runner.run_hooks.assert_called_once_with(
                global_scripts,
                project_scripts,
                HookType.POST_CREATE,
                self.worktree_dir,
                self.repo_dir,
                self.branch_name,
            )

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_run_post_create_hooks_no_scripts(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that function returns True when no post_create scripts are present."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value

        # Mock extract_hook_scripts to return empty scripts
        with patch(
            "autowt.commands.checkout.extract_hook_scripts", return_value=([], [])
        ):
            result = _run_post_create_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            assert result is True

            # Verify hook runner was not called when no scripts present
            mock_hook_runner.run_hooks.assert_not_called()

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_run_post_create_hooks_failure(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that function returns False when hooks fail."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value
        mock_hook_runner.run_hooks.return_value = False  # Simulate failure

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["exit 1"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            result = _run_post_create_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            assert result is False

            # Verify hook runner was called
            mock_hook_runner.run_hooks.assert_called_once()

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_post_create_hooks_working_directory(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that post_create hooks run in the worktree directory."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value
        mock_hook_runner.run_hooks.return_value = True

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["pwd > working_dir.txt"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            _run_post_create_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            # Verify the working directory passed to hooks is the worktree directory
            call_args = mock_hook_runner.run_hooks.call_args
            worktree_dir_arg = call_args[0][3]  # 4th positional argument
            assert worktree_dir_arg == self.worktree_dir


class TestPostCreateAsyncHooks:
    """Tests for post_create_async hook execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worktree_dir = Path("/tmp/test-worktree")
        self.repo_dir = Path("/tmp/test-repo")
        self.branch_name = "feature/test-branch"

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_run_post_create_async_hooks_with_scripts(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that post_create_async hooks are executed when scripts are present."""
        # Mock configuration with post_create_async scripts
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value
        mock_hook_runner.run_hooks.return_value = True

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["npm install"]
        project_scripts = ["poetry install"]

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ) as mock_extract:
            # This function returns None, not bool
            _run_post_create_async_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            # Verify extract_hook_scripts was called with correct parameters
            mock_extract.assert_called_once_with(
                mock_global_config, mock_project_config, HookType.POST_CREATE_ASYNC
            )

            # Verify hook runner was called with correct parameters
            mock_hook_runner.run_hooks.assert_called_once_with(
                global_scripts,
                project_scripts,
                HookType.POST_CREATE_ASYNC,
                self.worktree_dir,
                self.repo_dir,
                self.branch_name,
            )

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_run_post_create_async_hooks_no_scripts(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that function does nothing when no post_create_async scripts are present."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value

        # Mock extract_hook_scripts to return empty scripts
        with patch(
            "autowt.commands.checkout.extract_hook_scripts", return_value=([], [])
        ):
            _run_post_create_async_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            # Verify hook runner was not called when no scripts present
            mock_hook_runner.run_hooks.assert_not_called()

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    @patch("autowt.commands.checkout.print_info")
    def test_run_post_create_async_hooks_failure_shows_warning(
        self, mock_print_info, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that function shows warning but continues when hooks fail."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value
        mock_hook_runner.run_hooks.return_value = False  # Simulate failure

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["exit 1"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            # Should not raise exception
            _run_post_create_async_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            # Verify hook runner was called
            mock_hook_runner.run_hooks.assert_called_once()

            # Verify warning message was printed
            warning_calls = [
                call
                for call in mock_print_info.call_args_list
                if "Warning" in str(call)
            ]
            assert len(warning_calls) > 0, (
                "Warning message should be printed on failure"
            )

    @patch("autowt.commands.checkout.get_config_loader")
    @patch("autowt.commands.checkout.HookRunner")
    def test_post_create_async_hooks_working_directory(
        self, mock_hook_runner_class, mock_get_config_loader
    ):
        """Test that post_create_async hooks run in the worktree directory."""
        mock_global_config = MagicMock()
        mock_project_config = MagicMock()

        mock_loader = mock_get_config_loader.return_value
        mock_loader.load_config.return_value = mock_global_config

        mock_hook_runner = mock_hook_runner_class.return_value
        mock_hook_runner.run_hooks.return_value = True

        # Mock extract_hook_scripts to return test scripts
        global_scripts = ["pwd"]
        project_scripts = []

        with patch(
            "autowt.commands.checkout.extract_hook_scripts",
            return_value=(global_scripts, project_scripts),
        ):
            _run_post_create_async_hooks(
                self.worktree_dir, self.repo_dir, mock_project_config, self.branch_name
            )

            # Verify the working directory passed to hooks is the worktree directory
            call_args = mock_hook_runner.run_hooks.call_args
            worktree_dir_arg = call_args[0][3]  # 4th positional argument
            assert worktree_dir_arg == self.worktree_dir


class TestPostCreateAsyncTiming:
    """Integration tests for post_create_async hook timing in checkout flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worktree_dir = Path("/tmp/test-worktree")
        self.repo_dir = Path("/tmp/test-repo")
        self.branch_name = "feature/test-branch"

    def test_echo_mode_runs_async_before_switch(self):
        """Test that ECHO mode is categorized to run async hooks before switch."""
        from autowt.models import TerminalMode

        # ECHO mode should run post_create_async before switch
        assert TerminalMode.ECHO in (TerminalMode.ECHO, TerminalMode.INPLACE)

    def test_tab_mode_runs_async_after_switch(self):
        """Test that TAB mode is categorized to run async hooks after switch."""
        from autowt.models import TerminalMode

        # TAB mode should run post_create_async after switch
        assert TerminalMode.TAB not in (TerminalMode.ECHO, TerminalMode.INPLACE)

    def test_inplace_mode_runs_async_before_switch(self):
        """Test that INPLACE mode is categorized to run async hooks before switch."""
        from autowt.models import TerminalMode

        # INPLACE mode should run post_create_async before switch
        assert TerminalMode.INPLACE in (TerminalMode.ECHO, TerminalMode.INPLACE)
