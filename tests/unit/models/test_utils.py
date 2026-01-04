"""Tests for utility functions."""

from autowt.utils import normalize_dynamic_branch_name, sanitize_branch_name


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


class TestNormalizeDynamicBranchName:
    """Tests for dynamic branch name normalization."""

    def test_spaces_to_dashes(self):
        """Test that spaces are converted to dashes."""
        assert normalize_dynamic_branch_name("Fix the login bug") == "fix-the-login-bug"

    def test_underscores_to_dashes(self):
        """Test that underscores are converted to dashes."""
        assert normalize_dynamic_branch_name("fix_the_bug") == "fix-the-bug"

    def test_lowercase_conversion(self):
        """Test that input is lowercased."""
        assert normalize_dynamic_branch_name("FIX THE BUG") == "fix-the-bug"

    def test_preserves_slashes_for_hierarchy(self):
        """Test that slashes are preserved for hierarchical branches."""
        assert (
            normalize_dynamic_branch_name("feature/Add user auth")
            == "feature/add-user-auth"
        )
        assert normalize_dynamic_branch_name("bug/Fix login") == "bug/fix-login"

    def test_removes_git_invalid_chars(self):
        """Test removal of git-invalid characters."""
        assert normalize_dynamic_branch_name("branch~name") == "branchname"
        assert normalize_dynamic_branch_name("branch^name") == "branchname"
        assert normalize_dynamic_branch_name("branch:name") == "branchname"
        assert normalize_dynamic_branch_name("branch?name") == "branchname"
        assert normalize_dynamic_branch_name("branch*name") == "branchname"
        assert normalize_dynamic_branch_name("branch[name]") == "branchname"
        assert normalize_dynamic_branch_name("branch@name") == "branchname"
        assert normalize_dynamic_branch_name("branch\\name") == "branchname"

    def test_collapses_double_dots(self):
        """Test that .. sequences are collapsed to single dot."""
        assert normalize_dynamic_branch_name("branch..name") == "branch.name"

    def test_collapses_consecutive_dashes(self):
        """Test that consecutive dashes are collapsed."""
        assert normalize_dynamic_branch_name("branch---name") == "branch-name"
        assert normalize_dynamic_branch_name("a  b") == "a-b"  # spaces become dashes

    def test_collapses_consecutive_slashes(self):
        """Test that consecutive slashes are collapsed."""
        assert normalize_dynamic_branch_name("feature//name") == "feature/name"

    def test_strips_leading_trailing_chars(self):
        """Test that leading/trailing dashes, dots, slashes are stripped."""
        assert normalize_dynamic_branch_name("-branch") == "branch"
        assert normalize_dynamic_branch_name("branch-") == "branch"
        assert normalize_dynamic_branch_name(".branch") == "branch"
        assert normalize_dynamic_branch_name("branch.") == "branch"
        assert normalize_dynamic_branch_name("/branch") == "branch"
        assert normalize_dynamic_branch_name("branch/") == "branch"

    def test_component_leading_dot_stripped(self):
        """Test that path components don't start with dots."""
        assert normalize_dynamic_branch_name("feature/.hidden") == "feature/hidden"

    def test_component_lock_suffix_removed(self):
        """Test that .lock suffix is removed from components."""
        assert normalize_dynamic_branch_name("branch.lock") == "branch"
        assert normalize_dynamic_branch_name("feature/name.lock") == "feature/name"

    def test_component_leading_dash_stripped(self):
        """Test that path components don't start with dashes."""
        assert normalize_dynamic_branch_name("feature/-name") == "feature/name"

    def test_example_transformations_from_spec(self):
        """Test the example transformations from the spec."""
        assert normalize_dynamic_branch_name("Fix the login bug") == "fix-the-login-bug"
        assert (
            normalize_dynamic_branch_name("Feature: Add OAuth") == "feature-add-oauth"
        )
        assert (
            normalize_dynamic_branch_name("[BUG] Crash on startup")
            == "bug-crash-on-startup"
        )
        assert (
            normalize_dynamic_branch_name("feature/Add user auth")
            == "feature/add-user-auth"
        )

    def test_empty_result_handling(self):
        """Test handling of inputs that result in empty strings."""
        # All invalid characters
        assert normalize_dynamic_branch_name("~^:?*[]\\@") == ""
        # All stripped characters
        assert normalize_dynamic_branch_name("-.-/") == ""

    def test_real_world_github_issue_titles(self):
        """Test realistic GitHub issue titles."""
        assert (
            normalize_dynamic_branch_name("Add support for OAuth 2.0 authentication")
            == "add-support-for-oauth-2.0-authentication"
        )
        assert (
            normalize_dynamic_branch_name("[Feature Request] Dark mode toggle")
            == "feature-request-dark-mode-toggle"
        )
        assert (
            normalize_dynamic_branch_name("Bug: TypeError when clicking submit")
            == "bug-typeerror-when-clicking-submit"
        )

    def test_max_length_truncation(self):
        """Test that branch names are truncated to max 255 characters."""
        long_input = "a" * 300
        result = normalize_dynamic_branch_name(long_input)
        assert len(result) == 255
        assert result == "a" * 255

    def test_max_length_truncation_strips_trailing_chars(self):
        """Test that truncation strips trailing dashes, dots, slashes."""
        # Create input that will have trailing dash after truncation
        long_input = "a" * 254 + "-b"
        result = normalize_dynamic_branch_name(long_input)
        assert len(result) == 254
        assert result == "a" * 254
        assert not result.endswith("-")
