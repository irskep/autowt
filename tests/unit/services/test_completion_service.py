"""Tests for the shell completion service."""

from pathlib import Path
from unittest.mock import Mock, patch

from autowt.services.completion import (
    _get_worktree_branches,
    complete_worktree_branches,
)

# Realistic `git worktree list --porcelain` output used across multiple tests.
_PORCELAIN_TWO_WORKTREES = """\
worktree /home/user/myproject
HEAD abc123def456
branch refs/heads/main

worktree /home/user/myproject-feature-foo
HEAD 111222333444
branch refs/heads/feature-foo

"""

_PORCELAIN_WITH_DETACHED = """\
worktree /home/user/myproject
HEAD abc123def456
branch refs/heads/main

worktree /home/user/myproject-detached
HEAD deadbeef1234
detached

"""

_PORCELAIN_MANY = """\
worktree /home/user/myproject
HEAD aaa
branch refs/heads/main

worktree /home/user/myproject-foo-bar
HEAD bbb
branch refs/heads/foo-bar

worktree /home/user/myproject-foo-feature-cool
HEAD ccc
branch refs/heads/foo-feature-cool

worktree /home/user/myproject-baz-foo-qux
HEAD ddd
branch refs/heads/baz-foo-qux

"""


def _make_subprocess_result(stdout: str = "", returncode: int = 0) -> Mock:
    result = Mock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = ""
    return result


class TestGetWorktreeBranches:
    """Tests for the _get_worktree_branches helper."""

    def test_parses_single_worktree(self):
        with patch("autowt.services.completion.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result(
                stdout="""\
worktree /home/user/myproject
HEAD abc123
branch refs/heads/main

""",
            )

            result = _get_worktree_branches(Path("/home/user/myproject"))

            assert result == ["main"]

    def test_parses_multiple_worktrees(self):
        with patch("autowt.services.completion.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result(
                stdout=_PORCELAIN_TWO_WORKTREES
            )

            result = _get_worktree_branches(Path("/home/user/myproject"))

            assert result == ["main", "feature-foo"]

    def test_ignores_detached_head_worktrees(self):
        with patch("autowt.services.completion.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result(
                stdout=_PORCELAIN_WITH_DETACHED
            )

            result = _get_worktree_branches(Path("/home/user/myproject"))

            assert result == ["main"]
            assert "detached" not in result

    def test_empty_output_returns_empty_list(self):
        with patch("autowt.services.completion.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result(stdout="")

            result = _get_worktree_branches(Path("/home/user/myproject"))

            assert result == []

    def test_git_error_returns_empty_list(self):
        with patch("autowt.services.completion.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result(returncode=128)

            result = _get_worktree_branches(Path("/home/user/myproject"))

            assert result == []

    def test_preserves_slashes_in_branch_names(self):
        with patch("autowt.services.completion.subprocess.run") as mock_run:
            mock_run.return_value = _make_subprocess_result(
                stdout="""\
worktree /home/user/myproject
HEAD abc123
branch refs/heads/feature/user-auth

"""
            )

            result = _get_worktree_branches(Path("/home/user/myproject"))

            assert result == ["feature/user-auth"]


class TestCompleteWorktreeBranches:
    """Tests for the public complete_worktree_branches function."""

    def _patch_both(self, repo_path: str, porcelain_stdout: str, returncode: int = 0):
        """Return context managers that mock both subprocess.run calls."""
        root_result = _make_subprocess_result(stdout=repo_path + "\n", returncode=0)
        worktree_result = _make_subprocess_result(
            stdout=porcelain_stdout, returncode=returncode
        )
        return patch(
            "autowt.services.completion.subprocess.run",
            side_effect=[root_result, worktree_result],
        )

    def test_returns_all_worktrees_when_incomplete_is_empty(self):
        with self._patch_both("/home/user/myproject", _PORCELAIN_MANY):
            result = complete_worktree_branches("")

            branches = [branch for branch, _ in result]
            assert "main" in branches
            assert "foo-bar" in branches
            assert "foo-feature-cool" in branches
            assert "baz-foo-qux" in branches
            assert len(result) == 4

    def test_prefix_match(self):
        with self._patch_both("/home/user/myproject", _PORCELAIN_MANY):
            result = complete_worktree_branches("foo")

            branches = [branch for branch, _ in result]
            assert "foo-bar" in branches
            assert "foo-feature-cool" in branches
            # baz-foo-qux also contains "foo" as substring — expected
            assert "baz-foo-qux" in branches
            # main does not contain "foo"
            assert "main" not in branches

    def test_substring_match(self):
        """Core feature: 'feat' should match 'foo-feature-cool' even though
        it does not start with 'feat'."""
        with self._patch_both("/home/user/myproject", _PORCELAIN_MANY):
            result = complete_worktree_branches("feat")

            branches = [branch for branch, _ in result]
            assert "foo-feature-cool" in branches

    def test_case_insensitive_match(self):
        with self._patch_both("/home/user/myproject", _PORCELAIN_MANY):
            result = complete_worktree_branches("FEAT")

            branches = [branch for branch, _ in result]
            assert "foo-feature-cool" in branches

    def test_no_match_returns_empty(self):
        with self._patch_both("/home/user/myproject", _PORCELAIN_MANY):
            result = complete_worktree_branches("zzz-no-match")

            assert result == []

    def test_exact_match(self):
        with self._patch_both("/home/user/myproject", _PORCELAIN_TWO_WORKTREES):
            result = complete_worktree_branches("main")

            branches = [branch for branch, _ in result]
            assert branches == ["main"]
