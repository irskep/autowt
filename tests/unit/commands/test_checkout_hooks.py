"""Tests for checkout command hook execution."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from autowt.commands.checkout import (
    _run_post_create_async_hooks,
    _run_post_create_hooks,
    _run_pre_create_hooks,
)
from autowt.config import Config, ScriptsConfig
from autowt.hooks import HookType
from autowt.models import TerminalMode


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

    def test_run_post_create_async_hooks_with_scripts(self):
        """Test that post_create_async hooks are executed when scripts are present."""
        # Create configs with scripts
        global_config = Config(scripts=ScriptsConfig(post_create_async="npm install"))
        project_config = Config(
            scripts=ScriptsConfig(post_create_async="poetry install")
        )

        # Create a simple mock hook runner
        class MockHookRunner:
            def __init__(self):
                self.calls = []

            def run_hooks(self, global_scripts, project_scripts, hook_type, *args):
                self.calls.append(
                    {
                        "global_scripts": global_scripts,
                        "project_scripts": project_scripts,
                        "hook_type": hook_type,
                        "args": args,
                    }
                )
                return True

        mock_hook_runner = MockHookRunner()

        # Run the function
        _run_post_create_async_hooks(
            self.worktree_dir,
            self.repo_dir,
            project_config,
            self.branch_name,
            hook_runner=mock_hook_runner,
            global_config=global_config,
        )

        # Verify hook runner was called with correct parameters
        assert len(mock_hook_runner.calls) == 1
        call = mock_hook_runner.calls[0]
        assert call["global_scripts"] == ["npm install"]
        assert call["project_scripts"] == ["poetry install"]
        assert call["hook_type"] == HookType.POST_CREATE_ASYNC
        assert call["args"] == (
            self.worktree_dir,
            self.repo_dir,
            self.branch_name,
        )

    def test_run_post_create_async_hooks_no_scripts(self):
        """Test that function does nothing when no post_create_async scripts are present."""
        # Create configs without post_create_async scripts
        global_config = Config()
        project_config = Config()

        # Create a simple mock hook runner
        class MockHookRunner:
            def __init__(self):
                self.calls = []

            def run_hooks(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                return True

        mock_hook_runner = MockHookRunner()

        # Run the function
        _run_post_create_async_hooks(
            self.worktree_dir,
            self.repo_dir,
            project_config,
            self.branch_name,
            hook_runner=mock_hook_runner,
            global_config=global_config,
        )

        # Verify hook runner was not called when no scripts present
        assert len(mock_hook_runner.calls) == 0

    def test_run_post_create_async_hooks_failure_shows_warning(self, capsys):
        """Test that function shows warning but continues when hooks fail."""
        # Create configs with scripts that will "fail"
        global_config = Config(scripts=ScriptsConfig(post_create_async="exit 1"))
        project_config = Config()

        # Create a mock hook runner that returns False (failure)
        class MockHookRunner:
            def __init__(self):
                self.called = False

            def run_hooks(self, *args, **kwargs):
                self.called = True
                return False  # Simulate failure

        mock_hook_runner = MockHookRunner()

        # Should not raise exception
        _run_post_create_async_hooks(
            self.worktree_dir,
            self.repo_dir,
            project_config,
            self.branch_name,
            hook_runner=mock_hook_runner,
            global_config=global_config,
        )

        # Verify hook runner was called
        assert mock_hook_runner.called

        # Verify warning message was printed
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Warning" in captured.err

    def test_post_create_async_hooks_working_directory(self):
        """Test that post_create_async hooks run in the worktree directory."""
        # Create configs with scripts
        global_config = Config(scripts=ScriptsConfig(post_create_async="pwd"))
        project_config = Config()

        # Create a mock hook runner that captures arguments
        class MockHookRunner:
            def __init__(self):
                self.worktree_dir = None

            def run_hooks(
                self,
                global_scripts,
                project_scripts,
                hook_type,
                worktree_dir,
                repo_dir,
                branch_name,
            ):
                self.worktree_dir = worktree_dir
                return True

        mock_hook_runner = MockHookRunner()

        # Run the function
        _run_post_create_async_hooks(
            self.worktree_dir,
            self.repo_dir,
            project_config,
            self.branch_name,
            hook_runner=mock_hook_runner,
            global_config=global_config,
        )

        # Verify the working directory passed to hooks is the worktree directory
        assert mock_hook_runner.worktree_dir == self.worktree_dir


class TestPostCreateAsyncTiming:
    """Integration tests for post_create_async hook timing in checkout flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.worktree_dir = Path("/tmp/test-worktree")
        self.repo_dir = Path("/tmp/test-repo")
        self.branch_name = "feature/test-branch"

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
