"""Tests for data models."""

from pathlib import Path

from autowt.models import (
    BranchStatus,
    CleanupMode,
    CustomScript,
    ProjectScriptsConfig,
    SwitchCommand,
    TerminalMode,
    WorktreeInfo,
)


class TestWorktreeInfo:
    """Tests for WorktreeInfo model."""

    def test_worktree_info_creation(self):
        """Test creating WorktreeInfo instance."""
        path = Path("/test/path")
        worktree = WorktreeInfo(branch="test-branch", path=path, is_current=True)

        assert worktree.branch == "test-branch"
        assert worktree.path == path
        assert worktree.is_current is True

    def test_worktree_info_defaults(self):
        """Test WorktreeInfo default values."""
        worktree = WorktreeInfo(branch="test", path=Path("/test"))

        assert worktree.is_current is False


class TestBranchStatus:
    """Tests for BranchStatus model."""

    def test_branch_status_creation(self):
        """Test creating BranchStatus instance."""
        path = Path("/test/path")
        status = BranchStatus(
            branch="test-branch",
            has_remote=True,
            is_merged=False,
            is_identical=False,
            path=path,
        )

        assert status.branch == "test-branch"
        assert status.has_remote is True
        assert status.is_merged is False
        assert status.is_identical is False
        assert status.path == path


class TestSwitchCommand:
    """Tests for SwitchCommand model."""

    def test_switch_command_creation(self):
        """Test creating SwitchCommand instance."""
        cmd = SwitchCommand(
            branch="test-branch", terminal_mode=TerminalMode.TAB, from_branch="main"
        )

        assert cmd.branch == "test-branch"
        assert cmd.terminal_mode == TerminalMode.TAB
        assert cmd.from_branch == "main"

    def test_switch_command_defaults(self):
        """Test SwitchCommand default values."""
        cmd = SwitchCommand(branch="test-branch")

        assert cmd.branch == "test-branch"
        assert cmd.terminal_mode is None
        assert cmd.init_script is None
        assert cmd.after_init is None
        assert cmd.ignore_same_session is False
        assert cmd.auto_confirm is False
        assert cmd.debug is False
        assert cmd.from_branch is None


class TestEnums:
    """Tests for enum values."""

    def test_terminal_mode_values(self):
        """Test TerminalMode enum values."""
        assert TerminalMode.TAB.value == "tab"
        assert TerminalMode.WINDOW.value == "window"
        assert TerminalMode.INPLACE.value == "inplace"

    def test_cleanup_mode_values(self):
        """Test CleanupMode enum values."""
        assert CleanupMode.ALL.value == "all"
        assert CleanupMode.REMOTELESS.value == "remoteless"
        assert CleanupMode.MERGED.value == "merged"
        assert CleanupMode.INTERACTIVE.value == "interactive"


class TestCustomScript:
    """Tests for CustomScript dataclass."""

    def test_custom_script_creation_defaults(self):
        """Test CustomScript default values."""
        script = CustomScript()

        assert script.branch_name is None
        assert script.inherit_hooks is True
        assert script.pre_create is None
        assert script.post_create is None
        assert script.post_create_async is None
        assert script.session_init is None
        assert script.pre_cleanup is None
        assert script.post_cleanup is None
        assert script.pre_switch is None
        assert script.post_switch is None

    def test_custom_script_with_session_init_only(self):
        """Test CustomScript with only session_init (simple string equivalent)."""
        script = CustomScript(session_init="npm test")

        assert script.session_init == "npm test"
        assert script.inherit_hooks is True
        assert script.branch_name is None

    def test_custom_script_full_profile(self):
        """Test CustomScript with all fields set."""
        script = CustomScript(
            branch_name="gh issue view $1 --json title",
            inherit_hooks=False,
            pre_create="echo pre",
            post_create="echo post",
            session_init='claude "Fix issue $1"',
        )

        assert script.branch_name == "gh issue view $1 --json title"
        assert script.inherit_hooks is False
        assert script.pre_create == "echo pre"
        assert script.post_create == "echo post"
        assert script.session_init == 'claude "Fix issue $1"'


class TestProjectScriptsConfig:
    """Tests for ProjectScriptsConfig backward compatibility."""

    def test_from_dict_with_session_init_only(self):
        """Test creating config with only session_init specified."""
        data = {"session_init": "npm install", "custom": {"test": "npm test"}}
        config = ProjectScriptsConfig.from_dict(data)

        assert config.session_init == "npm install"
        # Custom scripts are normalized to CustomScript objects
        assert config.custom is not None
        assert "test" in config.custom
        assert isinstance(config.custom["test"], CustomScript)
        assert config.custom["test"].session_init == "npm test"
        assert config.custom["test"].inherit_hooks is True

    def test_from_dict_with_init_only_maps_to_session_init(self):
        """Test creating config with only init maps to session_init."""
        data = {"init": "make setup", "custom": {"build": "make build"}}
        config = ProjectScriptsConfig.from_dict(data)

        assert config.session_init == "make setup"
        assert config.custom is not None
        assert isinstance(config.custom["build"], CustomScript)
        assert config.custom["build"].session_init == "make build"

    def test_from_dict_with_both_init_and_session_init_prefers_session_init(self):
        """Test that session_init is preferred when both are specified."""
        data = {
            "init": "old command",
            "session_init": "new command",
            "custom": {"deploy": "make deploy"},
        }

        config = ProjectScriptsConfig.from_dict(data)

        assert config.session_init == "new command"  # session_init takes precedence
        assert config.custom is not None
        assert isinstance(config.custom["deploy"], CustomScript)
        assert config.custom["deploy"].session_init == "make deploy"

    def test_from_dict_with_nested_custom_script(self):
        """Test creating config with nested table format custom scripts."""
        data = {
            "custom": {
                "ghllm": {
                    "branch_name": "gh issue view $1 --json title",
                    "inherit_hooks": False,
                    "session_init": 'claude "Fix issue $1"',
                    "pre_create": "echo starting",
                }
            }
        }

        config = ProjectScriptsConfig.from_dict(data)

        assert config.custom is not None
        script = config.custom["ghllm"]
        assert isinstance(script, CustomScript)
        assert script.branch_name == "gh issue view $1 --json title"
        assert script.inherit_hooks is False
        assert script.session_init == 'claude "Fix issue $1"'
        assert script.pre_create == "echo starting"

    def test_from_dict_with_mixed_custom_scripts(self):
        """Test config with both simple string and nested table format."""
        data = {
            "custom": {
                "simple": "npm test",  # Simple string format
                "complex": {  # Nested table format
                    "branch_name": "git branch --show-current",
                    "session_init": "make run",
                },
            }
        }

        config = ProjectScriptsConfig.from_dict(data)

        assert config.custom is not None
        # Simple format normalized to CustomScript
        assert isinstance(config.custom["simple"], CustomScript)
        assert config.custom["simple"].session_init == "npm test"
        assert config.custom["simple"].inherit_hooks is True

        # Nested format also normalized
        assert isinstance(config.custom["complex"], CustomScript)
        assert config.custom["complex"].branch_name == "git branch --show-current"
        assert config.custom["complex"].session_init == "make run"

    def test_from_dict_with_empty_dict(self):
        """Test creating config from empty dictionary."""
        config = ProjectScriptsConfig.from_dict({})

        assert config.session_init is None
        assert config.custom is None

    def test_to_dict_includes_session_init(self):
        """Test that to_dict outputs session_init, not init."""
        config = ProjectScriptsConfig(
            session_init="python setup.py",
            custom={
                "test": CustomScript(session_init="pytest"),
                "lint": CustomScript(session_init="ruff"),
            },
        )

        result = config.to_dict()

        assert result["session_init"] == "python setup.py"
        assert "custom" in result
        # CustomScript objects serialized to dicts
        assert result["custom"]["test"] == {"session_init": "pytest"}
        assert result["custom"]["lint"] == {"session_init": "ruff"}
        assert "init" not in result  # Should not output deprecated key

    def test_to_dict_with_full_custom_script(self):
        """Test to_dict with full CustomScript fields."""
        config = ProjectScriptsConfig(
            custom={
                "ghllm": CustomScript(
                    branch_name="gh issue view $1",
                    inherit_hooks=False,
                    session_init='claude "Fix $1"',
                    pre_create="echo pre",
                )
            }
        )

        result = config.to_dict()

        assert result["custom"]["ghllm"] == {
            "branch_name": "gh issue view $1",
            "inherit_hooks": False,
            "session_init": 'claude "Fix $1"',
            "pre_create": "echo pre",
        }

    def test_to_dict_with_none_values(self):
        """Test that to_dict excludes None values."""
        config = ProjectScriptsConfig(session_init=None, custom=None)

        result = config.to_dict()

        assert result == {}  # Empty dict when all values are None
