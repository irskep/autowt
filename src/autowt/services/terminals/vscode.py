import logging
from abc import abstractmethod
from pathlib import Path
from urllib.parse import quote

from autowt.utils import run_command

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class EditorTerminal(BaseTerminal):
    """Abstract base class for editor terminal implementations (VSCode, Cursor, etc.)."""

    @property
    @abstractmethod
    def cli_command(self) -> str:
        """CLI command name (e.g., 'code', 'cursor')."""
        pass

    @property
    @abstractmethod
    def app_names(self) -> list[str]:
        """Application process names for AppleScript detection."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for logging and error messages."""
        pass

    def get_current_session_id(self) -> str | None:
        """Editors don't have session IDs."""
        return None

    def supports_session_management(self) -> bool:
        """Editors support window detection on macOS."""
        return self.is_macos

    def _path_to_file_url(self, path: Path) -> str:
        """Convert absolute path to file:// URL format."""
        path = path.resolve()
        return f"file://{quote(str(path), safe='/')}"

    def _find_window_with_path(self, worktree_path: Path) -> bool:
        """Find and activate editor window containing the target path."""
        if not self.is_macos:
            return False

        target_url = self._path_to_file_url(worktree_path)

        for app_name in self.app_names:
            applescript = f"""
            tell application "System Events"
                if not (exists process "{app_name}") then
                    return false
                end if

                tell process "{app_name}"
                    set targetURL to "{target_url}"
                    set foundWindow to missing value
                    set windowIndex to 0

                    repeat with w in windows
                        set windowIndex to windowIndex + 1
                        try
                            set docPath to value of attribute "AXDocument" of w
                            if docPath starts with targetURL or targetURL starts with docPath then
                                set foundWindow to windowIndex
                                exit repeat
                            end if
                        on error
                            -- window has no document attribute
                        end try
                    end repeat

                    if foundWindow is not missing value then
                        -- Activate the window
                        set frontmost to true
                        click window foundWindow
                        return true
                    else
                        return false
                    end if
                end tell
            end tell
            """

            result = self._run_applescript_with_result(applescript)
            if result == "true":
                return True

        return False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Try to switch to existing editor window with the given path."""
        if not self.is_macos:
            return False

        # For editors, session_id is the worktree path
        try:
            worktree_path = Path(session_id)
            return self._find_window_with_path(worktree_path)
        except Exception:
            return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open new editor window (editors don't support tabs via CLI)."""
        return self.open_new_window(worktree_path, session_init_script)

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new editor window."""
        logger.debug(f"Opening new {self.display_name} window for {worktree_path}")

        if session_init_script:
            logger.warning(
                f"{self.display_name} doesn't support running init scripts via CLI. "
                "The init script will not be executed."
            )

        try:
            cmd = [self.cli_command, "-n", str(worktree_path)]
            result = run_command(
                cmd,
                timeout=10,
                description=f"Open {self.display_name} window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open {self.display_name} window: {e}")
            return False


class VSCodeTerminal(EditorTerminal):
    """VSCode terminal implementation using 'code' CLI command."""

    @property
    def cli_command(self) -> str:
        return "code"

    @property
    def app_names(self) -> list[str]:
        return ["Code", "Visual Studio Code"]

    @property
    def display_name(self) -> str:
        return "VSCode"


class CursorTerminal(EditorTerminal):
    """Cursor terminal implementation using 'cursor' CLI command."""

    @property
    def cli_command(self) -> str:
        return "cursor"

    @property
    def app_names(self) -> list[str]:
        return ["Cursor"]

    @property
    def display_name(self) -> str:
        return "Cursor"
