"""Comprehensive configuration system for autowt.

This module provides type-safe configuration management with support for:
- Global and project configuration files
- Environment variable overrides
- Command line argument overrides
- Proper precedence order and cascading
"""

import logging
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import toml

from autowt.models import CleanupMode, TerminalMode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TerminalConfig:
    """Terminal management configuration."""

    mode: TerminalMode = TerminalMode.TAB
    always_new: bool = False
    program: str | None = None


@dataclass(frozen=True)
class BranchSanitizationConfig:
    """Branch name sanitization rules."""

    replace_chars: str = "/:#@^~"
    max_length: int = 255
    lowercase: bool = False


@dataclass(frozen=True)
class WorktreeConfig:
    """Worktree management configuration."""

    directory_pattern: str = "../{repo_name}-worktrees/{branch}"
    max_worktrees: int | None = None
    auto_fetch: bool = True
    default_remote: str = "origin"
    branch_sanitization: BranchSanitizationConfig = field(
        default_factory=BranchSanitizationConfig
    )


@dataclass(frozen=True)
class CleanupConfig:
    """Cleanup behavior configuration."""

    kill_processes: bool = True
    kill_process_timeout: int = 10
    default_mode: CleanupMode = CleanupMode.INTERACTIVE


@dataclass(frozen=True)
class ScriptsConfig:
    """Lifecycle scripts and custom commands."""

    post_create: str | None = None
    session_init: str | None = None
    pre_cleanup: str | None = None
    pre_process_kill: str | None = None
    post_cleanup: str | None = None
    pre_switch: str | None = None
    post_switch: str | None = None
    custom: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfirmationsConfig:
    """User confirmation settings."""

    cleanup_multiple: bool = True
    kill_process: bool = True
    force_operations: bool = True


@dataclass(frozen=True)
class Config:
    """Complete autowt configuration."""

    terminal: TerminalConfig = field(default_factory=TerminalConfig)
    worktree: WorktreeConfig = field(default_factory=WorktreeConfig)
    cleanup: CleanupConfig = field(default_factory=CleanupConfig)
    scripts: ScriptsConfig = field(default_factory=ScriptsConfig)
    confirmations: ConfirmationsConfig = field(default_factory=ConfirmationsConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create configuration from dictionary with proper type conversion."""
        terminal_data = data.get("terminal", {})
        worktree_data = data.get("worktree", {})
        cleanup_data = data.get("cleanup", {})
        scripts_data = data.get("scripts", {})
        confirmations_data = data.get("confirmations", {})

        # Handle nested configurations
        branch_sanitization_data = worktree_data.get("branch_sanitization", {})
        branch_sanitization = BranchSanitizationConfig(
            replace_chars=branch_sanitization_data.get("replace_chars", "/:#@^~"),
            max_length=branch_sanitization_data.get("max_length", 255),
            lowercase=branch_sanitization_data.get("lowercase", False),
        )

        worktree_config = WorktreeConfig(
            directory_pattern=worktree_data.get(
                "directory_pattern", "../{repo_name}-worktrees/{branch}"
            ),
            max_worktrees=worktree_data.get("max_worktrees"),
            auto_fetch=worktree_data.get("auto_fetch", True),
            default_remote=worktree_data.get("default_remote", "origin"),
            branch_sanitization=branch_sanitization,
        )

        # Handle case where terminal_data might be a string (legacy compatibility)
        if isinstance(terminal_data, str):
            terminal_config = TerminalConfig(
                mode=TerminalMode(terminal_data),
                always_new=False,
                program=None,
            )
        else:
            terminal_config = TerminalConfig(
                mode=TerminalMode(terminal_data.get("mode", "tab")),
                always_new=terminal_data.get("always_new", False),
                program=terminal_data.get("program"),
            )

        cleanup_config = CleanupConfig(
            kill_processes=cleanup_data.get("kill_processes", True),
            kill_process_timeout=cleanup_data.get("kill_process_timeout", 10),
            default_mode=CleanupMode(cleanup_data.get("default_mode", "interactive")),
        )

        # Handle backward compatibility for init -> session_init migration
        session_init_value = None
        init_value = scripts_data.get("init")
        session_init_explicit = scripts_data.get("session_init")

        if session_init_explicit is not None and init_value is not None:
            # Both specified - use session_init and warn about ignoring init
            logger.warning(
                "Both 'init' and 'session_init' specified in scripts config. "
                "Using 'session_init' and ignoring deprecated 'init'. "
                "Please remove 'init' from your configuration."
            )
            session_init_value = session_init_explicit
        elif session_init_explicit is not None:
            # Only session_init specified
            session_init_value = session_init_explicit
        elif init_value is not None:
            # Only init specified - migrate to session_init with deprecation warning
            logger.warning(
                "The 'init' script key is deprecated. Please rename it to 'session_init' in your configuration. "
                "Support for 'init' will be removed in a future version."
            )
            session_init_value = init_value

        scripts_config = ScriptsConfig(
            post_create=scripts_data.get("post_create"),
            session_init=session_init_value,
            pre_cleanup=scripts_data.get("pre_cleanup"),
            pre_process_kill=scripts_data.get("pre_process_kill"),
            post_cleanup=scripts_data.get("post_cleanup"),
            pre_switch=scripts_data.get("pre_switch"),
            post_switch=scripts_data.get("post_switch"),
            custom=scripts_data.get("custom", {}),
        )

        confirmations_config = ConfirmationsConfig(
            cleanup_multiple=confirmations_data.get("cleanup_multiple", True),
            kill_process=confirmations_data.get("kill_process", True),
            force_operations=confirmations_data.get("force_operations", True),
        )

        return cls(
            terminal=terminal_config,
            worktree=worktree_config,
            cleanup=cleanup_config,
            scripts=scripts_config,
            confirmations=confirmations_config,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "terminal": {
                "mode": self.terminal.mode.value,
                "always_new": self.terminal.always_new,
                "program": self.terminal.program,
            },
            "worktree": {
                "directory_pattern": self.worktree.directory_pattern,
                "max_worktrees": self.worktree.max_worktrees,
                "auto_fetch": self.worktree.auto_fetch,
                "default_remote": self.worktree.default_remote,
                "branch_sanitization": {
                    "replace_chars": self.worktree.branch_sanitization.replace_chars,
                    "max_length": self.worktree.branch_sanitization.max_length,
                    "lowercase": self.worktree.branch_sanitization.lowercase,
                },
            },
            "cleanup": {
                "kill_processes": self.cleanup.kill_processes,
                "kill_process_timeout": self.cleanup.kill_process_timeout,
                "default_mode": self.cleanup.default_mode.value,
            },
            "scripts": {
                "post_create": self.scripts.post_create,
                "session_init": self.scripts.session_init,
                "pre_cleanup": self.scripts.pre_cleanup,
                "pre_process_kill": self.scripts.pre_process_kill,
                "post_cleanup": self.scripts.post_cleanup,
                "pre_switch": self.scripts.pre_switch,
                "post_switch": self.scripts.post_switch,
                "custom": self.scripts.custom,
            },
            "confirmations": {
                "cleanup_multiple": self.confirmations.cleanup_multiple,
                "kill_process": self.confirmations.kill_process,
                "force_operations": self.confirmations.force_operations,
            },
        }


class ConfigLoader:
    """Handles loading and merging configuration from multiple sources."""

    def __init__(self, app_dir: Path | None = None):
        """Initialize configuration loader."""
        if app_dir is None:
            app_dir = self._get_default_app_dir()

        self.app_dir = app_dir
        self.global_config_file = app_dir / "config.toml"

        # Ensure app directory exists
        self.app_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Config loader initialized with app dir: {self.app_dir}")

    def _get_default_app_dir(self) -> Path:
        """Get the default application directory based on platform."""
        system = platform.system()
        if system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "autowt"
        elif system == "Linux":
            # Follow XDG Base Directory Specification
            xdg_config = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
            return xdg_config / "autowt"
        else:
            # Windows or other
            return Path.home() / ".autowt"

    def load_config(
        self,
        project_dir: Path | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> Config:
        """Load configuration with proper precedence order.

        Precedence (later overrides earlier):
        1. Built-in defaults
        2. Global config file
        3. Project config file
        4. Environment variables
        5. CLI overrides
        """
        logger.debug("Loading configuration with cascading precedence")

        # 1. Start with defaults
        config_data: dict[str, Any] = {}

        # 2. Load global config file
        global_data = self._load_global_config()
        config_data = self._merge_dicts(config_data, global_data)

        # 3. Load project config file
        if project_dir:
            project_data = self._load_project_config(project_dir)
            config_data = self._merge_dicts(config_data, project_data)

        # 4. Apply environment variables
        env_data = self._load_env_vars()
        config_data = self._merge_dicts(config_data, env_data)

        # 5. Apply CLI overrides
        if cli_overrides:
            config_data = self._merge_dicts(config_data, cli_overrides)

        # Convert to Config object
        return Config.from_dict(config_data)

    def _load_global_config(self) -> dict[str, Any]:
        """Load global configuration file."""
        if not self.global_config_file.exists():
            logger.debug("No global config file found")
            return {}

        try:
            data = toml.load(self.global_config_file)
            logger.debug("Global configuration loaded successfully")
            return data
        except Exception as e:
            logger.error(f"Failed to load global configuration: {e}")
            return {}

    def _load_project_config(self, project_dir: Path) -> dict[str, Any]:
        """Load project-specific configuration."""
        config_files = [project_dir / "autowt.toml", project_dir / ".autowt.toml"]

        for config_file in config_files:
            if config_file.exists():
                logger.debug(f"Found project config file: {config_file}")
                try:
                    data = toml.load(config_file)
                    logger.debug("Project configuration loaded successfully")
                    return data
                except Exception as e:
                    logger.error(
                        f"Failed to load project configuration from {config_file}: {e}"
                    )
                    continue

        logger.debug("No project config file found")
        return {}

    def _load_env_vars(self) -> dict[str, Any]:
        """Load configuration from environment variables with AUTOWT_ prefix."""
        config_data: dict[str, Any] = {}

        # Define the mapping from environment variable suffixes to config paths
        # This handles field names with underscores correctly
        env_mapping = {
            "TERMINAL_MODE": ["terminal", "mode"],
            "TERMINAL_ALWAYS_NEW": ["terminal", "always_new"],
            "TERMINAL_PROGRAM": ["terminal", "program"],
            "WORKTREE_DIRECTORY_PATTERN": ["worktree", "directory_pattern"],
            "WORKTREE_MAX_WORKTREES": ["worktree", "max_worktrees"],
            "WORKTREE_AUTO_FETCH": ["worktree", "auto_fetch"],
            "WORKTREE_DEFAULT_REMOTE": ["worktree", "default_remote"],
            "WORKTREE_BRANCH_SANITIZATION_REPLACE_CHARS": [
                "worktree",
                "branch_sanitization",
                "replace_chars",
            ],
            "WORKTREE_BRANCH_SANITIZATION_MAX_LENGTH": [
                "worktree",
                "branch_sanitization",
                "max_length",
            ],
            "WORKTREE_BRANCH_SANITIZATION_LOWERCASE": [
                "worktree",
                "branch_sanitization",
                "lowercase",
            ],
            "CLEANUP_KILL_PROCESSES": ["cleanup", "kill_processes"],
            "CLEANUP_KILL_PROCESS_TIMEOUT": ["cleanup", "kill_process_timeout"],
            "CLEANUP_DEFAULT_MODE": ["cleanup", "default_mode"],
            "SCRIPTS_POST_CREATE": ["scripts", "post_create"],
            "SCRIPTS_SESSION_INIT": ["scripts", "session_init"],
            "SCRIPTS_PRE_CLEANUP": ["scripts", "pre_cleanup"],
            "SCRIPTS_PRE_PROCESS_KILL": ["scripts", "pre_process_kill"],
            "SCRIPTS_POST_CLEANUP": ["scripts", "post_cleanup"],
            "SCRIPTS_PRE_SWITCH": ["scripts", "pre_switch"],
            "SCRIPTS_POST_SWITCH": ["scripts", "post_switch"],
            "CONFIRMATIONS_CLEANUP_MULTIPLE": ["confirmations", "cleanup_multiple"],
            "CONFIRMATIONS_KILL_PROCESS": ["confirmations", "kill_process"],
            "CONFIRMATIONS_FORCE_OPERATIONS": ["confirmations", "force_operations"],
        }

        for key, value in os.environ.items():
            if not key.startswith("AUTOWT_"):
                continue

            # Get the suffix after AUTOWT_
            suffix = key[7:]  # Remove AUTOWT_ prefix

            # Look up the config path
            if suffix in env_mapping:
                path_parts = env_mapping[suffix]

                # Convert value to appropriate type
                converted_value = self._convert_env_value(value)

                # Set nested value in config_data
                self._set_nested_value(config_data, path_parts, converted_value)
            else:
                logger.warning(f"Unknown environment variable: {key}")

        if config_data:
            logger.debug(
                f"Loaded configuration from {len([k for k in os.environ if k.startswith('AUTOWT_')])} environment variables"
            )

        return config_data

    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate Python type."""
        # Boolean conversion
        if value.lower() in ("true", "yes", "1", "on"):
            return True
        elif value.lower() in ("false", "no", "0", "off"):
            return False

        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass

        # Return as string
        return value

    def _set_nested_value(
        self, data: dict[str, Any], path: list[str], value: Any
    ) -> None:
        """Set a nested value in a dictionary using a path list."""
        current = data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    def _merge_dicts(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge two dictionaries, with override taking precedence."""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    def save_config(self, config: Config) -> None:
        """Save configuration to global config file."""
        logger.debug("Saving global configuration")

        try:
            with open(self.global_config_file, "w") as f:
                toml.dump(config.to_dict(), f)
            logger.debug("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise


# Global configuration instance
_config: Config | None = None
_config_loader: ConfigLoader | None = None


def get_config() -> Config:
    """Get the current global configuration.

    Raises RuntimeError if configuration hasn't been loaded yet.
    """
    if _config is None:
        raise RuntimeError("Configuration not initialized. Call load_config() first.")
    return _config


def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_config(
    project_dir: Path | None = None, cli_overrides: dict[str, Any] | None = None
) -> Config:
    """Load configuration and set it globally.

    Args:
        project_dir: Optional project directory for project-specific config
        cli_overrides: Optional dictionary of CLI argument overrides

    Returns:
        The loaded configuration object
    """
    global _config

    loader = get_config_loader()
    _config = loader.load_config(project_dir=project_dir, cli_overrides=cli_overrides)

    logger.debug("Global configuration loaded and set")
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration (mainly for testing)."""
    global _config
    _config = config


def save_config() -> None:
    """Save the current global configuration."""
    if _config is None:
        raise RuntimeError("No configuration to save")

    loader = get_config_loader()
    loader.save_config(_config)
