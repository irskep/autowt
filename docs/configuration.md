# Configuring autowt

`autowt` is designed to work out of the box with sensible defaults, but you can customize its behavior to perfectly match your workflow. This guide covers the different ways you can configure `autowt`, from global settings to project-specific rules and one-time command-line overrides.

For a comprehensive example configuration file with comments explaining all options, see the [example_config.toml](https://github.com/irskep/autowt/blob/main/example_config.toml) in the repository.

## Configuration layers

`autowt` uses a hierarchical configuration system. Settings are loaded from multiple sources, and later sources override earlier ones. The order of precedence is:

1.  **Built-in Defaults**: Sensible defaults for all settings.
2.  **Global `config.toml`**: User-wide settings that apply to all your projects.
3.  **Project `.autowt.toml`**: Project-specific settings, defined in your repository's root.
4.  **Environment Variables**: System-wide overrides, prefixed with `AUTOWT_`.
5.  **Command-Line Flags**: The highest priority, for on-the-fly adjustments.

## Configuration files

### Global configuration

Your global settings are stored in a `config.toml` file in a platform-appropriate directory:

-   **macOS**: `~/Library/Application Support/autowt/config.toml`
-   **Linux**: `~/.config/autowt/config.toml` (or `$XDG_CONFIG_HOME/autowt/config.toml`)
-   **Windows**: `~/.autowt/config.toml`

The easiest way to manage common settings is with the `autowt config` command, which launches an interactive TUI (Text-based User Interface) for the most frequently used options. For the complete set of configuration options, you can edit the config file directly.

### Project-specific configuration

For settings that should apply only to a specific project, create a `.autowt.toml` file in the root of your repository. This is the ideal place to define project-wide init scripts or worktree settings.

## All configuration options

This section provides a comprehensive reference for all available configuration options, organized by section. Each option includes its TOML key, the corresponding environment variable, and any command-line flags.

---

### `[terminal]` - Terminal management

Controls how `autowt` interacts with your terminal.

<div class="autowt-clitable-wrapper"></div>

| Key          | Type    | Default | Description                                                                                                                                                                                                                                                                                                                |
| ------------ | ------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mode`       | string  | `"tab"` | Determines how `autowt` opens worktrees. <br> • `tab`: Open in a new tab (default). <br> • `window`: Open in a new window. <br> • `inplace`: Switch the current terminal to the worktree directory. <br> • `echo`: Output shell commands to stdout. <br> **ENV**: `AUTOWT_TERMINAL_MODE` <br> **CLI**: `--terminal <mode>` |
| `always_new` | boolean | `false` | If `true`, always creates a new terminal session instead of switching to an existing one for a worktree. <br> **ENV**: `AUTOWT_TERMINAL_ALWAYS_NEW` <br> **CLI**: `--ignore-same-session`                                                                                                                                  |
| `program`    | string  | `null`  | Force `autowt` to use a specific terminal program instead of auto-detecting one. <br> _Examples: `iterm2`, `terminal`, `tmux`_ <br> **ENV**: `AUTOWT_TERMINAL_PROGRAM`                                                                                                                                                     |

---

### `[worktree]` - Worktree management

Defines how worktrees are created and managed.

<div class="autowt-clitable-wrapper"></div>

| Key                 | Type    | Default                               | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------------- | ------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `directory_pattern` | string  | `"../{repo_name}-worktrees/{branch}"` | The template for creating worktree directory paths. Can use variables `{repo_dir}` (full repo path), `{repo_name}` (repo directory name), `{repo_parent_dir}` (parent directory of repo), `{branch}` (branch name), and environment variables like `$HOME`. Examples: `"{repo_parent_dir}/worktrees/{branch}"`, `"$HOME/worktrees/{repo_name}/{branch}"`. This can be overridden on a per-command basis using the `--dir` flag. <br> **ENV**: `AUTOWT_WORKTREE_DIRECTORY_PATTERN` <br> **CLI**: `--dir <path>` |
| `auto_fetch`        | boolean | `true`                                | If `true`, automatically fetches from the remote before creating new worktrees. <br> **ENV**: `AUTOWT_WORKTREE_AUTO_FETCH` <br> **CLI**: `--no-fetch` (to disable)                                                                                                                                                                                                                                                                                                                                             |
| `branch_prefix`     | string  | `null`                                | Automatically prefix new branch names with a template. Can use variables `{repo_name}`, `{github_username}` (if `gh` CLI is available), and environment variables. Examples: `"feature/"`, `"{github_username}/"`. When set, `autowt my-feature` creates `feature/my-feature`. Also applies when switching: `autowt my-feature` switches to `feature/my-feature` if it exists. Prevents double-prefixing if the branch name already includes the prefix. <br> **ENV**: `AUTOWT_WORKTREE_BRANCH_PREFIX`         |

---

### `[cleanup]` - Cleanup behavior

Configures the `autowt cleanup` command.

<div class="autowt-clitable-wrapper"></div>

| Key            | Type   | Default         | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------- | ------ | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `default_mode` | string | `"interactive"` | The default mode for the `cleanup` command. <br> • `interactive`: Opens a TUI to let you choose what to remove. <br> • `merged`: Selects branches that have been merged into your main branch. <br> • `remoteless`: Selects local branches that don't have an upstream remote. <br> • `all`: Non-interactively selects all merged and remoteless branches. <br> • `github`: Uses the GitHub CLI (`gh`) to identify branches with merged or closed pull requests. <br><br> **First run**: If not configured, autowt will prompt you to select your preferred mode on first use. If `gh` is available, the `github` option will be offered; otherwise, a note will mention it becomes available when `gh` is installed. <br> **ENV**: `AUTOWT_CLEANUP_DEFAULT_MODE` <br> **CLI**: `--mode <mode>` |

---

### `[scripts]` - Lifecycle hooks and scripts

See [Lifecycle Hooks](lifecyclehooks.md).

#### `[scripts.custom]`

Define named, reusable scripts for specialized workflows. Custom scripts can be simple command strings or full workflow profiles with their own lifecycle hooks and dynamic branch naming.

##### Simple format

The simplest form is a command string that runs as `session_init`. For simple format scripts, the first CLI argument is used as the branch name:

```toml
[scripts.custom]
# Simple: just a session_init command
# First argument ($1) becomes the branch name
bugfix = 'claude "Fix the bug described in GitHub issue $1"'
```

Usage: `awt bugfix 123` creates a branch named `123` with the session_init command.

##### Enhanced format

For more control, use a nested table to define a complete workflow profile:

```toml
[scripts.custom.ghllm]
# Help text for --help output
description = "Create worktree from GitHub issue"

# Dynamic branch name from command output
branch_name = "gh issue view $1 --json title --template '{{.title}}'"

# Hook inheritance (default: true)
inherit_hooks = true

# Any lifecycle hook can be overridden
pre_create = "echo 'Starting ghllm workflow'"
session_init = 'claude "Work on GitHub issue $1"'
```

##### Custom script fields

<div class="autowt-hooks-wrapper"></div>

| Field               | Type    | Default | Description                                                                                                   |
| ------------------- | ------- | ------- | ------------------------------------------------------------------------------------------------------------- |
| `description`       | string  | `null`  | Help text shown in `awt --help` output.                                                                       |
| `branch_name`       | string  | `null`  | Shell command whose stdout becomes the branch name. Output is automatically normalized and truncated.         |
| `inherit_hooks`     | boolean | `true`  | When `true`, global/project hooks run before custom script hooks. When `false`, only custom script hooks run. |
| `pre_create`        | string  | `null`  | Runs before worktree creation (in main repo directory).                                                       |
| `post_create`       | string  | `null`  | Runs after worktree creation (in worktree directory).                                                         |
| `post_create_async` | string  | `null`  | Runs after worktree creation, non-blocking.                                                                   |
| `session_init`      | string  | `null`  | Runs when opening a terminal in the worktree.                                                                 |
| `pre_cleanup`       | string  | `null`  | Runs before worktree deletion.                                                                                |
| `post_cleanup`      | string  | `null`  | Runs after worktree deletion (in main repo directory).                                                        |
| `pre_switch`        | string  | `null`  | Runs before switching to an existing worktree.                                                                |
| `post_switch`       | string  | `null`  | Runs after switching to an existing worktree.                                                                 |

##### Argument interpolation

All string fields support `$1`, `$2`, `$3`, etc. placeholders that are replaced with arguments passed to the custom script:

```bash
# Invoke custom script directly (recommended)
awt ghllm 123

# Or using the legacy flag
awt --custom-script="ghllm 123"

# $1 is replaced with "123" in all fields
```

##### Dynamic branch naming

When `branch_name` is set, the command is executed and its stdout becomes the branch name. The output is automatically normalized to be a valid git ref:

-   Converted to lowercase
-   Spaces and underscores become dashes
-   Invalid git ref characters are removed
-   Double dots, consecutive dashes/slashes are collapsed

Example transformations:

| Command output           | Resulting branch name   |
| ------------------------ | ----------------------- |
| `Fix the login bug`      | `fix-the-login-bug`     |
| `Feature: Add OAuth`     | `feature-add-oauth`     |
| `[BUG] Crash on startup` | `bug-crash-on-startup`  |
| `feature/Add user auth`  | `feature/add-user-auth` |

##### Hook inheritance

When `inherit_hooks = true` (the default), hooks run in this order:

1. Global config hook (if defined)
2. Project config hook (if defined)
3. Custom script hook (if defined)

When `inherit_hooks = false`, only the custom script's hooks run; global and project hooks are skipped.

##### Example workflows

**GitHub issue workflow** - Creates a branch named after the issue title:

```toml
[scripts.custom.ghissue]
branch_name = "gh issue view $1 --json title --template '{{.title}}'"
session_init = 'claude "Work on GitHub issue $1: $(gh issue view $1 --json title --template '\''{{.title}}'\'')"'
```

**Release workflow** - Custom pre_create and session_init:

```toml
[scripts.custom.release]
inherit_hooks = false  # Skip normal hooks
pre_create = "git fetch --tags"
session_init = 'claude "/release"'
```

Custom scripts are invoked directly as subcommands:

```bash
# Enhanced format (branch_name field) - issue number is an argument
awt ghissue 123

# Simple format - first argument is used as the branch name
awt release release-v2.0
```

**Resolution priority**: When `autowt` receives an unknown command, it checks in this order:

1. Built-in commands (`ls`, `cleanup`, `config`, `switch`, and their aliases)
2. Custom scripts (matches against `[scripts.custom]` names)
3. Branch names (treats the command as a branch to switch to)

If you have a custom script named `main` and want to switch to a branch named `main`, use `awt switch main` to force branch interpretation.

---

### `[confirmations]` - User interface

Manage which operations require a confirmation prompt.

<div class="autowt-clitable-wrapper"></div>

| Key                | Type    | Default | Description                                                                                                                               |
| ------------------ | ------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `cleanup_multiple` | boolean | `true`  | Ask for confirmation before cleaning up multiple worktrees in non-interactive mode. <br> **ENV**: `AUTOWT_CONFIRMATIONS_CLEANUP_MULTIPLE` |
| `force_operations` | boolean | `true`  | Ask for confirmation when using a `--force` flag. <br> **ENV**: `AUTOWT_CONFIRMATIONS_FORCE_OPERATIONS`                                   |

You can skip all confirmations for a single command by using the `-y` or `--yes` flag.
