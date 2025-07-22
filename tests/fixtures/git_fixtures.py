"""Git-related test fixtures and data builders."""

from pathlib import Path

from autowt.models import BranchStatus, WorktreeInfo


def build_sample_worktrees(base_path: Path) -> list[WorktreeInfo]:
    """Build sample worktree data for testing."""
    worktree_base = base_path.parent / "test-repo-worktrees"
    return [
        WorktreeInfo(
            branch="feature1",
            path=worktree_base / "feature1",
            is_current=False,
        ),
        WorktreeInfo(
            branch="feature2",
            path=worktree_base / "feature2",
            is_current=True,
        ),
        WorktreeInfo(
            branch="bugfix",
            path=worktree_base / "bugfix",
            is_current=False,
        ),
    ]


def build_sample_branch_statuses(worktrees: list[WorktreeInfo]) -> list[BranchStatus]:
    """Build sample branch status data for testing."""
    return [
        BranchStatus(
            branch="feature1",
            has_remote=False,  # Make it remoteless so it gets cleaned up
            is_merged=False,
            is_identical=False,
            path=worktrees[0].path,
        ),
        BranchStatus(
            branch="feature2",
            has_remote=False,
            is_merged=False,
            is_identical=True,  # This branch is identical to main
            path=worktrees[1].path,
        ),
        BranchStatus(
            branch="bugfix",
            has_remote=True,
            is_merged=True,
            is_identical=False,
            path=worktrees[2].path,
        ),
    ]
