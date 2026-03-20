"""Shell completion helpers for autowt.

Kept import-light intentionally: this module runs on every tab press inside a
shell-spawned subprocess, so minimising Python import overhead matters.

Only GitOutputParser is imported from the application — it has no heavy
transitive dependencies (just WorktreeInfo from models).
"""

import subprocess
from pathlib import Path

from autowt.services.git import GitOutputParser


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
    """Return branch names of all existing worktrees.

    Delegates porcelain parsing to GitOutputParser so the logic lives in one place.
    Excludes detached-HEAD worktrees (they have no branch name).
    """
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

    worktrees = GitOutputParser.parse_worktree_list(result.stdout)
    return [wt.branch for wt in worktrees]


def complete_worktree_branches(incomplete: str) -> list[tuple[str, str]]:
    """Return (branch, help_text) pairs for existing worktrees matching *incomplete*.

    Matching is case-insensitive substring search, so 'feat' matches
    'foo-bar-feature-cool'. Returns an empty list on any error so completion
    degrades gracefully.
    """
    repo_path = _find_repo_root()
    if repo_path is None:
        return []

    branches = _get_worktree_branches(repo_path)
    return [
        (branch, "switch to this worktree")
        for branch in branches
        if incomplete.lower() in branch.lower()
    ]
