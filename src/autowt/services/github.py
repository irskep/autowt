"""GitHub-specific service for interacting with GitHub repositories and PRs."""

import json
import logging
import re
import shutil
from pathlib import Path

from autowt.models import BranchStatus, WorktreeInfo
from autowt.utils import run_command_quiet_on_failure

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for GitHub-specific operations using the gh CLI tool."""

    def is_github_repo(self, repo_path: Path) -> bool:
        """Check if the repository's origin remote is a GitHub URL."""
        try:
            result = run_command_quiet_on_failure(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                timeout=10,
                description="Get origin remote URL",
            )

            if result.returncode != 0:
                return False

            origin_url = result.stdout.strip()
            # Check if the URL contains github.com
            return bool(re.search(r"\bgithub\.com\b", origin_url))
        except Exception:
            return False

    def check_gh_available(self) -> bool:
        """Check if the GitHub CLI (gh) is available in PATH."""
        return shutil.which("gh") is not None

    def get_github_username(self) -> str | None:
        """Get the authenticated GitHub username from gh CLI.

        Returns:
            The GitHub username if gh is available and authenticated, None otherwise.
        """
        if not self.check_gh_available():
            return None

        try:
            result = run_command_quiet_on_failure(
                ["gh", "api", "user", "--jq", ".login"],
                timeout=10,
                description="Get GitHub username",
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

        return None

    def get_pr_status_for_branch(self, repo_path: Path, branch: str) -> str | None:
        """Get the PR status for a branch using GitHub CLI.

        Returns:
            'merged', 'closed', 'open', or None if no PR found or error
        """
        try:
            # Query GitHub for PRs associated with this branch
            result = run_command_quiet_on_failure(
                [
                    "gh",
                    "pr",
                    "list",
                    "--head",
                    branch,
                    "--state",
                    "all",
                    "--json",
                    "state,number,headRefName",
                    "--limit",
                    "10",
                ],
                cwd=repo_path,
                timeout=30,
                description=f"Query GitHub PRs for branch {branch}",
            )

            if result.returncode != 0:
                logger.debug(f"Failed to query GitHub PRs for branch {branch}")
                return None

            try:
                prs = json.loads(result.stdout.strip() or "[]")
            except json.JSONDecodeError:
                logger.debug(f"Failed to parse GitHub PR response for branch {branch}")
                return None

            if not prs:
                logger.debug(f"No PRs found for branch {branch}")
                return None

            # Check PR states - prioritize merged, then closed, then open
            for pr in prs:
                state = pr.get("state", "").upper()
                if state == "MERGED":
                    return "merged"

            for pr in prs:
                state = pr.get("state", "").upper()
                if state == "CLOSED":
                    return "closed"

            # If we get here, all PRs are open
            return "open"

        except Exception as e:
            logger.debug(f"Error querying GitHub PRs for branch {branch}: {e}")
            return None

    def analyze_branches_for_cleanup(
        self,
        repo_path: Path,
        worktrees: list[WorktreeInfo],
        git_service,
    ) -> list[BranchStatus]:
        """Analyze branches using GitHub PR status to determine cleanup candidates.

        Args:
            repo_path: Repository path
            worktrees: List of worktrees to analyze
            git_service: GitService instance for git operations

        Returns:
            List of BranchStatus objects with GitHub PR information
        """
        logger.debug("Analyzing branches for GitHub cleanup")

        # Check if gh CLI is available
        if not self.check_gh_available():
            raise RuntimeError(
                "GitHub cleanup requires 'gh' CLI tool to be installed.\n"
                "Install it from: https://cli.github.com/\n"
                "Or use a different cleanup mode: --mode merged, --mode remoteless, etc."
            )

        branch_statuses = []
        for worktree in worktrees:
            branch = worktree.branch
            pr_status = self.get_pr_status_for_branch(repo_path, branch)

            # Create BranchStatus based on PR status
            # For GitHub mode, we consider a branch "merged" if it has a merged or closed PR
            is_github_done = pr_status in ["merged", "closed"]

            branch_status = BranchStatus(
                branch=branch,
                has_remote=True,  # Assume true for GitHub mode
                is_merged=is_github_done,
                is_identical=False,  # Not relevant for GitHub mode
                path=worktree.path,
                has_uncommitted_changes=git_service.has_uncommitted_changes(
                    worktree.path
                ),
            )

            branch_statuses.append(branch_status)

            if pr_status:
                logger.debug(f"Branch {branch} has PR status: {pr_status}")

        return branch_statuses
