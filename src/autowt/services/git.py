"""Git operations service for autowt."""

import logging
from collections.abc import Callable
from pathlib import Path

from autowt.models import BranchStatus, WorktreeInfo
from autowt.prompts import confirm_default_no
from autowt.utils import run_command, run_command_quiet_on_failure, run_command_visible

logger = logging.getLogger(__name__)


class GitCommands:
    """Low-level git command construction."""

    @staticmethod
    def worktree_add_existing(worktree_path: Path, branch: str) -> list[str]:
        """Build command to add worktree for existing branch."""
        return ["git", "worktree", "add", str(worktree_path), branch]

    @staticmethod
    def worktree_add_new_branch(
        worktree_path: Path, branch: str, start_point: str
    ) -> list[str]:
        """Build command to add worktree with new branch from start point."""
        return ["git", "worktree", "add", str(worktree_path), "-b", branch, start_point]

    @staticmethod
    def worktree_remove(worktree_path: Path, force: bool = False) -> list[str]:
        """Build command to remove worktree."""
        cmd = ["git", "worktree", "remove"]
        if force:
            cmd.append("--force")
        cmd.append(str(worktree_path))
        return cmd

    @staticmethod
    def branch_exists_locally(branch: str) -> list[str]:
        """Build command to check if branch exists locally."""
        return ["git", "show-ref", "--verify", f"refs/heads/{branch}"]

    @staticmethod
    def branch_exists_remotely(branch: str, remote: str = "origin") -> list[str]:
        """Build command to check if branch exists on remote.

        Args:
            branch: Branch name to check
            remote: Remote name (defaults to "origin" for backward compatibility)

        Returns:
            Git command as list of strings
        """
        return ["git", "show-ref", "--verify", f"refs/remotes/{remote}/{branch}"]


class BranchResolver:
    """Resolves branch existence and determines worktree creation strategy."""

    def __init__(self, git_service):
        self.commands = GitCommands()
        self.git_service = git_service

    def resolve_worktree_source(
        self, repo_path: Path, branch: str, from_branch: str | None
    ) -> Callable[[Path], list[str]]:
        """Return function that builds git command for creating worktree."""
        if from_branch:
            return self._build_command_from_specific_branch(
                repo_path, branch, from_branch
            )
        return self._build_command_from_branch_hierarchy(repo_path, branch)

    def check_remote_branch_availability(
        self, repo_path: Path, branch: str
    ) -> tuple[bool, str | None]:
        """Check if branch exists on remote.

        First checks if branch exists remotely (from previous fetches), then tries to fetch
        the specific branch if not found, and checks again. Uses the branch's tracking
        remote if configured, otherwise falls back to priority order (origin → upstream).

        Returns:
            Tuple of (exists_remotely, remote_name)
        """
        if self._branch_exists_locally(repo_path, branch):
            return False, None

        # Determine which remote to use (tracking remote or fallback)
        remote = self.git_service._get_remote_for_branch(repo_path, branch)
        if not remote:
            return False, None

        # First check if branch already exists remotely (from previous fetches)
        if self._branch_exists_remotely(repo_path, branch, remote):
            return True, remote

        # If not found, try to fetch the specific branch and check again
        if self._try_fetch_specific_branch(repo_path, branch, remote):
            if self._branch_exists_remotely(repo_path, branch, remote):
                return True, remote

        return False, None

    def _try_fetch_specific_branch(
        self, repo_path: Path, branch: str, remote: str
    ) -> bool:
        """Try to fetch a specific branch from remote.

        Returns:
            True if fetch succeeded, False otherwise
        """
        try:
            result = run_command_quiet_on_failure(
                ["git", "fetch", remote, f"{branch}:{branch}"],
                cwd=repo_path,
                timeout=30,
                description=f"Fetch specific branch {branch} from {remote}",
            )
            return result.returncode == 0
        except Exception:
            # If fetch fails (e.g., no remote, network issue), try a simpler fetch
            try:
                result = run_command_quiet_on_failure(
                    ["git", "fetch", remote, branch],
                    cwd=repo_path,
                    timeout=30,
                    description=f"Fetch branch {branch} from {remote}",
                )
                return result.returncode == 0
            except Exception:
                return False

    def _build_command_from_specific_branch(
        self, repo_path: Path, branch: str, from_branch: str
    ) -> Callable[[Path], list[str]]:
        """Return command builder when user specified source branch."""
        if self._branch_exists_locally(repo_path, branch):
            return lambda path: self.commands.worktree_add_existing(path, branch)
        return lambda path: self.commands.worktree_add_new_branch(
            path, branch, from_branch
        )

    def _build_command_from_branch_hierarchy(
        self, repo_path: Path, branch: str
    ) -> Callable[[Path], list[str]]:
        """Return command builder using branch resolution hierarchy."""
        if self._branch_exists_locally(repo_path, branch):
            return lambda path: self.commands.worktree_add_existing(path, branch)

        # Determine remote to use for this branch
        remote = self.git_service._get_remote_for_branch(repo_path, branch)
        if remote and self._branch_exists_remotely(repo_path, branch, remote):
            return lambda path: self.commands.worktree_add_new_branch(
                path, branch, f"{remote}/{branch}"
            )

        start_point = self._find_best_start_point(repo_path)
        return lambda path: self.commands.worktree_add_new_branch(
            path, branch, start_point
        )

    def _branch_exists_locally(self, repo_path: Path, branch: str) -> bool:
        """Check if branch exists locally."""
        result = run_command_quiet_on_failure(
            self.commands.branch_exists_locally(branch),
            cwd=repo_path,
            timeout=10,
            description=f"Check if branch {branch} exists locally",
        )
        return result.returncode == 0

    def _branch_exists_remotely(
        self, repo_path: Path, branch: str, remote: str = "origin"
    ) -> bool:
        """Check if branch exists on remote.

        Args:
            repo_path: Path to the repository
            branch: Branch name to check
            remote: Remote name (defaults to "origin")

        Returns:
            True if branch exists on the specified remote
        """
        result = run_command_quiet_on_failure(
            self.commands.branch_exists_remotely(branch, remote),
            cwd=repo_path,
            timeout=10,
            description=f"Check if remote branch {remote}/{branch} exists",
        )
        return result.returncode == 0

    def _find_best_start_point(self, repo_path: Path) -> str:
        """Find best starting point for new branch."""
        default_branch = self.git_service._get_default_branch(repo_path)
        if not default_branch:
            return "HEAD"

        # Try to use remote version of default branch if available
        remote = self.git_service._get_remote_for_branch(repo_path, default_branch)
        if remote and self._branch_exists_remotely(repo_path, default_branch, remote):
            return f"{remote}/{default_branch}"

        if self._branch_exists_locally(repo_path, default_branch):
            return default_branch

        return "HEAD"


class GitOutputParser:
    """Parses git command outputs into structured data."""

    @staticmethod
    def parse_worktree_list(porcelain_output: str) -> list[WorktreeInfo]:
        """Parse git worktree list --porcelain output into WorktreeInfo objects."""
        worktrees = []
        current_path = None
        current_branch = None
        is_first_worktree = True

        for line in porcelain_output.strip().split("\n"):
            if not line:
                if current_path and current_branch:
                    worktrees.append(
                        WorktreeInfo(
                            branch=current_branch,
                            path=Path(current_path),
                            is_current=False,  # We don't track this in porcelain output
                            is_primary=is_first_worktree,
                        )
                    )
                current_path = None
                current_branch = None
                is_first_worktree = False
            elif line.startswith("worktree "):
                current_path = line[9:]  # Remove 'worktree ' prefix
            elif line.startswith("branch refs/heads/"):
                current_branch = line[18:]  # Remove 'branch refs/heads/' prefix
            elif line in ["bare", "detached"] or line.startswith("HEAD "):
                continue

        # Process last entry
        if current_path and current_branch:
            worktrees.append(
                WorktreeInfo(
                    branch=current_branch,
                    path=Path(current_path),
                    is_current=False,
                    is_primary=is_first_worktree,
                )
            )

        return worktrees


class GitService:
    """Handles all git operations for worktree management."""

    def __init__(self):
        """Initialize git service."""
        self.commands = GitCommands()
        self.branch_resolver = BranchResolver(self)
        self.parser = GitOutputParser()
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
            result = self._execute_worktree_list_command(repo_path)
            if result.returncode != 0:
                logger.error(f"Git worktree list failed: {result.stderr}")
                return []

            worktrees = self.parser.parse_worktree_list(result.stdout)
            logger.debug(f"Found {len(worktrees)} worktrees")
            return worktrees

        except Exception as e:
            logger.error(f"Failed to list worktrees: {e}")
            return []

    def _execute_worktree_list_command(self, repo_path: Path):
        """Execute git worktree list command."""
        return run_command(
            ["git", "worktree", "list", "--porcelain"],
            cwd=repo_path,
            timeout=30,
            description="List git worktrees",
        )

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
        self,
        repo_path: Path,
        branch: str,
        worktree_path: Path,
        from_branch: str | None = None,
    ) -> bool:
        """Create a new worktree for the given branch."""
        logger.debug(f"Creating worktree for {branch} at {worktree_path}")

        try:
            command_builder = self.branch_resolver.resolve_worktree_source(
                repo_path, branch, from_branch
            )
            cmd = command_builder(worktree_path)
            result = run_command_visible(cmd, cwd=repo_path, timeout=30)

            return self._evaluate_worktree_creation_result(result, worktree_path)

        except Exception as e:
            logger.error(f"Failed to create worktree: {e}")
            return False

    def _evaluate_worktree_creation_result(self, result, worktree_path: Path) -> bool:
        """Evaluate worktree creation command result and log appropriately."""
        success = result.returncode == 0
        if success:
            logger.debug(f"Worktree created successfully at {worktree_path}")
        else:
            logger.error(f"Failed to create worktree: {result.stderr}")
        return success

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
            cmd = self.commands.worktree_remove(worktree_path, force)
            result = run_command_visible(cmd, cwd=repo_path)

            if result.returncode == 0:
                logger.debug("Worktree removed successfully")
                return True

            return self._retry_worktree_removal_if_needed(
                repo_path, worktree_path, force, interactive, result
            )

        except Exception as e:
            logger.error(f"Failed to remove worktree: {e}")
            return False

    def _retry_worktree_removal_if_needed(
        self,
        repo_path: Path,
        worktree_path: Path,
        force: bool,
        interactive: bool,
        result,
    ) -> bool:
        """Retry worktree removal with force if user confirms and conditions are met."""
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

    def analyze_branches_for_cleanup(
        self,
        repo_path: Path,
        worktrees: list[WorktreeInfo],
        preferred_remote: str | None = None,
    ) -> list[BranchStatus]:
        """Analyze branches to determine cleanup candidates.

        Args:
            repo_path: Repository path
            worktrees: List of worktrees to analyze
            preferred_remote: Preferred remote name (future --remote flag support)
        """
        logger.debug("Analyzing branches for cleanup")

        default_branch = self._prepare_default_branch_for_analysis(
            repo_path, preferred_remote
        )
        branch_statuses = [
            self._analyze_single_branch(repo_path, worktree, default_branch)
            for worktree in worktrees
        ]

        logger.debug(f"Analyzed {len(branch_statuses)} branches")
        return branch_statuses

    def _prepare_default_branch_for_analysis(
        self, repo_path: Path, preferred_remote: str | None = None
    ) -> str | None:
        """Prepare default branch reference for merge analysis.

        Args:
            repo_path: Repository path
            preferred_remote: Preferred remote name (future --remote flag support)

        Returns:
            Remote branch reference if remotes exist, otherwise local branch reference
        """
        default_branch = self._get_default_branch(repo_path)
        if not default_branch:
            logger.warning(
                "Could not determine default branch, skipping merge analysis"
            )
            return None

        # Try to find a remote branch reference first
        remote_ref = self._find_remote_branch_reference(
            repo_path, default_branch, preferred_remote
        )
        if remote_ref:
            logger.debug(f"Using remote branch reference: {remote_ref}")
            return remote_ref

        # Fall back to local branch for remoteless repos
        logger.debug(
            f"No remotes found, using local branch reference: {default_branch}"
        )
        return default_branch

    def _analyze_single_branch(
        self, repo_path: Path, worktree: WorktreeInfo, default_branch: str | None
    ) -> BranchStatus:
        """Analyze a single branch for cleanup eligibility."""
        branch = worktree.branch
        return BranchStatus(
            branch=branch,
            has_remote=self._branch_has_remote(repo_path, branch),
            is_merged=self._branch_is_merged_cached(repo_path, branch, default_branch),
            is_identical=self._branches_are_identical_cached(
                repo_path, branch, default_branch
            ),
            path=worktree.path,
            has_uncommitted_changes=self.has_uncommitted_changes(worktree.path),
        )

    def _get_default_branch(self, repo_path: Path) -> str | None:
        """Get the default branch name (main, master, etc.)."""
        try:
            # Try to get default branch from primary remote
            remotes = self._get_available_remotes(repo_path)
            if remotes:
                branch_from_remote = self._extract_default_branch_from_remote(
                    repo_path, remotes[0]
                )
                if branch_from_remote:
                    return branch_from_remote

            branch_from_common_names = self._find_common_default_branch(repo_path)
            if branch_from_common_names:
                return branch_from_common_names

            return self._get_current_branch_as_fallback(repo_path)
        except Exception:
            return None

    def _extract_default_branch_from_remote(
        self, repo_path: Path, remote: str
    ) -> str | None:
        """Extract default branch name from remote HEAD reference.

        Args:
            repo_path: Path to the repository
            remote: Remote name to query (e.g., "origin", "upstream")

        Returns:
            Default branch name, or None if not found
        """
        result = run_command_quiet_on_failure(
            ["git", "symbolic-ref", f"refs/remotes/{remote}/HEAD"],
            cwd=repo_path,
            timeout=10,
            description=f"Get default branch from {remote}",
        )
        if result.returncode == 0:
            branch_ref = result.stdout.strip()
            prefix = f"refs/remotes/{remote}/"
            if branch_ref.startswith(prefix):
                return branch_ref[len(prefix) :]
        return None

    def _find_common_default_branch(self, repo_path: Path) -> str | None:
        """Check for common default branch names (main, master)."""
        for branch in ["main", "master"]:
            result = run_command_quiet_on_failure(
                ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                cwd=repo_path,
                timeout=10,
                description=f"Check if {branch} exists",
            )
            if result.returncode == 0:
                return branch
        return None

    def _get_current_branch_as_fallback(self, repo_path: Path) -> str | None:
        """Get current branch as last resort fallback."""
        result = run_command(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
            timeout=10,
            description="Get current branch as fallback",
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None

    def _get_available_remotes(self, repo_path: Path) -> list[str]:
        """Get list of available remotes, with preferred remotes first."""
        try:
            result = run_command_quiet_on_failure(
                ["git", "remote"],
                cwd=repo_path,
                timeout=10,
                description="Get available remotes",
            )
            if result.returncode != 0:
                return []

            remotes = result.stdout.strip().split("\n") if result.stdout.strip() else []

            # Prioritize common remote names
            preferred_order = ["origin", "upstream"]
            sorted_remotes = []

            # Add preferred remotes first
            for preferred in preferred_order:
                if preferred in remotes:
                    sorted_remotes.append(preferred)

            # Add remaining remotes
            for remote in remotes:
                if remote not in sorted_remotes:
                    sorted_remotes.append(remote)

            return sorted_remotes
        except Exception:
            return []

    def _get_remote_default_branch(self, repo_path: Path, remote: str) -> str | None:
        """Get the default branch for a specific remote."""
        try:
            # Try to get from remote HEAD reference
            result = run_command_quiet_on_failure(
                ["git", "symbolic-ref", f"refs/remotes/{remote}/HEAD"],
                cwd=repo_path,
                timeout=10,
                description=f"Get default branch from {remote} HEAD",
            )
            if result.returncode == 0:
                branch_ref = result.stdout.strip()
                if branch_ref.startswith(f"refs/remotes/{remote}/"):
                    return branch_ref[len(f"refs/remotes/{remote}/") :]
            return None
        except Exception:
            return None

    def _find_remote_branch_reference(
        self, repo_path: Path, local_branch: str, preferred_remote: str | None = None
    ) -> str | None:
        """Find the best remote branch reference for comparison.

        Args:
            repo_path: Repository path
            local_branch: Local branch name (e.g., "main")
            preferred_remote: Preferred remote name (future --remote flag support)

        Returns:
            Remote branch reference (e.g., "origin/main") or None if no remotes exist
        """
        remotes = self._get_available_remotes(repo_path)
        if not remotes:
            return None

        # If a specific remote is preferred (future --remote flag), try it first
        if preferred_remote and preferred_remote in remotes:
            candidate = f"{preferred_remote}/{local_branch}"
            if self._remote_branch_exists(repo_path, candidate):
                return candidate

        # Try each available remote in priority order
        for remote in remotes:
            candidate = f"{remote}/{local_branch}"
            if self._remote_branch_exists(repo_path, candidate):
                return candidate

        return None

    def _remote_branch_exists(self, repo_path: Path, remote_branch: str) -> bool:
        """Check if a remote branch reference exists."""
        try:
            result = run_command_quiet_on_failure(
                ["git", "show-ref", "--verify", f"refs/remotes/{remote_branch}"],
                cwd=repo_path,
                timeout=10,
                description=f"Check if {remote_branch} exists",
            )
            return result.returncode == 0
        except Exception:
            return False

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

    def _get_branch_tracking_remote(self, repo_path: Path, branch: str) -> str | None:
        """Get the remote that a branch is tracking, if any.

        Args:
            repo_path: Path to the repository
            branch: Branch name to check

        Returns:
            Remote name (e.g., "origin", "upstream") if branch has tracking remote,
            None otherwise
        """
        try:
            result = run_command_quiet_on_failure(
                ["git", "config", f"branch.{branch}.remote"],
                cwd=repo_path,
                timeout=10,
                description=f"Get tracking remote for branch {branch}",
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def _get_remote_for_branch(self, repo_path: Path, branch: str) -> str | None:
        """Get remote to use for a branch (tracking remote or fallback).

        This method first checks if the branch has a configured tracking remote.
        If not, it falls back to available remotes in priority order:
        origin → upstream → first available remote.

        Args:
            repo_path: Path to the repository
            branch: Branch name to check

        Returns:
            Remote name to use, or None if no remotes available
        """
        # First try tracking remote
        tracking_remote = self._get_branch_tracking_remote(repo_path, branch)
        if tracking_remote:
            return tracking_remote

        # Fall back to available remotes in priority order
        available = self._get_available_remotes(repo_path)
        return available[0] if available else None

    def _branches_are_identical_cached(
        self, repo_path: Path, branch: str, default_branch: str | None
    ) -> bool:
        """Check if branch points to the same commit as default branch."""
        try:
            if not default_branch:
                return False

            branch_hash = self._get_commit_hash(repo_path, branch)
            default_hash = self._get_commit_hash(repo_path, default_branch)

            return branch_hash and default_hash and branch_hash == default_hash
        except Exception:
            return False

    def _get_commit_hash(self, repo_path: Path, branch: str) -> str | None:
        """Get commit hash for a branch."""
        result = run_command_quiet_on_failure(
            ["git", "rev-parse", branch],
            cwd=repo_path,
            timeout=10,
            description=f"Get commit hash for {branch}",
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def _branch_is_merged_cached(
        self, repo_path: Path, branch: str, default_branch: str | None
    ) -> bool:
        """Check if branch is merged into default branch (but not identical)."""
        try:
            if not default_branch:
                return False

            if self._branches_are_identical_cached(repo_path, branch, default_branch):
                return False

            return self._is_branch_ancestor_of_default(
                repo_path, branch, default_branch
            )
        except Exception:
            return False

    def _is_branch_ancestor_of_default(
        self, repo_path: Path, branch: str, default_branch: str
    ) -> bool:
        """Check if branch is an ancestor of default branch (was merged)."""
        result = run_command_quiet_on_failure(
            ["git", "merge-base", "--is-ancestor", branch, default_branch],
            cwd=repo_path,
            timeout=10,
            description=f"Check if {branch} is merged into {default_branch}",
        )
        return result.returncode == 0

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
            bare_repos = []
            # Look for directories ending in .git
            for item in path.iterdir():
                if item.is_dir() and item.name.endswith(".git"):
                    if self._is_bare_repo(item):
                        bare_repos.append(item)

            if len(bare_repos) == 0:
                return None
            elif len(bare_repos) == 1:
                return bare_repos[0]
            else:
                # Multiple bare repositories found - this is ambiguous
                repo_names = [repo.name for repo in bare_repos]
                raise ValueError(
                    f"Multiple bare git repositories found in {path}: {', '.join(repo_names)}. "
                    f"Please run autowt from within one of the specific repository directories."
                )
        except ValueError:
            # Re-raise ValueError to preserve the specific error message
            raise
        except Exception:
            return None
