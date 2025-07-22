"""Terminal management service for autowt."""

import logging
import os
import platform
import shlex
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from autowt.models import TerminalMode
from autowt.prompts import confirm_default_yes
from autowt.services.state import StateService
from autowt.utils import run_command, sanitize_branch_name

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
        self, session_id: str, session_session_init_script: str | None = None
    ) -> bool:
        """Switch to existing session if supported."""
        pass

    @abstractmethod
    def open_new_tab(
        self, worktree_path: Path, session_session_init_script: str | None = None
    ) -> bool:
        """Open new tab in current window."""
        pass

    @abstractmethod
    def open_new_window(
        self, worktree_path: Path, session_session_init_script: str | None = None
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

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists in iTerm2."""
        if not session_id:
            return False

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Checking if session exists: {session_uuid}")

        applescript = f'''
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
        '''

        result = self._run_applescript_with_result(applescript)
        return result == "true" if result else False

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if iTerm2 session exists and is in the specified directory."""
        if not session_id:
            return False

        # Extract UUID part from session ID (format: w0t0p2:UUID)
        session_uuid = session_id.split(":")[-1] if ":" in session_id else session_id
        logger.debug(f"Checking if session {session_uuid} is in directory {directory}")

        applescript = f'''
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
        '''

        result = self._run_applescript_with_result(applescript)
        return result == "true" if result else False

    def switch_to_session(
        self, session_id: str, session_session_init_script: str | None = None
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

        if session_session_init_script:
            applescript += f'''
                            tell theSession
                                write text "{self._escape_for_applescript(session_session_init_script)}"
                            end tell'''

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
        self, worktree_path: Path, session_session_init_script: str | None = None
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

        if session_session_init_script:
            commands.append(session_session_init_script)

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

        applescript = f'''
        tell application "iTerm2"
            tell current session of current window
                write text "{self._escape_for_applescript(command)}"
            end tell
        end tell
        '''

        return self._run_applescript(applescript)


class TerminalAppTerminal(Terminal):
    """Terminal.app implementation."""

    def get_current_session_id(self) -> str | None:
        """Get Terminal.app working directory as session identifier."""
        try:
            applescript = """
            tell application "Terminal"
                set tabTTY to tty of selected tab of front window
                return tabTTY
            end tell
            """

            result = run_command(
                ["osascript", "-e", applescript],
                timeout=5,
                description="Get Terminal.app current tab TTY",
            )

            if result.returncode == 0 and result.stdout.strip():
                tty = result.stdout.strip()
                # Get working directory from shell process
                working_dir = self._get_working_directory_from_tty(tty)
                return working_dir

            return None

        except Exception:
            return None

    def supports_session_management(self) -> bool:
        """Terminal.app supports session management via working directory detection."""
        return True

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists in Terminal.app by working directory."""
        if not session_id:
            return False

        applescript = f'''
        tell application "Terminal"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set applescriptShellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|sh)' | head -1 | awk '{{print $2}}'"
                        set shellPid to do shell script applescriptShellCmd
                        if shellPid is not "" then
                            set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{{print $9}}'"
                            set workingDir to do shell script cwdCmd
                            if workingDir is "{self._escape_for_applescript(session_id)}" then
                                return true
                            end if
                        end if
                    end try
                end repeat
            end repeat
            return false
        end tell
        '''

        result = self._run_applescript_with_result(applescript)
        return result == "true" if result else False

    def _get_working_directory_from_tty(self, tty: str) -> str | None:
        """Get working directory of shell process using the given TTY."""
        try:
            # Find shell process for this TTY
            shell_cmd = f"lsof {shlex.quote(tty)} | grep -E '(zsh|bash|sh)' | head -1 | awk '{{print $2}}'"
            shell_result = run_command(
                ["bash", "-c", shell_cmd],
                timeout=5,
                description=f"Find shell process for TTY {tty}",
            )

            if shell_result.returncode != 0 or not shell_result.stdout.strip():
                return None

            pid = shell_result.stdout.strip()

            # Get working directory of that process
            cwd_cmd = f"lsof -p {shlex.quote(pid)} | grep cwd | awk '{{print $9}}'"
            cwd_result = run_command(
                ["bash", "-c", cwd_cmd],
                timeout=5,
                description=f"Get working directory for PID {pid}",
            )

            if cwd_result.returncode == 0 and cwd_result.stdout.strip():
                return cwd_result.stdout.strip()

            return None

        except Exception as e:
            logger.debug(f"Failed to get working directory from TTY {tty}: {e}")
            return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to existing Terminal.app session by working directory."""
        # Find the window title that contains our target directory
        find_window_script = f'''
        tell application "Terminal"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set shellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|sh)' | head -1 | awk '{{print $2}}'"
                        set shellPid to do shell script shellCmd
                        if shellPid is not "" then
                            set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{{print $9}}'"
                            set workingDir to do shell script cwdCmd
                            if workingDir is "{self._escape_for_applescript(session_id)}" then
                                -- Return the window name for menu matching
                                return name of theWindow
                            end if
                        end if
                    end try
                end repeat
            end repeat
            return ""
        end tell
        '''

        window_name = self._run_applescript_with_result(find_window_script)
        if not window_name:
            return False

        # Use System Events to click the exact menu item
        switch_script = f'''
        tell application "System Events"
            tell process "Terminal"
                try
                    -- Click the menu item with the exact window name
                    click menu item "{self._escape_for_applescript(window_name)}" of menu "Window" of menu bar 1
                    return "success"
                on error errMsg
                    -- Try with localized menu name
                    try
                        click menu item "{self._escape_for_applescript(window_name)}" of menu "窗口" of menu bar 1
                        return "success"
                    on error
                        return "error: " & errMsg
                    end try
                end try
            end tell
        end tell
        '''

        # Run init script if provided
        if session_init_script:
            init_result = self._run_applescript(f'''
            tell application "Terminal"
                do script "{self._escape_for_applescript(session_init_script)}" in front window
            end tell
            ''')
            if not init_result:
                logger.warning("Failed to run init script")

        switch_result = self._run_applescript_with_result(switch_script)
        return switch_result and switch_result.startswith("success")

    def session_in_directory(self, session_id: str, directory: Path) -> bool:
        """Check if Terminal.app session exists and is in the specified directory or subdirectory."""

        applescript = f'''
        tell application "Terminal"
            repeat with theWindow in windows
                repeat with theTab in tabs of theWindow
                    try
                        set tabTTY to tty of theTab
                        set applescriptShellCmd to "lsof " & tabTTY & " | grep -E '(zsh|bash|sh)' | head -1 | awk '{{print $2}}'"
                        set shellPid to do shell script applescriptShellCmd
                        if shellPid is not "" then
                            set cwdCmd to "lsof -p " & shellPid & " | grep cwd | awk '{{print $9}}'"
                            set workingDir to do shell script cwdCmd
                            if workingDir starts with "{self._escape_for_applescript(str(directory))}" then
                                return true
                            end if
                        end if
                    end try
                end repeat
            end repeat
            return false
        end tell
        '''

        result = self._run_applescript_with_result(applescript)
        return result == "true" if result else False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Terminal.app tab.

        Terminal.app requires System Events (accessibility permissions) to create
        actual tabs via Cmd+T keyboard simulation.
        """
        logger.debug(f"Opening new Terminal.app tab for {worktree_path}")

        commands = [f"cd {shlex.quote(str(worktree_path))}"]
        if session_init_script:
            commands.append(session_init_script)

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
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Terminal.app window."""
        logger.debug(f"Opening new Terminal.app window for {worktree_path}")

        commands = [f"cd {shlex.quote(str(worktree_path))}"]
        if session_init_script:
            commands.append(session_init_script)

        command_string = self._escape_for_applescript("; ".join(commands))

        applescript = f"""
        tell application "Terminal"
            do script "{command_string}"
        end tell
        """

        return self._run_applescript(applescript)

    def execute_in_current_session(self, command: str) -> bool:
        """Execute a command in the current Terminal.app session."""
        logger.debug(f"Executing command in current Terminal.app session: {command}")

        applescript = f'''
        tell application "Terminal"
            do script "{self._escape_for_applescript(command)}" in selected tab of front window
        end tell
        '''

        return self._run_applescript(applescript)


class TmuxTerminal(Terminal):
    """tmux terminal implementation for users already using tmux."""

    def __init__(self):
        """Initialize tmux terminal implementation."""
        super().__init__()
        self.is_in_tmux = bool(os.getenv("TMUX"))

    def get_current_session_id(self) -> str | None:
        """Get current tmux session name."""
        if not self.is_in_tmux:
            return None

        try:
            result = run_command(
                ["tmux", "display-message", "-p", "#S"],
                timeout=5,
                description="Get current tmux session name",
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def supports_session_management(self) -> bool:
        """tmux supports excellent session management."""
        return True

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Switch to existing tmux session."""
        logger.debug(f"Switching to tmux session: {session_id}")

        try:
            # Check if session exists
            result = run_command(
                ["tmux", "has-session", "-t", session_id],
                timeout=5,
                description=f"Check if tmux session {session_id} exists",
            )

            if result.returncode != 0:
                return False

            # Switch to session
            if self.is_in_tmux:
                # If inside tmux, switch within tmux
                switch_result = run_command(
                    ["tmux", "switch-client", "-t", session_id],
                    timeout=5,
                    description=f"Switch to tmux session {session_id}",
                )
            else:
                # Not in tmux, attach to session
                switch_result = run_command(
                    ["tmux", "attach-session", "-t", session_id],
                    timeout=5,
                    description=f"Attach to tmux session {session_id}",
                )

            success = switch_result.returncode == 0

            # Run init script if provided and switch succeeded
            if success and session_init_script:
                run_command(
                    [
                        "tmux",
                        "send-keys",
                        "-t",
                        session_id,
                        session_init_script,
                        "Enter",
                    ],
                    timeout=5,
                    description=f"Send init script to tmux session {session_id}",
                )

            return success

        except Exception as e:
            logger.error(f"Failed to switch to tmux session: {e}")
            return False

    def _create_session_name(self, worktree_path: Path) -> str:
        """Create a tmux session name for the worktree."""
        # Use sanitized worktree directory name
        return f"autowt-{sanitize_branch_name(worktree_path.name)}"

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Create new tmux window (tmux equivalent of tab)."""
        return self.open_new_window(worktree_path, session_init_script)

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Create new tmux session for the worktree."""
        logger.debug(f"Creating tmux session for {worktree_path}")

        session_name = self._create_session_name(worktree_path)

        try:
            # Create or attach to session
            cmd = [
                "tmux",
                "new-session",
                "-A",
                "-s",
                session_name,
                "-c",
                str(worktree_path),
            ]

            if self.is_in_tmux:
                # If inside tmux, create detached and switch
                cmd.insert(-1, "-d")
                create_result = run_command(
                    cmd,
                    timeout=10,
                    description=f"Create tmux session {session_name}",
                )
                if create_result.returncode == 0:
                    return self.switch_to_session(session_name, session_init_script)
                return False
            else:
                # Not in tmux, can attach directly
                result = run_command(
                    cmd,
                    timeout=10,
                    description=f"Create/attach tmux session {session_name}",
                )

                if result.returncode == 0 and session_init_script:
                    run_command(
                        ["tmux", "send-keys", session_init_script, "Enter"],
                        timeout=5,
                        description="Send init script to new tmux session",
                    )

                return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to create tmux session: {e}")
            return False


class GnomeTerminalTerminal(Terminal):
    """GNOME Terminal implementation for Linux."""

    def get_current_session_id(self) -> str | None:
        """GNOME Terminal doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """GNOME Terminal doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new GNOME Terminal tab."""
        logger.info(
            "Using experimental support for GNOME Terminal. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new GNOME Terminal tab for {worktree_path}")

        try:
            cmd = ["gnome-terminal", "--tab", "--working-directory", str(worktree_path)]
            if session_init_script:
                cmd.extend(["--", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open GNOME Terminal tab",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open GNOME Terminal tab: {e}")
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new GNOME Terminal window."""
        logger.info(
            "Using experimental support for GNOME Terminal. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new GNOME Terminal window for {worktree_path}")

        try:
            cmd = [
                "gnome-terminal",
                "--window",
                "--working-directory",
                str(worktree_path),
            ]
            if session_init_script:
                cmd.extend(["--", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open GNOME Terminal window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open GNOME Terminal window: {e}")
            return False


class KonsoleTerminal(Terminal):
    """Konsole terminal implementation for KDE."""

    def get_current_session_id(self) -> str | None:
        """Konsole doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Konsole doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Konsole tab."""
        logger.info(
            "Using experimental support for Konsole. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Konsole tab for {worktree_path}")

        try:
            cmd = ["konsole", "--new-tab", "--workdir", str(worktree_path)]
            if session_init_script:
                cmd.extend(["-e", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Konsole tab",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Konsole tab: {e}")
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Konsole window."""
        logger.info(
            "Using experimental support for Konsole. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Konsole window for {worktree_path}")

        try:
            cmd = ["konsole", "--workdir", str(worktree_path)]
            if session_init_script:
                cmd.extend(["-e", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Konsole window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Konsole window: {e}")
            return False


class XfceTerminalTerminal(Terminal):
    """XFCE4 Terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """XFCE4 Terminal doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """XFCE4 Terminal doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new XFCE4 Terminal tab."""
        logger.info(
            "Using experimental support for XFCE4 Terminal. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new XFCE4 Terminal tab for {worktree_path}")

        try:
            cmd = ["xfce4-terminal", "--tab", "--working-directory", str(worktree_path)]
            if session_init_script:
                cmd.extend(["--command", f"bash -c '{session_init_script}; exec bash'"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open XFCE4 Terminal tab",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open XFCE4 Terminal tab: {e}")
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new XFCE4 Terminal window."""
        logger.info(
            "Using experimental support for XFCE4 Terminal. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new XFCE4 Terminal window for {worktree_path}")

        try:
            cmd = [
                "xfce4-terminal",
                "--window",
                "--working-directory",
                str(worktree_path),
            ]
            if session_init_script:
                cmd.extend(["--command", f"bash -c '{session_init_script}; exec bash'"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open XFCE4 Terminal window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open XFCE4 Terminal window: {e}")
            return False


class TilixTerminal(Terminal):
    """Tilix terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """Tilix doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Tilix doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Tilix session (tab equivalent)."""
        logger.info(
            "Using experimental support for Tilix. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Tilix session for {worktree_path}")

        try:
            cmd = [
                "tilix",
                "--focus-window",
                "--action=app-new-session",
                "--working-directory",
                str(worktree_path),
            ]
            if session_init_script:
                cmd.extend(["-x", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Tilix session",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Tilix session: {e}")
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Tilix window."""
        logger.info(
            "Using experimental support for Tilix. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Tilix window for {worktree_path}")

        try:
            cmd = [
                "tilix",
                "--action=app-new-window",
                "--working-directory",
                str(worktree_path),
            ]
            if session_init_script:
                cmd.extend(["-x", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Tilix window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Tilix window: {e}")
            return False


class TerminatorTerminal(Terminal):
    """Terminator terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """Terminator doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Terminator doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Terminator tab."""
        logger.info(
            "Using experimental support for Terminator. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Terminator tab for {worktree_path}")

        try:
            cmd = ["terminator", "--new-tab", f"--working-directory={worktree_path}"]
            if session_init_script:
                cmd.extend(["-x", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Terminator tab",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Terminator tab: {e}")
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Terminator window."""
        logger.info(
            "Using experimental support for Terminator. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Terminator window for {worktree_path}")

        try:
            cmd = ["terminator", f"--working-directory={worktree_path}"]
            if session_init_script:
                cmd.extend(["-x", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Terminator window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Terminator window: {e}")
            return False


class AlacrittyTerminal(Terminal):
    """Alacritty terminal implementation (no tab support, window-only)."""

    def get_current_session_id(self) -> str | None:
        """Alacritty doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Alacritty doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Alacritty doesn't support tabs, fall back to window."""
        logger.warning("Alacritty doesn't support tabs, opening new window instead")
        return self.open_new_window(worktree_path, session_init_script)

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Alacritty window."""
        logger.info(
            "Using experimental support for Alacritty. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Alacritty window for {worktree_path}")

        try:
            cmd = ["alacritty", "--working-directory", str(worktree_path)]
            if session_init_script:
                cmd.extend(["-e", "bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Alacritty window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Alacritty window: {e}")
            return False


class KittyTerminal(Terminal):
    """Kitty terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """Kitty doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Kitty doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Kitty tab using remote control."""
        logger.info(
            "Using experimental support for Kitty. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Kitty tab for {worktree_path}")

        try:
            # Try using kitty remote control first
            cmd = ["kitty", "@", "launch", "--type=tab", "--cwd", str(worktree_path)]
            if session_init_script:
                cmd.extend(["bash", "-c", f"{session_init_script}; exec bash"])
            else:
                cmd.append("bash")

            result = run_command(
                cmd,
                timeout=10,
                description="Open Kitty tab via remote control",
            )

            if result.returncode == 0:
                return True

            # Fall back to opening new window if remote control fails
            logger.debug("Kitty remote control failed, falling back to new window")
            return self.open_new_window(worktree_path, session_init_script)

        except Exception as e:
            logger.error(f"Failed to open Kitty tab: {e}")
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Kitty window."""
        logger.info(
            "Using experimental support for Kitty. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Kitty window for {worktree_path}")

        try:
            cmd = ["kitty", "--directory", str(worktree_path)]
            if session_init_script:
                cmd.extend(["bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Kitty window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Kitty window: {e}")
            return False


class WezTermTerminal(Terminal):
    """WezTerm terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """WezTerm doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """WezTerm doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new WezTerm tab."""
        logger.info(
            "Using experimental support for WezTerm. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new WezTerm tab for {worktree_path}")

        try:
            cmd = ["wezterm", "cli", "spawn", "--cwd", str(worktree_path)]
            if session_init_script:
                cmd.extend(["bash", "-c", f"{session_init_script}; exec bash"])
            else:
                cmd.append("bash")

            result = run_command(
                cmd,
                timeout=10,
                description="Open WezTerm tab",
            )

            if result.returncode == 0:
                return True

            # Fall back to opening new window if CLI fails
            logger.debug("WezTerm CLI failed, falling back to new window")
            return self.open_new_window(worktree_path, session_init_script)

        except Exception as e:
            logger.error(f"Failed to open WezTerm tab: {e}")
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new WezTerm window."""
        logger.info(
            "Using experimental support for WezTerm. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new WezTerm window for {worktree_path}")

        try:
            cmd = ["wezterm", "start", "--cwd", str(worktree_path)]
            if session_init_script:
                cmd.extend(["bash", "-c", f"{session_init_script}; exec bash"])

            result = run_command(
                cmd,
                timeout=10,
                description="Open WezTerm window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open WezTerm window: {e}")
            return False


class HyperTerminal(Terminal):
    """Hyper terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """Hyper doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Hyper doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open new Hyper tab (same as window for Hyper)."""
        return self.open_new_window(worktree_path, session_init_script)

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Hyper window."""
        logger.info(
            "Using experimental support for Hyper. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Hyper window for {worktree_path}")

        try:
            if self.is_macos:
                cmd = ["open", "-a", "Hyper", str(worktree_path)]
            else:
                cmd = ["hyper", str(worktree_path)]

            if session_init_script:
                # Hyper doesn't easily support init scripts via command line
                logger.warning(
                    "Hyper doesn't support init scripts via command line. "
                    "You may need to run the init script manually."
                )

            result = run_command(
                cmd,
                timeout=10,
                description="Open Hyper window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Hyper window: {e}")
            return False


class WindowsTerminalTerminal(Terminal):
    """Windows Terminal implementation."""

    def get_current_session_id(self) -> str | None:
        """Windows Terminal doesn't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Windows Terminal doesn't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Windows Terminal tab."""
        logger.info(
            "Using experimental support for Windows Terminal. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Windows Terminal tab for {worktree_path}")

        try:
            cmd = ["wt", "-d", str(worktree_path)]
            if session_init_script:
                # Use PowerShell to run the init script
                cmd.extend(["powershell", "-NoExit", "-Command", session_init_script])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Windows Terminal tab",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Windows Terminal tab: {e}")
            return False

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open a new Windows Terminal window."""
        logger.info(
            "Using experimental support for Windows Terminal. "
            "Please report issues at https://github.com/irskep/autowt/issues"
        )
        logger.debug(f"Opening new Windows Terminal window for {worktree_path}")

        try:
            cmd = ["wt", "--window", "0", "-d", str(worktree_path)]
            if session_init_script:
                # Use PowerShell to run the init script
                cmd.extend(["powershell", "-NoExit", "-Command", session_init_script])

            result = run_command(
                cmd,
                timeout=10,
                description="Open Windows Terminal window",
            )
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to open Windows Terminal window: {e}")
            return False


class GenericTerminal(Terminal):
    """Generic terminal implementation for fallback - echoes commands instead of executing them."""

    def get_current_session_id(self) -> str | None:
        """Generic terminals don't have session IDs."""
        return None

    def switch_to_session(
        self, session_id: str, session_init_script: str | None = None
    ) -> bool:
        """Generic terminals don't support session switching."""
        return False

    def open_new_tab(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Open terminal using generic methods (same as new window)."""
        return self.open_new_window(worktree_path, session_init_script)

    def _collect_debug_info(self) -> dict:
        """Collect debug information for GitHub issue reporting."""
        debug_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.architecture(),
            "shell": os.environ.get("SHELL", "unknown"),
            "term": os.environ.get("TERM", "unknown"),
            "term_program": os.environ.get("TERM_PROGRAM", "unknown"),
            "desktop_env": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
            "display": os.environ.get("DISPLAY", "not set"),
            "wayland_display": os.environ.get("WAYLAND_DISPLAY", "not set"),
        }

        # Check for common terminal executables
        terminal_programs = [
            "gnome-terminal",
            "konsole",
            "xterm",
            "xfce4-terminal",
            "tilix",
            "terminator",
            "alacritty",
            "kitty",
            "wezterm",
        ]

        available_terminals = []
        for terminal in terminal_programs:
            try:
                result = run_command(
                    ["which", terminal]
                    if not platform.system() == "Windows"
                    else ["where", terminal],
                    timeout=2,
                    description=f"Check for {terminal}",
                )
                if result.returncode == 0:
                    available_terminals.append(f"{terminal}: {result.stdout.strip()}")
            except Exception:
                pass

        debug_info["available_terminals"] = available_terminals
        return debug_info

    def open_new_window(
        self, worktree_path: Path, session_init_script: str | None = None
    ) -> bool:
        """Echo commands that would open a terminal instead of executing them."""
        print("\n=== Generic Terminal Fallback - Manual Commands Required ===")
        print(
            "autowt detected an unsupported terminal. Please run these commands manually:"
        )
        print()

        # Show the basic navigation command
        print("# Change to worktree directory:")
        print(f"cd {shlex.quote(str(worktree_path))}")

        if session_init_script:
            print("\n# Run initialization script:")
            print(f"{session_init_script}")

        print()

        # Platform-specific suggestions
        if self.is_macos:
            print("# To open a new Terminal window on macOS:")
            print(f"open -a Terminal {shlex.quote(str(worktree_path))}")
        elif platform.system() == "Windows":
            print(
                "# To open a new terminal window on Windows (if Windows Terminal is installed):"
            )
            print(f"wt -d {shlex.quote(str(worktree_path))}")
            print("# Or with Command Prompt:")
            print(f'start cmd /k "cd /d {shlex.quote(str(worktree_path))}"')
        else:
            print("# To open a new terminal window on Linux, try one of these:")
            terminals_with_commands = [
                (
                    "gnome-terminal",
                    f"gnome-terminal --working-directory={shlex.quote(str(worktree_path))}",
                ),
                ("konsole", f"konsole --workdir {shlex.quote(str(worktree_path))}"),
                (
                    "xfce4-terminal",
                    f"xfce4-terminal --working-directory={shlex.quote(str(worktree_path))}",
                ),
                ("xterm", f"cd {shlex.quote(str(worktree_path))} && xterm"),
            ]

            for terminal_name, command in terminals_with_commands:
                print(f"{command}")

        print()
        print("=== Debug Information for GitHub Issues ===")
        print(
            "If you'd like to request support for your terminal, please create an issue at:"
        )
        print("https://github.com/irskep/autowt/issues")
        print()
        print("Include this debug information:")

        debug_info = self._collect_debug_info()
        for key, value in debug_info.items():
            if isinstance(value, list):
                print(f"{key}:")
                for item in value:
                    print(f"  - {item}")
            else:
                print(f"{key}: {value}")

        print()
        print("=== End Debug Information ===")
        print()

        # Return True since we successfully provided the user with information
        return True


class TerminalService:
    """Handles terminal switching and session management."""

    def __init__(self, state_service: StateService):
        """Initialize terminal service."""
        self.state_service = state_service
        self.is_macos = platform.system() == "Darwin"
        self.terminal = self._create_terminal_implementation()
        logger.debug(
            f"Terminal service initialized with {type(self.terminal).__name__}"
        )

    def _is_experimental_terminal(self) -> bool:
        """Check if the current terminal is experimental (not fully supported)."""
        # Skip warning for Mock objects during testing
        if (
            hasattr(self.terminal, "_mock_name")
            or type(self.terminal).__name__ == "Mock"
        ):
            return False

        # Skip warning during pytest runs (pytest sets PYTEST_CURRENT_TEST)
        if os.getenv("PYTEST_CURRENT_TEST"):
            return False

        # Fully supported terminals
        fully_supported = (ITerm2Terminal, TerminalAppTerminal)
        return not isinstance(self.terminal, fully_supported)

    def _get_terminal_github_url(self) -> str:
        """Get GitHub URL pointing to the terminal implementation source code."""
        base_url = (
            "https://github.com/irskep/autowt/blob/main/src/autowt/services/terminal.py"
        )

        # Map terminal classes to their approximate line numbers in the source
        terminal_lines = {
            TmuxTerminal: "#L674",
            GnomeTerminalTerminal: "#L812",
            KonsoleTerminal: "#L881",
            XfceTerminalTerminal: "#L945",
            TilixTerminal: "#L1014",
            TerminatorTerminal: "#L1089",
            AlacrittyTerminal: "#L1153",
            KittyTerminal: "#L1198",
            WezTermTerminal: "#L1271",
            HyperTerminal: "#L1343",
            WindowsTerminalTerminal: "#L1395",
            GenericTerminal: "#L1461",
        }

        line_fragment = terminal_lines.get(type(self.terminal), "#L1")
        return f"{base_url}{line_fragment}"

    def _show_experimental_terminal_warning(self) -> bool:
        """Show experimental terminal warning and get user confirmation."""
        terminal_name = type(self.terminal).__name__.replace("Terminal", "")
        github_url = self._get_terminal_github_url()

        print("\n⚠️  Experimental Terminal Support")
        print(
            f"You're using {terminal_name}, which has experimental support in autowt."
        )
        print("This means it may be unstable or have limited functionality.")
        print("")
        print(f"Implementation: {github_url}")
        print("Report issues: https://github.com/irskep/autowt/issues")
        print("")

        return confirm_default_yes("Continue with experimental terminal support?")

    def _create_terminal_implementation(self) -> Terminal:
        """Create the appropriate terminal implementation."""
        # Check for tmux first (works on all platforms)
        if os.getenv("TMUX"):
            logger.debug("Detected tmux environment")
            return TmuxTerminal()

        term_program = os.getenv("TERM_PROGRAM", "")
        logger.debug(f"TERM_PROGRAM: {term_program}")

        # Check for specific terminal programs first
        if term_program == "iTerm.app":
            return ITerm2Terminal()
        elif term_program == "Apple_Terminal":
            return TerminalAppTerminal()
        elif term_program == "WezTerm":
            return WezTermTerminal()
        elif term_program == "Hyper":
            return HyperTerminal()

        # Check for terminal-specific environment variables
        if os.getenv("KITTY_WINDOW_ID"):
            return KittyTerminal()
        if os.getenv("ALACRITTY_SOCKET") or os.getenv("ALACRITTY_LOG"):
            return AlacrittyTerminal()

        # Platform-specific detection
        if platform.system() == "Windows":
            # Check if Windows Terminal is available
            try:
                result = run_command(
                    ["where", "wt"],
                    timeout=5,
                    description="Check for Windows Terminal",
                )
                if result.returncode == 0:
                    return WindowsTerminalTerminal()
            except Exception:
                pass
            return GenericTerminal()

        # Linux/Unix terminal detection
        if not self.is_macos:
            # Check desktop environment for default terminals
            desktop_env = os.getenv("XDG_CURRENT_DESKTOP", "").lower()

            # Try to detect based on available executables
            terminal_checks = [
                ("tilix", TilixTerminal),
                ("terminator", TerminatorTerminal),
                ("kitty", KittyTerminal),
                ("alacritty", AlacrittyTerminal),
                ("wezterm", WezTermTerminal),
                ("konsole", KonsoleTerminal),
                ("gnome-terminal", GnomeTerminalTerminal),
                ("xfce4-terminal", XfceTerminalTerminal),
            ]

            # Prioritize based on desktop environment
            if "gnome" in desktop_env:
                terminal_checks.insert(0, ("gnome-terminal", GnomeTerminalTerminal))
            elif "kde" in desktop_env or "plasma" in desktop_env:
                terminal_checks.insert(0, ("konsole", KonsoleTerminal))
            elif "xfce" in desktop_env:
                terminal_checks.insert(0, ("xfce4-terminal", XfceTerminalTerminal))

            # Check which terminals are available
            for terminal_name, terminal_class in terminal_checks:
                try:
                    result = run_command(
                        ["which", terminal_name],
                        timeout=5,
                        description=f"Check for {terminal_name}",
                    )
                    if result.returncode == 0:
                        logger.debug(
                            f"Found {terminal_name}, using {terminal_class.__name__}"
                        )
                        return terminal_class()
                except Exception:
                    continue

        # Fallback to generic terminal
        return GenericTerminal()

    def get_current_session_id(self) -> str | None:
        """Get the current terminal session ID."""
        return self.terminal.get_current_session_id()

    def _combine_scripts(
        self, session_init_script: str | None, after_init: str | None
    ) -> str | None:
        """Combine init script and after-init command into a single script."""
        scripts = []
        if session_init_script:
            scripts.append(session_init_script)
        if after_init:
            scripts.append(after_init)
        return "; ".join(scripts) if scripts else None

    def switch_to_worktree(
        self,
        worktree_path: Path,
        mode: TerminalMode,
        session_id: str | None = None,
        session_init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        """Switch to a worktree using the specified terminal mode."""
        logger.debug(f"Switching to worktree {worktree_path} with mode {mode}")

        # Force echo mode for testing if environment variable is set
        if os.getenv("AUTOWT_TEST_FORCE_ECHO"):
            mode = TerminalMode.ECHO

        # Check for experimental terminal warning on first use
        if self._is_experimental_terminal():
            if not self.state_service.has_shown_experimental_terminal_warning():
                if not self._show_experimental_terminal_warning():
                    # User declined to continue with experimental terminal
                    return False
                self.state_service.mark_experimental_terminal_warning_shown()

        if mode == TerminalMode.INPLACE:
            return self._change_directory_inplace(
                worktree_path, session_init_script, after_init
            )
        elif mode == TerminalMode.ECHO:
            return self._echo_commands(worktree_path, session_init_script, after_init)
        elif mode == TerminalMode.TAB:
            return self._switch_to_existing_or_new_tab(
                worktree_path,
                session_id,
                session_init_script,
                after_init,
                branch_name,
                auto_confirm,
                ignore_same_session,
            )
        elif mode == TerminalMode.WINDOW:
            return self._switch_to_existing_or_new_window(
                worktree_path,
                session_id,
                session_init_script,
                after_init,
                branch_name,
                auto_confirm,
                ignore_same_session,
            )
        else:
            logger.error(f"Unknown terminal mode: {mode}")
            return False

    def _echo_commands(
        self,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
    ) -> bool:
        """Output shell command to change directory for eval usage."""
        logger.debug(f"Outputting cd command for {worktree_path}")

        try:
            # Output the cd command that the user can evaluate
            # Usage: eval "$(autowt ci --terminal=echo)"
            commands = [f"cd {shlex.quote(str(worktree_path))}"]
            if session_init_script:
                # Handle multi-line scripts by replacing newlines with semicolons
                normalized_script = session_init_script.replace("\n", "; ").strip()
                if normalized_script:
                    commands.append(normalized_script)
            if after_init:
                # Handle multi-line scripts by replacing newlines with semicolons
                normalized_after = after_init.replace("\n", "; ").strip()
                if normalized_after:
                    commands.append(normalized_after)
            print("; ".join(commands))
            return True
        except Exception as e:
            logger.error(f"Failed to output cd command: {e}")
            return False

    def _change_directory_inplace(
        self,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
    ) -> bool:
        """Execute directory change and commands directly in current terminal session."""
        logger.debug(f"Executing cd command in current session for {worktree_path}")

        try:
            # Build command list
            commands = [f"cd {shlex.quote(str(worktree_path))}"]
            if session_init_script:
                commands.append(session_init_script)
            if after_init:
                commands.append(after_init)

            combined_command = "; ".join(commands)

            # Try to execute in current terminal session using osascript
            if hasattr(self.terminal, "execute_in_current_session"):
                return self.terminal.execute_in_current_session(combined_command)
            else:
                # Fallback to echo behavior for unsupported terminals
                logger.warning(
                    "Current terminal doesn't support inplace execution, falling back to echo"
                )
                print(combined_command)
                return True

        except Exception as e:
            logger.error(f"Failed to execute cd command in current session: {e}")
            return False

    def _switch_to_existing_or_new_tab(
        self,
        worktree_path: Path,
        session_id: str | None = None,
        session_init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        """Switch to existing session or create new tab."""
        # If ignore_same_session is True, skip session detection and always create new tab
        if not ignore_same_session:
            # For Terminal.app, use worktree path as session identifier
            # For other terminals (iTerm2, tmux), use provided session_id
            if self.terminal.supports_session_management():
                if isinstance(self.terminal, TerminalAppTerminal):
                    effective_session_id = str(worktree_path)
                else:
                    effective_session_id = session_id

                # First try: Check if the stored session ID exists and is in correct directory
                if effective_session_id and self.terminal.session_exists(
                    effective_session_id
                ):
                    # For iTerm2, verify the session is still in the correct directory
                    if isinstance(self.terminal, ITerm2Terminal):
                        if not self.terminal.session_in_directory(
                            effective_session_id, worktree_path
                        ):
                            logger.debug(
                                f"Session {effective_session_id} no longer in directory {worktree_path}, discarding"
                            )
                            # Skip using this session ID and fall through to create new tab
                        else:
                            if auto_confirm or self._should_switch_to_existing(
                                branch_name
                            ):
                                # Try to switch to existing session (no init script - session already exists)
                                if self.terminal.switch_to_session(
                                    effective_session_id, None
                                ):
                                    print(
                                        f"Switched to existing {branch_name or 'worktree'} session"
                                    )
                                    return True
                    else:
                        # For other terminals, use existing logic
                        if auto_confirm or self._should_switch_to_existing(branch_name):
                            # Try to switch to existing session (no init script - session already exists)
                            if self.terminal.switch_to_session(
                                effective_session_id, None
                            ):
                                print(
                                    f"Switched to existing {branch_name or 'worktree'} session"
                                )
                                return True

                # Second try: For iTerm2, check if there's a session in the worktree directory
                if isinstance(self.terminal, ITerm2Terminal) and hasattr(
                    self.terminal, "find_session_by_working_directory"
                ):
                    fallback_session_id = (
                        self.terminal.find_session_by_working_directory(
                            str(worktree_path)
                        )
                    )
                    if fallback_session_id:
                        logger.debug(
                            f"Found session {fallback_session_id} in directory {worktree_path}"
                        )
                        if auto_confirm or self._should_switch_to_existing(branch_name):
                            if self.terminal.switch_to_session(
                                fallback_session_id, None
                            ):
                                print(
                                    f"Switched to existing {branch_name or 'worktree'} session (found by directory)"
                                )
                                return True

                # Second try: For Terminal.app, always scan for existing tabs in target directory
                elif isinstance(self.terminal, TerminalAppTerminal):
                    # Always scan for tabs in the worktree directory (Terminal.app should use workdir matching every time)
                    logger.debug(
                        f"Scanning Terminal.app tabs for directory: {worktree_path}"
                    )
                    if auto_confirm or self._should_switch_to_existing(branch_name):
                        if self.terminal.switch_to_session(str(worktree_path), None):
                            print(
                                f"Switched to existing {branch_name or 'worktree'} session (found by directory scan)"
                            )
                            return True

        # Fall back to creating new tab (or forced by ignore_same_session)
        combined_script = self._combine_scripts(session_init_script, after_init)
        return self.terminal.open_new_tab(worktree_path, combined_script)

    def _switch_to_existing_or_new_window(
        self,
        worktree_path: Path,
        session_id: str | None = None,
        session_init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        """Switch to existing session or create new window."""
        # If ignore_same_session is True, skip session detection and always create new window
        if not ignore_same_session:
            # For Terminal.app, use worktree path as session identifier
            # For other terminals (iTerm2, tmux), use provided session_id
            if self.terminal.supports_session_management():
                if isinstance(self.terminal, TerminalAppTerminal):
                    effective_session_id = str(worktree_path)
                else:
                    effective_session_id = session_id

                # First try: Check if the stored session ID exists and is in correct directory
                if effective_session_id and self.terminal.session_exists(
                    effective_session_id
                ):
                    # For iTerm2, verify the session is still in the correct directory
                    if isinstance(self.terminal, ITerm2Terminal):
                        if not self.terminal.session_in_directory(
                            effective_session_id, worktree_path
                        ):
                            logger.debug(
                                f"Session {effective_session_id} no longer in directory {worktree_path}, discarding"
                            )
                            # Skip using this session ID and fall through to create new window
                        else:
                            if auto_confirm or self._should_switch_to_existing(
                                branch_name
                            ):
                                # Try to switch to existing session (no init script - session already exists)
                                if self.terminal.switch_to_session(
                                    effective_session_id, None
                                ):
                                    print(
                                        f"Switched to existing {branch_name or 'worktree'} session"
                                    )
                                    return True
                    else:
                        # For other terminals, use existing logic
                        if auto_confirm or self._should_switch_to_existing(branch_name):
                            # Try to switch to existing session (no init script - session already exists)
                            if self.terminal.switch_to_session(
                                effective_session_id, None
                            ):
                                print(
                                    f"Switched to existing {branch_name or 'worktree'} session"
                                )
                                return True

                # Second try: For iTerm2, check if there's a session in the worktree directory
                if isinstance(self.terminal, ITerm2Terminal) and hasattr(
                    self.terminal, "find_session_by_working_directory"
                ):
                    fallback_session_id = (
                        self.terminal.find_session_by_working_directory(
                            str(worktree_path)
                        )
                    )
                    if fallback_session_id:
                        logger.debug(
                            f"Found session {fallback_session_id} in directory {worktree_path}"
                        )
                        if auto_confirm or self._should_switch_to_existing(branch_name):
                            if self.terminal.switch_to_session(
                                fallback_session_id, None
                            ):
                                print(
                                    f"Switched to existing {branch_name or 'worktree'} session (found by directory)"
                                )
                                return True

                # Second try: For Terminal.app, always scan for existing tabs in target directory
                elif isinstance(self.terminal, TerminalAppTerminal):
                    # Always scan for tabs in the worktree directory (Terminal.app should use workdir matching every time)
                    logger.debug(
                        f"Scanning Terminal.app tabs for directory: {worktree_path}"
                    )
                    if auto_confirm or self._should_switch_to_existing(branch_name):
                        if self.terminal.switch_to_session(str(worktree_path), None):
                            print(
                                f"Switched to existing {branch_name or 'worktree'} session (found by directory scan)"
                            )
                            return True

        # Fall back to creating new window (or forced by ignore_same_session)
        combined_script = self._combine_scripts(session_init_script, after_init)
        return self.terminal.open_new_window(worktree_path, combined_script)

    def _should_switch_to_existing(self, branch_name: str | None) -> bool:
        """Ask user if they want to switch to existing session."""
        if branch_name:
            return confirm_default_yes(
                f"{branch_name} already has a session. Switch to it?"
            )
        else:
            return confirm_default_yes("Worktree already has a session. Switch to it?")
