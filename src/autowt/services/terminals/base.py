"""Terminal management service for autowt."""

import logging
import platform
from abc import ABC, abstractmethod
from pathlib import Path

from autowt.utils import run_command

logger = logging.getLogger(__name__)


class BaseTerminal(ABC):
    """Base class for terminal implementations."""

    def __init__(self):
        """Initialize terminal implementation."""
        self.is_macos = platform.system() == "Darwin"

    @abstractmethod
    def get_current_session_id(self) -> str | None:
        """Get current session ID if supported."""
        pass

    @abstractmethod
    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to existing session if supported."""
        pass

    @abstractmethod
    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open new tab in current window."""
        pass

    @abstractmethod
    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open new window."""
        pass

    def supports_session_management(self) -> bool:
        """Whether this terminal supports session management."""
        return False

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists in the terminal."""
        return False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if a session exists and is currently in the specified directory."""
        return False

    def _escape_for_applescript(self, text: str) -> str:
        """Escape text for use in AppleScript strings."""
        return text.replace("\\", "\\\\").replace('"', '\\"')

    def _escape_path_for_command(self, path: Path) -> str:
        """Escape a path for use inside AppleScript command strings."""
        return str(path).replace("\\", "\\\\").replace('"', '\\"')

    def _run_applescript(self, script: str) -> bool:
        """Execute AppleScript and return success status."""
        if not self.is_macos:
            logger.warning("AppleScript not available on this platform")
            return False

        try:
            result = run_command(
                ["osascript", "-e", script],
                timeout=30,
                description="Execute AppleScript for terminal switching",
            )

            success = result.returncode == 0
            if success:
                logger.debug("AppleScript executed successfully")
            else:
                logger.error(f"AppleScript failed: {result.stderr}")

            return success

        except Exception as e:
            logger.error(f"Failed to run AppleScript: {e}")
            return False

    def _run_applescript_with_result(self, script: str) -> str | None:
        """Execute AppleScript and return the output string."""
        if not self.is_macos:
            logger.warning("AppleScript not available on this platform")
            return None

        try:
            result = run_command(
                ["osascript", "-e", script],
                timeout=30,
                description="Execute AppleScript for terminal switching",
            )

            if result.returncode != 0:
                logger.error(f"AppleScript failed: {result.stderr}")
                return None

            return result.stdout.strip()

        except Exception as e:
            logger.error(f"Failed to run AppleScript: {e}")
            return None
