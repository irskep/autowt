"""Terminal management service for autowt."""

import logging
import os
import platform
import shlex
from pathlib import Path

from autowt.models import TerminalMode
from autowt.prompts import confirm_default_yes
from autowt.services.state import StateService
from autowt.services.terminals.apple import TerminalAppTerminal
from autowt.services.terminals.base import BaseTerminal
from autowt.services.terminals.echo import EchoTerminal
from autowt.services.terminals.ghostty import GhosttyMacTerminal
from autowt.services.terminals.iterm2 import ITerm2Terminal
from autowt.services.terminals.vscode import CursorTerminal, VSCodeTerminal

logger = logging.getLogger(__name__)


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

    def _create_terminal_implementation(self) -> BaseTerminal:
        """Create the appropriate terminal implementation."""
        term_program = os.getenv("TERM_PROGRAM", "")
        logger.debug(f"TERM_PROGRAM: {term_program}")

        # Check for specific terminal programs first
        if term_program == "iTerm.app":
            return ITerm2Terminal()
        elif term_program == "Apple_Terminal":
            return TerminalAppTerminal()
        elif term_program == "vscode":
            # Both VSCode and Cursor set TERM_PROGRAM to "vscode"
            # Check for Cursor-specific environment variable
            if os.getenv("CURSOR_TRACE_ID"):
                return CursorTerminal()
            else:
                return VSCodeTerminal()
        elif term_program == "ghostty" and self.is_macos:
            return GhosttyMacTerminal()

        # Platform-specific detection
        if platform.system() == "Windows":
            return EchoTerminal()

        # Linux/Unix terminal detection
        if not self.is_macos:
            return EchoTerminal()

        # Fallback to generic terminal
        return EchoTerminal()

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
        elif mode == TerminalMode.VSCODE:
            # Force use of VSCodeTerminal regardless of detected terminal
            vscode_terminal = VSCodeTerminal()

            # Try to switch to existing window first on macOS
            if vscode_terminal.supports_session_management():
                if vscode_terminal.switch_to_session(str(worktree_path)):
                    print(
                        f"Switched to existing VSCode window for {branch_name or 'worktree'}"
                    )
                    return True

            # Fall back to opening new window
            combined_script = self._combine_scripts(session_init_script, after_init)
            return vscode_terminal.open_new_window(worktree_path, combined_script)
        elif mode == TerminalMode.CURSOR:
            # Force use of CursorTerminal regardless of detected terminal
            cursor_terminal = CursorTerminal()

            # Try to switch to existing window first on macOS
            if cursor_terminal.supports_session_management():
                if cursor_terminal.switch_to_session(str(worktree_path)):
                    print(
                        f"Switched to existing Cursor window for {branch_name or 'worktree'}"
                    )
                    return True

            # Fall back to opening new window
            combined_script = self._combine_scripts(session_init_script, after_init)
            return cursor_terminal.open_new_window(worktree_path, combined_script)
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
