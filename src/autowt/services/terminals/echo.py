import logging
import os
import platform
import shlex
from pathlib import Path

from autowt.utils import run_command

from .base import BaseTerminal

logger = logging.getLogger(__name__)


class EchoTerminal(BaseTerminal):
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
