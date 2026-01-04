"""Tests for CLI command routing and argument handling."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from autowt.cli import main
from autowt.models import CleanupMode, CustomScript
from tests.fixtures.service_builders import MockServices


def create_mock_config(
    custom_scripts: dict | None = None,
    terminal_mode: str = "tab",
    session_init: str | None = None,
    always_new: bool = False,
    cleanup_mode: CleanupMode | None = None,
):
    """Create a properly structured mock config for CLI tests.

    This helper eliminates repetitive mock setup across tests.
    """
    mock_scripts = Mock()
    mock_scripts.custom = custom_scripts or {}
    mock_scripts.session_init = session_init

    mock_terminal = Mock()
    mock_terminal.mode = terminal_mode
    mock_terminal.always_new = always_new

    mock_config = Mock()
    mock_config.terminal = mock_terminal
    mock_config.scripts = mock_scripts

    if cleanup_mode is not None:
        mock_cleanup = Mock()
        mock_cleanup.default_mode = cleanup_mode
        mock_config.cleanup = mock_cleanup

    return mock_config


class TestCLIRouting:
    """Tests for CLI command routing and fallback behavior."""

    def test_explicit_commands_work(self):
        """Test that explicit subcommands work correctly."""
        runner = CliRunner()

        # Mock all the command functions to avoid actual execution
        with (
            patch("autowt.cli.list_worktrees") as mock_ls,
            patch("autowt.cli.cleanup_worktrees") as mock_cleanup,
            patch("autowt.cli.configure_settings") as mock_configure,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.is_interactive_terminal", return_value=True),
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            # Setup mock services
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_config.cleanup.default_mode = CleanupMode.INTERACTIVE
            mock_get_config.return_value = mock_config

            # Mock config loader to indicate user has configured cleanup mode
            mock_services.config_loader.user_configured_cleanup_mode = True
            # Test ls command
            result = runner.invoke(main, ["ls"])
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            assert result.exit_code == 0
            mock_ls.assert_called_once()

            # Test cleanup command
            result = runner.invoke(main, ["cleanup"])
            assert result.exit_code == 0
            mock_cleanup.assert_called_once()

            # Test config command
            result = runner.invoke(main, ["config"])
            assert result.exit_code == 0
            mock_configure.assert_called_once()

    def test_switch_command_works(self):
        """Test that explicit switch command works."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            mock_get_config.return_value = create_mock_config()

            result = runner.invoke(main, ["switch", "feature-branch"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            # Check that the SwitchCommand was created correctly
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-branch"

    def test_branch_name_fallback(self):
        """Test that unknown commands are treated as branch names."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            mock_get_config.return_value = create_mock_config()

            # Test simple branch name
            result = runner.invoke(main, ["feature-branch"])
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-branch"

            mock_checkout.reset_mock()

            # Test branch name with slashes
            result = runner.invoke(main, ["steve/bugfix"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "steve/bugfix"

    def test_terminal_option_passed_through(self):
        """Test that --terminal option is passed to checkout function."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            mock_get_config.return_value = create_mock_config()

            # Test with explicit switch command
            result = runner.invoke(
                main, ["switch", "feature-branch", "--terminal", "window"]
            )
            assert result.exit_code == 0
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-branch"
            assert switch_cmd.terminal_mode.value == "window"

            mock_checkout.reset_mock()

            # Test with branch name fallback
            result = runner.invoke(main, ["feature-branch", "--terminal", "tab"])
            assert result.exit_code == 0
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-branch"
            assert switch_cmd.terminal_mode.value == "tab"

    def test_no_args_shows_list(self):
        """Test that running with no arguments shows the worktree list."""
        runner = CliRunner()

        with (
            patch("autowt.cli.list_worktrees") as mock_ls,
            patch("autowt.cli.create_services") as mock_create_services,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            result = runner.invoke(main, [])
            assert result.exit_code == 0
            mock_ls.assert_called_once()

    def test_help_works(self):
        """Test that help commands work correctly."""
        runner = CliRunner()

        # Main help
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Git worktree manager" in result.output

        # Subcommand help
        result = runner.invoke(main, ["switch", "--help"])
        assert result.exit_code == 0
        assert "Switch to or create a worktree" in result.output

    def test_debug_flag_works(self):
        """Test that debug flag is handled correctly."""
        runner = CliRunner()

        with (
            patch("autowt.cli.setup_logging") as mock_setup_logging,
            patch("autowt.cli.list_worktrees"),
            patch("autowt.cli.create_services") as mock_create_services,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Test debug flag - setup_logging is called in both main and ls command
            result = runner.invoke(main, ["ls", "--debug"])
            assert result.exit_code == 0
            # Should be called twice: once from main group, once from ls command
            assert mock_setup_logging.call_count == 2
            mock_setup_logging.assert_any_call(True)

            mock_setup_logging.reset_mock()

            # Test without debug flag
            result = runner.invoke(main, ["ls"])
            assert result.exit_code == 0
            # Should be called twice: once from main group, once from ls command
            assert mock_setup_logging.call_count == 2
            mock_setup_logging.assert_any_call(False)

    def test_cleanup_mode_options(self):
        """Test that cleanup mode options work correctly."""
        runner = CliRunner()

        with (
            patch("autowt.cli.cleanup_worktrees") as mock_cleanup,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_get_config.return_value = mock_config

            # Test different modes
            for mode_str, mode_enum in [
                ("all", CleanupMode.ALL),
                ("merged", CleanupMode.MERGED),
                ("remoteless", CleanupMode.REMOTELESS),
                ("interactive", CleanupMode.INTERACTIVE),
            ]:
                result = runner.invoke(main, ["cleanup", "--mode", mode_str])
                assert result.exit_code == 0
                mock_cleanup.assert_called_once()
                args, kwargs = mock_cleanup.call_args
                cleanup_cmd = args[0]
                assert cleanup_cmd.mode == mode_enum
                mock_cleanup.reset_mock()

    def test_complex_branch_names(self):
        """Test that complex branch names work as fallback."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            mock_get_config.return_value = create_mock_config()

            # Test various complex branch names
            complex_names = [
                "feature/user-auth",
                "steve/bugfix-123",
                "release/v2.1.0",
                "hotfix/critical-bug",
                "chore/update-deps",
            ]

            for branch_name in complex_names:
                result = runner.invoke(main, [branch_name])
                assert result.exit_code == 0, f"Failed for branch: {branch_name}"
                mock_checkout.assert_called_once()
                args, kwargs = mock_checkout.call_args
                switch_cmd = args[0]
                assert switch_cmd.branch == branch_name
                mock_checkout.reset_mock()

    def test_reserved_words_as_branch_names(self):
        """Test handling of reserved command names as branch names using switch."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services

            # Setup mock config
            mock_config = Mock()
            mock_config.terminal.mode = "tab"
            mock_config.scripts.session_init = None
            mock_config.terminal.always_new = False
            mock_get_config.return_value = mock_config

            # If someone has a branch literally named 'cleanup', they need to use 'switch'
            result = runner.invoke(main, ["switch", "cleanup"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "cleanup"


class TestCustomScriptCommands:
    """Tests for elevated custom scripts as first-class commands."""

    def test_custom_script_recognized_as_command(self):
        """Test that a custom script name is recognized as a command."""
        runner = CliRunner()

        custom_scripts = {
            "ghllm": CustomScript(
                branch_name="gh issue view $1 --json title -q .title",
                session_init='claude "Work on issue $1"',
            )
        }

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
            patch("autowt.cli.resolve_custom_script") as mock_resolve,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )
            mock_resolve.return_value = CustomScript(
                branch_name="gh issue view 123 --json title -q .title",
                session_init='claude "Work on issue 123"',
            )

            result = runner.invoke(main, ["ghllm", "123"])
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
            assert result.exit_code == 0
            mock_checkout.assert_called_once()

            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            # With branch_name field, branch should be None (resolved later)
            assert switch_cmd.branch is None
            assert switch_cmd.custom_script == "ghllm 123"
            assert switch_cmd.custom_script_name == "ghllm"

    def test_custom_script_with_simple_format(self):
        """Test simple format custom script uses first arg as branch."""
        runner = CliRunner()

        custom_scripts = {"bugfix": CustomScript(session_init='claude "Fix issue $1"')}

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
            patch("autowt.cli.resolve_custom_script") as mock_resolve,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )
            mock_resolve.return_value = CustomScript(
                session_init='claude "Fix issue 456"'
            )

            result = runner.invoke(main, ["bugfix", "456"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()

            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "456"
            assert switch_cmd.custom_script == "bugfix 456"

    def test_simple_format_requires_branch_arg(self):
        """Test that simple format custom script errors without branch arg."""
        runner = CliRunner()

        custom_scripts = {"bugfix": CustomScript(session_init='claude "Fix issue $1"')}

        with (
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
            patch("autowt.cli.resolve_custom_script") as mock_resolve,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )
            mock_resolve.return_value = CustomScript(session_init='claude "Fix issue"')

            result = runner.invoke(main, ["bugfix"])
            assert "requires a branch name argument" in result.output

    def test_builtin_commands_take_precedence(self):
        """Test that built-in commands override custom scripts with same name."""
        runner = CliRunner()

        custom_scripts = {"ls": CustomScript(session_init="echo This should not run")}

        with (
            patch("autowt.cli.list_worktrees") as mock_ls,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )

            result = runner.invoke(main, ["ls"])
            assert result.exit_code == 0
            mock_ls.assert_called_once()

    def test_branch_fallback_when_not_custom_script(self):
        """Test unknown commands still fallback to branch names."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config()

            result = runner.invoke(main, ["feature-123"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()
            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-123"
            assert switch_cmd.custom_script is None

    def test_custom_script_with_multiple_args(self):
        """Test custom script with multiple arguments."""
        runner = CliRunner()

        custom_scripts = {"multi": CustomScript(session_init='echo "$1 $2 $3"')}

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
            patch("autowt.cli.resolve_custom_script") as mock_resolve,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )
            mock_resolve.return_value = CustomScript(session_init='echo "a b c"')

            result = runner.invoke(main, ["multi", "branch-name", "arg2", "arg3"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()

            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.custom_script == "multi branch-name arg2 arg3"
            assert switch_cmd.branch == "branch-name"

    def test_custom_script_with_options(self):
        """Test custom script command accepts standard options."""
        runner = CliRunner()

        custom_scripts = {"myfix": CustomScript(session_init='claude "Fix $1"')}

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
            patch("autowt.cli.resolve_custom_script") as mock_resolve,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )
            mock_resolve.return_value = CustomScript(session_init='claude "Fix 123"')

            result = runner.invoke(main, ["myfix", "123", "--terminal", "window", "-y"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()

            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.terminal_mode.value == "window"
            assert switch_cmd.auto_confirm is True


class TestCLIPriorityBehavior:
    """Tests for command resolution priority: builtins > custom scripts > branches."""

    def test_priority_builtin_over_custom_script(self):
        """Test that built-in commands take precedence over custom scripts."""
        runner = CliRunner()

        custom_scripts = {
            "cleanup": CustomScript(session_init="echo This should not run")
        }

        with (
            patch("autowt.cli.cleanup_worktrees") as mock_cleanup,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
            patch("autowt.cli.is_interactive_terminal", return_value=True),
        ):
            mock_services = MockServices()
            mock_create_services.return_value = mock_services
            mock_services.config_loader.user_configured_cleanup_mode = True
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts, cleanup_mode=CleanupMode.INTERACTIVE
            )

            result = runner.invoke(main, ["cleanup"])
            assert result.exit_code == 0
            mock_cleanup.assert_called_once()

    def test_priority_custom_script_over_branch(self):
        """Test that custom scripts take precedence over branch names."""
        runner = CliRunner()

        custom_scripts = {"feature": CustomScript(session_init='claude "New feature"')}

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
            patch("autowt.cli.resolve_custom_script") as mock_resolve,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )
            mock_resolve.return_value = CustomScript(
                session_init='claude "New feature"'
            )

            result = runner.invoke(main, ["feature", "123"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()

            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.custom_script == "feature 123"
            assert switch_cmd.branch == "123"

    def test_priority_branch_when_no_custom_script(self):
        """Test that branch names work when no matching custom script exists."""
        runner = CliRunner()

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts={"bugfix": Mock()}
            )

            result = runner.invoke(main, ["feature-xyz"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()

            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "feature-xyz"
            assert switch_cmd.custom_script is None

    def test_switch_command_bypasses_custom_script(self):
        """Test that explicit 'switch' command can switch to branch with same name as custom script."""
        runner = CliRunner()

        custom_scripts = {"myfeature": CustomScript(session_init="echo custom script")}

        with (
            patch("autowt.cli.checkout_branch") as mock_checkout,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )

            result = runner.invoke(main, ["switch", "myfeature"])
            assert result.exit_code == 0
            mock_checkout.assert_called_once()

            args, kwargs = mock_checkout.call_args
            switch_cmd = args[0]
            assert switch_cmd.branch == "myfeature"
            assert switch_cmd.custom_script is None

    def test_all_command_aliases_take_precedence(self):
        """Test that command aliases also take precedence over custom scripts."""
        runner = CliRunner()

        custom_scripts = {"ll": CustomScript(session_init="echo This should not run")}

        with (
            patch("autowt.cli.list_worktrees") as mock_ls,
            patch("autowt.cli.create_services") as mock_create_services,
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_create_services.return_value = MockServices()
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )

            result = runner.invoke(main, ["ll"])
            assert result.exit_code == 0
            mock_ls.assert_called_once()


class TestCustomScriptHelpOutput:
    """Tests for custom scripts appearing in --help output."""

    def test_custom_scripts_appear_in_main_help(self):
        """Test that custom scripts are listed in main --help output."""
        runner = CliRunner()

        custom_scripts = {
            "ghissue": CustomScript(
                description="Create worktree from GitHub issue",
                branch_name="gh issue view $1 --json title -q .title",
            ),
            "bugfix": CustomScript(session_init='claude "Fix $1"'),
        }

        with (
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )

            result = runner.invoke(main, ["--help"])
            assert result.exit_code == 0
            # Custom scripts should appear in the commands list
            assert "ghissue" in result.output
            assert "bugfix" in result.output

    def test_custom_script_description_in_help(self):
        """Test that custom script description is shown in help output."""
        runner = CliRunner()

        custom_scripts = {
            "ghissue": CustomScript(
                description="Create worktree from GitHub issue",
                branch_name="gh issue view $1 --json title -q .title",
            ),
        }

        with (
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )

            result = runner.invoke(main, ["--help"])
            assert result.exit_code == 0
            assert "Create worktree from GitHub issue" in result.output

    def test_custom_script_without_description_shows_default(self):
        """Test that scripts without description show default help text."""
        runner = CliRunner()

        custom_scripts = {"myfix": CustomScript(session_init='claude "Fix $1"')}

        with (
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )

            result = runner.invoke(main, ["--help"])
            assert result.exit_code == 0
            assert "myfix" in result.output
            assert "Run custom script 'myfix'" in result.output

    def test_custom_script_individual_help(self):
        """Test that custom script --help shows its description."""
        runner = CliRunner()

        custom_scripts = {
            "ghissue": CustomScript(
                description="Create worktree from GitHub issue",
                branch_name="gh issue view $1 --json title -q .title",
            ),
        }

        with (
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )

            result = runner.invoke(main, ["ghissue", "--help"])
            assert result.exit_code == 0
            assert "Create worktree from GitHub issue" in result.output

    def test_custom_scripts_in_separate_section(self):
        """Test that custom scripts appear in separate 'Custom Scripts:' section."""
        runner = CliRunner()

        custom_scripts = {
            "ghissue": CustomScript(
                description="Create worktree from GitHub issue",
                branch_name="gh issue view $1 --json title -q .title",
            ),
        }

        with (
            patch("autowt.cli.initialize_config"),
            patch("autowt.cli.get_config") as mock_get_config,
        ):
            mock_get_config.return_value = create_mock_config(
                custom_scripts=custom_scripts
            )

            result = runner.invoke(main, ["--help"])
            assert result.exit_code == 0
            # Built-in commands should be in "Commands:" section
            assert "Commands:" in result.output
            assert "cleanup" in result.output
            # Custom scripts should be in "Custom Scripts:" section
            assert "Custom Scripts:" in result.output
            assert "ghissue" in result.output
            # Verify ordering: Commands section comes before Custom Scripts section
            commands_idx = result.output.index("Commands:")
            custom_idx = result.output.index("Custom Scripts:")
            assert commands_idx < custom_idx
