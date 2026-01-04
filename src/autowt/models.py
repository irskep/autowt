"""Data models for autowt state and configuration."""

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autowt.config import ConfigLoader
    from autowt.hooks import HookRunner
    from autowt.services.git import GitService
    from autowt.services.github import GitHubService
    from autowt.services.state import StateService
    from autowt.services.terminal import TerminalService
    from autowt.services.version_check import VersionCheckService


class TerminalMode(Enum):
    """Terminal switching modes."""

    TAB = "tab"
    WINDOW = "window"
    INPLACE = "inplace"
    ECHO = "echo"
    VSCODE = "vscode"
    CURSOR = "cursor"


class CleanupMode(Enum):
    """Cleanup selection modes."""

    ALL = "all"
    REMOTELESS = "remoteless"
    MERGED = "merged"
    INTERACTIVE = "interactive"
    GITHUB = "github"


@dataclass
class WorktreeInfo:
    """Information about a single worktree."""

    branch: str
    path: Path
    is_current: bool = False
    is_primary: bool = False


@dataclass
class BranchStatus:
    """Status information for cleanup decisions."""

    branch: str
    has_remote: bool
    is_merged: bool
    is_identical: bool  # True if branch has no unique commits vs main
    path: Path
    has_uncommitted_changes: bool = False


@dataclass
class CustomScript:
    """Enhanced custom script with optional hook overrides and dynamic branch naming."""

    # Help text shown in --help output
    description: str | None = None

    # Dynamic branch name - shell command whose stdout becomes the branch name
    branch_name: str | None = None

    # When True, global/project hooks run first, then script-specific hooks
    # When False, only script-specific hooks run
    inherit_hooks: bool = True

    # All 8 lifecycle hooks can be overridden
    pre_create: str | None = None
    post_create: str | None = None
    post_create_async: str | None = None
    session_init: str | None = None
    pre_cleanup: str | None = None
    post_cleanup: str | None = None
    pre_switch: str | None = None
    post_switch: str | None = None


@dataclass
class ProjectScriptsConfig:
    """Project-specific scripts configuration."""

    session_init: str | None = None
    custom: dict[str, "CustomScript"] | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectScriptsConfig":
        """Create project scripts configuration from dictionary."""
        # Handle backward compatibility for init -> session_init migration
        session_init_value = None
        init_value = data.get("init")
        session_init_explicit = data.get("session_init")

        if session_init_explicit is not None and init_value is not None:
            # Both specified - use session_init and warn about ignoring init
            logger = logging.getLogger(__name__)
            logger.warning(
                "Both 'init' and 'session_init' specified in project scripts config. "
                "Using 'session_init' and ignoring deprecated 'init'. "
                "Please remove 'init' from your configuration."
            )
            session_init_value = session_init_explicit
        elif session_init_explicit is not None:
            # Only session_init specified
            session_init_value = session_init_explicit
        elif init_value is not None:
            # Only init specified - migrate to session_init with deprecation warning
            logger = logging.getLogger(__name__)
            logger.warning(
                "The 'init' script key is deprecated. Please rename it to 'session_init' in your configuration. "
                "Support for 'init' will be removed in a future version."
            )
            session_init_value = init_value

        # Normalize custom scripts to CustomScript objects
        raw_custom = data.get("custom")
        normalized_custom: dict[str, CustomScript] | None = None
        if raw_custom:
            normalized_custom = {}
            for name, value in raw_custom.items():
                if isinstance(value, str):
                    # Simple string format is shorthand for session_init only
                    normalized_custom[name] = CustomScript(session_init=value)
                elif isinstance(value, dict):
                    # Nested table format
                    normalized_custom[name] = CustomScript(**value)
                elif isinstance(value, CustomScript):
                    # Already a CustomScript (e.g., from tests)
                    normalized_custom[name] = value

        return cls(
            session_init=session_init_value,
            custom=normalized_custom,
        )

    def to_dict(self) -> dict:
        """Convert project scripts configuration to dictionary."""
        result = {}
        if self.session_init is not None:
            result["session_init"] = self.session_init
        if self.custom is not None:
            # Serialize CustomScript objects to dicts
            custom_dict = {}
            for name, script in self.custom.items():
                script_data = {}
                if script.description is not None:
                    script_data["description"] = script.description
                if script.branch_name is not None:
                    script_data["branch_name"] = script.branch_name
                if not script.inherit_hooks:
                    script_data["inherit_hooks"] = script.inherit_hooks
                if script.pre_create is not None:
                    script_data["pre_create"] = script.pre_create
                if script.post_create is not None:
                    script_data["post_create"] = script.post_create
                if script.post_create_async is not None:
                    script_data["post_create_async"] = script.post_create_async
                if script.session_init is not None:
                    script_data["session_init"] = script.session_init
                if script.pre_cleanup is not None:
                    script_data["pre_cleanup"] = script.pre_cleanup
                if script.post_cleanup is not None:
                    script_data["post_cleanup"] = script.post_cleanup
                if script.pre_switch is not None:
                    script_data["pre_switch"] = script.pre_switch
                if script.post_switch is not None:
                    script_data["post_switch"] = script.post_switch
                custom_dict[name] = script_data
            result["custom"] = custom_dict
        return result


@dataclass
class ProjectConfig:
    """Project-specific configuration."""

    scripts: ProjectScriptsConfig | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        """Create project configuration from dictionary."""
        scripts_data = data.get("scripts", {})
        scripts = ProjectScriptsConfig.from_dict(scripts_data) if scripts_data else None
        return cls(
            scripts=scripts,
        )

    def to_dict(self) -> dict:
        """Convert project configuration to dictionary."""
        result = {}
        if self.scripts is not None:
            scripts_dict = self.scripts.to_dict()
            if scripts_dict:
                result["scripts"] = scripts_dict
        return result

    @property
    def session_init(self) -> str | None:
        """Get session_init script from scripts configuration."""
        return self.scripts.session_init if self.scripts else None


@dataclass
class Services:
    """Container for all application services."""

    state: "StateService"
    git: "GitService"
    terminal: "TerminalService"
    github: "GitHubService"
    config_loader: "ConfigLoader"
    hooks: "HookRunner"
    version_check: "VersionCheckService"

    @classmethod
    def create(cls) -> "Services":
        """Create a new Services container with all services initialized."""
        # Import here to avoid circular imports
        from autowt.config import ConfigLoader  # noqa: PLC0415
        from autowt.hooks import HookRunner  # noqa: PLC0415
        from autowt.services.git import GitService  # noqa: PLC0415
        from autowt.services.github import GitHubService  # noqa: PLC0415
        from autowt.services.state import StateService  # noqa: PLC0415
        from autowt.services.terminal import TerminalService  # noqa: PLC0415
        from autowt.services.version_check import VersionCheckService  # noqa: PLC0415

        # Create ConfigLoader first so it can be passed to StateService
        config_loader = ConfigLoader()
        state_service = StateService(config_loader=config_loader)
        return cls(
            state=state_service,
            git=GitService(),
            terminal=TerminalService(state_service),
            github=GitHubService(),
            config_loader=config_loader,
            hooks=HookRunner(),
            version_check=VersionCheckService(state_service.app_dir),
        )


@dataclass
class SwitchCommand:
    """Encapsulates all parameters for switching to/creating a worktree."""

    branch: str | None = None  # None when using dynamic branch from custom script
    terminal_mode: TerminalMode | None = None
    init_script: str | None = None
    after_init: str | None = None
    ignore_same_session: bool = False
    auto_confirm: bool = False
    debug: bool = False
    custom_script: str | None = None  # Script spec string like "ghllm 123"
    custom_script_name: str | None = None  # Original script name for reference
    from_branch: str | None = None
    dir: str | None = None
    from_dynamic_command: bool = False


@dataclass
class CleanupCommand:
    """Encapsulates all parameters for cleaning up worktrees."""

    mode: CleanupMode
    dry_run: bool = False
    auto_confirm: bool = False
    force: bool = False
    debug: bool = False
    worktrees: list[str] | None = None  # Branch names or paths to clean up
