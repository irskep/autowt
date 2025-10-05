import logging
import os
import shlex
from pathlib import Path

from autowt.services.git import GitService
from autowt.services.terminals.base import BaseTerminal

logger = logging.getLogger(__name__)


class GhosttyMacTerminal(BaseTerminal):
    """Ghostty implementation. Ghostty has no AppleScript support, so it's bare-bones."""

    def get_current_session_id(self) -> str | None:
        return GitService().find_repo_root(os.cwd())

    def supports_session_management(self) -> bool:
        return False

    def session_exists(self, session_id: str) -> bool:
        return False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        return False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        # Ghostty requires System Events (accessibility permissions) to create
        # actual tabs via Cmd+T keyboard simulation.
        logger.debug(f"Opening new Ghostty tab for {worktree_path}")

        commands = [f"cd {shlex.quote(str(worktree_path))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self._escape_for_applescript("; ".join(commands))

        applescript = f"""
        tell application "Ghostty"
            activate
            tell application "System Events"
                tell process "Ghostty"
                    keystroke "t" using command down
                    delay 0.3
                    keystroke "{self._escape_for_applescript(command_string)}"
                    key code 36 -- Return
                end tell
            end tell
        end tell
        """

        if self._run_applescript(applescript):
            return True
        else:
            # System Events failed, fall back to window creation
            logger.warning(
                "Failed to create tab (missing accessibility permissions). "
                "To fix: Enable Terminal in "
                "System Settings -> Privacy & Security -> Accessibility"
            )
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        logger.debug(f"Opening new Terminal.app window for {worktree_path}")

        commands = [f"cd {shlex.quote(str(worktree_path))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self._escape_for_applescript("; ".join(commands))

        applescript = f"""
        tell application "Ghostty"
            activate
            tell application "System Events"
                tell process "Ghostty"
                    keystroke "n" using command down
                    delay 0.3
                    keystroke "{self._escape_for_applescript(command_string)}"
                    key code 36 -- Return
                end tell
            end tell
        end tell
        """

        return self._run_applescript(applescript)

    def execute_in_current_session(self, command: str) -> bool:
        logger.debug(f"Executing command in current Ghostty session: {command}")

        applescript = f"""
        tell application "System Events"
            tell process "Ghostty"
                keystroke "{self._escape_for_applescript(command)}"
                key code 36 -- Return
            end tell
        end tell
        """

        return self._run_applescript(applescript)
