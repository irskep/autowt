# Changelog

<!-- loosely based on https://keepachangelog.com/en/1.0.0/ -->

## 0.4.0 - 2025-07-22

### Added

- Lifecycle hooks system for worktree automation
    - `pre_cleanup` hook runs before cleaning up worktrees (resource cleanup, backups)
    - `pre_process_kill` hook runs before terminating processes (graceful shutdown)
    - `post_cleanup` hook runs after worktrees are removed (volume cleanup, state updates)
    - `pre_switch` hook runs before switching worktrees (stop current services)
    - `post_switch` hook runs after switching worktrees (start new services)
    - Hooks receive environment variables (`AUTOWT_WORKTREE_DIR`, `AUTOWT_MAIN_REPO_DIR`, `AUTOWT_BRANCH_NAME`, `AUTOWT_HOOK_TYPE`)
    - Both global and project hooks run in sequence (global first, then project)
    - Comprehensive documentation with real-world examples for Docker, databases, and service orchestration

### Changed

- Improved hook script execution to pass scripts directly to shell without preprocessing
- Hook scripts now use environment variables only (no positional arguments)
- Modernized test suite with pytest patterns

### Fixed

- Fixed git error output appearing during cleanup in bare repositories without remotes

## 0.3.5 - 2025-07-22

### Added

- Custom script argument interpolation with `--custom-script` option
    - Run custom scripts with arguments: `autowt switch branch --custom-script="bugfix 123"`
    - Arguments are interpolated into script templates using `$1`, `$2`, etc. placeholders
    - Supports shell-style quoting for arguments with spaces: `--custom-script='deploy "staging env" --force'`
    - Works with both new and existing worktrees
- Added `--from` flag to specify source branch/commit when creating worktrees
    - Accepts any git revision: branch names, tags, commit hashes, `HEAD`, etc.
    - Available for both `autowt switch` and direct branch commands (`autowt my-branch --from main`)
    - Only used when creating new worktrees; ignored when switching to existing ones
- Added `--dir` option to override worktree directory at creation time
    - Specify custom directory path: `autowt switch branch --dir /tmp/my-worktree`
    - Supports both absolute and relative paths
    - Available for both `autowt switch` and direct branch commands

### Changed

### Fixed

## 0.3.4 - 2025-07-22

### Added

### Changed

### Fixed

- Fixed worktree directory naming for bare repositories ending in `.git`
    - Bare repositories like `myrepo.git` now create worktree directories named `myrepo-worktrees` instead of `myrepo.git-worktrees`
    - Maintains backward compatibility for regular repositories (no change in behavior)

## 0.3.3 - 2025-07-22

### Added

- Support for bare git repositories (#40)
    - autowt now works from directories containing bare repositories (*.git directories), matching `git worktree add` behavior
    - When multiple bare repositories exist in the same directory, autowt shows a clear error message instead of picking one arbitrarily

### Changed

### Fixed

- Fixed `directory_pattern` configuration being completely ignored when creating worktrees (#39)
    - Worktree paths now respect custom `directory_pattern` settings in both global and project configs
    - Added support for template variables: `{repo_dir}`, `{repo_name}`, `{repo_parent_dir}`, `{branch}`
    - Added support for environment variable expansion in directory patterns (e.g., `$HOME`)

## 0.3.2 - 2025-07-21

### Added

- Added experimental terminal warning on first use of unsupported terminals
- First-run warning displays terminal name, GitHub source link, and issue reporting URL
- User can confirm or decline to continue with experimental terminal support

### Changed

### Fixed

## 0.3.1 - 2025-07-21

### Added

### Changed

### Fixed

- Fixed session ID conflicts between repositories with same branch names

## 0.3.0 - 2025-07-20

### Added

- Added agent monitoring system with Claude Code hooks integration
- Added `autowt agents` command for live agent status dashboard
- Added `autowt hooks-install` command to install Claude Code hooks
- Added `--show` flag to `hooks-install` to display current hook status
- Added `--waiting` and `--latest` flags to `autowt switch` for agent-aware navigation
- Enhanced `autowt ls` to display agent status indicators alongside terminal sessions

### Changed

### Fixed

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