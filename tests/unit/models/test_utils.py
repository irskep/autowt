"""Tests for utility functions."""

from autowt.utils import sanitize_branch_name


class TestSanitizeBranchName:
    """Tests for branch name sanitization."""

    def test_simple_branch_name(self):
        """Test that simple branch names pass through unchanged."""
        assert sanitize_branch_name("feature") == "feature"
        assert sanitize_branch_name("main") == "main"
        assert sanitize_branch_name("develop") == "develop"

    def test_slash_replacement(self):
        """Test that slashes are replaced with hyphens."""
        assert sanitize_branch_name("steve/bugfix") == "steve-bugfix"
        assert sanitize_branch_name("feature/user-auth") == "feature-user-auth"
        assert sanitize_branch_name("fix/multiple/slashes") == "fix-multiple-slashes"

    def test_space_replacement(self):
        """Test that spaces are replaced with hyphens."""
        assert sanitize_branch_name("fix bug") == "fix-bug"
        assert sanitize_branch_name("new feature") == "new-feature"

    def test_backslash_replacement(self):
        """Test that backslashes are replaced with hyphens."""
        assert sanitize_branch_name("windows\\path") == "windows-path"

    def test_special_characters_removal(self):
        """Test that problematic characters are removed."""
        # These characters can cause filesystem issues
        assert sanitize_branch_name("branch@name") == "branchname"
        assert sanitize_branch_name("branch#hash") == "branchhash"
        assert sanitize_branch_name("branch:colon") == "branchcolon"

    def test_dots_and_hyphens_trimming(self):
        """Test that leading/trailing dots and hyphens are removed."""
        assert sanitize_branch_name(".hidden-branch") == "hidden-branch"
        assert sanitize_branch_name("branch-name.") == "branch-name"
        assert sanitize_branch_name("-leading-hyphen") == "leading-hyphen"
        assert sanitize_branch_name("trailing-hyphen-") == "trailing-hyphen"

    def test_allowed_characters_preserved(self):
        """Test that allowed characters are preserved."""
        assert sanitize_branch_name("feature_123") == "feature_123"
        assert sanitize_branch_name("v1.2.3") == "v1.2.3"
        assert sanitize_branch_name("branch-name") == "branch-name"

    def test_empty_or_invalid_names(self):
        """Test handling of empty or completely invalid names."""
        assert sanitize_branch_name("") == "branch"
        assert sanitize_branch_name("...") == "branch"
        assert sanitize_branch_name("---") == "branch"
        assert sanitize_branch_name("@#$%") == "branch"

    def test_complex_branch_names(self):
        """Test complex real-world branch names."""
        assert (
            sanitize_branch_name("feature/user-auth/oauth2.0")
            == "feature-user-auth-oauth2.0"
        )
        assert (
            sanitize_branch_name("bugfix/issue-123_critical")
            == "bugfix-issue-123_critical"
        )
        assert sanitize_branch_name("release/v2.1.0-rc1") == "release-v2.1.0-rc1"
