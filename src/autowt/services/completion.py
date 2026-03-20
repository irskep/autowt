"""Shell completion helpers for autowt.

Kept import-light intentionally: this module runs on every tab press inside a
shell-spawned subprocess, so minimising Python import overhead matters.

No application modules are imported — only stdlib — so the import cost is minimal.
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


def _parse_worktree_branches(porcelain_output: str) -> list[str]:
    """Extract branch names from 'git worktree list --porcelain' output.

    Only returns branches (skips detached-HEAD worktrees).
    This is an intentionally lightweight re-implementation that avoids importing
    GitOutputParser (and its heavy transitive deps) on every tab press.
    """
    branches: list[str] = []
    current_branch: str | None = None

    for line in porcelain_output.strip().split("\n"):
        if not line:
            if current_branch is not None:
                branches.append(current_branch)
            current_branch = None
        elif line.startswith("branch refs/heads/"):
            current_branch = line[18:]  # strip 'branch refs/heads/'

    # Flush last entry (no trailing blank line)
    if current_branch is not None:
        branches.append(current_branch)

    return branches


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

    return _parse_worktree_branches(result.stdout)


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
