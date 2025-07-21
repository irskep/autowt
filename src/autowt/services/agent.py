"""Agent monitoring service for Claude Code integration."""

import logging
import subprocess
from pathlib import Path

from autowt.models import AgentStatus, WorktreeInfo, WorktreeWithAgent

logger = logging.getLogger(__name__)


class AgentService:
    """Service for detecting and monitoring Claude Code agents."""

    def _is_claude_process_running(self, directory: Path) -> bool:
        """Check if Claude Code process is running in directory using lsof."""
        try:
            result = subprocess.run(
                ["lsof", "+D", str(directory)],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # lsof can return exit code 1 but still produce valid output
            # Check output regardless of return code if stdout is not empty
            if not result.stdout.strip():
                return False

            # Look for node processes and verify they're actually Claude
            for line in result.stdout.splitlines():
                if "node" in line.lower():
                    # Extract PID from lsof output
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1])
                            # Check if this PID is actually a Claude process
                            ps_result = subprocess.run(
                                ["ps", "-p", str(pid), "-o", "command="],
                                capture_output=True,
                                text=True,
                                timeout=2,
                            )
                            if (
                                ps_result.returncode == 0
                                and "claude" in ps_result.stdout.strip()
                            ):
                                return True
                        except (ValueError, subprocess.TimeoutExpired):
                            continue

            return False

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            # lsof unavailable or failed - can't determine process status
            return False

    def _cleanup_stale_status_file(self, status_file: Path) -> None:
        """Remove a stale status file."""
        try:
            status_file.unlink()
            logger.debug(f"Removed stale status file: {status_file}")
        except OSError:
            # File already gone or permission issue - ignore
            pass

    def detect_agent_status(self, worktree_path: Path) -> AgentStatus | None:
        """Detect Claude Code agent status in a worktree."""
        status_file = worktree_path / ".claude" / "autowt" / "status"
        agent_status = AgentStatus.from_file(status_file)

        if not agent_status:
            return None

        # Verify Claude is actually running
        if self._is_claude_process_running(worktree_path):
            return agent_status

        # Status file exists but no Claude process - clean up stale file
        self._cleanup_stale_status_file(status_file)
        return None

    def enhance_worktrees_with_agent_status(
        self, worktrees: list[WorktreeInfo], state_service, repo_path: Path
    ) -> list[WorktreeWithAgent]:
        """Add agent status to worktree information."""
        enhanced = []

        for worktree in worktrees:
            agent_status = self.detect_agent_status(worktree.path)
            session_id = state_service.get_session_id(repo_path, worktree.branch)
            has_session = session_id is not None

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
