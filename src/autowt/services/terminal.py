"""Terminal management service for autowt."""

import logging
import os
import platform
import shlex
from pathlib import Path

from autowt.models import TerminalMode
from autowt.utils import run_command

logger = logging.getLogger(__name__)


class TerminalService:
    """Handles terminal switching and session management."""

    def __init__(self):
        """Initialize terminal service."""
        self.is_macos = platform.system() == "Darwin"
        self.is_iterm = self._detect_iterm()
        logger.debug(
            f"Terminal service initialized (macOS: {self.is_macos}, iTerm: {self.is_iterm})"
        )

    def _detect_iterm(self) -> bool:
        """Detect if we're running in iTerm2."""
        if not self.is_macos:
            return False

        term_program = os.getenv("TERM_PROGRAM", "")
        is_iterm = term_program == "iTerm.app"
        logger.debug(f"TERM_PROGRAM: {term_program}, is_iterm: {is_iterm}")
        return is_iterm

    def get_current_session_id(self) -> str | None:
        """Get the current terminal session ID."""
        if self.is_iterm:
            session_id = os.getenv("ITERM_SESSION_ID")
            logger.debug(f"Current session ID: {session_id}")
            return session_id

        # For other terminals, we might use other methods
        logger.debug("Session ID not available for this terminal")
        return None

    def switch_to_worktree(
        self,
        worktree_path: Path,
        mode: TerminalMode,
        session_id: str | None = None,
        init_script: str | None = None,
    ) -> bool:
        """Switch to a worktree using the specified terminal mode."""
        logger.debug(f"Switching to worktree {worktree_path} with mode {mode}")

        if mode == TerminalMode.INPLACE:
            return self._change_directory_inplace(worktree_path, init_script)
        elif mode == TerminalMode.SAME:
            return self._switch_to_existing_or_new(
                worktree_path, session_id, init_script
            )
        elif mode == TerminalMode.TAB:
            return self._open_new_tab(worktree_path, init_script)
        elif mode == TerminalMode.WINDOW:
            return self._open_new_window(worktree_path, init_script)
        else:
            logger.error(f"Unknown terminal mode: {mode}")
            return False

    def _change_directory_inplace(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Output shell command to change directory in the current shell."""
        logger.debug(f"Outputting cd command for {worktree_path}")

        try:
            # Output the cd command that the user can evaluate
            # Usage: eval "$(autowt ci --terminal=inplace)"
            commands = [f"cd {shlex.quote(str(worktree_path))}"]
            if init_script:
                commands.append(init_script)
            print("; ".join(commands))
            return True
        except Exception as e:
            logger.error(f"Failed to output cd command: {e}")
            return False

    def _switch_to_existing_or_new(
        self,
        worktree_path: Path,
        session_id: str | None = None,
        init_script: str | None = None,
    ) -> bool:
        """Switch to existing session or create new tab."""
        if session_id and self.is_iterm:
            # Try to switch to existing session
            if self._switch_to_iterm_session(session_id, init_script):
                return True

        # Fall back to creating new tab
        return self._open_new_tab(worktree_path, init_script)

    def _switch_to_iterm_session(
        self, session_id: str, init_script: str | None = None
    ) -> bool:
        """Switch to an existing iTerm session."""
        logger.debug(f"Switching to iTerm session: {session_id}")

        if not self.is_iterm:
            logger.warning("Not in iTerm, cannot switch sessions")
            return False

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Using session UUID: {session_uuid}")

        applescript = f'''
        tell application "iTerm2"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    repeat with theSession in sessions of theTab
                        if id of theSession is "{session_uuid}" then
                            select theTab
                            select theWindow'''

        if init_script:
            applescript += f'''
                            write text "{self._escape_for_applescript(init_script)}" to theSession'''

        applescript += """
                            return
                        end if
                    end repeat
                end repeat
            end repeat
        end tell
        """

        return self._run_applescript(applescript)

    def _open_new_tab(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Open a new terminal tab in the worktree directory."""
        logger.debug(f"Opening new tab for {worktree_path}")

        if self.is_iterm:
            return self._open_iterm_tab(worktree_path, init_script)
        else:
            # Generic terminal fallback
            return self._open_generic_terminal(worktree_path, init_script)

    def _open_new_window(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Open a new terminal window in the worktree directory."""
        logger.debug(f"Opening new window for {worktree_path}")

        if self.is_iterm:
            return self._open_iterm_window(worktree_path, init_script)
        else:
            return self._open_generic_terminal(worktree_path, init_script)

    def _open_iterm_tab(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Open a new iTerm tab."""
        commands = [f"cd {self._escape_path_for_command(worktree_path)}"]
        if init_script:
            commands.append(init_script)

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

    def _open_iterm_window(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Open a new iTerm window."""
        commands = [f"cd {self._escape_path_for_command(worktree_path)}"]
        if init_script:
            commands.append(init_script)

        applescript = f"""
        tell application "iTerm2"
            create window with default profile
            tell current session of current window
                write text "{"; ".join(commands)}"
            end tell
        end tell
        """

        return self._run_applescript(applescript)

    def _open_generic_terminal(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Open terminal using generic methods."""
        logger.debug("Using generic terminal opening method")

        try:
            if self.is_macos:
                # Use open command on macOS
                run_command(
                    ["open", "-a", "Terminal", str(worktree_path)],
                    timeout=10,
                    description=f"Open Terminal app at {worktree_path}",
                )
            else:
                # Try common Linux terminal emulators
                terminals = ["gnome-terminal", "konsole", "xterm"]
                for terminal in terminals:
                    try:
                        cmd = [terminal, "--working-directory", str(worktree_path)]
                        if init_script:
                            # For terminals that support it, try to run the init script
                            if terminal == "gnome-terminal":
                                cmd.extend(
                                    [
                                        "--",
                                        "bash",
                                        "-c",
                                        f"cd {shlex.quote(str(worktree_path))}; {init_script}; exec bash",
                                    ]
                                )
                            elif terminal == "konsole":
                                cmd.extend(
                                    [
                                        "-e",
                                        "bash",
                                        "-c",
                                        f"cd {shlex.quote(str(worktree_path))}; {init_script}; exec bash",
                                    ]
                                )

                        run_command(
                            cmd,
                            timeout=10,
                            description=f"Open {terminal} at {worktree_path}",
                        )
                        return True
                    except FileNotFoundError:
                        continue

                logger.warning("No suitable terminal emulator found")
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to open generic terminal: {e}")
            return False

    def _escape_path_for_command(self, path: Path) -> str:
        """Escape a path for use inside AppleScript command strings."""
        # For use inside "write text" commands - don't add extra quotes
        return str(path).replace("\\", "\\\\").replace('"', '\\"')

    def _escape_path(self, path: Path) -> str:
        """Escape a path for use in AppleScript (with quotes)."""
        # AppleScript string escaping: double quotes and backslashes
        escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def _escape_for_applescript(self, text: str) -> str:
        """Escape text for use in AppleScript strings."""
        return text.replace("\\", "\\\\").replace('"', '\\"')

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
