"""State management service for autowt."""

import logging
import os
import platform
from pathlib import Path
from typing import Any

import toml

from autowt.config import Config, ConfigLoader
from autowt.models import ProjectConfig

logger = logging.getLogger(__name__)


class StateService:
    """Manages application state and configuration files."""

    def __init__(self, app_dir: Path | None = None):
        """Initialize state service with optional custom app directory."""
        if app_dir is None:
            app_dir = self._get_default_app_dir()

        self.app_dir = app_dir
        self.config_file = app_dir / "config.toml"
        self.session_file = app_dir / "sessionids.toml"
        self.state_file = app_dir / "state.toml"

        # Ensure app directory exists
        self.app_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"State service initialized with app dir: {self.app_dir}")

    def _get_default_app_dir(self) -> Path:
        """Get the default application directory based on platform."""
        system = platform.system()
        if system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "autowt"
        elif system == "Linux":
            # Follow XDG Base Directory Specification
            xdg_data = Path(
                os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")
            )
            return xdg_data / "autowt"
        else:
            # Windows or other
            return Path.home() / ".autowt"

    def load_config(self, project_dir: Path | None = None) -> Config:
        """Load application configuration using new config system."""
        logger.debug(
            f"Loading configuration via ConfigLoader with project_dir={project_dir}"
        )

        # Use the new configuration system
        config_loader = ConfigLoader(app_dir=self.app_dir)
        return config_loader.load_config(project_dir=project_dir)

    def load_project_config(self, cwd: Path) -> ProjectConfig:
        """Load project configuration from autowt.toml or .autowt.toml in current directory."""
        logger.debug(f"Loading project configuration from {cwd}")

        # Check for autowt.toml first, then .autowt.toml
        config_files = [cwd / "autowt.toml", cwd / ".autowt.toml"]

        for config_file in config_files:
            if config_file.exists():
                logger.debug(f"Found project config file: {config_file}")
                try:
                    data = toml.load(config_file)
                    config = ProjectConfig.from_dict(data)
                    logger.debug("Project configuration loaded successfully")
                    return config
                except Exception as e:
                    logger.error(
                        f"Failed to load project configuration from {config_file}: {e}"
                    )
                    continue

        logger.debug("No project config file found, using defaults")
        return ProjectConfig()

    def save_config(self, config: Config) -> None:
        """Save application configuration using new config system."""
        logger.debug("Saving configuration via ConfigLoader")

        # Use the new configuration system
        config_loader = ConfigLoader(app_dir=self.app_dir)
        config_loader.save_config(config)

    def load_session_ids(self) -> dict[str, str]:
        """Load session ID mappings for branches."""
        logger.debug("Loading session IDs")

        if not self.session_file.exists():
            logger.debug("No session file found")
            return {}

        try:
            data = toml.load(self.session_file)
            logger.debug(f"Loaded {len(data)} session mappings")
            return data
        except Exception as e:
            logger.error(f"Failed to load session IDs: {e}")
            return {}

    def save_session_ids(self, session_ids: dict[str, str]) -> None:
        """Save session ID mappings for branches."""
        logger.debug(f"Saving {len(session_ids)} session mappings")

        try:
            with open(self.session_file, "w") as f:
                toml.dump(session_ids, f)
            logger.debug("Session IDs saved successfully")
        except Exception as e:
            logger.error(f"Failed to save session IDs: {e}")
            raise

    def _make_session_key(self, repo_path: Path, branch_name: str) -> str:
        """Create a composite key for session storage."""
        return f"{repo_path.resolve()}:{branch_name}"

    def get_session_id(self, repo_path: Path, branch_name: str) -> str | None:
        """Get session ID for specific repo/branch combination."""
        session_ids = self.load_session_ids()
        key = self._make_session_key(repo_path, branch_name)
        return session_ids.get(key)

    def set_session_id(
        self, repo_path: Path, branch_name: str, session_id: str
    ) -> None:
        """Set session ID for specific repo/branch combination."""
        session_ids = self.load_session_ids()
        key = self._make_session_key(repo_path, branch_name)
        session_ids[key] = session_id
        self.save_session_ids(session_ids)

    def remove_session_id(self, repo_path: Path, branch_name: str) -> None:
        """Remove session ID for specific repo/branch combination."""
        session_ids = self.load_session_ids()
        key = self._make_session_key(repo_path, branch_name)
        if key in session_ids:
            session_ids.pop(key)
            self.save_session_ids(session_ids)

    def get_session_ids_for_repo(self, repo_path: Path) -> dict[str, str]:
        """Get all session IDs for a repo, with branch names as keys."""
        session_ids = self.load_session_ids()
        repo_key_prefix = f"{repo_path.resolve()}:"

        result = {}
        for key, session_id in session_ids.items():
            if key.startswith(repo_key_prefix):
                branch_name = key[len(repo_key_prefix) :]
                result[branch_name] = session_id

        return result

    def load_app_state(self) -> dict[str, Any]:
        """Load application state including UI preferences and prompt tracking."""
        logger.debug("Loading application state")

        if not self.state_file.exists():
            logger.debug("No state file found")
            return {}

        try:
            data = toml.load(self.state_file)
            logger.debug("Application state loaded successfully")
            return data
        except Exception as e:
            logger.error(f"Failed to load application state: {e}")
            return {}

    def save_app_state(self, state: dict[str, Any]) -> None:
        """Save application state including UI preferences and prompt tracking."""
        logger.debug("Saving application state")

        try:
            with open(self.state_file, "w") as f:
                toml.dump(state, f)
            logger.debug("Application state saved successfully")
        except Exception as e:
            logger.error(f"Failed to save application state: {e}")
            raise

    def has_shown_hooks_prompt(self) -> bool:
        """Check if we have already shown the hooks installation prompt."""
        state = self.load_app_state()
        return state.get("hooks_prompt_shown", False)

    def mark_hooks_prompt_shown(self) -> None:
        """Mark that we have shown the hooks installation prompt."""
        state = self.load_app_state()
        state["hooks_prompt_shown"] = True
        self.save_app_state(state)

    def has_shown_experimental_terminal_warning(self) -> bool:
        """Check if we have already shown the experimental terminal warning."""
        state = self.load_app_state()
        return state.get("experimental_terminal_warning_shown", False)

    def mark_experimental_terminal_warning_shown(self) -> None:
        """Mark that we have shown the experimental terminal warning."""
        state = self.load_app_state()
        state["experimental_terminal_warning_shown"] = True
        self.save_app_state(state)
