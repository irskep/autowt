"""Tests for cleanup mode first-run prompt functionality."""

from unittest.mock import patch

from autowt.config import CleanupMode, ConfigLoader
from autowt.prompts import prompt_cleanup_mode_selection


class TestCleanupFirstRun:
    """Tests for cleanup mode first-run prompt."""

    def test_has_user_configured_cleanup_mode_no_config_file(self, tmp_path):
        """Test that has_user_configured_cleanup_mode returns False when no config exists."""
        config_loader = ConfigLoader(app_dir=tmp_path)
        assert config_loader.has_user_configured_cleanup_mode() is False

    def test_has_user_configured_cleanup_mode_empty_config(self, tmp_path):
        """Test that has_user_configured_cleanup_mode returns False with empty config."""
        config_loader = ConfigLoader(app_dir=tmp_path)
        config_file = tmp_path / "config.toml"
        config_file.write_text("")
        assert config_loader.has_user_configured_cleanup_mode() is False

    def test_has_user_configured_cleanup_mode_with_cleanup_mode(self, tmp_path):
        """Test that has_user_configured_cleanup_mode returns True when mode is configured."""
        config_loader = ConfigLoader(app_dir=tmp_path)
        config_file = tmp_path / "config.toml"
        config_file.write_text('[cleanup]\ndefault_mode = "merged"')
        assert config_loader.has_user_configured_cleanup_mode() is True

    def test_save_cleanup_mode_creates_new_config(self, tmp_path):
        """Test that save_cleanup_mode creates a new config file if none exists."""
        config_loader = ConfigLoader(app_dir=tmp_path)
        config_loader.save_cleanup_mode(CleanupMode.MERGED)

        config_file = tmp_path / "config.toml"
        assert config_file.exists()
        content = config_file.read_text()
        assert 'default_mode = "merged"' in content

    def test_save_cleanup_mode_preserves_existing_config(self, tmp_path):
        """Test that save_cleanup_mode preserves other settings."""
        config_loader = ConfigLoader(app_dir=tmp_path)
        config_file = tmp_path / "config.toml"

        # Create config with existing settings
        config_file.write_text(
            '[terminal]\nmode = "window"\n[scripts]\npre_create = "echo test"'
        )

        # Save cleanup mode
        config_loader.save_cleanup_mode(CleanupMode.GITHUB)

        # Check that both old and new settings exist
        content = config_file.read_text()
        assert 'mode = "window"' in content
        assert 'pre_create = "echo test"' in content
        assert 'default_mode = "github"' in content

    def test_prompt_cleanup_mode_selection_with_gh(self):
        """Test prompt when gh is available."""
        with patch("shutil.which", return_value="/usr/local/bin/gh"):
            with patch("click.prompt", return_value="4"):
                mode = prompt_cleanup_mode_selection()
                assert mode == CleanupMode.GITHUB

    def test_prompt_cleanup_mode_selection_without_gh(self):
        """Test prompt when gh is not available."""
        with patch("shutil.which", return_value=None):
            with patch("click.prompt", return_value="1"):
                with patch("builtins.print") as mock_print:
                    mode = prompt_cleanup_mode_selection()
                    assert mode == CleanupMode.INTERACTIVE

                    # Check that GitHub unavailable message was shown
                    calls = [str(call) for call in mock_print.call_args_list]
                    assert any("GitHub CLI" in str(call) for call in calls)
                    assert any("cli.github.com" in str(call) for call in calls)

    def test_prompt_cleanup_mode_selection_choices(self):
        """Test all prompt choices work correctly."""
        test_cases = [
            ("1", CleanupMode.INTERACTIVE),
            ("2", CleanupMode.MERGED),
            ("3", CleanupMode.REMOTELESS),
        ]

        for choice, expected_mode in test_cases:
            with patch("shutil.which", return_value=None):  # No gh
                with patch("click.prompt", return_value=choice):
                    mode = prompt_cleanup_mode_selection()
                    assert mode == expected_mode
