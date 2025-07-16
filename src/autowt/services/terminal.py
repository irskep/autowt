"""Terminal management service for autowt."""

import logging
import os
import platform
import shlex
from abc import ABC, abstractmethod
from pathlib import Path

from autowt.models import TerminalMode
from autowt.prompts import confirm_default_yes
from autowt.utils import run_command

logger = logging.getLogger(__name__)


class Terminal(ABC):
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
        self, session_id: str, init_script: str | None = None
    ) -> bool:
        """Switch to existing session if supported."""
        pass

    @abstractmethod
    def open_new_tab(self, worktree_path: Path, init_script: str | None = None) -> bool:
        """Open new tab in current window."""
        pass

    @abstractmethod
    def open_new_window(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Open new window."""
        pass

    def supports_session_management(self) -> bool:
        """Whether this terminal supports session management."""
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


class ITerm2Terminal(Terminal):
    """iTerm2 terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """Get current iTerm2 session ID."""
        session_id = os.getenv("ITERM_SESSION_ID")
        logger.debug(f"Current iTerm2 session ID: {session_id}")
        return session_id

    def supports_session_management(self) -> bool:
        """iTerm2 supports session management."""
        return True

    def switch_to_session(
        self, session_id: str, init_script: str | None = None
    ) -> bool:
        """Switch to an existing iTerm2 session."""
        logger.debug(f"Switching to iTerm2 session: {session_id}")

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

    def open_new_tab(self, worktree_path: Path, init_script: str | None = None) -> bool:
        """Open a new iTerm2 tab."""
        logger.debug(f"Opening new iTerm2 tab for {worktree_path}")

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

    def open_new_window(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Open a new iTerm2 window."""
        logger.debug(f"Opening new iTerm2 window for {worktree_path}")

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


class TerminalAppTerminal(Terminal):
    """Terminal.app implementation."""

    def get_current_session_id(self) -> str | None:
        """Terminal.app doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, init_script: str | None = None
    ) -> bool:
        """Terminal.app doesn't support session switching."""
        return False

    def open_new_tab(self, worktree_path: Path, init_script: str | None = None) -> bool:
        """Open a new Terminal.app tab.

        Terminal.app requires System Events (accessibility permissions) to create
        actual tabs via Cmd+T keyboard simulation.
        """
        logger.debug(f"Opening new Terminal.app tab for {worktree_path}")

        commands = [f"cd {shlex.quote(str(worktree_path))}"]
        if init_script:
            commands.append(init_script)

        command_string = self._escape_for_applescript("; ".join(commands))

        # First check if we have any Terminal windows open
        check_windows_script = """
        tell application "Terminal"
            return count of windows
        end tell
        """

        try:
            result = run_command(
                ["osascript", "-e", check_windows_script],
                timeout=5,
                description="Check Terminal windows",
            )
            window_count = int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            window_count = 0

        if window_count == 0:
            # No windows open, create first window
            applescript = f"""
            tell application "Terminal"
                do script "{command_string}"
            end tell
            """
        else:
            # Windows exist, try to create a tab using System Events
            applescript = f"""
            tell application "Terminal"
                activate
                tell application "System Events"
                    tell process "Terminal"
                        keystroke "t" using command down
                    end tell
                end tell
                delay 0.3
                do script "{command_string}" in selected tab of front window
            end tell
            """

        success = self._run_applescript(applescript)

        if not success and window_count > 0:
            # System Events failed, fall back to window creation
            logger.warning(
                "Failed to create tab (missing accessibility permissions). "
                "Creating new window instead. To fix: Enable Terminal in "
                "System Settings -> Privacy & Security -> Accessibility"
            )
            fallback_script = f"""
            tell application "Terminal"
                do script "{command_string}"
            end tell
            """
            return self._run_applescript(fallback_script)

        return success

    def open_new_window(
        self, worktree_path: Path, init_script: str | None = None
    ) -> bool:
        """Open a new Terminal.app window."""
        logger.debug(f"Opening new Terminal.app window for {worktree_path}")

        commands = [f"cd {shlex.quote(str(worktree_path))}"]
        if init_script:
            commands.append(init_script)

        command_string = self._escape_for_applescript("; ".join(commands))

        applescript = f"""
        tell application "Terminal"
            do script "{command_string}"
        end tell
        """

        return self._run_applescript(applescript)


class GenericTerminal(Terminal):
    """Generic terminal implementation for fallback."""

    def get_current_session_id(self) -> str | None:
        """Generic terminals don't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, init_script: str | None = None
    ) -> bool:
        """Generic terminals don't support session switching."""
        return False

    def open_new_tab(self, worktree_path: Path, init_script: str | None = None) -> bool:
        """Open terminal using generic methods (same as new window)."""
        return self.open_new_window(worktree_path, init_script)

    def open_new_window(
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
            elif platform.system() == "Windows":
                # Windows terminal operations not yet supported
                logger.info("Windows terminal operations not yet supported - skipping")
                return False
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


class TerminalService:
    """Handles terminal switching and session management."""

    def __init__(self):
        """Initialize terminal service."""
        self.is_macos = platform.system() == "Darwin"
        self.terminal = self._create_terminal_implementation()
        logger.debug(
            f"Terminal service initialized with {type(self.terminal).__name__}"
        )

    def _create_terminal_implementation(self) -> Terminal:
        """Create the appropriate terminal implementation."""
        if not self.is_macos:
            return GenericTerminal()

        term_program = os.getenv("TERM_PROGRAM", "")
        logger.debug(f"TERM_PROGRAM: {term_program}")

        if term_program == "iTerm.app":
            return ITerm2Terminal()
        elif term_program == "Apple_Terminal":
            return TerminalAppTerminal()
        else:
            # Fallback to generic terminal
            return GenericTerminal()

    def get_current_session_id(self) -> str | None:
        """Get the current terminal session ID."""
        return self.terminal.get_current_session_id()

    def switch_to_worktree(
        self,
        worktree_path: Path,
        mode: TerminalMode,
        session_id: str | None = None,
        init_script: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
    ) -> bool:
        """Switch to a worktree using the specified terminal mode."""
        logger.debug(f"Switching to worktree {worktree_path} with mode {mode}")

        if mode == TerminalMode.INPLACE:
            return self._change_directory_inplace(worktree_path, init_script)
        elif mode == TerminalMode.TAB:
            return self._switch_to_existing_or_new_tab(
                worktree_path, session_id, init_script, branch_name, auto_confirm
            )
        elif mode == TerminalMode.WINDOW:
            return self._switch_to_existing_or_new_window(
                worktree_path, session_id, init_script, branch_name, auto_confirm
            )
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

    def _switch_to_existing_or_new_tab(
        self,
        worktree_path: Path,
        session_id: str | None = None,
        init_script: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
    ) -> bool:
        """Switch to existing session or create new tab."""
        # If we have a session ID and terminal supports it, ask user if they want to switch to existing
        if session_id and self.terminal.supports_session_management():
            if auto_confirm or self._should_switch_to_existing(branch_name):
                # Try to switch to existing session
                if self.terminal.switch_to_session(session_id, init_script):
                    print(f"Switched to existing {branch_name or 'worktree'} session")
                    return True

        # Fall back to creating new tab
        return self.terminal.open_new_tab(worktree_path, init_script)

    def _switch_to_existing_or_new_window(
        self,
        worktree_path: Path,
        session_id: str | None = None,
        init_script: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
    ) -> bool:
        """Switch to existing session or create new window."""
        # If we have a session ID and terminal supports it, ask user if they want to switch to existing
        if session_id and self.terminal.supports_session_management():
            if auto_confirm or self._should_switch_to_existing(branch_name):
                # Try to switch to existing session
                if self.terminal.switch_to_session(session_id, init_script):
                    print(f"Switched to existing {branch_name or 'worktree'} session")
                    return True

        # Fall back to creating new window
        return self.terminal.open_new_window(worktree_path, init_script)

    def _should_switch_to_existing(self, branch_name: str | None) -> bool:
        """Ask user if they want to switch to existing session."""
        if branch_name:
            return confirm_default_yes(
                f"{branch_name} already has a session. Switch to it?"
            )
        else:
            return confirm_default_yes("Worktree already has a session. Switch to it?")
