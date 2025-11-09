"""Terminal management service for autowt."""

import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from automate_terminal import (
    TerminalNotFoundError,
    check,
    list_sessions,
    new_tab,
    new_window,
    run_in_active_session,
    switch_to_session,
)

from autowt.models import TerminalMode
from autowt.prompts import confirm_default_yes
from autowt.services.state import StateService

logger = logging.getLogger(__name__)


class TerminalService:
    """Handles terminal switching and session management."""

    def __init__(self, state_service: StateService):
        """Initialize terminal service."""
        self.state_service = state_service
        self._capabilities = None

    def _get_capabilities(self):
        """Get terminal capabilities, cached."""
        if self._capabilities is None:
            try:
                self._capabilities = check(debug=False)
            except TerminalNotFoundError:
                self._capabilities = {"capabilities": {}}
        return self._capabilities

    def switch_to_worktree(
        self,
        worktree_path: Path,
        mode: TerminalMode,
        session_init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        """Switch to a worktree using the specified terminal mode.

        Args:
            worktree_path: Path to the worktree directory
            mode: Terminal mode (TAB, WINDOW, INPLACE, ECHO)
            session_init_script: Script to run when creating new session
            after_init: Additional script to run after init
            branch_name: Branch name for display purposes
            auto_confirm: Skip user confirmation prompts
            ignore_same_session: Force new tab/window even if session exists
        """
        logger.debug(f"Switching to worktree {worktree_path} with mode {mode}")

        # Force echo mode for testing if environment variable is set
        if os.getenv("AUTOWT_TEST_FORCE_ECHO"):
            mode = TerminalMode.ECHO

        if mode == TerminalMode.ECHO:
            return self._echo_commands(worktree_path, session_init_script, after_init)
        elif mode == TerminalMode.INPLACE:
            return self._inplace_commands(
                worktree_path, session_init_script, after_init
            )
        elif mode == TerminalMode.TAB:
            return self._tab_mode(
                worktree_path,
                session_init_script,
                after_init,
                branch_name,
                auto_confirm,
                ignore_same_session,
            )
        elif mode == TerminalMode.WINDOW:
            return self._window_mode(
                worktree_path,
                session_init_script,
                after_init,
                branch_name,
                auto_confirm,
                ignore_same_session,
            )
        elif mode == TerminalMode.VSCODE:
            return self._vscode_mode(
                worktree_path,
                session_init_script,
                after_init,
                branch_name,
                auto_confirm,
                ignore_same_session,
            )
        elif mode == TerminalMode.CURSOR:
            return self._cursor_mode(
                worktree_path,
                session_init_script,
                after_init,
                branch_name,
                auto_confirm,
                ignore_same_session,
            )
        else:
            logger.error(f"Unknown terminal mode: {mode}")
            return False

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

    def _echo_commands(
        self,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
    ) -> bool:
        """Output shell command to change directory for eval usage."""
        logger.debug(f"Outputting cd command for {worktree_path}")

        try:
            commands = [f"cd {shlex.quote(str(worktree_path))}"]
            if session_init_script:
                normalized_script = session_init_script.replace("\n", "; ").strip()
                if normalized_script:
                    commands.append(normalized_script)
            if after_init:
                normalized_after = after_init.replace("\n", "; ").strip()
                if normalized_after:
                    commands.append(normalized_after)
            print("; ".join(commands))
            return True
        except Exception as e:
            logger.error(f"Failed to output cd command: {e}")
            return False

    def _inplace_commands(
        self,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
    ) -> bool:
        """Execute directory change and commands in current terminal session.

        Note: session_init runs in the current session for INPLACE mode. This is correct
        for current use cases (e.g., launching `claude`, activating venvs), but if we add
        a hook like `post_create_async` that runs in the original session after switch,
        we'll need to carefully consider the interaction with session_init in INPLACE mode.
        """
        logger.debug(f"Executing cd command in current session for {worktree_path}")

        commands = [f"cd {shlex.quote(str(worktree_path))}"]
        if session_init_script:
            commands.append(session_init_script)
        if after_init:
            commands.append(after_init)

        combined_command = "; ".join(commands)

        if run_script_inplace(combined_command):
            return True
        else:
            # Fallback to echo if inplace fails
            logger.warning("Inplace execution failed, falling back to echo")
            print(combined_command)
            return True

    def _find_existing_session(self, worktree_path: Path) -> bool:
        """Check if a session exists at the given worktree path using list_sessions."""
        try:
            sessions = list_sessions(debug=False)
            target_path = str(worktree_path.resolve())

            for session in sessions:
                session_path = session.get("working_directory", "")
                # Check if session is in the target directory
                if session_path == target_path or session_path.startswith(
                    target_path + "/"
                ):
                    return True

            return False
        except Exception as e:
            logger.debug(f"Failed to list sessions: {e}")
            return False

    def _tab_mode(
        self,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        """Switch to or create tab."""
        caps = self._get_capabilities()

        if not caps.get("capabilities", {}).get("can_create_tabs"):
            logger.warning("Terminal doesn't support tabs, falling back to echo")
            return self._echo_commands(worktree_path, session_init_script, after_init)

        # Check if paste scripts will work
        can_paste = caps.get("capabilities", {}).get("can_paste_commands", False)
        combined_script = self._combine_scripts(session_init_script, after_init)

        if combined_script and not can_paste:
            print(
                f"Warning: {caps.get('terminal', 'Your terminal')} cannot execute paste scripts."
            )
            print("You will need to run these commands manually:")
            print(f"  {combined_script}")

        # Try to switch to existing session first (unless ignore_same_session)
        if not ignore_same_session:
            if caps.get("capabilities", {}).get("can_switch_to_session"):
                # Check if session exists BEFORE asking
                if self._find_existing_session(worktree_path):
                    # Ask user if they want to switch
                    if auto_confirm or self._should_switch_to_existing(branch_name):
                        try:
                            if switch_to_session(working_directory=str(worktree_path)):
                                print(
                                    f"Switched to existing {branch_name or 'worktree'} session"
                                )
                                return True
                        except Exception as e:
                            logger.debug(f"Switch to session failed: {e}")

        # Create new tab
        try:
            success = new_tab(
                working_directory=str(worktree_path),
                paste_script=combined_script,
            )

            if success:
                return True
            else:
                logger.error("Failed to create new tab")
                return False

        except Exception as e:
            logger.error(f"Failed to create tab: {e}")
            # Fall back to echo
            return self._echo_commands(worktree_path, session_init_script, after_init)

    def _window_mode(
        self,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        """Switch to or create window."""
        caps = self._get_capabilities()

        if not caps.get("capabilities", {}).get("can_create_windows"):
            logger.warning("Terminal doesn't support windows, falling back to echo")
            return self._echo_commands(worktree_path, session_init_script, after_init)

        # Check if paste scripts will work
        can_paste = caps.get("capabilities", {}).get("can_paste_commands", False)
        combined_script = self._combine_scripts(session_init_script, after_init)

        if combined_script and not can_paste:
            print(
                f"Warning: {caps.get('terminal', 'Your terminal')} cannot execute paste scripts."
            )
            print("You will need to run these commands manually:")
            print(f"  {combined_script}")

        # Try to switch to existing session first (unless ignore_same_session)
        if not ignore_same_session:
            if caps.get("capabilities", {}).get("can_switch_to_session"):
                # Check if session exists BEFORE asking
                if self._find_existing_session(worktree_path):
                    # Ask user if they want to switch
                    if auto_confirm or self._should_switch_to_existing(branch_name):
                        try:
                            if switch_to_session(working_directory=str(worktree_path)):
                                print(
                                    f"Switched to existing {branch_name or 'worktree'} session"
                                )
                                return True
                        except Exception as e:
                            logger.debug(f"Switch to session failed: {e}")

        # Create new window
        try:
            success = new_window(
                working_directory=str(worktree_path),
                paste_script=combined_script,
            )

            if success:
                return True
            else:
                logger.error("Failed to create new window")
                return False

        except Exception as e:
            logger.error(f"Failed to create window: {e}")
            # Fall back to echo
            return self._echo_commands(worktree_path, session_init_script, after_init)

    def _should_switch_to_existing(self, branch_name: str | None) -> bool:
        """Ask user if they want to switch to existing session."""
        if branch_name:
            return confirm_default_yes(
                f"{branch_name} already has a session. Switch to it?"
            )
        else:
            return confirm_default_yes("Worktree already has a session. Switch to it?")

    def _vscode_mode(
        self,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        """Open in VSCode (idempotent)."""
        return self._open_in_editor(
            "code", "VSCode", worktree_path, session_init_script, after_init
        )

    def _cursor_mode(
        self,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
        branch_name: str | None = None,
        auto_confirm: bool = False,
        ignore_same_session: bool = False,
    ) -> bool:
        """Open in Cursor (idempotent)."""
        return self._open_in_editor(
            "cursor", "Cursor", worktree_path, session_init_script, after_init
        )

    def _open_in_editor(
        self,
        cli_command: str,
        editor_name: str,
        worktree_path: Path,
        session_init_script: str | None = None,
        after_init: str | None = None,
    ) -> bool:
        """Open path in editor CLI (idempotent)."""
        if not shutil.which(cli_command):
            logger.error(f"{editor_name} CLI '{cli_command}' not found in PATH")
            return self._echo_commands(worktree_path, session_init_script, after_init)

        combined_script = self._combine_scripts(session_init_script, after_init)
        if combined_script:
            print(f"Warning: {editor_name} cannot execute initialization scripts.")
            print("You will need to run these commands manually:")
            print(f"  {combined_script}")

        try:
            result = subprocess.run(
                [cli_command, str(worktree_path)],
                timeout=10,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to open {editor_name}: {e}")
            return False


def run_script_inplace(command: str) -> bool:
    """Execute command in current terminal session.

    Uses automate-terminal's run_in_active_session API.
    Falls back to False if unsupported.

    Args:
        command: Shell command to execute

    Returns:
        True if executed successfully, False if unsupported/failed
    """
    try:
        return run_in_active_session(command, debug=False)
    except TerminalNotFoundError:
        # Terminal doesn't support running commands in active session
        logger.debug("Terminal doesn't support run_in_active_session")
        return False
    except Exception as e:
        logger.error(f"Failed to execute inplace command: {e}")
        return False
