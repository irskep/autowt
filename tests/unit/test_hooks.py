"""Unit tests for lifecycle hooks functionality."""

import os
import tempfile
from pathlib import Path
from subprocess import TimeoutExpired
from unittest.mock import MagicMock, patch

import pytest

from autowt.hooks import HookRunner, HookType, extract_hook_scripts


class TestHookRunner:
    """Test the HookRunner class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.hook_runner = HookRunner()
        self.test_worktree_dir = Path("/tmp/test-worktree")
        self.test_main_repo_dir = Path("/tmp/test-main-repo")
        self.test_branch_name = "feature/test-branch"

    @patch("subprocess.run")
    def test_run_hook_success(self, mock_subprocess_run):
        """Test successful hook execution."""
        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Hook executed successfully"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        # Run the hook
        success = self.hook_runner.run_hook(
            "echo 'test hook'",
            HookType.SESSION_INIT,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )

        # Verify success
        assert success is True

        # Verify subprocess was called with correct parameters
        mock_subprocess_run.assert_called_once()
        call_args = mock_subprocess_run.call_args

        # Check that the command is the raw hook script (no arguments appended)
        command = call_args[0][0]
        assert command == "echo 'test hook'"

        # Check keyword arguments
        kwargs = call_args[1]
        assert kwargs["shell"] is True
        assert kwargs["cwd"] == str(self.test_worktree_dir)
        assert kwargs["timeout"] == 60

        # Check environment variables are set
        env = kwargs["env"]
        assert env["AUTOWT_WORKTREE_DIR"] == str(self.test_worktree_dir)
        assert env["AUTOWT_MAIN_REPO_DIR"] == str(self.test_main_repo_dir)
        assert env["AUTOWT_BRANCH_NAME"] == self.test_branch_name
        assert env["AUTOWT_HOOK_TYPE"] == HookType.SESSION_INIT

    @patch("subprocess.run")
    def test_run_hook_failure(self, mock_subprocess_run):
        """Test hook execution failure."""
        # Mock failed subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command failed"
        mock_subprocess_run.return_value = mock_result

        # Run the hook
        success = self.hook_runner.run_hook(
            "exit 1",
            HookType.PRE_CLEANUP,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )

        # Verify failure
        assert success is False

    @patch("subprocess.run")
    def test_run_hook_timeout(self, mock_subprocess_run):
        """Test hook execution timeout."""
        # Mock timeout
        mock_subprocess_run.side_effect = TimeoutExpired("cmd", 5)

        # Run the hook
        success = self.hook_runner.run_hook(
            "sleep 10",
            HookType.POST_SWITCH,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
            timeout=5,
        )

        # Verify failure due to timeout
        assert success is False

    def test_run_hook_empty_script(self):
        """Test that empty scripts are handled gracefully."""
        # Test with None
        success = self.hook_runner.run_hook(
            None,
            HookType.SESSION_INIT,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )
        assert success is True

        # Test with empty string
        success = self.hook_runner.run_hook(
            "",
            HookType.SESSION_INIT,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )
        assert success is True

        # Test with whitespace only
        success = self.hook_runner.run_hook(
            "   \t\n  ",
            HookType.SESSION_INIT,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )
        assert success is True

    @patch("subprocess.run")
    def test_run_hooks_global_and_project(self, mock_subprocess_run):
        """Test running both global and project hooks."""
        # Mock successful subprocess runs
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        global_scripts = ["echo 'global hook 1'", "echo 'global hook 2'"]
        project_scripts = ["echo 'project hook 1'"]

        # Run the hooks
        success = self.hook_runner.run_hooks(
            global_scripts,
            project_scripts,
            HookType.PRE_CLEANUP,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )

        # Verify success
        assert success is True

        # Verify all 3 hooks were called (2 global + 1 project)
        assert mock_subprocess_run.call_count == 3

        # Verify order: global hooks first, then project hooks
        calls = mock_subprocess_run.call_args_list
        assert "global hook 1" in calls[0][0][0]
        assert "global hook 2" in calls[1][0][0]
        assert "project hook 1" in calls[2][0][0]

    @patch("subprocess.run")
    def test_run_hooks_failure_stops_execution(self, mock_subprocess_run):
        """Test that hook failure stops execution of remaining hooks."""
        # First call succeeds, second fails
        mock_results = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="Failed"),
        ]
        mock_subprocess_run.side_effect = mock_results

        global_scripts = ["echo 'will succeed'", "exit 1", "echo 'will not run'"]
        project_scripts = ["echo 'will not run either'"]

        # Run the hooks
        success = self.hook_runner.run_hooks(
            global_scripts,
            project_scripts,
            HookType.POST_CLEANUP,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )

        # Verify failure
        assert success is False

        # Verify only 2 hooks were called (first succeeded, second failed, rest skipped)
        assert mock_subprocess_run.call_count == 2

    def test_run_hooks_empty_scripts(self):
        """Test that empty script lists are handled gracefully."""
        success = self.hook_runner.run_hooks(
            [],  # No global scripts
            [],  # No project scripts
            HookType.SESSION_INIT,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )
        assert success is True

    def test_prepare_environment(self):
        """Test environment variable preparation."""
        # Test the private method
        env = self.hook_runner._prepare_environment(
            HookType.PRE_SWITCH,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )

        # Verify autowt-specific variables are set
        assert env["AUTOWT_WORKTREE_DIR"] == str(self.test_worktree_dir)
        assert env["AUTOWT_MAIN_REPO_DIR"] == str(self.test_main_repo_dir)
        assert env["AUTOWT_BRANCH_NAME"] == self.test_branch_name
        assert env["AUTOWT_HOOK_TYPE"] == HookType.PRE_SWITCH

        # Verify original environment is preserved
        assert "PATH" in env  # Should have system PATH
        assert env.get("HOME") == os.environ.get("HOME")

    @patch("subprocess.run")
    def test_multiline_script_preserved(self, mock_subprocess_run):
        """Test that multiline scripts are passed through unchanged."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        multiline_script = """
        echo 'line 1'
        echo 'line 2'
        echo 'line 3'
        """

        # Run the hook
        success = self.hook_runner.run_hook(
            multiline_script,
            HookType.SESSION_INIT,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )

        assert success is True

        # Verify the script was passed as-is (no normalization)
        call_args = mock_subprocess_run.call_args
        command = call_args[0][0]
        assert command == multiline_script  # Script should be unchanged
        assert "\n" in command  # Newlines should be preserved

    @patch("subprocess.run")
    def test_pre_create_hook_runs_in_main_repo_dir(self, mock_subprocess_run):
        """Test that pre_create hooks run in main repo directory since worktree doesn't exist yet."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        # Run pre_create hook
        success = self.hook_runner.run_hook(
            "echo 'pre_create'",
            HookType.PRE_CREATE,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )

        assert success is True

        # Verify hook ran in main repo directory (not worktree which doesn't exist yet)
        call_args = mock_subprocess_run.call_args
        kwargs = call_args[1]
        assert kwargs["cwd"] == str(self.test_main_repo_dir)

        # Verify worktree dir is still set in environment variable for future reference
        env = kwargs["env"]
        assert env["AUTOWT_WORKTREE_DIR"] == str(self.test_worktree_dir)
        assert env["AUTOWT_MAIN_REPO_DIR"] == str(self.test_main_repo_dir)

    @patch("subprocess.run")
    def test_post_cleanup_hook_runs_in_main_repo_dir(self, mock_subprocess_run):
        """Test that post_cleanup hooks run in main repo directory since worktree was deleted."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        # Run post_cleanup hook
        success = self.hook_runner.run_hook(
            "echo 'post_cleanup'",
            HookType.POST_CLEANUP,
            self.test_worktree_dir,
            self.test_main_repo_dir,
            self.test_branch_name,
        )

        assert success is True

        # Verify hook ran in main repo directory (not worktree which was deleted)
        call_args = mock_subprocess_run.call_args
        kwargs = call_args[1]
        assert kwargs["cwd"] == str(self.test_main_repo_dir)

        # Verify worktree dir is still set in environment variable for reference
        env = kwargs["env"]
        assert env["AUTOWT_WORKTREE_DIR"] == str(self.test_worktree_dir)
        assert env["AUTOWT_MAIN_REPO_DIR"] == str(self.test_main_repo_dir)

    @patch("subprocess.run")
    def test_other_hooks_run_in_worktree_dir(self, mock_subprocess_run):
        """Test that hooks other than pre_create and post_cleanup run in worktree directory."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        # Test various hook types that should run in worktree directory
        hook_types = [
            HookType.POST_CREATE,
            HookType.SESSION_INIT,
            HookType.PRE_CLEANUP,
            HookType.PRE_SWITCH,
            HookType.POST_SWITCH,
            HookType.POST_CREATE_ASYNC,
        ]

        for hook_type in hook_types:
            mock_subprocess_run.reset_mock()

            success = self.hook_runner.run_hook(
                f"echo '{hook_type}'",
                hook_type,
                self.test_worktree_dir,
                self.test_main_repo_dir,
                self.test_branch_name,
            )

            assert success is True

            # Verify hook ran in worktree directory
            call_args = mock_subprocess_run.call_args
            kwargs = call_args[1]
            assert kwargs["cwd"] == str(self.test_worktree_dir), (
                f"{hook_type} should run in worktree_dir"
            )


class TestExtractHookScripts:
    """Test the extract_hook_scripts function."""

    def test_extract_from_configs(self):
        """Test extracting hook scripts from global and project configs."""
        # Mock global config - need to set specific values to avoid MagicMock default behavior
        global_config = MagicMock()
        global_config.scripts = MagicMock()
        global_config.scripts.pre_create = "global pre_create script"
        global_config.scripts.post_create = None
        global_config.scripts.session_init = "global session_init script"
        global_config.scripts.pre_cleanup = "global pre_cleanup script"
        global_config.scripts.post_cleanup = None
        global_config.scripts.pre_switch = None
        global_config.scripts.post_switch = None

        # Mock project config - need to set specific values to avoid MagicMock default behavior
        project_config = MagicMock()
        project_config.scripts = MagicMock()
        project_config.scripts.pre_create = None
        project_config.scripts.post_create = "project post_create script"
        project_config.scripts.session_init = "project session_init script"
        project_config.scripts.pre_cleanup = None
        project_config.scripts.post_cleanup = None
        project_config.scripts.pre_switch = None
        project_config.scripts.post_switch = "project post_switch script"

        # Test pre_create hook extraction
        global_scripts, project_scripts = extract_hook_scripts(
            global_config, project_config, HookType.PRE_CREATE
        )
        assert global_scripts == ["global pre_create script"]
        assert project_scripts == []

        # Test post_create hook extraction
        global_scripts, project_scripts = extract_hook_scripts(
            global_config, project_config, HookType.POST_CREATE
        )
        assert global_scripts == []
        assert project_scripts == ["project post_create script"]

        # Test init hook extraction
        global_scripts, project_scripts = extract_hook_scripts(
            global_config, project_config, HookType.SESSION_INIT
        )
        assert global_scripts == ["global session_init script"]
        assert project_scripts == ["project session_init script"]

        # Test pre_cleanup hook extraction
        global_scripts, project_scripts = extract_hook_scripts(
            global_config, project_config, HookType.PRE_CLEANUP
        )
        assert global_scripts == ["global pre_cleanup script"]
        assert project_scripts == []

        # Test post_switch hook extraction
        global_scripts, project_scripts = extract_hook_scripts(
            global_config, project_config, HookType.POST_SWITCH
        )
        assert global_scripts == []
        assert project_scripts == ["project post_switch script"]

    def test_extract_with_none_configs(self):
        """Test extracting when configs are None."""
        global_scripts, project_scripts = extract_hook_scripts(
            None, None, HookType.SESSION_INIT
        )
        assert global_scripts == []
        assert project_scripts == []

    def test_extract_with_missing_scripts_attr(self):
        """Test extracting when config objects don't have scripts attribute."""
        global_config = MagicMock()
        global_config.scripts = None

        # Create project_config without scripts attribute
        project_config = MagicMock(spec=[])  # Empty spec means no attributes

        global_scripts, project_scripts = extract_hook_scripts(
            global_config, project_config, HookType.SESSION_INIT
        )
        assert global_scripts == []
        assert project_scripts == []


class TestHookType:
    """Test the HookType constants."""

    def test_hook_type_constants(self):
        """Test that all hook type constants are defined correctly."""
        assert HookType.PRE_CREATE == "pre_create"
        assert HookType.POST_CREATE == "post_create"
        assert HookType.SESSION_INIT == "session_init"
        assert HookType.PRE_CLEANUP == "pre_cleanup"
        assert HookType.POST_CLEANUP == "post_cleanup"
        assert HookType.PRE_SWITCH == "pre_switch"
        assert HookType.POST_SWITCH == "post_switch"


class TestHookIntegration:
    """Integration tests for hook functionality with real subprocess calls."""

    @pytest.mark.slow
    def test_real_hook_execution(self):
        """Test actual hook execution with real subprocess (marked as slow)."""
        hook_runner = HookRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            worktree_dir = Path(temp_dir) / "worktree"
            main_repo_dir = Path(temp_dir) / "main"
            worktree_dir.mkdir()
            main_repo_dir.mkdir()

            # Test simple echo command
            success = hook_runner.run_hook(
                "echo 'Hello from hook'",
                HookType.SESSION_INIT,
                worktree_dir,
                main_repo_dir,
                "test-branch",
                timeout=10,
            )

            assert success is True

    @pytest.mark.slow
    def test_hook_environment_variables(self):
        """Test that environment variables are properly passed to hooks."""
        hook_runner = HookRunner()

        with tempfile.TemporaryDirectory() as temp_dir:
            worktree_dir = Path(temp_dir) / "worktree"
            main_repo_dir = Path(temp_dir) / "main"
            test_file = worktree_dir / "env_test.txt"
            worktree_dir.mkdir()
            main_repo_dir.mkdir()

            # Create a hook that writes environment variables to a file
            hook_script = f"""echo "WORKTREE_DIR=$AUTOWT_WORKTREE_DIR" > {test_file}
echo "MAIN_REPO_DIR=$AUTOWT_MAIN_REPO_DIR" >> {test_file}
echo "BRANCH_NAME=$AUTOWT_BRANCH_NAME" >> {test_file}
echo "HOOK_TYPE=$AUTOWT_HOOK_TYPE" >> {test_file}"""

            success = hook_runner.run_hook(
                hook_script,
                HookType.PRE_CLEANUP,
                worktree_dir,
                main_repo_dir,
                "feature/env-test",
                timeout=10,
            )

            assert success is True
            assert test_file.exists()

            # Verify environment variables were set correctly
            content = test_file.read_text()
            assert f"WORKTREE_DIR={worktree_dir}" in content
            assert f"MAIN_REPO_DIR={main_repo_dir}" in content
            assert "BRANCH_NAME=feature/env-test" in content
            assert "HOOK_TYPE=pre_cleanup" in content
