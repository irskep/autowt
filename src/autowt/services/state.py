"""State management service for autowt."""

import logging
from pathlib import Path
from typing import Any

import toml

from autowt.config import Config, ConfigLoader
from autowt.models import ProjectConfig
from autowt.utils.platform import get_default_state_dir

logger = logging.getLogger(__name__)


class StateService:
    """Manages application state and configuration files."""

    def __init__(self, config_loader: ConfigLoader, app_dir: Path | None = None):
        """Initialize state service with config loader and optional app directory."""
        if app_dir is None:
            app_dir = get_default_state_dir()

        self.app_dir = app_dir
        self.config_file = app_dir / "config.toml"
        self.state_file = app_dir / "state.toml"
        self._setup_done = False
        self.config_loader = config_loader

        logger.debug(f"State service initialized with app dir: {self.app_dir}")

    def setup(self) -> None:
        """Ensure app directory exists. Called lazily when needed."""
        if not self._setup_done:
            self.app_dir.mkdir(parents=True, exist_ok=True)
            self._setup_done = True
            logger.debug(f"State service setup complete: {self.app_dir}")

    def load_config(self, project_dir: Path | None = None) -> Config:
        """Load application configuration using new config system."""
        logger.debug(
            f"Loading configuration via ConfigLoader with project_dir={project_dir}"
        )

        # Use the injected configuration loader
        return self.config_loader.load_config(project_dir=project_dir)

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
        self.setup()  # Ensure directory exists
        logger.debug("Saving configuration via ConfigLoader")

        # Use the injected configuration loader
        self.config_loader.save_config(config)

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
        self.setup()  # Ensure directory exists
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
