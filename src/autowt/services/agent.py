"""Agent monitoring service for Claude Code integration."""

import logging
from pathlib import Path

from autowt.models import AgentStatus, WorktreeInfo, WorktreeWithAgent

logger = logging.getLogger(__name__)


class AgentService:
    """Service for detecting and monitoring Claude Code agents."""

    def detect_agent_status(self, worktree_path: Path) -> AgentStatus | None:
        """Detect Claude Code agent status in a worktree."""
        status_file = worktree_path / ".claude" / "autowt" / "status"
        return AgentStatus.from_file(status_file)

    def enhance_worktrees_with_agent_status(
        self, worktrees: list[WorktreeInfo], session_ids: dict[str, str]
    ) -> list[WorktreeWithAgent]:
        """Add agent status to worktree information."""
        enhanced = []

        for worktree in worktrees:
            agent_status = self.detect_agent_status(worktree.path)
            has_session = worktree.branch in session_ids

            enhanced.append(
                WorktreeWithAgent(
                    branch=worktree.branch,
                    path=worktree.path,
                    is_current=worktree.is_current,
                    is_primary=worktree.is_primary,
                    agent_status=agent_status,
                    has_active_session=has_session,
                )
            )

        return enhanced

    def find_waiting_agents(
        self, enhanced_worktrees: list[WorktreeWithAgent]
    ) -> list[WorktreeWithAgent]:
        """Find worktrees with agents waiting for input."""
        waiting = []
        for wt in enhanced_worktrees:
            if wt.agent_status and wt.agent_status.status == "waiting":
                waiting.append(wt)

        # Sort by last activity (oldest first)
        return sorted(waiting, key=lambda w: w.agent_status.last_activity)

    def find_latest_active_agent(
        self, enhanced_worktrees: list[WorktreeWithAgent]
    ) -> WorktreeWithAgent | None:
        """Find the most recently active agent."""
        active_agents = [
            wt
            for wt in enhanced_worktrees
            if wt.agent_status
            and wt.agent_status.status in ["working", "idle", "waiting"]
        ]

        if not active_agents:
            return None

        # Sort by last activity (newest first)
        return sorted(
            active_agents, key=lambda w: w.agent_status.last_activity, reverse=True
        )[0]
