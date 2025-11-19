# Changelog

<!-- loosely based on https://keepachangelog.com/en/1.0.0/ -->

## 0.5.0 - Unreleased

See [this discussion](https://github.com/irskep/autowt/discussions/75) for more background on this release.

### Added

-   You can use `awt` as a shortened form of `autowt`. Combined with other command aliases, you can get quite concise, for example `awt go <branch>` instead of `autowt switch`.
-   Commands which accept worktrees as arguments (`switch`, and now `cleanup`) accept paths in addition to branch names.
-   Many improvements to `cleanup` in this release! `cleanup` has become a general worktree removal command.
    -   New aliases: `rm`, `remove`, `del`, `delete`
    -   Pass worktrees as arguments if you know what you want to clean up
    -   If you have a non-interactive default cleanup mode configured, and you call `cleanup`, but it doesn't find anything to clean up, it will ask you if you want to go into interactive mode, unless you passed `-y`.
-   New lifecycle hook: `post_create_async` runs after creating a worktree in the original terminal without blocking the new session.
-   Branch prefix configuration option: automatically prefix new branch names with a customizable template.
    -   Configure via `worktree.branch_prefix` in config files or `AUTOWT_WORKTREE_BRANCH_PREFIX` environment variable
    -   Supports template variables: `{repo_name}` and `{github_username}` (when gh CLI is available)
    -   Smart prefix resolution: when switching to or cleaning up a branch, tries adding the prefix if exact match doesn't exist
    -   Prevents double-prefixing when branch name already includes the prefix
    -   Can be edited within `autowt config`

### Changed

-   Terminal automation is now owned by the [automate-terminal](https://github.com/irskep/automate-terminal) project, which has the same maintainer as autowt. Keeping this code separate simplifies the process of testing new terminal automations, keeps autowt's code more maintainable, and adds more value to the community.
    -   Because some terminals require extra dependencies, autowt uses dependency groups. Guake terminal support is newly available via the `guake` dependency group (`pip install autowt[guake]`).
-   Visual overhaul of interactive TUIs for `switch`, `cleanup`, and `config`.
-   `autowt config` only shows and edits global config (not project config), and now includes default cleanup mode. Previously, it would display fully resolved values in the context of a project, but write to the global config file, which was confusing.

### Fixed

-   The output of lifecycle hook scripts is sent to stdio instead of being eaten by autowt.
-   `post_cleanup` and `pre_create` hooks execute in the main repo directory, not the worktree, since the worktree doesn't exist yet/anymore.

### Removed

-   Removed experimental `shellconfig` command - shell integration was not functional due to hook and script output contaminating stdout
-   Removed automatic process killing during cleanup. If you want this behavior, use the lifecycle scripts. Open a GitHub issue if you were relying on it and we can work out an appopriate solution.
-   Removed unnecessary config options
    -   `worktree.default_remote`: autowt now queries git for branch tracking remotes with fallback priority (origin → upstream → first available)
    -   `worktree.branch_name_sanitization_enabled` and `worktree.branch_name_sanitization_replacements`: no one ever used these
-   Removed agent-related functionality, as it wasn't being used by autowt's maintainer or probably anyone else
-   Removed `--init` flag (redundant with `--after-init`)

## 0.4.8 - 2025-11-08

### Fixed

-   Autowt sets the correct base branch at all times instead of just when using `switch` (fix #71)

## 0.4.7 - 2025-10-05

### Added

-   GitHub cleanup mode: A new `--mode github` option for the `cleanup` command that uses the GitHub CLI (`gh`) to identify branches with merged or closed pull requests. This provides more accurate cleanup decisions for GitHub-based workflows. Requires `gh` CLI to be installed.
    -   Falls back gracefully with helpful error messages if `gh` is not installed
-   First-run cleanup mode selection: When running `autowt cleanup` for the first time, users are now prompted to select their preferred cleanup mode
    -   Interactive prompt shows available modes with descriptions
    -   GitHub mode is offered if `gh` CLI is available, otherwise a note mentions it would be available if `gh` were installed
    -   User's selection is saved to config and used as the default for future runs
    -   Can be changed later via `autowt config` or by editing config.toml
-   Removed vibecoded terminal support
-   Added Ghostty terminal support

## 0.4.6 - 2025-08-13

### Added

-   VSCode and Cursor support as terminal options - use `--terminal=vscode` or `--terminal=cursor` to open worktrees directly in editor windows
-   Window detection for VSCode and Cursor on macOS - switches to existing editor windows when possible instead of opening duplicates

## 0.4.5 - 2025-08-11

### Fixed

-   Removed 30-second timeout from git worktree remove operations

## 0.4.4 - 2025-08-07

### Added

-   Shell-only process killing for faster and safer cleanup operations

### Changed

-   Process killing now targets only shell processes (zsh, bash, sh, fish) running directly in worktree directories, using single `lsof +d` call for improved performance (fixes #60, #61, #62, #63)
-   Removed hardcoded 30-second timeout from process discovery (fixes #62)

### Removed

-   `process_scan_max_depth` configuration option
-   Process hierarchy building and parent-only killing logic
-   PPID tracking and process relationship analysis

## 0.4.3 - 2025-07-28

### Added

-   Remote branch detection and confirmation prompts when creating worktrees
    -   When attempting to create a worktree for a branch that doesn't exist locally, autowt now checks if it exists on remote
    -   Automatically fetches the specific branch from your default remote (e.g. `origin`) if available (optimized to only fetch when not already cached)
    -   Prompts user to confirm creating a local worktree that tracks the remote branch
    -   Can be bypassed with `-y`/`--yes` flag for automated workflows
    -   Only applies when no explicit `--from` branch is specified

## 0.4.2 - 2025-07-26

### Added

-   Version update notifications that check PyPI hourly for newer releases
    -   Auto-detects installation method (UV, Poetry, pip) from project files
    -   Shows appropriate upgrade command for detected package manager
    -   Rate-limited to check at most once per hour to avoid being intrusive
-   `autowt switch` without a branch name will let you choose or create a worktree interactively

## 0.4.1 - 2025-07-24

### Added

-   `pre_create` lifecycle hook for worktree creation validation
    -   Runs before worktree creation begins in the parent directory
    -   Can abort worktree creation by exiting with non-zero status
    -   Perfect for branch naming validation, resource checks, and pre-flight validation
    -   Comprehensive documentation with team workflow examples
-   Two-character command aliases for improved usability
    -   `ls` → `list`, `ll`
    -   `cleanup` → `cl`, `clean`, `prune`
    -   `config` → `configure`, `settings`, `cfg`, `conf`
    -   `switch` → `sw`, `checkout`, `co`, `goto`, `go`
-   Confirmation prompt for dynamic branch commands to prevent typos
    -   Prompts "Create a branch 'branch-name' and worktree? (Y/n)" for commands like `autowt swtch`
    -   Defaults to "yes" for quick confirmation
    -   Can be bypassed with `-y`/`--yes` flag

## 0.4.0 - 2025-07-22

### Added

-   Lifecycle hooks system for worktree automation
    -   `pre_cleanup` hook runs before cleaning up worktrees (resource cleanup, backups)
    -   `pre_process_kill` hook runs before terminating processes (graceful shutdown)
    -   `post_cleanup` hook runs after worktrees are removed (volume cleanup, state updates)
    -   `pre_switch` hook runs before switching worktrees (stop current services)
    -   `post_switch` hook runs after switching worktrees (start new services)
    -   Hooks receive environment variables (`AUTOWT_WORKTREE_DIR`, `AUTOWT_MAIN_REPO_DIR`, `AUTOWT_BRANCH_NAME`, `AUTOWT_HOOK_TYPE`)
    -   Both global and project hooks run in sequence (global first, then project)
    -   Comprehensive documentation with real-world examples for Docker, databases, and service orchestration

### Changed

-   Improved hook script execution to pass scripts directly to shell without preprocessing
-   Hook scripts now use environment variables only (no positional arguments)
-   Modernized test suite with pytest patterns

### Fixed

-   Fixed git error output appearing during cleanup in bare repositories without remotes

## 0.3.5 - 2025-07-22

### Added

-   Custom script argument interpolation with `--custom-script` option
    -   Run custom scripts with arguments: `autowt switch branch --custom-script="bugfix 123"`
    -   Arguments are interpolated into script templates using `$1`, `$2`, etc. placeholders
    -   Supports shell-style quoting for arguments with spaces: `--custom-script='deploy "staging env" --force'`
    -   Works with both new and existing worktrees
-   Added `--from` flag to specify source branch/commit when creating worktrees
    -   Accepts any git revision: branch names, tags, commit hashes, `HEAD`, etc.
    -   Available for both `autowt switch` and direct branch commands (`autowt my-branch --from main`)
    -   Only used when creating new worktrees; ignored when switching to existing ones
-   Added `--dir` option to override worktree directory at creation time
    -   Specify custom directory path: `autowt switch branch --dir /tmp/my-worktree`
    -   Supports both absolute and relative paths
    -   Available for both `autowt switch` and direct branch commands

## 0.3.4 - 2025-07-22

### Fixed

-   Fixed worktree directory naming for bare repositories ending in `.git`
    -   Bare repositories like `myrepo.git` now create worktree directories named `myrepo-worktrees` instead of `myrepo.git-worktrees`
    -   Maintains backward compatibility for regular repositories (no change in behavior)

## 0.3.3 - 2025-07-22

### Added

-   Support for bare git repositories (#40)
    -   autowt now works from directories containing bare repositories (\*.git directories), matching `git worktree add` behavior
    -   When multiple bare repositories exist in the same directory, autowt shows a clear error message instead of picking one arbitrarily

### Fixed

-   Fixed `directory_pattern` configuration being completely ignored when creating worktrees (#39)
    -   Worktree paths now respect custom `directory_pattern` settings in both global and project configs
    -   Added support for template variables: `{repo_dir}`, `{repo_name}`, `{repo_parent_dir}`, `{branch}`
    -   Added support for environment variable expansion in directory patterns (e.g., `$HOME`)

## 0.3.2 - 2025-07-21

### Added

-   Added experimental terminal warning on first use of unsupported terminals
-   First-run warning displays terminal name, GitHub source link, and issue reporting URL
-   User can confirm or decline to continue with experimental terminal support

## 0.3.1 - 2025-07-21

### Fixed

-   Fixed session ID conflicts between repositories with same branch names

## 0.3.0 - 2025-07-20

### Added

-   Added agent monitoring system with Claude Code hooks integration
-   Added `autowt agents` command for live agent status dashboard
-   Added `autowt hooks-install` command to install Claude Code hooks
-   Added `--show` flag to `hooks-install` to display current hook status
-   Added `--waiting` and `--latest` flags to `autowt switch` for agent-aware navigation
-   Enhanced `autowt ls` to display agent status indicators alongside terminal sessions

## 0.2.1 - 2025-07-18

### Added

-   Added `--version` flag to CLI to display current version

### Changed

### Fixed

-   Fixed Terminal.app session switching that was inconsistently working
-   Fixed `-y`/`--yes` flag not working with dynamic branch commands

## 0.2.0 - 2025-07-18

### Added

-   Added `echo` terminal mode for users who want to avoid terminal automation
-   Enhanced `autowt config` TUI with additional configuration options:
    -   Support for all four terminal modes (tab, window, inplace, echo)
    -   Auto-fetch toggle for worktree creation
    -   Kill processes toggle for cleanup behavior
-   Added documentation section on disabling terminal control
-   Comprehensive test suite for configuration TUI functionality

### Changed

-   Major refactoring of the configuration system. Settings are now managed via a hierarchical system with global `config.toml` and project `autowt.toml`/`.autowt.toml` files, environment variables, and CLI flags. See the [configuration guide](configuration.md) for full details.
-   Improved `autowt config` TUI to display actual platform-specific config file paths
-   Updated documentation to accurately reflect TUI capabilities and limitations

### Fixed

-   Fixed missing `echo` terminal mode in configuration TUI
-   Removed dead configuration TUI code to eliminate confusion

## 0.1.0 - 2025-07-18

### Added

-   Initial release of autowt
-   Core worktree management commands: checkout, cleanup, ls
-   Automatic terminal switching between worktrees
-   Branch cleanup with interactive confirmation
-   Configuration management with init scripts
