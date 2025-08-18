"""Tests for GitHub cleanup functionality in GitService."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from autowt.models import WorktreeInfo
from autowt.services.git import GitService


class TestGitHubCleanup:
    """Tests for GitHub cleanup methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.git_service = GitService()
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
        """Test that _check_gh_available returns True when gh is in PATH."""
        with patch("shutil.which", return_value="/usr/local/bin/gh"):
            assert self.git_service._check_gh_available() is True

    def test_check_gh_available_when_missing(self):
        """Test that _check_gh_available returns False when gh is not in PATH."""
        with patch("shutil.which", return_value=None):
            assert self.git_service._check_gh_available() is False

    def test_get_pr_status_merged(self):
        """Test getting PR status for a merged PR."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            [{"state": "MERGED", "number": 123, "headRefName": "feature-merged"}]
        )

        with patch(
            "autowt.services.git.run_command_quiet_on_failure", return_value=mock_result
        ):
            status = self.git_service._get_pr_status_for_branch(
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
            "autowt.services.git.run_command_quiet_on_failure", return_value=mock_result
        ):
            status = self.git_service._get_pr_status_for_branch(
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
            "autowt.services.git.run_command_quiet_on_failure", return_value=mock_result
        ):
            status = self.git_service._get_pr_status_for_branch(
                self.repo_path, "feature-open"
            )
            assert status == "open"

    def test_get_pr_status_no_pr(self):
        """Test getting PR status when no PR exists."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"

        with patch(
            "autowt.services.git.run_command_quiet_on_failure", return_value=mock_result
        ):
            status = self.git_service._get_pr_status_for_branch(
                self.repo_path, "feature-no-pr"
            )
            assert status is None

    def test_get_pr_status_command_fails(self):
        """Test getting PR status when gh command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch(
            "autowt.services.git.run_command_quiet_on_failure", return_value=mock_result
        ):
            status = self.git_service._get_pr_status_for_branch(
                self.repo_path, "feature-error"
            )
            assert status is None

    def test_get_pr_status_invalid_json(self):
        """Test getting PR status when response is invalid JSON."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"

        with patch(
            "autowt.services.git.run_command_quiet_on_failure", return_value=mock_result
        ):
            status = self.git_service._get_pr_status_for_branch(
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
            "autowt.services.git.run_command_quiet_on_failure", return_value=mock_result
        ):
            status = self.git_service._get_pr_status_for_branch(
                self.repo_path, "feature"
            )
            assert status == "merged"

    def test_analyze_branches_for_github_cleanup_gh_not_available(self):
        """Test that analyze_branches_for_github_cleanup raises error when gh is not available."""
        with patch.object(self.git_service, "_check_gh_available", return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                self.git_service.analyze_branches_for_github_cleanup(
                    self.repo_path, self.sample_worktrees
                )
            assert "GitHub cleanup requires 'gh' CLI tool" in str(exc_info.value)

    def test_analyze_branches_for_github_cleanup_success(self):
        """Test successful analysis of branches for GitHub cleanup."""
        # Mock gh availability
        with patch.object(self.git_service, "_check_gh_available", return_value=True):
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
                self.git_service,
                "_get_pr_status_for_branch",
                side_effect=mock_get_pr_status,
            ):
                # Mock has_uncommitted_changes to return False for all
                with patch.object(
                    self.git_service, "has_uncommitted_changes", return_value=False
                ):
                    branch_statuses = (
                        self.git_service.analyze_branches_for_github_cleanup(
                            self.repo_path, self.sample_worktrees
                        )
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

    def test_analyze_branches_for_github_cleanup_with_uncommitted_changes(self):
        """Test that uncommitted changes are detected during GitHub cleanup analysis."""
        with patch.object(self.git_service, "_check_gh_available", return_value=True):
            with patch.object(
                self.git_service, "_get_pr_status_for_branch", return_value="merged"
            ):
                # Mock has_uncommitted_changes to return True for first worktree
                def mock_has_uncommitted(path):
                    return path == Path("/test/worktrees/feature-merged")

                with patch.object(
                    self.git_service,
                    "has_uncommitted_changes",
                    side_effect=mock_has_uncommitted,
                ):
                    branch_statuses = (
                        self.git_service.analyze_branches_for_github_cleanup(
                            self.repo_path, self.sample_worktrees[:1]
                        )
                    )

                    assert len(branch_statuses) == 1
                    assert branch_statuses[0].has_uncommitted_changes is True
                    assert branch_statuses[0].is_merged is True
