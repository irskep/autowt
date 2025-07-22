"""Tests for GitService remote detection and branch analysis."""

from pathlib import Path
from unittest.mock import Mock, patch

from autowt.models import WorktreeInfo
from autowt.services.git import GitService


class TestGitServiceRemoteDetection:
    """Tests for GitService remote detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.git_service = GitService()
        self.repo_path = Path("/mock/repo")

    def test_get_available_remotes_with_no_remotes(self):
        """Test that _get_available_remotes returns empty list when no remotes exist."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            # Simulate no remotes (empty stdout)
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            remotes = self.git_service._get_available_remotes(self.repo_path)

            assert remotes == []
            mock_run.assert_called_once_with(
                ["git", "remote"],
                cwd=self.repo_path,
                timeout=10,
                description="Get available remotes",
            )

    def test_get_available_remotes_with_origin(self):
        """Test that _get_available_remotes returns origin when it exists."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            # Simulate origin remote
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "origin\n"
            mock_run.return_value = mock_result

            remotes = self.git_service._get_available_remotes(self.repo_path)

            assert remotes == ["origin"]

    def test_get_available_remotes_prioritizes_origin_and_upstream(self):
        """Test that _get_available_remotes prioritizes origin and upstream."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            # Simulate multiple remotes with upstream and origin
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "fork\nupstream\norigin\nother\n"
            mock_run.return_value = mock_result

            remotes = self.git_service._get_available_remotes(self.repo_path)

            # Should prioritize origin, then upstream, then others
            assert remotes == ["origin", "upstream", "fork", "other"]

    def test_find_remote_branch_reference_with_no_remotes(self):
        """Test that _find_remote_branch_reference returns None when no remotes exist."""
        with patch.object(self.git_service, "_get_available_remotes", return_value=[]):
            result = self.git_service._find_remote_branch_reference(
                self.repo_path, "main"
            )
            assert result is None

    def test_find_remote_branch_reference_with_existing_remote_branch(self):
        """Test that _find_remote_branch_reference finds existing remote branch."""
        with patch.object(
            self.git_service, "_get_available_remotes", return_value=["origin"]
        ):
            with patch.object(
                self.git_service, "_remote_branch_exists", return_value=True
            ):
                result = self.git_service._find_remote_branch_reference(
                    self.repo_path, "main"
                )
                assert result == "origin/main"

    def test_prepare_default_branch_for_analysis_with_remotes(self):
        """Test that _prepare_default_branch_for_analysis uses remote branch when available."""
        with patch.object(self.git_service, "_get_default_branch", return_value="main"):
            with patch.object(
                self.git_service,
                "_find_remote_branch_reference",
                return_value="origin/main",
            ):
                result = self.git_service._prepare_default_branch_for_analysis(
                    self.repo_path
                )
                assert result == "origin/main"

    def test_prepare_default_branch_for_analysis_remoteless_repo(self):
        """Test that _prepare_default_branch_for_analysis falls back to local branch for remoteless repos."""
        with patch.object(self.git_service, "_get_default_branch", return_value="main"):
            with patch.object(
                self.git_service, "_find_remote_branch_reference", return_value=None
            ):
                result = self.git_service._prepare_default_branch_for_analysis(
                    self.repo_path
                )
                assert result == "main"

    def test_prepare_default_branch_for_analysis_with_preferred_remote(self):
        """Test that _prepare_default_branch_for_analysis respects preferred_remote parameter."""
        with patch.object(self.git_service, "_get_default_branch", return_value="main"):
            with patch.object(
                self.git_service,
                "_find_remote_branch_reference",
                return_value="upstream/main",
            ) as mock_find:
                result = self.git_service._prepare_default_branch_for_analysis(
                    self.repo_path, preferred_remote="upstream"
                )
                assert result == "upstream/main"
                mock_find.assert_called_once_with(self.repo_path, "main", "upstream")

    def test_analyze_branches_for_cleanup_remoteless_repo_integration(self):
        """Integration test for branch analysis in remoteless repo scenario."""
        worktrees = [
            WorktreeInfo(
                branch="feature1", path=Path("/mock/worktree1"), is_current=False
            ),
            WorktreeInfo(
                branch="feature2", path=Path("/mock/worktree2"), is_current=False
            ),
        ]

        # Mock all the git service methods to simulate a remoteless repo
        with (
            patch.object(self.git_service, "_get_default_branch", return_value="main"),
            patch.object(self.git_service, "_get_available_remotes", return_value=[]),
            patch.object(self.git_service, "_branch_has_remote", return_value=False),
            patch.object(self.git_service, "_get_commit_hash") as mock_get_hash,
            patch.object(
                self.git_service, "_is_branch_ancestor_of_default", return_value=False
            ),
            patch.object(
                self.git_service, "has_uncommitted_changes", return_value=False
            ),
        ):
            # Mock commit hashes to simulate different branches
            mock_get_hash.side_effect = lambda repo_path, branch: {
                "feature1": "abc123",
                "feature2": "def456",
                "main": "abc123",  # feature1 is identical to main
            }.get(branch)

            result = self.git_service.analyze_branches_for_cleanup(
                self.repo_path, worktrees
            )

            assert len(result) == 2

            # feature1 should be identical to main (same commit hash)
            feature1_status = next(bs for bs in result if bs.branch == "feature1")
            assert not feature1_status.has_remote
            assert feature1_status.is_identical  # Same as main branch
            assert not feature1_status.is_merged

            # feature2 should be different from main
            feature2_status = next(bs for bs in result if bs.branch == "feature2")
            assert not feature2_status.has_remote
            assert not feature2_status.is_identical  # Different from main branch
            assert not feature2_status.is_merged


class TestGitServiceQuietFailure:
    """Tests to ensure git commands use quiet failure mode to prevent error output."""

    def setup_method(self):
        """Set up test fixtures."""
        self.git_service = GitService()
        self.repo_path = Path("/mock/repo")

    def test_get_commit_hash_uses_quiet_failure(self):
        """Test that _get_commit_hash uses run_command_quiet_on_failure."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 128  # Git error
            mock_result.stdout = ""
            mock_result.stderr = "fatal: ambiguous argument 'origin/master'"
            mock_run.return_value = mock_result

            result = self.git_service._get_commit_hash(self.repo_path, "origin/master")

            assert result is None
            mock_run.assert_called_once_with(
                ["git", "rev-parse", "origin/master"],
                cwd=self.repo_path,
                timeout=10,
                description="Get commit hash for origin/master",
            )

    def test_is_branch_ancestor_of_default_uses_quiet_failure(self):
        """Test that _is_branch_ancestor_of_default uses run_command_quiet_on_failure."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 128  # Git error
            mock_result.stdout = ""
            mock_result.stderr = "fatal: ambiguous argument 'origin/master'"
            mock_run.return_value = mock_result

            result = self.git_service._is_branch_ancestor_of_default(
                self.repo_path, "feature", "origin/master"
            )

            assert result is False
            mock_run.assert_called_once_with(
                ["git", "merge-base", "--is-ancestor", "feature", "origin/master"],
                cwd=self.repo_path,
                timeout=10,
                description="Check if feature is merged into origin/master",
            )

    def test_remote_branch_exists_uses_quiet_failure(self):
        """Test that _remote_branch_exists uses run_command_quiet_on_failure."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 128  # Git error
            mock_result.stdout = ""
            mock_result.stderr = "fatal: ambiguous argument"
            mock_run.return_value = mock_result

            result = self.git_service._remote_branch_exists(
                self.repo_path, "origin/master"
            )

            assert result is False
            mock_run.assert_called_once_with(
                ["git", "show-ref", "--verify", "refs/remotes/origin/master"],
                cwd=self.repo_path,
                timeout=10,
                description="Check if origin/master exists",
            )
