"""State management service for autowt."""

import logging
import os
import platform
from pathlib import Path

import toml

from autowt.models import Configuration, ProjectConfig

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

    def load_config(self) -> Configuration:
        """Load application configuration."""
        logger.debug("Loading configuration")

        if not self.config_file.exists():
            logger.debug("No config file found, using defaults")
            return Configuration()

        try:
            data = toml.load(self.config_file)
            config = Configuration.from_dict(data)
            logger.debug("Configuration loaded successfully")
            return config
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return Configuration()

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

    def save_config(self, config: Configuration) -> None:
        """Save application configuration."""
        logger.debug("Saving configuration")

        try:
            with open(self.config_file, "w") as f:
                toml.dump(config.to_dict(), f)
            logger.debug("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

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
