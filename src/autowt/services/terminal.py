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
        self, session_id: str, init_script: str | None = None
    ) -> bool:
        """Switch to existing Terminal.app session by working directory."""
        logger.debug(f"Searching for Terminal.app tab in directory: {session_id}")

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
                                select theTab
                                set frontmost of theWindow to true
                                set index of theWindow to 1'''

        if init_script:
            applescript += f'''
                                do script "{self._escape_for_applescript(init_script)}" in theTab'''

        applescript += """
                                return true
                            end if
                        end if
                    end try
                end repeat
            end repeat
            return false
        end tell
        """

        return self._run_applescript(applescript)

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
        self, session_id: str, init_script: str | None = None
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
            if success and init_script:
                run_command(
                    ["tmux", "send-keys", "-t", session_id, init_script, "Enter"],
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
        from autowt.utils import sanitize_branch_name

        return f"autowt-{sanitize_branch_name(worktree_path.name)}"

    def open_new_tab(self, worktree_path: Path, init_script: str | None = None) -> bool:
        """Create new tmux window (tmux equivalent of tab)."""
        return self.open_new_window(worktree_path, init_script)

    def open_new_window(
        self, worktree_path: Path, init_script: str | None = None
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
                    return self.switch_to_session(session_name, init_script)
                return False
            else:
                # Not in tmux, can attach directly
                result = run_command(
                    cmd,
                    timeout=10,
                    description=f"Create/attach tmux session {session_name}",
                )

                if result.returncode == 0 and init_script:
                    run_command(
                        ["tmux", "send-keys", init_script, "Enter"],
                        timeout=5,
                        description="Send init script to new tmux session",
                    )

                return result.returncode == 0

        except Exception as e:
            logger.error(f"Failed to create tmux session: {e}")
            return False


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
        # Check for tmux first (works on all platforms)
        if os.getenv("TMUX"):
            logger.debug("Detected tmux environment")
            return TmuxTerminal()

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
        # For Terminal.app, use worktree path as session identifier
        # For other terminals (iTerm2, tmux), use provided session_id
        if self.terminal.supports_session_management():
            if isinstance(self.terminal, TerminalAppTerminal):
                effective_session_id = str(worktree_path)
            else:
                effective_session_id = session_id

            if effective_session_id:
                if auto_confirm or self._should_switch_to_existing(branch_name):
                    # Try to switch to existing session
                    if self.terminal.switch_to_session(
                        effective_session_id, init_script
                    ):
                        print(
                            f"Switched to existing {branch_name or 'worktree'} session"
                        )
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
        # For Terminal.app, use worktree path as session identifier
        # For other terminals (iTerm2, tmux), use provided session_id
        if self.terminal.supports_session_management():
            if isinstance(self.terminal, TerminalAppTerminal):
                effective_session_id = str(worktree_path)
            else:
                effective_session_id = session_id

            if effective_session_id:
                if auto_confirm or self._should_switch_to_existing(branch_name):
                    # Try to switch to existing session
                    if self.terminal.switch_to_session(
                        effective_session_id, init_script
                    ):
                        print(
                            f"Switched to existing {branch_name or 'worktree'} session"
                        )
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
