"""State management service for autowt."""

import logging
import os
import platform
from pathlib import Path

import toml

from autowt.models import ApplicationState, Configuration

logger = logging.getLogger(__name__)


class StateService:
    """Manages application state and configuration files."""

    def __init__(self, app_dir: Path | None = None):
        """Initialize state service with optional custom app directory."""
        if app_dir is None:
            app_dir = self._get_default_app_dir()

        self.app_dir = app_dir
        self.state_file = app_dir / "state.toml"
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

    def load_state(self, repo_path: Path) -> ApplicationState:
        """Load application state for the given repository."""
        logger.debug(f"Loading state for repo: {repo_path}")

        if not self.state_file.exists():
            logger.debug("No state file found, creating empty state")
            return ApplicationState(primary_clone=repo_path, worktrees=[])

        try:
            data = toml.load(self.state_file)
            repo_data = data.get(str(repo_path), {})
            state = ApplicationState.from_dict(repo_data, repo_path)
            logger.debug(f"Loaded state with {len(state.worktrees)} worktrees")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return ApplicationState(primary_clone=repo_path, worktrees=[])

    def save_state(self, state: ApplicationState) -> None:
        """Save application state."""
        logger.debug(f"Saving state for repo: {state.primary_clone}")

        # Load existing data to preserve other repos
        data = {}
        if self.state_file.exists():
            try:
                data = toml.load(self.state_file)
            except Exception as e:
                logger.warning(f"Failed to load existing state file: {e}")

        # Update data for this repository
        data[str(state.primary_clone)] = state.to_dict()

        try:
            with open(self.state_file, "w") as f:
                toml.dump(data, f)
            logger.debug("State saved successfully")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            raise

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
