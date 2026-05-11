"""Shell completion helpers for autowt.

Kept import-light: this module runs on every tab press, so it avoids
importing autowt's application modules (Click, Rich, config, etc.)
and shells out to git directly.
"""

import subprocess
from pathlib import Path


def _find_repo_root() -> Path | None:
    """Find the git repository root from the current directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _get_worktree_branches(repo_path: Path) -> list[str]:
    """Return branch names of all existing worktrees."""
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=repo_path,
        )
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []

    branches: list[str] = []
    current_branch: str | None = None

    for line in result.stdout.strip().split("\n"):
        if not line:
            if current_branch is not None:
                branches.append(current_branch)
            current_branch = None
        elif line.startswith("branch refs/heads/"):
            current_branch = line[len("branch refs/heads/") :]

    if current_branch is not None:
        branches.append(current_branch)

    return branches


def complete_worktree_branches(incomplete: str) -> list[tuple[str, str]]:
    """Return (branch, help_text) pairs for worktrees matching incomplete.

    Case-insensitive substring matching. Returns empty list on any error.
    """
    repo_path = _find_repo_root()
    if repo_path is None:
        return []

    return [
        (branch, "worktree")
        for branch in _get_worktree_branches(repo_path)
        if incomplete.lower() in branch.lower()
    ]
