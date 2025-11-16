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


class TestBranchResolver:
    """Tests for BranchResolver remote branch detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.git_service = GitService()
        self.repo_path = Path("/mock/repo")

    def test_check_remote_branch_availability_when_local_exists(self):
        """Test that check_remote_branch_availability returns False when branch exists locally."""
        with patch.object(
            self.git_service.branch_resolver,
            "_branch_exists_locally",
            return_value=True,
        ):
            result = self.git_service.branch_resolver.check_remote_branch_availability(
                self.repo_path, "main"
            )
            assert result == (False, None)

    def test_check_remote_branch_availability_finds_existing_remote(self):
        """Test that check_remote_branch_availability finds existing remote branch without fetching."""
        with (
            patch.object(
                self.git_service.branch_resolver,
                "_branch_exists_locally",
                return_value=False,
            ),
            patch.object(
                self.git_service,
                "_get_remote_for_branch",
                return_value="origin",
            ),
            patch.object(
                self.git_service.branch_resolver,
                "_branch_exists_remotely",
                return_value=True,
            ),
            patch.object(
                self.git_service.branch_resolver,
                "_try_fetch_specific_branch",
            ) as mock_fetch,
        ):
            result = self.git_service.branch_resolver.check_remote_branch_availability(
                self.repo_path, "feature-branch"
            )
            assert result == (True, "origin")
            # Should not fetch if branch already exists remotely
            mock_fetch.assert_not_called()

    def test_check_remote_branch_availability_fetches_when_not_found_remotely(self):
        """Test that check_remote_branch_availability fetches when branch not found remotely initially."""
        with (
            patch.object(
                self.git_service.branch_resolver,
                "_branch_exists_locally",
                return_value=False,
            ),
            patch.object(
                self.git_service,
                "_get_remote_for_branch",
                return_value="origin",
            ),
            patch.object(
                self.git_service.branch_resolver,
                "_branch_exists_remotely",
                side_effect=[
                    False,
                    True,
                ],  # First call: not found, second call: found after fetch
            ),
            patch.object(
                self.git_service.branch_resolver,
                "_try_fetch_specific_branch",
                return_value=True,
            ) as mock_fetch,
        ):
            result = self.git_service.branch_resolver.check_remote_branch_availability(
                self.repo_path, "feature-branch"
            )
            assert result == (True, "origin")
            # Should fetch when branch not initially found remotely
            mock_fetch.assert_called_once_with(
                self.repo_path, "feature-branch", "origin"
            )

    def test_check_remote_branch_availability_fetch_fails(self):
        """Test that check_remote_branch_availability returns False when fetch fails."""
        with (
            patch.object(
                self.git_service.branch_resolver,
                "_branch_exists_locally",
                return_value=False,
            ),
            patch.object(
                self.git_service.branch_resolver,
                "_branch_exists_remotely",
                return_value=False,  # Not found remotely initially or after fetch
            ),
            patch.object(
                self.git_service.branch_resolver,
                "_try_fetch_specific_branch",
                return_value=False,
            ),
        ):
            result = self.git_service.branch_resolver.check_remote_branch_availability(
                self.repo_path, "nonexistent-branch"
            )
            assert result == (False, None)

    def test_check_remote_branch_availability_fetch_succeeds_but_no_remote_branch(self):
        """Test that check_remote_branch_availability returns False when fetch succeeds but branch not found remotely."""
        with (
            patch.object(
                self.git_service.branch_resolver,
                "_branch_exists_locally",
                return_value=False,
            ),
            patch.object(
                self.git_service.branch_resolver,
                "_branch_exists_remotely",
                return_value=False,  # Not found remotely before or after fetch
            ),
            patch.object(
                self.git_service.branch_resolver,
                "_try_fetch_specific_branch",
                return_value=True,
            ),
        ):
            result = self.git_service.branch_resolver.check_remote_branch_availability(
                self.repo_path, "feature-branch"
            )
            assert result == (False, None)

    def test_try_fetch_specific_branch_succeeds(self):
        """Test that _try_fetch_specific_branch returns True when git fetch succeeds."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = self.git_service.branch_resolver._try_fetch_specific_branch(
                self.repo_path, "feature-branch", "origin"
            )

            assert result is True
            mock_run.assert_called_once_with(
                ["git", "fetch", "origin", "feature-branch:feature-branch"],
                cwd=self.repo_path,
                timeout=30,
                description="Fetch specific branch feature-branch from origin",
            )

    def test_try_fetch_specific_branch_fallback_to_simple_fetch(self):
        """Test that _try_fetch_specific_branch falls back to simple fetch when first attempt fails."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            # First call fails, second succeeds
            mock_result_fail = Mock()
            mock_result_fail.returncode = 1
            mock_result_success = Mock()
            mock_result_success.returncode = 0
            mock_run.side_effect = [Exception(), mock_result_success]

            result = self.git_service.branch_resolver._try_fetch_specific_branch(
                self.repo_path, "feature-branch", "origin"
            )

            assert result is True
            # Should have been called twice due to fallback
            assert mock_run.call_count == 2
            mock_run.assert_any_call(
                ["git", "fetch", "origin", "feature-branch"],
                cwd=self.repo_path,
                timeout=30,
                description="Fetch branch feature-branch from origin",
            )

    def test_try_fetch_specific_branch_both_attempts_fail(self):
        """Test that _try_fetch_specific_branch returns False when both fetch attempts fail."""
        with patch("autowt.services.git.run_command_quiet_on_failure") as mock_run:
            mock_run.side_effect = [Exception(), Exception()]

            result = self.git_service.branch_resolver._try_fetch_specific_branch(
                self.repo_path, "feature-branch", "origin"
            )

            assert result is False
