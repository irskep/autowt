"""Initialize autowt in a git repository."""

import logging

from autowt.models import Services

logger = logging.getLogger(__name__)


def init_autowt(services: Services) -> None:
    """Initialize autowt in the current git repository."""
    logger.debug("Initializing autowt")

    # Find git repository
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print("Error: Not in a git repository")
        return

    print(f"Initializing autowt in {repo_path}")

    # Create initial state
    try:
        state = services.state.load_state(repo_path)
        services.state.save_state(state)
        print("✓ State file initialized")
    except Exception as e:
        logger.error(f"Failed to initialize state: {e}")
        print("✗ Failed to initialize state file")
        return

    print("\nAutowt initialization complete!")
    print("You can now use 'autowt <branch>' to create and switch between worktrees.")
