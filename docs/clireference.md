# CLI reference

This page provides a comprehensive reference for all `autowt` commands, their options, and usage patterns. For a hands-on introduction, check out the [Getting Started](gettingstarted.md) guide.

### `autowt <branch-name>`
*(Alias: `autowt switch <branch-name>`)*

This is the primary and most convenient way to use `autowt`. It's a dynamic command that intelligently handles switching to an existing worktree or creating a new one. `autowt` automatically determines whether the branch exists locally or on the remote, or if it needs to be created from your repository's main branch.

The `autowt <branch-name>` form is a convenient shortcut. Use the explicit `switch` command if your branch name conflicts with another `autowt` command (e.g., `autowt switch cleanup`).

<div class="autowt-clitable-wrapper"></div>

| Option | Description |
|---|---|
| `--terminal <mode>` | Overrides the default terminal behavior. Modes include `tab`, `window`, `inplace`, and `echo`. See [Terminal Support](terminalsupport.md) for details. |
| `--init <script>` | Runs a setup script in the new terminal session (maps to `session_init` hook). Ideal for environment setup and shell configuration. See [Lifecycle Hooks](lifecyclehooks.md). |
| `--after-init <script>` | Runs a command *after* the `session_init` script completes. Perfect for starting a dev server or an [AI agent](agents.md). |
| `--ignore-same-session` | Forces `autowt` to create a new terminal, even if a session for that worktree already exists. |
| `--from <branch>` | Source branch/commit to create worktree from. Accepts any git revision: branch names, tags, commit hashes, `HEAD`, etc. Only used when creating new worktrees. |
| `--dir <path>` | Directory path for the new worktree. Overrides the configured directory pattern. Supports both absolute and relative paths. |
| `--custom-script <script>` | Runs a named custom script with arguments. Scripts are defined in your configuration file. Example: `--custom-script="bugfix 123"`. |
| `--waiting` | Switch to first agent waiting for input. |
| `--latest` | Switch to most recently active agent. |
| `-y`, `--yes` | Automatically confirms all prompts, such as the prompt to switch to an existing terminal session. |

### `autowt ls`
*(Alias: `list`)*

Lists all worktrees for the current project, indicating the main worktree, your current location, and any active terminal sessions. Running `autowt` with no arguments is equivalent to `autowt ls`.

The @ symbol indicates that there is an active terminal session for a worktree. When using Claude Code with agent monitoring enabled, you'll also see agent status indicators like `C?` (waiting), `C…` (working), `C~` (processing), and `C*` (subagent complete). See [AI Agents](agents.md) for detailed information about agent status monitoring.

```txt
> autowt ls

  Worktrees:
→ ~/dev/my-project (main worktree)                         main ←
  ~/dev/my-project-worktrees/feature-new-ui @   feature-new-ui
  ~/dev/my-project-worktrees/hotfix-bug              hotfix-bug
```

### `autowt cleanup`

Safely removes worktrees, their directories, and associated local git branches. By default, it launches an interactive TUI to let you select which worktrees to remove. For more on cleanup strategies, see the [Branch Management](branchmanagement.md) guide.

<div class="autowt-clitable-wrapper"></div>

| Option | Description |
|---|---|
| `--mode <mode>` | Sets the cleanup mode. If not specified in a non-interactive environment (like CI), the command will exit. <br> • `interactive`: (Default in a TTY) Opens a TUI to let you choose what to remove. <br> • `all`: Non-interactively selects all merged and remoteless branches. <br> • `merged`: Selects branches that have been merged into your main branch. <br> • `remoteless`: Selects local branches that don't have an upstream remote. |
| `--dry-run` | Previews which worktrees and branches would be removed without actually deleting anything. |
| `--force` | **Use with caution.** Force-removes worktrees even if they have uncommitted changes. |
| `--kill` / `--no-kill` | Overrides the configured behavior for terminating processes running in a worktree's directory before removal. |

### `autowt config`
*(Aliases: `configure`, `settings`)*

Opens an interactive TUI to configure global `autowt` settings, such as the default terminal mode. Learn more in the [Configuration](configuration.md) guide.

<div class="autowt-clitable-wrapper"></div>

| Option | Description |
|---|---|
| `--show` | Display current configuration values from all sources (global and project). Useful for debugging configuration issues. |

### `autowt shellconfig`

Displays a function you could choose to add to your shell config to cd to worktrees without needing autowt to control your terminal program.

<div class="autowt-clitable-wrapper"></div>

| Option | Description |
|---|---|
| `--shell <shell>` | Override shell detection. Supported shells: `bash`, `zsh`, `fish`, `tcsh`, `csh`, `nu`, `oil`, `elvish`. |

For example, if you use zsh, you'd see this:

```zsh
# Shell Integration for autowt
# Add this function to your shell configuration for convenient worktree switching:

# Add to ~/.zshrc:
# Example usage: autowt_cd feature-branch
autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }
```

Once added to your shell's config, you can run `autowt_cd my-branch` to change the directory of your *current* terminal session, which is useful in terminals that don't support advanced control.

### `autowt agents`

Shows a live dashboard of Claude Code agent status across worktrees. Auto-refreshes every few seconds and provides keyboard navigation.

<div class="autowt-clitable-wrapper"></div>

| Option | Description |
|---|---|
| `--debug` | Enables verbose debug logging. |

Press `q` to quit, arrow keys to navigate, Enter to switch worktrees, `w` to jump to waiting agents.

### `autowt hooks-install`

Installs Claude Code hooks for agent monitoring. Hooks track agent status and create status files. Only available when Claude CLI is installed.

<div class="autowt-clitable-wrapper"></div>

| Option | Description |
|---|---|
| `--user` | Install hooks at user level (affects all projects). |
| `--project` | Install hooks at project level (current project only). |
| `--dry-run` | Show what would be installed without making changes. |
| `--show` | Display currently installed autowt hooks. |
| `--remove` | Remove autowt hooks (requires --user or --project). |

### Global options

These options can be used with any `autowt` command.

<div class="autowt-clitable-wrapper"></div>

| Option | Description |
|---|---|
| `-y`, `--yes` | Automatically answers "yes" to all confirmation prompts. |
| `--debug` | Enables verbose debug logging for troubleshooting. |
| `-h`, `--help` | Shows the help message for `autowt` or a specific subcommand. |
| `--version` | Shows the autowt version and exits. |
