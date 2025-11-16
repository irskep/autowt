"""Tests for branch prefix utility functions."""

import os
from pathlib import Path
from unittest.mock import Mock

from autowt.models import WorktreeInfo
from autowt.utils import (
    apply_branch_prefix,
    build_branch_template_context,
    get_canonical_branch_name,
)


class TestApplyBranchPrefix:
    """Tests for apply_branch_prefix function."""

    def test_no_prefix_returns_branch_unchanged(self):
        """Test that None prefix returns branch unchanged."""
        result = apply_branch_prefix("my-branch", None, {})
        assert result == "my-branch"

    def test_simple_prefix(self):
        """Test simple string prefix."""
        result = apply_branch_prefix("my-branch", "feature/", {})
        assert result == "feature/my-branch"

    def test_template_prefix_with_repo_name(self):
        """Test prefix template with repo_name variable."""
        context = {"repo_name": "myrepo"}
        result = apply_branch_prefix("my-branch", "{repo_name}/", context)
        assert result == "myrepo/my-branch"

    def test_template_prefix_with_github_username(self):
        """Test prefix template with github_username variable."""
        context = {"github_username": "alice"}
        result = apply_branch_prefix("my-branch", "{github_username}/", context)
        assert result == "alice/my-branch"

    def test_combined_template_prefix(self):
        """Test prefix template with multiple variables."""
        context = {"repo_name": "myrepo", "github_username": "alice"}
        result = apply_branch_prefix("feat", "{github_username}/{repo_name}-", context)
        assert result == "alice/myrepo-feat"

    def test_avoids_double_prefixing(self):
        """Test that prefix is not applied if branch already has it."""
        result = apply_branch_prefix("feature/my-branch", "feature/", {})
        assert result == "feature/my-branch"

    def test_avoids_double_prefixing_with_template(self):
        """Test that templated prefix avoids double-prefixing."""
        context = {"github_username": "alice"}
        result = apply_branch_prefix("alice/my-branch", "{github_username}/", context)
        assert result == "alice/my-branch"

    def test_missing_template_variable_returns_unchanged(self):
        """Test that missing template variable returns branch unchanged."""
        result = apply_branch_prefix("my-branch", "{missing_var}/", {})
        assert result == "my-branch"

    def test_environment_variable_expansion(self):
        """Test that environment variables are expanded."""
        os.environ["TEST_PREFIX"] = "test-prefix"
        try:
            result = apply_branch_prefix("my-branch", "$TEST_PREFIX/", {})
            assert result == "test-prefix/my-branch"
        finally:
            del os.environ["TEST_PREFIX"]


class TestBuildBranchTemplateContext:
    """Tests for build_branch_template_context function."""

    def test_basic_context_with_repo_name(self):
        """Test that context includes repo_name."""
        repo_path = Path("/path/to/myrepo")
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = None

        context = build_branch_template_context(repo_path, mock_services)

        assert "repo_name" in context
        assert context["repo_name"] == "myrepo"

    def test_context_includes_github_username_when_available(self):
        """Test that context includes github_username if available."""
        repo_path = Path("/path/to/myrepo")
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = "alice"

        context = build_branch_template_context(repo_path, mock_services)

        assert context["repo_name"] == "myrepo"
        assert context["github_username"] == "alice"

    def test_context_excludes_github_username_when_not_available(self):
        """Test that context excludes github_username if not available."""
        repo_path = Path("/path/to/myrepo")
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = None

        context = build_branch_template_context(repo_path, mock_services)

        assert context["repo_name"] == "myrepo"
        assert "github_username" not in context


class TestGetCanonicalBranchName:
    """Tests for get_canonical_branch_name function."""

    def test_no_prefix_returns_branch_unchanged(self):
        """Test that None prefix returns branch unchanged."""
        worktrees = []
        result = get_canonical_branch_name(
            "my-branch",
            None,
            worktrees,
            Path("/repo"),
            Mock(),
        )
        assert result == "my-branch"

    def test_exact_match_exists_returns_unchanged(self):
        """Test that exact match takes precedence."""
        worktrees = [
            WorktreeInfo(branch="my-branch", path=Path("/worktree")),
        ]
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = None

        result = get_canonical_branch_name(
            "my-branch",
            "feature/",
            worktrees,
            Path("/repo"),
            mock_services,
        )
        assert result == "my-branch"

    def test_prefixed_match_exists_uses_prefixed(self):
        """Test that prefixed version is used if it exists."""
        worktrees = [
            WorktreeInfo(branch="feature/my-branch", path=Path("/worktree")),
        ]
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = None

        result = get_canonical_branch_name(
            "my-branch",
            "feature/",
            worktrees,
            Path("/repo"),
            mock_services,
        )
        assert result == "feature/my-branch"

    def test_apply_to_new_branches_true_applies_prefix(self):
        """Test that prefix is applied to new branches when enabled."""
        worktrees = []
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = None

        result = get_canonical_branch_name(
            "my-branch",
            "feature/",
            worktrees,
            Path("/repo"),
            mock_services,
            apply_to_new_branches=True,
        )
        assert result == "feature/my-branch"

    def test_apply_to_new_branches_false_keeps_original(self):
        """Test that prefix is not applied to new branches when disabled."""
        worktrees = []
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = None

        result = get_canonical_branch_name(
            "my-branch",
            "feature/",
            worktrees,
            Path("/repo"),
            mock_services,
            apply_to_new_branches=False,
        )
        assert result == "my-branch"

    def test_with_github_username_template(self):
        """Test prefix resolution with github_username template."""
        worktrees = []
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = "alice"

        result = get_canonical_branch_name(
            "my-feature",
            "{github_username}/",
            worktrees,
            Path("/myrepo"),
            mock_services,
            apply_to_new_branches=True,
        )
        assert result == "alice/my-feature"

    def test_both_exact_and_prefixed_exist_prefers_exact(self):
        """Test that exact match is preferred when both exist."""
        worktrees = [
            WorktreeInfo(branch="my-branch", path=Path("/worktree1")),
            WorktreeInfo(branch="feature/my-branch", path=Path("/worktree2")),
        ]
        mock_services = Mock()
        mock_services.github.get_github_username.return_value = None

        result = get_canonical_branch_name(
            "my-branch",
            "feature/",
            worktrees,
            Path("/repo"),
            mock_services,
        )
        assert result == "my-branch"
