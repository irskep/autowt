"""Git operations service for autowt."""

import logging
from pathlib import Path

from autowt.models import BranchStatus, WorktreeInfo
from autowt.utils import run_command, run_command_visible

logger = logging.getLogger(__name__)


class GitService:
    """Handles all git operations for worktree management."""

    def __init__(self):
        """Initialize git service."""
        logger.debug("Git service initialized")

    def find_repo_root(self, start_path: Path | None = None) -> Path | None:
        """Find the root of the git repository."""
        if start_path is None:
            start_path = Path.cwd()

        current = start_path.resolve()
        while current != current.parent:
            if (current / ".git").exists():
                logger.debug(f"Found repo root: {current}")
                return current
            current = current.parent

        logger.debug("No git repository found")
        return None

    def is_git_repo(self, path: Path) -> bool:
        """Check if the given path is a git repository."""
        try:
            result = run_command(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                timeout=10,
                description="Check if directory is git repo",
            )
            is_repo = result.returncode == 0
            logger.debug(f"Path {path} is git repo: {is_repo}")
            return is_repo
        except Exception as e:
            logger.debug(f"Error checking if {path} is git repo: {e}")
            return False

    def get_current_branch(self, repo_path: Path) -> str | None:
        """Get the current branch name."""
        try:
            result = run_command(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                timeout=10,
                description="Get current branch",
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                logger.debug(f"Current branch: {branch}")
                return branch
        except Exception as e:
            logger.error(f"Failed to get current branch: {e}")

        return None

    def list_worktrees(self, repo_path: Path) -> list[WorktreeInfo]:
        """List all git worktrees."""
        try:
            result = run_command(
                ["git", "worktree", "list", "--porcelain"],
                cwd=repo_path,
                timeout=30,
                description="List git worktrees",
            )

            if result.returncode != 0:
                logger.error(f"Git worktree list failed: {result.stderr}")
                return []

            worktrees = []
            current_worktree = None
            current_path = None
            current_branch = None

            for line in result.stdout.strip().split("\n"):
                if not line:
                    # End of worktree entry
                    if current_path and current_branch:
                        worktrees.append(
                            WorktreeInfo(
                                branch=current_branch,
                                path=Path(current_path),
                                is_current=current_worktree is not None,
                            )
                        )
                    current_worktree = None
                    current_path = None
                    current_branch = None
                elif line.startswith("worktree "):
                    current_path = line[9:]  # Remove 'worktree ' prefix
                elif line.startswith("HEAD "):
                    current_branch = line[5:]  # Remove 'HEAD ' prefix
                elif line == "bare":
                    # Skip bare repositories
                    continue
                elif line == "detached":
                    # Skip detached HEAD
                    continue

            # Handle last entry
            if current_path and current_branch:
                worktrees.append(
                    WorktreeInfo(
                        branch=current_branch,
                        path=Path(current_path),
                        is_current=current_worktree is not None,
                    )
                )

            logger.debug(f"Found {len(worktrees)} worktrees")
            return worktrees

        except Exception as e:
            logger.error(f"Failed to list worktrees: {e}")
            return []

    def fetch_branches(self, repo_path: Path) -> bool:
        """Fetch latest branches from remote."""
        logger.debug("Fetching branches from remote")
        try:
            result = run_command_visible(
                ["git", "fetch", "--prune"],
                cwd=repo_path,
                timeout=60,
            )

            success = result.returncode == 0
            if success:
                logger.debug("Fetch completed successfully")
            else:
                logger.error(f"Fetch failed: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Failed to fetch branches: {e}")
            return False

    def create_worktree(
        self, repo_path: Path, branch: str, worktree_path: Path
    ) -> bool:
        """Create a new worktree for the given branch."""
        logger.debug(f"Creating worktree for {branch} at {worktree_path}")

        try:
            # Check if branch exists locally
            result = run_command(
                ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                cwd=repo_path,
                timeout=10,
                description=f"Check if branch {branch} exists locally",
            )

            if result.returncode == 0:
                # Branch exists locally
                cmd = ["git", "worktree", "add", str(worktree_path), branch]
            else:
                # Try to create from remote
                cmd = [
                    "git",
                    "worktree",
                    "add",
                    str(worktree_path),
                    "-b",
                    branch,
                    f"origin/{branch}",
                ]

            result = run_command_visible(
                cmd, cwd=repo_path, timeout=30
            )

            success = result.returncode == 0
            if success:
                logger.debug(f"Worktree created successfully at {worktree_path}")
            else:
                logger.error(f"Failed to create worktree: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Failed to create worktree: {e}")
            return False

    def remove_worktree(self, repo_path: Path, worktree_path: Path) -> bool:
        """Remove a worktree."""
        logger.debug(f"Removing worktree at {worktree_path}")

        try:
            result = run_command_visible(
                ["git", "worktree", "remove", str(worktree_path)],
                cwd=repo_path,
                timeout=30,
            )

            success = result.returncode == 0
            if success:
                logger.debug("Worktree removed successfully")
            else:
                logger.error(f"Failed to remove worktree: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Failed to remove worktree: {e}")
            return False

    def analyze_branches_for_cleanup(
        self, repo_path: Path, worktrees: list[WorktreeInfo]
    ) -> list[BranchStatus]:
        """Analyze branches to determine cleanup candidates."""
        logger.debug("Analyzing branches for cleanup")

        branch_statuses = []

        for worktree in worktrees:
            branch = worktree.branch

            # Check if branch has remote
            has_remote = self._branch_has_remote(repo_path, branch)

            # Check if branch is merged
            is_merged = self._branch_is_merged(repo_path, branch)

            branch_statuses.append(
                BranchStatus(
                    branch=branch,
                    has_remote=has_remote,
                    is_merged=is_merged,
                    path=worktree.path,
                )
            )

        logger.debug(f"Analyzed {len(branch_statuses)} branches")
        return branch_statuses

    def _branch_has_remote(self, repo_path: Path, branch: str) -> bool:
        """Check if branch has a remote tracking branch."""
        try:
            result = run_command(
                ["git", "config", f"branch.{branch}.remote"],
                cwd=repo_path,
                timeout=10,
                description=f"Check if branch {branch} has remote",
            )
            return result.returncode == 0
        except Exception:
            return False

    def _branch_is_merged(self, repo_path: Path, branch: str) -> bool:
        """Check if branch is merged into main/master (including squash merges)."""
        try:
            # Try main first, then master
            for base_branch in ["main", "master"]:
                # Check regular merge
                result = run_command(
                    ["git", "merge-base", "--is-ancestor", branch, base_branch],
                    cwd=repo_path,
                    timeout=10,
                    description=f"Check if {branch} is merged into {base_branch}",
                )
                if result.returncode == 0:
                    return True

                # Check for squash merge by looking for identical trees
                result = run_command(
                    [
                        "git",
                        "rev-list",
                        "--cherry-pick",
                        "--left-only",
                        f"{branch}...{base_branch}",
                    ],
                    cwd=repo_path,
                    timeout=10,
                    description=f"Check for squash merge of {branch} into {base_branch}",
                )
                if result.returncode == 0 and not result.stdout.strip():
                    # No commits unique to branch means it was squash merged
                    return True

            return False
        except Exception:
            return False

