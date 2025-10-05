import logging
import os
import shlex
import sys
from pathlib import Path

from autowt.utils import run_command

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class ITerm2Terminal(BaseTerminal):
    """iTerm2 terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """Get current iTerm2 session ID."""
        session_id = os.getenv("ITERM_SESSION_ID")
        logger.debug(f"Current iTerm2 session ID: {session_id}")
        return session_id

    def supports_session_management(self) -> bool:
        """iTerm2 supports session management."""
        return True

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists in iTerm2."""
        if not session_id:
            return False

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Checking if session exists: {session_uuid}")

        applescript = f"""
        tell application "iTerm2"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        if id of theSession is "{session_uuid}" then
                            return true
                        end if
                    end repeat
                end repeat
            end repeat
            return false
        end tell
        """

        result = self._run_applescript_with_result(applescript)
        return result == "true" if result else False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if iTerm2 session exists and is in the specified directory."""
        if not session_id:
            return False

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Checking if session {session_uuid} is in directory {directory}")

        applescript = f"""
        tell application "iTerm2"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        if id of theSession is "{session_uuid}" then
                            set currentDirectory to get variable named "PWD" of theSession
                            if currentDirectory starts with "{self._escape_for_applescript(str(directory))}" then
                                return true
                            else
                                return false
                            end if
                        end if
                    end repeat
                end repeat
            end repeat
            return false
        end tell
        """

        result = self._run_applescript_with_result(applescript)
        return result == "true" if result else False

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to an existing iTerm2 session."""
        logger.debug(f"Switching to iTerm2 session: {session_id}")

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Using session UUID: {session_uuid}")

        applescript = f"""
        tell application "iTerm2"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        if id of theSession is "{session_uuid}" then
                            select theTab
                            select theWindow"""

        if session_init_script:
            applescript += f"""
                            tell theSession
                                write text "{self._escape_for_applescript(session_init_script)}"
                            end tell"""

        applescript += """
                            return
                        end if
                    end repeat
                end repeat
            end repeat
        end tell
        """

        return self._run_applescript(applescript)

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new iTerm2 tab."""
        logger.debug(f"Opening new iTerm2 tab for {worktree_path}")

        # Get the path to the current autowt executable
        autowt_path = sys.argv[0]
        if not autowt_path.startswith("/"):
            # If relative path, make it absolute
            autowt_path = os.path.abspath(autowt_path)

        # Escape the autowt_path for shell execution
        escaped_autowt_path = shlex.quote(autowt_path)

        commands = [f"cd {self._escape_path_for_command(worktree_path)}"]

        # Add session registration command (uses current working directory)
        commands.append(f"{escaped_autowt_path} register-session-for-path")

        if session_init_script:
            commands.append(session_init_script)

        applescript = f"""
        tell application "iTerm2"
            tell current window
                create tab with default profile
                tell current session of current tab
                    write text "{"; ".join(commands)}"
                end tell
            end tell
        end tell
        """

        return self._run_applescript(applescript)

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new iTerm2 window."""
        logger.debug(f"Opening new iTerm2 window for {worktree_path}")

        commands = [f"cd {self._escape_path_for_command(worktree_path)}"]
        if session_init_script:
            commands.append(session_init_script)

        applescript = f"""
        tell application "iTerm2"
            create window with default profile
            tell current session of current window
                write text "{"; ".join(commands)}"
            end tell
        end tell
        """

        return self._run_applescript(applescript)

    def _run_applescript_for_output(self, script: str) -> str | None:
        """Execute AppleScript and return the output string."""
        if not self.is_macos:
            logger.warning("AppleScript not available on this platform")
            return None

        try:
            result = run_command(
                ["osascript", "-e", script],
                timeout=30,
                description="Execute AppleScript for output",
            )

            if result.returncode != 0:
                logger.error(f"AppleScript failed: {result.stderr}")
                return None

            return result.stdout.strip()

        except Exception as e:
            logger.error(f"Failed to run AppleScript: {e}")
            return None

    def list_sessions_with_directories(self) -> list[dict[str, str]]:
        """List all iTerm2 sessions with their working directories."""
        applescript = """
        tell application "iTerm2"
            set sessionData to ""
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        try
                            set sessionId to id of theSession
                            set sessionPath to (variable named "session.path") of theSession
                            if sessionData is not "" then
                                set sessionData to sessionData & return
                            end if
                            set sessionData to sessionData & sessionId & "|" & sessionPath
                        on error
                            if sessionData is not "" then
                                set sessionData to sessionData & return
                            end if
                            set sessionData to sessionData & sessionId & "|unknown"
                        end try
                    end repeat
                end repeat
            end repeat
            return sessionData
        end tell
        """

        output = self._run_applescript_for_output(applescript)
        if not output:
            return []

        sessions = []
        # Output format: "session1|/path1\nsession2|/path2\n..."
        for line in output.split("\n"):
            line = line.strip()
            if line and "|" in line:
                session_id, path = line.split("|", 1)
                sessions.append(
                    {
                        "session_id": session_id.strip(),
                        "working_directory": path.strip(),
                    }
                )

        return sessions

    def find_session_by_working_directory(self, target_path: str) -> str | None:
        """Find a session ID that matches the given working directory or is within it."""
        sessions = self.list_sessions_with_directories()
        target_path = str(Path(target_path).resolve())  # Normalize path

        for session in sessions:
            session_path = str(Path(session["working_directory"]).resolve())
            # Check if the session is in the target directory or any subdirectory
            if session_path.startswith(target_path):
                return session["session_id"]

        return None

    def execute_in_current_session(self, command: str) -> bool:
        """Execute a command in the current iTerm2 session."""
        logger.debug(f"Executing command in current iTerm2 session: {command}")

        applescript = f"""
        tell application "iTerm2"
            tell current session of current window
                write text "{self._escape_for_applescript(command)}"
            end tell
        end tell
        """

        return self._run_applescript(applescript)
