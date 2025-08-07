"""Tests for ProcessService."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from autowt.models import ProcessInfo
from autowt.services.process import ProcessService


class TestProcessService:
    """Tests for ProcessService functionality."""

    @pytest.fixture
    def process_service(self):
        """Create a ProcessService instance."""
        return ProcessService()

    def test_initialization(self, process_service):
        """Test ProcessService initializes correctly."""
        assert process_service is not None

    def test_shell_filtering(self, process_service):
        """Test that only known shells are considered."""
        test_cases = [
            ("zsh", True),
            ("bash", True),
            ("sh", True),
            ("fish", True),
            ("/bin/zsh", True),
            ("/usr/local/bin/fish", True),
            ("python", False),
            ("node", False),
            ("code", False),
            ("vim", False),
        ]

        for command, expected in test_cases:
            result = process_service._is_known_shell(command)
            assert result == expected, f"Failed for command: {command}"

    def test_simple_process_discovery(self, process_service):
        """Test that find_processes_in_directory returns shells directly."""
        with patch("autowt.services.process.run_command") as mock_run:
            # Mock lsof output with shell and non-shell processes
            mock_run.return_value = Mock(
                returncode=0,
                stdout="COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\nzsh     123 user  cwd  DIR  259,2     4096 12345 /test/dir\nnode    456 user    3r REG  259,2     1024 67890 /test/dir/file.js\nfish    789 user  cwd  DIR  259,2     4096 12345 /test/dir",
            )

            processes = process_service.find_processes_in_directory(Path("/test/dir"))

            # Should only return shell processes
            assert len(processes) == 2
            shell_commands = [p.command for p in processes]
            assert "zsh" in shell_commands
            assert "fish" in shell_commands
            assert "node" not in shell_commands

    def test_no_processes_found(self, process_service):
        """Test behavior when no processes are found."""
        with patch("autowt.services.process.run_command") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="")

            processes = process_service.find_processes_in_directory(Path("/empty/dir"))
            assert processes == []

    def test_process_summary_display(self, process_service):
        """Test process summary doesn't crash."""
        processes = [
            ProcessInfo(pid=12345, command="node server.js", working_dir=Path("/test")),
        ]

        # Should not raise an exception
        try:
            process_service.print_process_summary(processes)
            process_service.print_process_summary([])  # Empty list
        except Exception as e:
            pytest.fail(f"print_process_summary raised an exception: {e}")

    def test_error_handling(self, process_service):
        """Test graceful error handling."""
        with patch("autowt.services.process.run_command") as mock_run:
            # Simulate command failure
            mock_run.side_effect = Exception("Command failed")

            # Should not raise exception
            processes = process_service.find_processes_in_directory(Path("/tmp"))
            assert processes == []

    def test_windows_support(self, process_service):
        """Test Windows returns empty list."""
        with patch("autowt.services.process.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"

            processes = process_service.find_processes_in_directory(Path("/tmp"))
            assert processes == []
