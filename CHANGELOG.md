# Changelog

<!-- loosely based on https://keepachangelog.com/en/1.0.0/ -->

## Unreleased

### Added

### Changed

- Major refactoring of the configuration system. Settings are now managed via a hierarchical system with `config.toml` files (global and project-specific), environment variables, and CLI flags. See the [configuration guide](configuration.md) for full details.

### Fixed

## 0.1.0 - 2025-07-18

### Added
- Initial release of autowt
- Core worktree management commands: checkout, cleanup, ls
- Automatic terminal switching between worktrees
- Branch cleanup with interactive confirmation
- Configuration management with init scripts