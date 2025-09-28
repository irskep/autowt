"""Tests for GitHub service functionality."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from autowt.models import WorktreeInfo
from autowt.services.git import GitService
from autowt.services.github import GitHubService


class TestGitHubService:
    """Tests for GitHub service methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.github_service = GitHubService()
        self.git_service = GitService()  # Needed for has_uncommitted_changes
        self.repo_path = Path("/test/repo")
        self.sample_worktrees = [
            WorktreeInfo(
                branch="feature-merged", path=Path("/test/worktrees/feature-merged")
            ),
            WorktreeInfo(
                branch="feature-closed", path=Path("/test/worktrees/feature-closed")
            ),
            WorktreeInfo(
                branch="feature-open", path=Path("/test/worktrees/feature-open")
            ),
            WorktreeInfo(
                branch="feature-no-pr", path=Path("/test/worktrees/feature-no-pr")
            ),
        ]

    def test_check_gh_available_when_present(self):
        """Test that check_gh_available returns True when gh is in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/gh"):
            assert self.github_service.check_gh_available() is True

    def test_check_gh_available_when_missing(self):
        """Test that check_gh_available returns False when gh is not in PATH."""
        with patch("shutil.which", return_value=None):
            assert self.github_service.check_gh_available() is False

    def test_is_github_repo_with_github_url(self):
        """Test that is_github_repo returns True for GitHub URLs."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/user/repo.git"

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            assert self.github_service.is_github_repo(self.repo_path) is True

        # Test with SSH URL
        mock_result.stdout = "git@github.com:user/repo.git"
        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            assert self.github_service.is_github_repo(self.repo_path) is True

    def test_is_github_repo_with_non_github_url(self):
        """Test that is_github_repo returns False for non-GitHub URLs."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "https://gitlab.com/user/repo.git"

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            assert self.github_service.is_github_repo(self.repo_path) is False

    def test_is_github_repo_with_no_origin(self):
        """Test that is_github_repo returns False when no origin remote exists."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            assert self.github_service.is_github_repo(self.repo_path) is False

    def test_get_pr_status_merged(self):
        """Test getting PR status for a merged PR."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [{"state": "MERGED", "number": 123, "headRefName": "feature-merged"}]
        )

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            status = self.github_service.get_pr_status_for_branch(
                self.repo_path, "feature-merged"
            )
            assert status == "merged"

    def test_get_pr_status_closed(self):
        """Test getting PR status for a closed PR."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [{"state": "CLOSED", "number": 124, "headRefName": "feature-closed"}]
        )

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            status = self.github_service.get_pr_status_for_branch(
                self.repo_path, "feature-closed"
            )
            assert status == "closed"

    def test_get_pr_status_open(self):
        """Test getting PR status for an open PR."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [{"state": "OPEN", "number": 125, "headRefName": "feature-open"}]
        )

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            status = self.github_service.get_pr_status_for_branch(
                self.repo_path, "feature-open"
            )
            assert status == "open"

    def test_get_pr_status_no_pr(self):
        """Test getting PR status when no PR exists."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            status = self.github_service.get_pr_status_for_branch(
                self.repo_path, "feature-no-pr"
            )
            assert status is None

    def test_get_pr_status_command_fails(self):
        """Test getting PR status when gh command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            status = self.github_service.get_pr_status_for_branch(
                self.repo_path, "feature-error"
            )
            assert status is None

    def test_get_pr_status_invalid_json(self):
        """Test getting PR status when response is invalid JSON."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            status = self.github_service.get_pr_status_for_branch(
                self.repo_path, "feature-invalid"
            )
            assert status is None

    def test_get_pr_status_multiple_prs_prioritizes_merged(self):
        """Test that merged PRs are prioritized when multiple PRs exist."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [
                {"state": "OPEN", "number": 125, "headRefName": "feature"},
                {"state": "MERGED", "number": 123, "headRefName": "feature"},
                {"state": "CLOSED", "number": 124, "headRefName": "feature"},
            ]
        )

        with patch(
            "autowt.services.github.run_command_quiet_on_failure",
            return_value=mock_result,
        ):
            status = self.github_service.get_pr_status_for_branch(
                self.repo_path, "feature"
            )
            assert status == "merged"

    def test_analyze_branches_for_cleanup_gh_not_available(self):
        """Test that analyze_branches_for_cleanup raises error when gh is not available."""
        with patch.object(
            self.github_service, "check_gh_available", return_value=False
        ):
            with pytest.raises(RuntimeError) as exc_info:
                self.github_service.analyze_branches_for_cleanup(
                    self.repo_path, self.sample_worktrees, self.git_service
                )
            assert "GitHub cleanup requires 'gh' CLI tool" in str(exc_info.value)

    def test_analyze_branches_for_cleanup_success(self):
        """Test successful analysis of branches for GitHub cleanup."""
        # Mock gh availability
        with patch.object(self.github_service, "check_gh_available", return_value=True):
            # Mock PR status for each branch
            pr_statuses = {
                "feature-merged": "merged",
                "feature-closed": "closed",
                "feature-open": "open",
                "feature-no-pr": None,
            }

            def mock_get_pr_status(repo_path, branch):
                return pr_statuses.get(branch)

            with patch.object(
                self.github_service,
                "get_pr_status_for_branch",
                side_effect=mock_get_pr_status,
            ):
                # Mock has_uncommitted_changes to return False for all
                with patch.object(
                    self.git_service, "has_uncommitted_changes", return_value=False
                ):
                    branch_statuses = self.github_service.analyze_branches_for_cleanup(
                        self.repo_path, self.sample_worktrees, self.git_service
                    )

                    # Verify results
                    assert len(branch_statuses) == 4

                    # Find each branch status
                    status_map = {bs.branch: bs for bs in branch_statuses}

                    # Merged PR should be marked as merged
                    assert status_map["feature-merged"].is_merged is True
                    assert status_map["feature-merged"].has_remote is True

                    # Closed PR should be marked as merged (for cleanup purposes)
                    assert status_map["feature-closed"].is_merged is True
                    assert status_map["feature-closed"].has_remote is True

                    # Open PR should NOT be marked as merged
                    assert status_map["feature-open"].is_merged is False
                    assert status_map["feature-open"].has_remote is True

                    # No PR should NOT be marked as merged
                    assert status_map["feature-no-pr"].is_merged is False
                    assert status_map["feature-no-pr"].has_remote is True

    def test_analyze_branches_for_cleanup_with_uncommitted_changes(self):
        """Test that uncommitted changes are detected during GitHub cleanup analysis."""
        with patch.object(self.github_service, "check_gh_available", return_value=True):
            with patch.object(
                self.github_service, "get_pr_status_for_branch", return_value="merged"
            ):
                # Mock has_uncommitted_changes to return True for first worktree
                def mock_has_uncommitted(path):
                    return path == Path("/test/worktrees/feature-merged")

                with patch.object(
                    self.git_service,
                    "has_uncommitted_changes",
                    side_effect=mock_has_uncommitted,
                ):
                    branch_statuses = self.github_service.analyze_branches_for_cleanup(
                        self.repo_path, self.sample_worktrees[:1], self.git_service
                    )

                    assert len(branch_statuses) == 1
                    assert branch_statuses[0].has_uncommitted_changes is True
                    assert branch_statuses[0].is_merged is True
