"""Data models for autowt state and configuration."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class TerminalMode(Enum):
    """Terminal switching modes."""

    TAB = "tab"
    WINDOW = "window"
    INPLACE = "inplace"


class CleanupMode(Enum):
    """Cleanup selection modes."""

    ALL = "all"
    REMOTELESS = "remoteless"
    MERGED = "merged"
    INTERACTIVE = "interactive"


@dataclass
class WorktreeInfo:
    """Information about a single worktree."""

    branch: str
    path: Path
    is_current: bool = False
    is_primary: bool = False
    session_id: str | None = None


@dataclass
class BranchStatus:
    """Status information for cleanup decisions."""

    branch: str
    has_remote: bool
    is_merged: bool
    is_identical: bool  # True if branch has no unique commits vs main
    path: Path


@dataclass
class Configuration:
    """Application configuration."""

    terminal: TerminalMode = TerminalMode.TAB
    terminal_always_new: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "Configuration":
        """Create configuration from dictionary."""
        return cls(
            terminal=TerminalMode(data.get("terminal", "tab")),
            terminal_always_new=data.get("terminal_always_new", False),
        )

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "terminal": self.terminal.value,
            "terminal_always_new": self.terminal_always_new,
        }


@dataclass
class ProjectConfig:
    """Project-specific configuration."""

    init: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectConfig":
        """Create project configuration from dictionary."""
        return cls(
            init=data.get("init"),
        )

    def to_dict(self) -> dict:
        """Convert project configuration to dictionary."""
        return {
            "init": self.init,
        }


@dataclass
class ApplicationState:
    """Main application state."""

    primary_clone: Path
    worktrees: list[WorktreeInfo]
    current_worktree: str | None = None

    @classmethod
    def from_dict(cls, data: dict, primary_clone: Path) -> "ApplicationState":
        """Create state from dictionary."""
        worktrees = []
        for wt_data in data.get("worktrees", []):
            worktrees.append(
                WorktreeInfo(
                    branch=wt_data["branch"],
                    path=Path(wt_data["path"]),
                    is_current=wt_data.get("is_current", False),
                    session_id=wt_data.get("session_id"),
                )
            )

        return cls(
            primary_clone=primary_clone,
            worktrees=worktrees,
            current_worktree=data.get("current_worktree"),
        )

    def to_dict(self) -> dict:
        """Convert state to dictionary."""
        return {
            "current_worktree": self.current_worktree,
            "worktrees": [
                {
                    "branch": wt.branch,
                    "path": str(wt.path),
                    "is_current": wt.is_current,
                    "session_id": wt.session_id,
                }
                for wt in self.worktrees
            ],
        }


@dataclass
class ProcessInfo:
    """Information about a running process."""

    pid: int
    command: str
    working_dir: Path
