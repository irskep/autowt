"""Tests for version checking service."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

from autowt.services.version_check import VersionCheckService, VersionInfo


class TestVersionCheckService:
    """Tests for VersionCheckService core functionality."""

    @patch("autowt.services.version_check.urlopen")
    @patch("autowt.services.version_check.version")
    def test_check_for_updates_with_update_available(self, mock_version, mock_urlopen):
        """Test the main update check flow when update is available."""
        # Mock current version and PyPI response
        mock_version.return_value = "0.4.1"
        mock_response = Mock()
        mock_response.read.return_value = b'{"info": {"version": "0.4.2"}}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            service = VersionCheckService(Path(temp_dir))
            result = service.check_for_updates(force=True)

            assert isinstance(result, VersionInfo)
            assert result.current == "0.4.1"
            assert result.latest == "0.4.2"
            assert result.update_available is True
            assert result.install_command is not None

    @patch("autowt.services.version_check.urlopen")
    @patch("autowt.services.version_check.version")
    def test_check_for_updates_no_update_needed(self, mock_version, mock_urlopen):
        """Test when no update is needed."""
        mock_version.return_value = "0.4.2"
        mock_response = Mock()
        mock_response.read.return_value = b'{"info": {"version": "0.4.2"}}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            service = VersionCheckService(Path(temp_dir))
            result = service.check_for_updates(force=True)

            assert result.update_available is False

    def test_rate_limiting_prevents_frequent_checks(self):
        """Test that rate limiting works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = VersionCheckService(Path(temp_dir))

            # Set recent check time
            recent_time = datetime.now() - timedelta(minutes=30)
            cache = {"last_check_time": recent_time.isoformat()}
            service._save_cache(cache)

            # Should be rate limited
            result = service.check_for_updates(force=False)
            assert result is None

    def test_installation_method_detection_basics(self):
        """Test that installation method detection works for common cases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test UV detection with uv.lock
            cwd = Path(temp_dir)
            uv_lock = cwd / "uv.lock"
            uv_lock.write_text("# uv lock file")

            service = VersionCheckService(Path(temp_dir) / "app")

            with patch("pathlib.Path.cwd", return_value=cwd):
                result = service._detect_installation_method()
                assert result.name == "uv"
                assert "uv add --upgrade" in result.command

            # Test Poetry detection with poetry.lock
            uv_lock.unlink()  # Remove uv.lock to test poetry
            poetry_lock = cwd / "poetry.lock"
            poetry_lock.write_text("# poetry lock file")

            with patch("pathlib.Path.cwd", return_value=cwd):
                result = service._detect_installation_method()
                assert result.name == "poetry"
                assert "poetry update" in result.command

    @patch("autowt.services.version_check.urlopen")
    def test_network_failure_handling(self, mock_urlopen):
        """Test graceful handling of network failures."""
        mock_urlopen.side_effect = URLError("Network error")

        with tempfile.TemporaryDirectory() as temp_dir:
            service = VersionCheckService(Path(temp_dir))
            result = service.check_for_updates(force=True)

            assert result is None  # Should return None on network failure
