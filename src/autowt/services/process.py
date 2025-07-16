"""Process management service for autowt."""

import logging
import time
from pathlib import Path

from autowt.models import ProcessInfo
from autowt.utils import run_command, run_command_visible

logger = logging.getLogger(__name__)


class ProcessService:
    """Handles process discovery and termination for cleanup operations."""

    def __init__(self):
        """Initialize process service."""
        logger.debug("Process service initialized")

    def find_processes_in_directory(self, directory: Path) -> list[ProcessInfo]:
        """Find all processes running in the specified directory."""
        logger.debug(f"Finding processes in directory: {directory}")

        processes = []

        try:
            # Use lsof to find processes with open files in the directory
            result = run_command(
                ["lsof", "+D", str(directory)],
                timeout=30,
                description=f"Find processes in directory {directory}",
            )

            if result.returncode != 0:
                # lsof returns 1 if no files found, which is normal
                if result.returncode == 1:
                    logger.debug("No processes found in directory")
                else:
                    logger.warning(f"lsof command failed: {result.stderr}")
                return processes

            # Parse lsof output
            lines = result.stdout.strip().split("\n")
            if len(lines) < 2:  # Header line + at least one process
                return processes

            # Skip header line
            for line in lines[1:]:
                try:
                    parts = line.split()
                    if len(parts) >= 2:
                        command = parts[0]
                        pid = int(parts[1])

                        # Get more detailed process info
                        process_info = self._get_process_details(
                            pid, command, directory
                        )
                        if process_info:
                            processes.append(process_info)

                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse lsof line: {line}, error: {e}")
                    continue

            logger.debug(f"Found {len(processes)} processes in directory")

        except Exception as e:
            logger.error(f"Failed to find processes: {e}")

        return processes

    def _get_process_details(
        self, pid: int, command: str, working_dir: Path
    ) -> ProcessInfo:
        """Get detailed information about a process."""
        try:
            # Get the full command line
            result = run_command(
                ["ps", "-p", str(pid), "-o", "command="],
                timeout=10,
                description=f"Get command details for PID {pid}",
            )

            if result.returncode == 0:
                full_command = result.stdout.strip()
            else:
                full_command = command

            return ProcessInfo(
                pid=pid,
                command=full_command,
                working_dir=working_dir,
            )

        except Exception as e:
            logger.debug(f"Failed to get process details for PID {pid}: {e}")
            return ProcessInfo(
                pid=pid,
                command=command,
                working_dir=working_dir,
            )

    def terminate_processes(self, processes: list[ProcessInfo]) -> bool:
        """Terminate the given processes with SIGINT then SIGKILL after 10 seconds."""
        if not processes:
            logger.debug("No processes to terminate")
            return True

        logger.info(f"Terminating {len(processes)} processes")

        # Send SIGINT to all processes
        for process in processes:
            logger.debug(f"Sending SIGINT to PID {process.pid} ({process.command})")
            try:
                run_command_visible(
                    ["kill", "-INT", str(process.pid)],
                    timeout=5,
                )
            except Exception as e:
                logger.warning(f"Failed to send SIGINT to PID {process.pid}: {e}")

        # Wait 10 seconds
        logger.debug("Waiting 10 seconds before SIGKILL")
        time.sleep(10)

        # Check which processes are still running and SIGKILL them
        still_running = []
        for process in processes:
            if self._is_process_running(process.pid):
                still_running.append(process)

        if still_running:
            logger.info(
                f"{len(still_running)} processes still running, sending SIGKILL"
            )

            for process in still_running:
                logger.debug(
                    f"Sending SIGKILL to PID {process.pid} ({process.command})"
                )
                try:
                    run_command_visible(
                        ["kill", "-KILL", str(process.pid)],
                        timeout=5,
                    )
                except Exception as e:
                    logger.warning(f"Failed to send SIGKILL to PID {process.pid}: {e}")

        # Give a moment for processes to die
        time.sleep(1)

        # Check if any processes are still running
        final_survivors = []
        for process in processes:
            if self._is_process_running(process.pid):
                final_survivors.append(process)

        if final_survivors:
            logger.error(f"{len(final_survivors)} processes could not be terminated:")
            for process in final_survivors:
                logger.error(f"  PID {process.pid}: {process.command}")
            return False

        logger.info("All processes terminated successfully")
        return True

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is still running."""
        try:
            result = run_command(
                ["ps", "-p", str(pid)],
                timeout=10,
                description=f"Check if PID {pid} is running",
            )
            return result.returncode == 0
        except Exception:
            return False

    def print_process_summary(self, processes: list[ProcessInfo]) -> None:
        """Print a summary of processes that will be terminated."""
        if not processes:
            print("No processes found running in worktrees to be deleted.")
            return

        print("Shutting down processes operating in worktrees to be deleted...")
        for process in processes:
            # Truncate long command lines for display
            command = process.command
            if len(command) > 60:
                command = command[:57] + "..."

            print(f"  {command} {process.pid}")
        print("  ...done")
