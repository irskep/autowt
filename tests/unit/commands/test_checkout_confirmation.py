"""Tests for checkout command confirmation behavior."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from autowt.commands.checkout import checkout_branch
from autowt.models import SwitchCommand, TerminalMode, WorktreeInfo


class TestCheckoutConfirmation:
    """Tests for confirmation behavior during checkout."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_services = MagicMock()
        self.mock_services.git.find_repo_root.return_value = Path("/mock/repo")
        self.mock_services.git.list_worktrees.return_value = []

        # Mock config with branch_prefix set to None
        config = MagicMock()
        config.worktree.branch_prefix = None
        self.mock_services.state.load_config.return_value = config

        # Mock project config to return None for session_init
        project_config = MagicMock()
        project_config.session_init = None
        self.mock_services.state.load_project_config.return_value = project_config

        # Mock branch resolver for remote branch detection
        self.mock_services.git.branch_resolver = MagicMock()
        self.mock_services.git.branch_resolver.check_remote_branch_availability.return_value = (
            False,
            None,
        )

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout._create_new_worktree")
    def test_dynamic_command_prompts_for_confirmation(
        self, mock_create_worktree, mock_confirm
    ):
        """Test that dynamic branch commands prompt for confirmation before creating worktree."""
        mock_confirm.return_value = True

        switch_cmd = SwitchCommand(
            branch="test-branch",
            terminal_mode=TerminalMode.ECHO,
            from_dynamic_command=True,
            auto_confirm=False,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should prompt for confirmation
        mock_confirm.assert_called_once_with(
            "Create a branch 'test-branch' and worktree?"
        )
        # Should proceed with worktree creation after confirmation
        mock_create_worktree.assert_called_once()

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout._create_new_worktree")
    @patch("autowt.commands.checkout.print_info")
    def test_dynamic_command_cancels_when_user_declines(
        self, mock_print_info, mock_create_worktree, mock_confirm
    ):
        """Test that dynamic branch commands cancel when user declines confirmation."""
        mock_confirm.return_value = False

        switch_cmd = SwitchCommand(
            branch="test-branch",
            terminal_mode=TerminalMode.ECHO,
            from_dynamic_command=True,
            auto_confirm=False,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should prompt for confirmation
        mock_confirm.assert_called_once_with(
            "Create a branch 'test-branch' and worktree?"
        )
        # Should not create worktree when declined
        mock_create_worktree.assert_not_called()
        # Should show cancellation message
        mock_print_info.assert_called_with("Worktree creation cancelled.")

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout._create_new_worktree")
    def test_dynamic_command_with_auto_confirm_skips_prompt(
        self, mock_create_worktree, mock_confirm
    ):
        """Test that dynamic commands with auto_confirm skip the confirmation prompt."""
        switch_cmd = SwitchCommand(
            branch="test-branch",
            terminal_mode=TerminalMode.ECHO,
            from_dynamic_command=True,
            auto_confirm=True,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should not prompt when auto_confirm is True
        mock_confirm.assert_not_called()
        # Should proceed with worktree creation
        mock_create_worktree.assert_called_once()

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout._create_new_worktree")
    def test_explicit_switch_command_does_not_prompt(
        self, mock_create_worktree, mock_confirm
    ):
        """Test that explicit switch commands do not prompt for confirmation."""
        switch_cmd = SwitchCommand(
            branch="test-branch",
            terminal_mode=TerminalMode.ECHO,
            from_dynamic_command=False,  # Explicit switch command
            auto_confirm=False,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should not prompt for explicit switch commands
        mock_confirm.assert_not_called()
        # Should proceed with worktree creation
        mock_create_worktree.assert_called_once()

    @patch("autowt.commands.checkout._create_new_worktree")
    def test_existing_worktree_does_not_prompt(self, mock_create_worktree):
        """Test that switching to existing worktree does not prompt."""
        # Mock existing worktree
        existing_worktree = WorktreeInfo(
            branch="test-branch",
            path=Path("/mock/repo-worktrees/test-branch"),
            is_current=False,
            is_primary=False,
        )
        self.mock_services.git.list_worktrees.return_value = [existing_worktree]

        # Mock successful terminal switch
        self.mock_services.terminal.switch_to_worktree.return_value = True

        switch_cmd = SwitchCommand(
            branch="test-branch",
            terminal_mode=TerminalMode.ECHO,
            from_dynamic_command=True,
            auto_confirm=False,
        )

        with patch("autowt.commands.checkout.confirm_default_yes") as mock_confirm:
            checkout_branch(switch_cmd, self.mock_services)

            # Should not prompt when worktree already exists
            mock_confirm.assert_not_called()
            # Should not create new worktree
            mock_create_worktree.assert_not_called()
            # Should switch to existing worktree
            self.mock_services.terminal.switch_to_worktree.assert_called_once()

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout._generate_worktree_path")
    @patch("autowt.commands.checkout._run_hook_set")
    def test_remote_branch_prompts_for_confirmation(
        self,
        mock_hook_set,
        mock_generate_path,
        mock_confirm,
    ):
        """Test that remote branches prompt for confirmation before creating worktree."""
        mock_confirm.return_value = True
        mock_generate_path.return_value = Path("/mock/worktree/path")
        mock_hook_set.return_value = True

        # Mock terminal switch success
        self.mock_services.terminal.switch_to_worktree.return_value = True

        # Mock remote branch detection
        self.mock_services.git.branch_resolver.check_remote_branch_availability.return_value = (
            True,
            "origin",
        )

        switch_cmd = SwitchCommand(
            branch="remote-branch",
            terminal_mode=TerminalMode.ECHO,
            auto_confirm=False,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should prompt for remote branch confirmation
        mock_confirm.assert_called_once_with(
            "Branch 'remote-branch' exists on remote 'origin'. Create a local worktree tracking the remote branch?"
        )
        # Should proceed with git worktree creation
        self.mock_services.git.create_worktree.assert_called_once()

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout.print_info")
    def test_remote_branch_cancels_when_user_declines(
        self, mock_print_info, mock_confirm
    ):
        """Test that remote branch checkout cancels when user declines confirmation."""
        mock_confirm.return_value = False

        # Mock remote branch detection
        self.mock_services.git.branch_resolver.check_remote_branch_availability.return_value = (
            True,
            "origin",
        )

        switch_cmd = SwitchCommand(
            branch="remote-branch",
            terminal_mode=TerminalMode.ECHO,
            auto_confirm=False,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should prompt for remote branch confirmation
        mock_confirm.assert_called_once_with(
            "Branch 'remote-branch' exists on remote 'origin'. Create a local worktree tracking the remote branch?"
        )
        # Should not create git worktree when declined
        self.mock_services.git.create_worktree.assert_not_called()
        # Should show cancellation message
        mock_print_info.assert_called_with("Worktree creation cancelled.")

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout._create_new_worktree")
    def test_remote_branch_with_auto_confirm_skips_prompt(
        self, mock_create_worktree, mock_confirm
    ):
        """Test that remote branches with auto_confirm skip the confirmation prompt."""
        # Mock remote branch detection
        self.mock_services.git.branch_resolver.check_remote_branch_availability.return_value = (
            True,
            "origin",
        )

        switch_cmd = SwitchCommand(
            branch="remote-branch",
            terminal_mode=TerminalMode.ECHO,
            auto_confirm=True,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should not prompt when auto_confirm is True
        mock_confirm.assert_not_called()
        # Should proceed with worktree creation
        mock_create_worktree.assert_called_once()

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout._create_new_worktree")
    def test_remote_branch_detection_skipped_with_from_branch(
        self, mock_create_worktree, mock_confirm
    ):
        """Test that remote branch detection is skipped when from_branch is specified."""
        # Mock remote branch detection (shouldn't be called)
        self.mock_services.git.branch_resolver.remote_branch_availability = (
            True,
            "origin",
        )

        switch_cmd = SwitchCommand(
            branch="new-branch",
            terminal_mode=TerminalMode.ECHO,
            from_branch="main",
            auto_confirm=False,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should not prompt for remote branch confirmation (from_branch specified)
        mock_confirm.assert_not_called()
        # Should proceed with worktree creation
        mock_create_worktree.assert_called_once()

    @patch("autowt.commands.checkout.confirm_default_yes")
    @patch("autowt.commands.checkout._create_new_worktree")
    def test_no_remote_branch_does_not_prompt(self, mock_create_worktree, mock_confirm):
        """Test that when no remote branch exists, no prompt is shown."""
        # Mock remote branch detection - no remote branch
        self.mock_services.git.branch_resolver.check_remote_branch_availability.return_value = (
            False,
            None,
        )

        switch_cmd = SwitchCommand(
            branch="new-branch",
            terminal_mode=TerminalMode.ECHO,
            auto_confirm=False,
        )

        checkout_branch(switch_cmd, self.mock_services)

        # Should not prompt when no remote branch exists
        mock_confirm.assert_not_called()
        # Should proceed with worktree creation
        mock_create_worktree.assert_called_once()
