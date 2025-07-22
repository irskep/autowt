"""Git operations service for autowt."""

import logging
from pathlib import Path

from autowt.models import BranchStatus, WorktreeInfo
from autowt.prompts import confirm_default_no
from autowt.utils import run_command, run_command_quiet_on_failure, run_command_visible

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
            # Check for normal git repository (.git directory)
            if (current / ".git").exists():
                logger.debug(f"Found repo root: {current}")
                return current

            # Check if current directory is a bare repository
            if self._is_bare_repo(current):
                logger.debug(f"Found bare repo root: {current}")
                return current

            # Check for bare repositories in subdirectories (*.git pattern)
            bare_repo = self._find_bare_repo_in_dir(current)
            if bare_repo:
                logger.debug(f"Found bare repo in subdirectory: {bare_repo}")
                return bare_repo

            current = current.parent

        logger.debug("No git repository found")
        return None

    def is_git_repo(self, path: Path) -> bool:
        """Check if the given path is a git repository."""
        try:
            # Check for regular git repository
            result = run_command(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                timeout=10,
                description="Check if directory is git repo",
            )
            if result.returncode == 0:
                logger.debug(f"Path {path} is regular git repo")
                return True

            # Check for bare repository
            is_bare = self._is_bare_repo(path)
            logger.debug(f"Path {path} is git repo (bare: {is_bare}): {is_bare}")
            return is_bare
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
            is_first_worktree = True

            for line in result.stdout.strip().split("\n"):
                if not line:
                    # End of worktree entry
                    if current_path and current_branch:
                        worktrees.append(
                            WorktreeInfo(
                                branch=current_branch,
                                path=Path(current_path),
                                is_current=current_worktree is not None,
                                is_primary=is_first_worktree,
                            )
                        )
                    current_worktree = None
                    current_path = None
                    current_branch = None
                    is_first_worktree = False
                elif line.startswith("worktree "):
                    current_path = line[9:]  # Remove 'worktree ' prefix
                elif line.startswith("branch refs/heads/"):
                    current_branch = line[18:]  # Remove 'branch refs/heads/' prefix
                elif line.startswith("HEAD "):
                    # This is just the commit hash, ignore for branch name
                    continue
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
                        is_primary=is_first_worktree,
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
            result = run_command_quiet_on_failure(
                ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                cwd=repo_path,
                timeout=10,
                description=f"Check if branch {branch} exists locally",
            )

            if result.returncode == 0:
                # Branch exists locally
                cmd = ["git", "worktree", "add", str(worktree_path), branch]
            else:
                # Check if remote branch exists
                result = run_command_quiet_on_failure(
                    ["git", "show-ref", "--verify", f"refs/remotes/origin/{branch}"],
                    cwd=repo_path,
                    timeout=10,
                    description=f"Check if remote branch origin/{branch} exists",
                )

                if result.returncode == 0:
                    # Remote branch exists, create from it
                    cmd = [
                        "git",
                        "worktree",
                        "add",
                        str(worktree_path),
                        "-b",
                        branch,
                        f"origin/{branch}",
                    ]
                else:
                    # Neither local nor remote exists, try fallback hierarchy
                    default_branch = self._get_default_branch(repo_path)

                    # Try origin/{default_branch} first, then {default_branch}, then HEAD
                    start_point = "HEAD"  # Ultimate fallback
                    if default_branch:
                        # Check if origin/{default_branch} exists
                        origin_result = run_command_quiet_on_failure(
                            [
                                "git",
                                "show-ref",
                                "--verify",
                                f"refs/remotes/origin/{default_branch}",
                            ],
                            cwd=repo_path,
                            timeout=10,
                            description=f"Check if origin/{default_branch} exists",
                        )
                        if origin_result.returncode == 0:
                            start_point = f"origin/{default_branch}"
                        else:
                            # Check if local default branch exists
                            local_result = run_command_quiet_on_failure(
                                [
                                    "git",
                                    "show-ref",
                                    "--verify",
                                    f"refs/heads/{default_branch}",
                                ],
                                cwd=repo_path,
                                timeout=10,
                                description=f"Check if local {default_branch} exists",
                            )
                            if local_result.returncode == 0:
                                start_point = default_branch

                    cmd = [
                        "git",
                        "worktree",
                        "add",
                        str(worktree_path),
                        "-b",
                        branch,
                        start_point,
                    ]
            result = run_command_visible(cmd, cwd=repo_path, timeout=30)

            success = result.returncode == 0
            if success:
                logger.debug(f"Worktree created successfully at {worktree_path}")
            else:
                logger.error(f"Failed to create worktree: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Failed to create worktree: {e}")
            return False

    def remove_worktree(
        self,
        repo_path: Path,
        worktree_path: Path,
        force: bool = False,
        interactive: bool = True,
    ) -> bool:
        """Remove a worktree."""
        logger.debug(f"Removing worktree at {worktree_path}")

        try:
            cmd = ["git", "worktree", "remove"]
            if force:
                cmd.append("--force")
            cmd.append(str(worktree_path))

            result = run_command_visible(cmd, cwd=repo_path, timeout=30)

            success = result.returncode == 0
            if success:
                logger.debug("Worktree removed successfully")
                return True

            # If removal failed and we haven't tried force yet
            if (
                not force
                and interactive
                and result.stderr
                and "modified or untracked files" in result.stderr
            ):
                logger.error(f"Failed to remove worktree: {result.stderr}")
                print(f"Git error: {result.stderr.strip()}")

                if confirm_default_no(
                    "Retry with --force to remove worktree with modified files?"
                ):
                    return self.remove_worktree(
                        repo_path, worktree_path, force=True, interactive=False
                    )
            else:
                logger.error(f"Failed to remove worktree: {result.stderr}")

            return False

        except Exception as e:
            logger.error(f"Failed to remove worktree: {e}")
            return False

    def analyze_branches_for_cleanup(
        self, repo_path: Path, worktrees: list[WorktreeInfo]
    ) -> list[BranchStatus]:
        """Analyze branches to determine cleanup candidates."""
        logger.debug("Analyzing branches for cleanup")

        # Get default branch once and cache it - use remote tracking branch for comparison
        default_branch = self._get_default_branch(repo_path)
        if not default_branch:
            logger.warning(
                "Could not determine default branch, skipping merge analysis"
            )
        else:
            # Use remote tracking branch for comparison after fetch
            default_branch = f"origin/{default_branch}"

        branch_statuses = []

        for worktree in worktrees:
            branch = worktree.branch

            # Check if branch has remote
            has_remote = self._branch_has_remote(repo_path, branch)

            # Check if branch is identical to default branch
            is_identical = self._branches_are_identical_cached(
                repo_path, branch, default_branch
            )

            # Check if branch is merged (only if it had unique commits)
            is_merged = self._branch_is_merged_cached(repo_path, branch, default_branch)

            # Check for uncommitted changes
            has_uncommitted = self.has_uncommitted_changes(worktree.path)

            branch_statuses.append(
                BranchStatus(
                    branch=branch,
                    has_remote=has_remote,
                    is_merged=is_merged,
                    is_identical=is_identical,
                    path=worktree.path,
                    has_uncommitted_changes=has_uncommitted,
                )
            )

        logger.debug(f"Analyzed {len(branch_statuses)} branches")
        return branch_statuses

    def _get_default_branch(self, repo_path: Path) -> str | None:
        """Get the default branch name (main, master, etc.)."""
        try:
            # Try to get the default branch from origin (this often fails, that's expected)
            result = run_command_quiet_on_failure(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                cwd=repo_path,
                timeout=10,
                description="Get default branch from origin",
            )
            if result.returncode == 0:
                # Extract branch name from refs/remotes/origin/main
                branch_ref = result.stdout.strip()
                if branch_ref.startswith("refs/remotes/origin/"):
                    return branch_ref[len("refs/remotes/origin/") :]

            # Fall back to checking common default branches
            for branch in ["main", "master"]:
                result = run_command_quiet_on_failure(
                    ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                    cwd=repo_path,
                    timeout=10,
                    description=f"Check if {branch} exists",
                )
                if result.returncode == 0:
                    return branch

            # If neither main nor master exist, try to get current branch as fallback
            result = run_command(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                timeout=10,
                description="Get current branch as fallback",
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            return None
        except Exception:
            return None

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

    def _branches_are_identical_cached(
        self, repo_path: Path, branch: str, default_branch: str | None
    ) -> bool:
        """Check if branch points to the same commit as default branch (with cached default branch)."""
        try:
            if not default_branch:
                return False

            # Get commit hashes for both branches
            branch_result = run_command(
                ["git", "rev-parse", branch],
                cwd=repo_path,
                timeout=10,
                description=f"Get commit hash for {branch}",
            )
            base_result = run_command(
                ["git", "rev-parse", default_branch],
                cwd=repo_path,
                timeout=10,
                description=f"Get commit hash for {default_branch}",
            )

            if branch_result.returncode == 0 and base_result.returncode == 0:
                # Branches are identical if they point to the same commit
                return branch_result.stdout.strip() == base_result.stdout.strip()

            return False
        except Exception:
            return False

    def _branch_is_merged_cached(
        self, repo_path: Path, branch: str, default_branch: str | None
    ) -> bool:
        """Check if branch is merged into default branch (but not identical) with cached default branch."""
        try:
            if not default_branch:
                return False

            # Don't consider identical branches as "merged"
            if self._branches_are_identical_cached(repo_path, branch, default_branch):
                return False

            # Check if branch is ancestor (was merged)
            result = run_command(
                ["git", "merge-base", "--is-ancestor", branch, default_branch],
                cwd=repo_path,
                timeout=10,
                description=f"Check if {branch} is merged into {default_branch}",
            )
            return result.returncode == 0

        except Exception:
            return False

    def has_uncommitted_changes(self, worktree_path: Path) -> bool:
        """Check if a worktree has uncommitted changes (staged or unstaged)."""
        try:
            # Check for staged and unstaged changes
            result = run_command(
                ["git", "status", "--porcelain"],
                cwd=worktree_path,
                timeout=10,
                description=f"Check uncommitted changes in {worktree_path}",
            )

            # If status command succeeds and has output, there are uncommitted changes
            if result.returncode == 0:
                has_changes = bool(result.stdout.strip())
                logger.debug(
                    f"Worktree {worktree_path} has uncommitted changes: {has_changes}"
                )
                return has_changes

            logger.debug(f"Failed to check status in {worktree_path}")
            return False

        except Exception as e:
            logger.debug(f"Error checking uncommitted changes in {worktree_path}: {e}")
            return False

    def delete_branch(self, repo_path: Path, branch: str, force: bool = False) -> bool:
        """Delete a local branch."""
        try:
            flag = "-D" if force else "-d"
            result = run_command(
                ["git", "branch", flag, branch],
                cwd=repo_path,
                timeout=10,
                description=f"Delete branch {branch}",
            )
            return result.returncode == 0
        except Exception:
            return False

    def _is_bare_repo(self, path: Path) -> bool:
        """Check if the given path is a bare git repository."""
        try:
            result = run_command(
                ["git", "rev-parse", "--is-bare-repository"],
                cwd=path,
                timeout=10,
                description=f"Check if {path} is bare repo",
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception:
            return False

    def _find_bare_repo_in_dir(self, path: Path) -> Path | None:
        """Find bare git repositories in subdirectories (*.git pattern)."""
        try:
            # Look for directories ending in .git
            for item in path.iterdir():
                if item.is_dir() and item.name.endswith(".git"):
                    if self._is_bare_repo(item):
                        return item
            return None
        except Exception:
            return None
