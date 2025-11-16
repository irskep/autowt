"""Tests for GitHub cleanup mode in cleanup command."""

from pathlib import Path
from unittest.mock import Mock, patch

from autowt.commands.cleanup import cleanup_worktrees
from autowt.models import BranchStatus, CleanupCommand, CleanupMode, WorktreeInfo


class TestGitHubCleanupMode:
    """Tests for GitHub cleanup mode."""

    def test_cleanup_github_mode_no_gh_installed(self, capsys):
        """Test that GitHub cleanup mode fails gracefully when gh is not installed."""
        # Create cleanup command with GitHub mode
        cleanup_cmd = CleanupCommand(mode=CleanupMode.GITHUB)

        # Create mock services
        mock_services = Mock()
        mock_services.git.find_repo_root.return_value = Path("/test/repo")
        mock_services.state.load_config.return_value = Mock()

        # Mock analyze_branches_for_cleanup to raise error
        mock_services.github.analyze_branches_for_cleanup.side_effect = RuntimeError(
            "GitHub cleanup requires 'gh' CLI tool to be installed.\n"
            "Install it from: https://cli.github.com/\n"
            "Or use a different cleanup mode: --mode merged, --mode remoteless, etc."
        )

        # Run cleanup
        cleanup_worktrees(cleanup_cmd, mock_services)

        # Check output
        captured = capsys.readouterr()
        assert "GitHub cleanup requires 'gh' CLI tool" in captured.out
        assert "https://cli.github.com/" in captured.out

    def test_cleanup_github_mode_with_merged_and_open_prs(self, capsys):
        """Test GitHub cleanup mode with a mix of merged and open PRs."""
        # Create cleanup command with GitHub mode
        cleanup_cmd = CleanupCommand(mode=CleanupMode.GITHUB)

        # Create mock services
        mock_services = Mock()
        mock_services.git.find_repo_root.return_value = Path("/test/repo")
        mock_services.state.load_config.return_value = Mock()
        mock_services.git.fetch_branches.return_value = True

        # Mock worktrees
        worktrees = [
            WorktreeInfo(
                branch="feature-merged", path=Path("/test/worktrees/feature-merged")
            ),
            WorktreeInfo(
                branch="feature-open", path=Path("/test/worktrees/feature-open")
            ),
            WorktreeInfo(
                branch="feature-closed", path=Path("/test/worktrees/feature-closed")
            ),
        ]
        mock_services.git.list_worktrees.return_value = worktrees

        # Mock branch statuses for GitHub mode
        github_statuses = [
            BranchStatus(
                branch="feature-merged",
                has_remote=True,
                is_merged=True,  # Has merged PR
                is_identical=False,
                path=Path("/test/worktrees/feature-merged"),
                has_uncommitted_changes=False,
            ),
            BranchStatus(
                branch="feature-open",
                has_remote=True,
                is_merged=False,  # Has open PR
                is_identical=False,
                path=Path("/test/worktrees/feature-open"),
                has_uncommitted_changes=False,
            ),
            BranchStatus(
                branch="feature-closed",
                has_remote=True,
                is_merged=True,  # Has closed PR
                is_identical=False,
                path=Path("/test/worktrees/feature-closed"),
                has_uncommitted_changes=False,
            ),
        ]
        mock_services.github.analyze_branches_for_cleanup.return_value = github_statuses

        # Mock user confirmation
        with patch("builtins.input", return_value="n"):  # User cancels
            cleanup_worktrees(cleanup_cmd, mock_services)

        # Check output
        captured = capsys.readouterr()
        assert "Branches with merged or closed PRs:" in captured.out
        assert "feature-merged" in captured.out
        assert "feature-closed" in captured.out
        assert "Branches with open or no PRs (will be kept):" in captured.out
        assert "feature-open" in captured.out

    def test_cleanup_github_mode_filters_uncommitted_changes(self, capsys):
        """Test that GitHub cleanup mode filters out branches with uncommitted changes."""
        # Create cleanup command with GitHub mode
        cleanup_cmd = CleanupCommand(mode=CleanupMode.GITHUB, auto_confirm=True)

        # Create mock services
        mock_services = Mock()
        mock_services.git.find_repo_root.return_value = Path("/test/repo")
        mock_services.state.load_config.return_value = Mock()
        mock_services.git.fetch_branches.return_value = True

        # Mock worktrees
        worktrees = [
            WorktreeInfo(
                branch="feature-clean", path=Path("/test/worktrees/feature-clean")
            ),
            WorktreeInfo(
                branch="feature-dirty", path=Path("/test/worktrees/feature-dirty")
            ),
        ]
        mock_services.git.list_worktrees.return_value = worktrees

        # Mock branch statuses for GitHub mode
        github_statuses = [
            BranchStatus(
                branch="feature-clean",
                has_remote=True,
                is_merged=True,  # Has merged PR
                is_identical=False,
                path=Path("/test/worktrees/feature-clean"),
                has_uncommitted_changes=False,
            ),
            BranchStatus(
                branch="feature-dirty",
                has_remote=True,
                is_merged=True,  # Has merged PR
                is_identical=False,
                path=Path("/test/worktrees/feature-dirty"),
                has_uncommitted_changes=True,  # Has uncommitted changes
            ),
        ]
        mock_services.github.analyze_branches_for_cleanup.return_value = github_statuses

        # Mock git services
        mock_services.git.remove_worktree.return_value = True
        mock_services.git.delete_branch.return_value = True
        mock_services.state.remove_session_id.return_value = None

        # Run cleanup with auto-confirm
        with patch("builtins.input", return_value="y"):  # Mock confirmation
            cleanup_worktrees(cleanup_cmd, mock_services)

        # Check output
        captured = capsys.readouterr()
        assert "Skipping 1 worktree(s) with uncommitted changes" in captured.out
        assert "feature-clean" in captured.out
        # feature-dirty should not be in the removal list
        assert "Worktrees to be removed:" in captured.out
        output_lines = captured.out.split("\n")
        removal_section = False
        for line in output_lines:
            if "Worktrees to be removed:" in line:
                removal_section = True
            elif removal_section and "feature-dirty" in line:
                assert False, "feature-dirty should not be in removal list"
            elif removal_section and line.strip() == "":
                break  # End of removal section

    def test_cleanup_github_mode_dry_run(self, capsys):
        """Test GitHub cleanup mode with dry-run flag."""
        # Create cleanup command with GitHub mode and dry-run
        cleanup_cmd = CleanupCommand(
            mode=CleanupMode.GITHUB, dry_run=True, auto_confirm=True
        )

        # Create mock services
        mock_services = Mock()
        mock_services.git.find_repo_root.return_value = Path("/test/repo")
        mock_services.state.load_config.return_value = Mock()
        mock_services.git.fetch_branches.return_value = True

        # Mock worktrees
        worktrees = [
            WorktreeInfo(
                branch="feature-to-remove",
                path=Path("/test/worktrees/feature-to-remove"),
            ),
        ]
        mock_services.git.list_worktrees.return_value = worktrees

        # Mock branch statuses for GitHub mode
        github_statuses = [
            BranchStatus(
                branch="feature-to-remove",
                has_remote=True,
                is_merged=True,  # Has merged PR
                is_identical=False,
                path=Path("/test/worktrees/feature-to-remove"),
                has_uncommitted_changes=False,
            ),
        ]
        mock_services.github.analyze_branches_for_cleanup.return_value = github_statuses

        mock_services.state.remove_session_id.return_value = None

        # Run cleanup with dry-run
        with patch("builtins.input", return_value="y"):  # Mock confirmation
            cleanup_worktrees(cleanup_cmd, mock_services)

        # Verify that remove_worktree was NOT called (dry-run)
        mock_services.git.remove_worktree.assert_not_called()
        mock_services.git.delete_branch.assert_not_called()

        # Check output
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "Would remove" in captured.out
        assert "feature-to-remove" in captured.out
