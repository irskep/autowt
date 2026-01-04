"""Tests for CLI configuration integration."""

from autowt.cli_config import interpolate_custom_script, resolve_custom_script
from autowt.config import Config, ScriptsConfig, set_config
from autowt.models import CustomScript


class TestInterpolateCustomScript:
    """Tests for interpolate_custom_script function."""

    def test_single_argument(self):
        """Test interpolation with a single argument."""
        script = CustomScript(session_init='claude "Fix issue $1"')
        result = interpolate_custom_script(script, ["123"])

        assert result.session_init == 'claude "Fix issue 123"'

    def test_multiple_arguments(self):
        """Test interpolation with multiple arguments."""
        script = CustomScript(
            session_init="process $1 $2 $3",
            branch_name="branch-$1-$2",
        )
        result = interpolate_custom_script(script, ["one", "two", "three"])

        assert result.session_init == "process one two three"
        assert result.branch_name == "branch-one-two"

    def test_all_string_fields_interpolated(self):
        """Test that all string fields get interpolated."""
        script = CustomScript(
            branch_name="issue-$1",
            pre_create="echo pre $1",
            post_create="echo post $1",
            session_init="work on $1",
        )
        result = interpolate_custom_script(script, ["456"])

        assert result.branch_name == "issue-456"
        assert result.pre_create == "echo pre 456"
        assert result.post_create == "echo post 456"
        assert result.session_init == "work on 456"

    def test_non_string_fields_preserved(self):
        """Test that non-string fields are preserved as-is."""
        script = CustomScript(
            session_init="work on $1",
            inherit_hooks=False,
        )
        result = interpolate_custom_script(script, ["123"])

        assert result.inherit_hooks is False

    def test_no_args_leaves_placeholders(self):
        """Test that placeholders remain if no args provided."""
        script = CustomScript(session_init='claude "Fix issue $1"')
        result = interpolate_custom_script(script, [])

        assert result.session_init == 'claude "Fix issue $1"'

    def test_none_fields_preserved(self):
        """Test that None fields remain None."""
        script = CustomScript(session_init="work on $1", branch_name=None)
        result = interpolate_custom_script(script, ["123"])

        assert result.branch_name is None


class TestResolveCustomScript:
    """Tests for resolve_custom_script function."""

    def setup_method(self):
        """Set up test configuration."""
        scripts_config = ScriptsConfig(
            custom={
                "bugfix": CustomScript(
                    session_init='claude "Fix bug described in issue $1"'
                ),
                "ghllm": CustomScript(
                    branch_name="gh issue view $1 --json title --template '{{.title}}'",
                    inherit_hooks=False,
                    session_init='claude "Work on GitHub issue $1"',
                    pre_create="echo 'Starting ghllm workflow for issue $1'",
                ),
            }
        )
        test_config = Config(scripts=scripts_config)
        set_config(test_config)

    def test_resolves_and_interpolates(self):
        """Test resolving a script with arguments."""
        script = resolve_custom_script("bugfix 123")

        assert script is not None
        assert script.session_init == 'claude "Fix bug described in issue 123"'

    def test_script_not_found(self):
        """Test handling of unknown script name."""
        script = resolve_custom_script("unknown 123")
        assert script is None

    def test_empty_spec(self):
        """Test handling of empty script specification."""
        script = resolve_custom_script("")
        assert script is None

    def test_invalid_shell_syntax(self):
        """Test handling of invalid shell syntax."""
        script = resolve_custom_script("bugfix 'unclosed")
        assert script is None

    def test_quoted_arguments(self):
        """Test that quoted arguments work correctly."""
        script = resolve_custom_script('bugfix "issue 123"')

        assert script is not None
        assert script.session_init == 'claude "Fix bug described in issue issue 123"'
