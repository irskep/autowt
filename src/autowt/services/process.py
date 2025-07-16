"""Process management service for autowt."""

import logging
import platform
import time
from pathlib import Path

from autowt.console import print_output, print_plain, print_success
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

        if platform.system() == "Windows":
            logger.info("Windows process discovery not yet supported - skipping")
            return []

        processes = []

        try:
            # Use lsof to find processes with open files in the directory
            result = run_command(
                ["lsof", "+D", str(directory)],
                timeout=30,
                description=f"Find processes in directory {directory}",
            )

            # lsof can return 1 even when it finds results, so check output content
            if result.returncode != 0 and not result.stdout.strip():
                logger.debug("No processes found in directory (no output)")
                return processes
            elif result.returncode not in [0, 1]:
                logger.warning(
                    f"lsof command failed with exit code {result.returncode}: {result.stderr}"
                )
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
        """Terminate the given processes with SIGINT then SIGKILL if needed."""
        if not processes:
            logger.debug("No processes to terminate")
            return True

        if platform.system() == "Windows":
            logger.info("Windows process termination not yet supported - skipping")
            return True

        logger.info(f"Terminating {len(processes)} processes")

        # Send SIGINT to all processes
        for process in processes:
            # Truncate long command lines for display
            command = process.command
            if len(command) > 60:
                command = command[:57] + "..."
            print_output(f"  Sending SIGINT to {command} (PID {process.pid})")
            logger.debug(f"Sending SIGINT to PID {process.pid} ({process.command})")
            try:
                run_command_visible(
                    ["kill", "-INT", str(process.pid)],
                    timeout=5,
                )
            except Exception as e:
                logger.warning(f"Failed to send SIGINT to PID {process.pid}: {e}")

        # Poll for up to 10 seconds to see if processes exit
        logger.debug("Polling for processes to exit (max 10 seconds)")
        max_wait_time = 10
        poll_interval = 0.5
        elapsed = 0

        while elapsed < max_wait_time:
            time.sleep(poll_interval)
            elapsed += poll_interval

            # Check which processes are still running
            still_running = []
            for process in processes:
                if self._is_process_running(process.pid):
                    still_running.append(process)

            # If all processes have exited, we're done
            if not still_running:
                print_success(f"  All processes exited after {elapsed:.1f} seconds")
                logger.info("All processes terminated successfully")
                return True

        # Check which processes are still running and SIGKILL them
        still_running = []
        for process in processes:
            if self._is_process_running(process.pid):
                still_running.append(process)

        if still_running:
            print_output(
                f"  {len(still_running)} processes still running, sending SIGKILL..."
            )
            logger.info(
                f"{len(still_running)} processes still running, sending SIGKILL"
            )

            for process in still_running:
                # Truncate long command lines for display
                command = process.command
                if len(command) > 60:
                    command = command[:57] + "..."
                print_output(f"  Sending SIGKILL to {command} (PID {process.pid})")
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
        if platform.system() == "Windows":
            # On Windows, we skip process discovery so we won't have PIDs to check
            return False

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
            print_plain("No processes found running in worktrees to be deleted.")
            return

        print_output("Shutting down processes operating in worktrees to be deleted...")
        for process in processes:
            # Truncate long command lines for display
            command = process.command
            if len(command) > 60:
                command = command[:57] + "..."

            print_output(f"  {command} {process.pid}")
        print_output("  ...done")
