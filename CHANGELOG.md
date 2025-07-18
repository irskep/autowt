# Changelog

<!-- loosely based on https://keepachangelog.com/en/1.0.0/ -->

## 0.2.1 - 2025-07-18

### Added

- Added `--version` flag to CLI to display current version

### Changed

### Fixed

- Fixed Terminal.app session switching that was inconsistently working
- Fixed `-y`/`--yes` flag not working with dynamic branch commands

## 0.2.0 - 2025-07-18

### Added

- Added `echo` terminal mode for users who want to avoid terminal automation
- Enhanced `autowt config` TUI with additional configuration options:
  - Support for all four terminal modes (tab, window, inplace, echo)
  - Auto-fetch toggle for worktree creation
  - Kill processes toggle for cleanup behavior
- Added documentation section on disabling terminal control
- Comprehensive test suite for configuration TUI functionality

### Changed

- Major refactoring of the configuration system. Settings are now managed via a hierarchical system with global `config.toml` and project `autowt.toml`/`.autowt.toml` files, environment variables, and CLI flags. See the [configuration guide](configuration.md) for full details.
- Improved `autowt config` TUI to display actual platform-specific config file paths
- Updated documentation to accurately reflect TUI capabilities and limitations

### Fixed

- Fixed missing `echo` terminal mode in configuration TUI
- Removed dead configuration TUI code to eliminate confusion

## 0.1.0 - 2025-07-18

### Added
- Initial release of autowt
- Core worktree management commands: checkout, cleanup, ls
- Automatic terminal switching between worktrees
- Branch cleanup with interactive confirmation
- Configuration management with init scripts