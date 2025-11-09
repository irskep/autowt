"""List worktrees command."""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from autowt.console import console, print_error, print_plain, print_section
from autowt.models import Services

logger = logging.getLogger(__name__)


@dataclass
class WorktreeSegments:
    """Segments for formatting a worktree display line."""

    left: str  # Current indicator + path
    middle: str  # Session indicators
    main_indicator: str  # "(main worktree)" with styling
    right: str  # Branch + current indicator


def _format_worktree_line(worktree, current_worktree_path, terminal_width: int) -> str:
    """Format a single worktree line with proper spacing and alignment."""
    # Build display path
    try:
        relative_path = worktree.path.relative_to(Path.home())
        display_path = f"~/{relative_path}"
    except ValueError:
        display_path = str(worktree.path)

    # Build segments
    segments = _build_worktree_segments(worktree, display_path, current_worktree_path)

    # Combine segments with intelligent spacing
    return _combine_segments(segments, terminal_width)


def _build_worktree_segments(
    worktree, display_path: str, current_worktree_path
) -> WorktreeSegments:
    """Build the individual segments for a worktree line."""
    # Left segment: current indicator + path
    current_indicator = "→ " if current_worktree_path == worktree.path else "  "
    left = f"{current_indicator}{display_path}"

    # Middle segment: removed (session tracking no longer supported)
    middle = ""

    # Main worktree indicator (styled)
    main_indicator = (
        "[dim grey50] (main worktree)[/dim grey50]" if worktree.is_primary else ""
    )

    # Right segment: branch + current indicator + padding for alignment
    branch_indicator = " ←" if current_worktree_path == worktree.path else ""
    padding = "" if current_worktree_path == worktree.path else "  "
    right = f"{worktree.branch}{branch_indicator}{padding}"

    return WorktreeSegments(
        left=left, middle=middle, main_indicator=main_indicator, right=right
    )


def _combine_segments(segments: WorktreeSegments, terminal_width: int) -> str:
    """Combine worktree segments with intelligent spacing."""
    # Calculate content length (without styling tags for main indicator)
    main_indicator_text = (
        " (main worktree)" if "main worktree" in segments.main_indicator else ""
    )
    content_length = (
        len(segments.left)
        + len(segments.middle)
        + len(main_indicator_text)
        + len(segments.right)
    )

    # Determine spacing
    min_spacing = 2  # Minimum space between left content and right branch

    if content_length + min_spacing <= terminal_width:
        # We have room - distribute remaining space
        padding = terminal_width - content_length
        return f"{segments.left}{segments.middle}{segments.main_indicator}{' ' * padding}{segments.right}"
    else:
        # Tight fit - use minimal spacing
        return f"{segments.left}{segments.middle}{segments.main_indicator}  {segments.right}"


def list_worktrees(services: Services, debug: bool = False) -> None:
    """List all worktrees and their status."""
    logger.debug("Listing worktrees")

    # Find git repository
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return

    # Get current directory to determine which worktree we're in
    current_path = Path.cwd()

    # Get worktrees from git
    worktrees = services.git.list_worktrees(repo_path)

    # Show debug information about paths if requested
    if debug:
        print_section("  Debug Information:")
        print_plain(f"    State directory: {services.state.app_dir}")
        print_plain(f"    State file: {services.state.state_file}")
        print_plain(f"    Config file: {services.state.config_file}")
        print_plain(f"    Git repository root: {repo_path}")

        # Check for project config files
        current_dir = Path.cwd()
        project_config_files = [
            current_dir / "autowt.toml",
            current_dir / ".autowt.toml",
        ]
        for config_file in project_config_files:
            if config_file.exists():
                print_plain(f"    Project config: {config_file}")

        print_plain("")

    # Determine which worktree we're currently in
    current_worktree_path = None
    for worktree in worktrees:
        try:
            if current_path.is_relative_to(worktree.path):
                current_worktree_path = worktree.path
                break
        except ValueError:
            # is_relative_to raises ValueError if not relative
            continue

    if not worktrees:
        print_plain("  No worktrees found.")
        return

    print_section("  Worktrees:")

    # Sort worktrees: primary first, then by branch name
    sorted_worktrees = sorted(worktrees, key=lambda w: (not w.is_primary, w.branch))

    # Calculate the maximum terminal width to align branch names
    terminal_width = 80  # Default fallback
    try:
        terminal_width = shutil.get_terminal_size().columns
    except OSError:
        pass

    for worktree in sorted_worktrees:
        line = _format_worktree_line(worktree, current_worktree_path, terminal_width)
        if worktree.is_primary and "[dim grey50]" in line:
            console.print(line)
        else:
            print_plain(line)

    print_plain("")
    print_plain("Use 'autowt <branch>' to switch to a worktree or create a new one.")
