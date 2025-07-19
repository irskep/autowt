"""Live agent monitoring dashboard command."""

import logging

from autowt.console import print_error
from autowt.models import Services
from autowt.tui.agents import AgentDashboard

logger = logging.getLogger(__name__)


def show_agent_dashboard(services: Services) -> dict | None:
    """Show live agent monitoring dashboard."""
    logger.debug("Starting agent dashboard")

    # Find git repository
    repo_path = services.git.find_repo_root()
    if not repo_path:
        print_error("Error: Not in a git repository")
        return None

    # Create and run dashboard
    app = AgentDashboard(services, repo_path)
    return app.run()
