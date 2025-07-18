"""Tests for checkout command worktree conflict resolution."""

from pathlib import Path
from unittest.mock import patch

from autowt.commands.checkout import (
    _generate_alternative_worktree_path,
    _prompt_for_alternative_worktree,
)
from autowt.models import WorktreeInfo


class TestCheckoutConflicts:
    """Tests for worktree conflict resolution during checkout."""

    def test_creates_alternative_path_when_conflict_exists(self):
        """Test that alternative path is generated correctly when conflicts exist."""

        # Mock existing worktrees that conflict with desired path
        existing_worktrees = [
            WorktreeInfo(
                branch="other-branch",
                path=Path("/mock/repo-worktrees/testbranch"),
                is_current=False,
                is_primary=False,
            ),
            WorktreeInfo(
                branch="another-branch",
                path=Path("/mock/repo-worktrees/testbranch-2"),
                is_current=False,
                is_primary=False,
            ),
        ]

        base_path = Path("/mock/repo-worktrees/testbranch")
        alternative_path = _generate_alternative_worktree_path(
            base_path, existing_worktrees
        )

        # Should generate testbranch-3 since testbranch and testbranch-2 are taken
        assert str(alternative_path).endswith("testbranch-3")

    def test_cancels_when_user_declines_alternative_path(self):
        """Test that worktree creation is cancelled when user declines alternative path."""
        with patch(
            "autowt.commands.checkout.confirm_default_yes", return_value=False
        ) as mock_confirm:
            original_path = Path("/mock/repo-worktrees/testbranch")
            alternative_path = Path("/mock/repo-worktrees/testbranch-2")

            # Should return False when user declines
            result = _prompt_for_alternative_worktree(
                original_path, alternative_path, "other-branch"
            )
            assert result is False
            mock_confirm.assert_called_once()
