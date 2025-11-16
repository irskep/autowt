"""Tests for the comprehensive configuration system."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import toml

import autowt.config
from autowt.config import (
    CleanupConfig,
    Config,
    ConfigLoader,
    ConfirmationsConfig,
    ScriptsConfig,
    TerminalConfig,
    WorktreeConfig,
    get_config,
    load_config,
    save_config,
    set_config,
)
from autowt.models import CleanupMode, TerminalMode


class TestConfigDataClasses:
    """Tests for configuration data classes."""

    def test_terminal_config_defaults(self):
        """Test TerminalConfig default values."""
        config = TerminalConfig()
        assert config.mode == TerminalMode.TAB
        assert config.always_new is False
        assert config.program is None

    def test_terminal_config_with_values(self):
        """Test TerminalConfig with custom values."""
        config = TerminalConfig(
            mode=TerminalMode.WINDOW, always_new=True, program="iterm2"
        )
        assert config.mode == TerminalMode.WINDOW
        assert config.always_new is True
        assert config.program == "iterm2"

    def test_worktree_config_defaults(self):
        """Test WorktreeConfig default values."""
        config = WorktreeConfig()
        assert config.directory_pattern == "../{repo_name}-worktrees/{branch}"
        assert config.auto_fetch is True
        assert config.branch_prefix is None

    def test_worktree_config_with_branch_prefix(self):
        """Test WorktreeConfig with branch_prefix value."""
        config = WorktreeConfig(
            directory_pattern="../{repo_name}-worktrees/{branch}",
            auto_fetch=True,
            branch_prefix="feature/",
        )
        assert config.branch_prefix == "feature/"

    def test_cleanup_config_defaults(self):
        """Test CleanupConfig default values."""
        config = CleanupConfig()
        assert config.default_mode == CleanupMode.INTERACTIVE

    def test_scripts_config_defaults(self):
        """Test ScriptsConfig default values."""
        config = ScriptsConfig()
        assert config.post_create is None
        assert config.session_init is None
        assert config.custom == {}

    def test_confirmations_config_defaults(self):
        """Test ConfirmationsConfig default values."""
        config = ConfirmationsConfig()
        assert config.cleanup_multiple is True
        assert config.force_operations is True

    def test_main_config_defaults(self):
        """Test main Config default values."""
        config = Config()
        assert isinstance(config.terminal, TerminalConfig)
        assert isinstance(config.worktree, WorktreeConfig)
        assert isinstance(config.cleanup, CleanupConfig)
        assert isinstance(config.scripts, ScriptsConfig)
        assert isinstance(config.confirmations, ConfirmationsConfig)


class TestConfigFromDict:
    """Tests for creating configuration from dictionaries."""

    def test_config_from_empty_dict(self):
        """Test creating config from empty dictionary uses defaults."""
        config = Config.from_dict({})
        assert config.terminal.mode == TerminalMode.TAB
        assert config.cleanup.default_mode == CleanupMode.INTERACTIVE

    def test_config_from_partial_dict(self):
        """Test creating config from partial dictionary."""
        data = {
            "terminal": {"mode": "window", "always_new": True},
            "cleanup": {"default_mode": "merged"},
        }
        config = Config.from_dict(data)

        assert config.terminal.mode == TerminalMode.WINDOW
        assert config.terminal.always_new is True
        assert config.terminal.program is None  # default
        assert config.cleanup.default_mode == CleanupMode.MERGED

    def test_config_from_complete_dict(self):
        """Test creating config from complete dictionary."""
        data = {
            "terminal": {"mode": "window", "always_new": True, "program": "iterm2"},
            "worktree": {
                "directory_pattern": "$HOME/worktrees/{repo_name}/{branch}",
                "auto_fetch": False,
            },
            "cleanup": {
                "default_mode": "merged",
            },
            "scripts": {
                "init": "npm install",
                "custom": {"test": "npm test", "build": "npm run build"},
            },
            "confirmations": {
                "cleanup_multiple": False,
                "force_operations": True,
            },
        }

        config = Config.from_dict(data)

        # Terminal config
        assert config.terminal.mode == TerminalMode.WINDOW
        assert config.terminal.always_new is True
        assert config.terminal.program == "iterm2"

        # Worktree config
        assert (
            config.worktree.directory_pattern == "$HOME/worktrees/{repo_name}/{branch}"
        )
        assert config.worktree.auto_fetch is False

        # Cleanup config
        assert config.cleanup.default_mode == CleanupMode.MERGED

        # Scripts config
        assert config.scripts.session_init == "npm install"
        assert config.scripts.custom == {"test": "npm test", "build": "npm run build"}

        # Confirmations config
        assert config.confirmations.cleanup_multiple is False
        assert config.confirmations.force_operations is True

    def test_config_with_branch_prefix(self):
        """Test creating config with branch_prefix."""
        data = {
            "worktree": {
                "branch_prefix": "feature/",
            },
        }
        config = Config.from_dict(data)
        assert config.worktree.branch_prefix == "feature/"

    def test_config_with_templated_branch_prefix(self):
        """Test creating config with templated branch_prefix."""
        data = {
            "worktree": {
                "branch_prefix": "{github_username}/",
            },
        }
        config = Config.from_dict(data)
        assert config.worktree.branch_prefix == "{github_username}/"

    def test_config_invalid_enum_values(self):
        """Test that invalid enum values raise appropriate errors."""
        with pytest.raises(ValueError):
            Config.from_dict({"terminal": {"mode": "invalid_mode"}})

        with pytest.raises(ValueError):
            Config.from_dict({"cleanup": {"default_mode": "invalid_mode"}})


class TestConfigToDict:
    """Tests for converting configuration to dictionaries."""

    def test_config_to_dict_defaults(self):
        """Test converting default config to dictionary."""
        config = Config()
        data = config.to_dict()

        expected = {
            "terminal": {"mode": "tab", "always_new": False, "program": None},
            "worktree": {
                "directory_pattern": "../{repo_name}-worktrees/{branch}",
                "auto_fetch": True,
                "branch_prefix": None,
            },
            "cleanup": {
                "default_mode": "interactive",
            },
            "scripts": {
                "pre_create": None,
                "post_create": None,
                "post_create_async": None,
                "session_init": None,
                "pre_cleanup": None,
                "post_cleanup": None,
                "pre_switch": None,
                "post_switch": None,
                "custom": {},
            },
            "confirmations": {
                "cleanup_multiple": True,
                "force_operations": True,
            },
        }

        assert data == expected

    def test_config_roundtrip(self):
        """Test that config can be converted to dict and back without loss."""
        original_config = Config.from_dict(
            {
                "terminal": {"mode": "window", "always_new": True},
                "cleanup": {"default_mode": "merged"},
                "scripts": {"init": "npm install", "custom": {"test": "npm test"}},
            }
        )

        data = original_config.to_dict()
        restored_config = Config.from_dict(data)

        assert original_config.terminal.mode == restored_config.terminal.mode
        assert (
            original_config.terminal.always_new == restored_config.terminal.always_new
        )
        assert (
            original_config.cleanup.default_mode == restored_config.cleanup.default_mode
        )
        assert (
            original_config.scripts.session_init == restored_config.scripts.session_init
        )
        assert original_config.scripts.custom == restored_config.scripts.custom


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def test_config_loader_init_with_custom_dir(self):
        """Test ConfigLoader initialization with custom directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir) / "custom" / "dir"
            loader = ConfigLoader(app_dir=custom_dir)
            assert loader.app_dir == custom_dir
            assert loader.global_config_file == custom_dir / "config.toml"
            # Directory should not exist until setup() is called
            assert not custom_dir.exists()
            loader.setup()
            assert custom_dir.exists()  # Should be created after setup

    def test_config_loader_default_app_dir_macos(self):
        """Test default app directory on macOS."""
        with patch("platform.system", return_value="Darwin"):
            loader = ConfigLoader()
            expected = Path.home() / "Library" / "Application Support" / "autowt"
            assert loader.app_dir == expected

    def test_config_loader_default_app_dir_linux(self):
        """Test default app directory on Linux."""
        with patch("platform.system", return_value="Linux"):
            with patch.dict(os.environ, {}, clear=True):
                loader = ConfigLoader()
                expected = Path.home() / ".config" / "autowt"
                assert loader.app_dir == expected

    def test_config_loader_default_app_dir_linux_xdg(self):
        """Test default app directory on Linux with XDG_CONFIG_HOME."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("platform.system", return_value="Linux"):
                with patch.dict(os.environ, {"XDG_CONFIG_HOME": temp_dir}):
                    loader = ConfigLoader()
                    expected = Path(temp_dir) / "autowt"
                    assert loader.app_dir == expected

    def test_config_loader_default_app_dir_windows(self):
        """Test default app directory on Windows."""
        with patch("platform.system", return_value="Windows"):
            loader = ConfigLoader()
            expected = Path.home() / ".autowt"
            assert loader.app_dir == expected

    def test_load_config_no_files(self):
        """Test loading config when no config files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            loader = ConfigLoader(app_dir=app_dir)
            config = loader.load_config()

            # Should return defaults
            assert config.terminal.mode == TerminalMode.TAB
            assert config.cleanup.default_mode == CleanupMode.INTERACTIVE

    def test_load_global_config(self):
        """Test loading global configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            # Create global config
            global_config = {
                "terminal": {"mode": "window", "always_new": True},
                "cleanup": {"default_mode": "merged"},
            }
            with open(app_dir / "config.toml", "w") as f:
                toml.dump(global_config, f)

            loader = ConfigLoader(app_dir=app_dir)
            config = loader.load_config()

            assert config.terminal.mode == TerminalMode.WINDOW
            assert config.terminal.always_new is True
            assert config.cleanup.default_mode == CleanupMode.MERGED

    def test_load_project_config(self):
        """Test loading project configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()

            # Create project config
            project_config = {
                "scripts": {"init": "npm install"},
                "terminal": {"mode": "inplace"},
            }
            with open(project_dir / "autowt.toml", "w") as f:
                toml.dump(project_config, f)

            loader = ConfigLoader(app_dir=app_dir)
            config = loader.load_config(project_dir=project_dir)

            assert config.scripts.session_init == "npm install"
            assert config.terminal.mode == TerminalMode.INPLACE

    def test_load_project_config_hidden_file(self):
        """Test loading project config from .autowt.toml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()

            # Create hidden project config
            project_config = {"scripts": {"init": "python setup.py"}}
            with open(project_dir / ".autowt.toml", "w") as f:
                toml.dump(project_config, f)

            loader = ConfigLoader(app_dir=app_dir)
            config = loader.load_config(project_dir=project_dir)

            assert config.scripts.session_init == "python setup.py"

    def test_environment_variables(self):
        """Test loading configuration from environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            # Set environment variables
            env_vars = {
                "AUTOWT_TERMINAL_MODE": "window",
                "AUTOWT_TERMINAL_ALWAYS_NEW": "true",
                "AUTOWT_CLEANUP_DEFAULT_MODE": "merged",
                "AUTOWT_WORKTREE_AUTO_FETCH": "false",
                "AUTOWT_WORKTREE_BRANCH_PREFIX": "feature/",
                "AUTOWT_SCRIPTS_SESSION_INIT": "make setup",
            }

            with patch.dict(os.environ, env_vars):
                loader = ConfigLoader(app_dir=app_dir)
                config = loader.load_config()

                assert config.terminal.mode == TerminalMode.WINDOW
                assert config.terminal.always_new is True
                assert config.cleanup.default_mode == CleanupMode.MERGED
                assert config.worktree.auto_fetch is False
                assert config.worktree.branch_prefix == "feature/"
                assert config.scripts.session_init == "make setup"

    def test_cli_overrides(self):
        """Test CLI overrides."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            cli_overrides = {
                "terminal": {"mode": "echo"},
                "cleanup": {"default_mode": "all"},
            }

            loader = ConfigLoader(app_dir=app_dir)
            config = loader.load_config(cli_overrides=cli_overrides)

            assert config.terminal.mode == TerminalMode.ECHO
            assert config.cleanup.default_mode == CleanupMode.ALL

    def test_precedence_order(self):
        """Test configuration precedence order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()

            # Global config
            global_config = {
                "terminal": {"mode": "tab", "always_new": False},
                "cleanup": {"default_mode": "interactive"},
                "scripts": {"init": "global init"},
            }
            with open(app_dir / "config.toml", "w") as f:
                toml.dump(global_config, f)

            # Project config
            project_config = {
                "terminal": {"mode": "window"},  # Override terminal mode
                "scripts": {"init": "project init"},  # Override init script
            }
            with open(project_dir / "autowt.toml", "w") as f:
                toml.dump(project_config, f)

            # Environment variables
            env_vars = {
                "AUTOWT_CLEANUP_DEFAULT_MODE": "merged",  # Override cleanup setting
                "AUTOWT_TERMINAL_ALWAYS_NEW": "true",  # Override always_new
            }

            # CLI overrides
            cli_overrides = {
                "scripts": {"init": "cli init"}  # Override init script again
            }

            with patch.dict(os.environ, env_vars):
                loader = ConfigLoader(app_dir=app_dir)
                config = loader.load_config(
                    project_dir=project_dir, cli_overrides=cli_overrides
                )

                # Check precedence: CLI > env > project > global > defaults
                assert config.terminal.mode == TerminalMode.WINDOW  # From project
                assert config.terminal.always_new is True  # From environment
                assert (
                    config.cleanup.default_mode == CleanupMode.MERGED
                )  # From environment
                assert config.scripts.session_init == "cli init"  # From CLI override

    def test_invalid_global_config_file(self):
        """Test handling of invalid global config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            # Create invalid TOML file
            with open(app_dir / "config.toml", "w") as f:
                f.write("invalid toml content [[[")

            loader = ConfigLoader(app_dir=app_dir)
            config = loader.load_config()

            # Should fall back to defaults
            assert config.terminal.mode == TerminalMode.TAB

    def test_invalid_project_config_file(self):
        """Test handling of invalid project config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()

            # Create invalid TOML file
            with open(project_dir / "autowt.toml", "w") as f:
                f.write("invalid toml content [[[")

            loader = ConfigLoader(app_dir=app_dir)
            config = loader.load_config(project_dir=project_dir)

            # Should fall back to defaults
            assert config.terminal.mode == TerminalMode.TAB

    def test_unknown_environment_variable(self):
        """Test handling of unknown environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            with patch.dict(os.environ, {"AUTOWT_UNKNOWN_SETTING": "value"}):
                loader = ConfigLoader(app_dir=app_dir)
                # Should not raise an exception, just log a warning
                config = loader.load_config()
                assert config.terminal.mode == TerminalMode.TAB

    def test_environment_variable_type_conversion(self):
        """Test environment variable type conversion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            env_vars = {
                "AUTOWT_TERMINAL_ALWAYS_NEW": "yes",  # Boolean true
                "AUTOWT_CLEANUP_DEFAULT_MODE": "all",  # String
                "AUTOWT_SCRIPTS_SESSION_INIT": "echo hello",  # String
            }

            with patch.dict(os.environ, env_vars):
                loader = ConfigLoader(app_dir=app_dir)
                config = loader.load_config()

                assert config.terminal.always_new is True
                assert config.cleanup.default_mode == CleanupMode.ALL
                assert config.scripts.session_init == "echo hello"

    def test_save_config(self):
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            config = Config.from_dict(
                {
                    "terminal": {"mode": "window", "always_new": True},
                    "cleanup": {"default_mode": "merged"},
                }
            )

            loader = ConfigLoader(app_dir=app_dir)
            loader.save_config(config)

            # Verify file was created and contains expected data
            assert (app_dir / "config.toml").exists()

            # Load it back and verify
            loaded_config = loader.load_config()
            assert loaded_config.terminal.mode == TerminalMode.WINDOW
            assert loaded_config.terminal.always_new is True
            assert loaded_config.cleanup.default_mode == CleanupMode.MERGED


class TestGlobalConfigManagement:
    """Tests for global configuration management functions."""

    def test_load_and_get_config(self):
        """Test loading and getting global configuration."""
        # Reset global config
        autowt.config._config = None
        autowt.config._config_loader = None

        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            # Create test config
            global_config = {"terminal": {"mode": "window"}}
            with open(app_dir / "config.toml", "w") as f:
                toml.dump(global_config, f)

            # Mock the config loader to use our temp directory
            with patch("autowt.config.ConfigLoader") as mock_loader_class:
                mock_loader = mock_loader_class.return_value
                mock_loader.load_config.return_value = Config.from_dict(global_config)

                config = load_config()
                assert config.terminal.mode == TerminalMode.WINDOW

                # Should be able to get it globally
                global_config_instance = get_config()
                assert global_config_instance.terminal.mode == TerminalMode.WINDOW

    def test_get_config_before_load_raises_error(self):
        """Test that getting config before loading raises an error."""
        # Reset global config
        autowt.config._config = None

        with pytest.raises(RuntimeError, match="Configuration not initialized"):
            get_config()

    def test_set_config(self):
        """Test setting configuration manually."""
        test_config = Config.from_dict({"terminal": {"mode": "inplace"}})
        set_config(test_config)

        global_config = get_config()
        assert global_config.terminal.mode == TerminalMode.INPLACE

    def test_save_config_function(self):
        """Test save_config function."""
        with tempfile.TemporaryDirectory():
            test_config = Config.from_dict({"terminal": {"mode": "window"}})
            set_config(test_config)

            # Mock the ConfigLoader class
            with patch("autowt.config.ConfigLoader") as mock_loader_class:
                mock_loader = mock_loader_class.return_value

                save_config()

                # Verify ConfigLoader was instantiated and save was called with the config
                mock_loader_class.assert_called_once()
                mock_loader.save_config.assert_called_once_with(test_config)

    def test_save_config_without_config_raises_error(self):
        """Test that saving without config raises an error."""
        # Reset global config
        autowt.config._config = None

        with pytest.raises(RuntimeError, match="No configuration to save"):
            save_config()


class TestConfigIntegration:
    """Integration tests for the complete configuration system."""

    def test_real_world_config_loading(self):
        """Test loading a realistic configuration setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()

            # Global config - user preferences
            global_config = {
                "terminal": {"mode": "tab", "program": "iterm2"},
                "cleanup": {"default_mode": "interactive"},
                "confirmations": {"cleanup_multiple": False},
            }
            with open(app_dir / "config.toml", "w") as f:
                toml.dump(global_config, f)

            # Project config - project-specific settings
            project_config = {
                "scripts": {
                    "init": "npm install && npm run setup",
                    "custom": {
                        "test": "npm test",
                        "build": "npm run build:prod",
                        "deploy": "npm run deploy",
                    },
                },
                "worktree": {
                    "directory_pattern": "$HOME/work-trees/{repo_name}/{branch}",
                    "auto_fetch": False,
                },
            }
            with open(project_dir / "autowt.toml", "w") as f:
                toml.dump(project_config, f)

            # Environment overrides - CI/deployment settings
            env_vars = {
                "AUTOWT_TERMINAL_MODE": "echo",  # For CI/scripts
                "AUTOWT_CLEANUP_DEFAULT_MODE": "merged",  # For CI
            }

            # CLI overrides - one-time overrides
            cli_overrides = {"terminal": {"always_new": True}}

            with patch.dict(os.environ, env_vars):
                loader = ConfigLoader(app_dir=app_dir)
                config = loader.load_config(
                    project_dir=project_dir, cli_overrides=cli_overrides
                )

                # Verify final configuration respects precedence
                assert config.terminal.mode == TerminalMode.ECHO  # From env
                assert config.terminal.always_new is True  # From CLI
                assert config.terminal.program == "iterm2"  # From global

                assert config.cleanup.default_mode == CleanupMode.MERGED  # From env

                assert (
                    config.scripts.session_init == "npm install && npm run setup"
                )  # From project
                assert len(config.scripts.custom) == 3  # From project

                assert (
                    config.worktree.directory_pattern
                    == "$HOME/work-trees/{repo_name}/{branch}"
                )  # From project
                assert config.worktree.auto_fetch is False  # From project

                assert config.confirmations.cleanup_multiple is False  # From global

    def test_minimal_config_setup(self):
        """Test that the system works with minimal configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            app_dir = Path(temp_dir)

            loader = ConfigLoader(app_dir=app_dir)
            config = loader.load_config()

            # Should work with all defaults
            assert config.terminal.mode == TerminalMode.TAB
            assert config.cleanup.default_mode == CleanupMode.INTERACTIVE
            assert config.scripts.session_init is None
            assert config.scripts.custom == {}

            # Should be able to save defaults
            loader.save_config(config)
            assert (app_dir / "config.toml").exists()
