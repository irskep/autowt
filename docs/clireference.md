# CLI reference

This page provides a comprehensive reference for all `autowt` commands, their options, and usage patterns. For a hands-on introduction, check out the [Getting Started](gettingstarted.md) guide.

### `autowt <branch-name>` / `autowt switch`

_(Aliases: `autowt switch <branch-name>`, `autowt sw <branch-name>`, `autowt checkout <branch-name>`, `autowt co <branch-name>`, `autowt goto <branch-name>`, `autowt go <branch-name>`)_

Switch to a worktree, or create a new one. Accepts either a branch name or a path to an existing worktree. Intelligently checks out existing branches from your default remote (i.e. `origin`), or offers to create a new one if none exists.

**Interactive Mode**: Running `autowt switch` with no arguments opens an interactive TUI.

The `autowt <branch-name>` form is a convenient shortcut. Use the explicit `switch` command if your branch name conflicts with another `autowt` command (e.g., `autowt switch cleanup`).

<div class="autowt-clitable-wrapper"></div>

| Option                     | Description                                                                                                                                                                |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--terminal <mode>`        | Overrides the default terminal behavior. Modes include `tab`, `window`, `inplace`, `echo`, `vscode`, and `cursor`. See [Terminal Support](terminalsupport.md) for details. |
| `--after-init <script>`    | Runs a command _after_ the `session_init` script completes. Perfect for starting a dev server.                                                                             |
| `--ignore-same-session`    | Forces `autowt` to create a new terminal, even if a session for that worktree already exists.                                                                              |
| `--from <branch>`          | Source branch/commit to create worktree from. Accepts any git revision: branch names, tags, commit hashes, `HEAD`, etc. Only used when creating new worktrees.             |
| `--dir <path>`             | Directory path for the new worktree. Overrides the configured directory pattern. Supports both absolute and relative paths.                                                |
| `--custom-script <script>` | Runs a named custom script with arguments. Scripts are defined in your configuration file. Example: `--custom-script="bugfix 123"`.                                        |
| `-y`, `--yes`              | Automatically confirms all prompts, such as the prompt to switch to an existing terminal session.                                                                          |

### `autowt ls`

_(Aliases: `list`, `ll`)_

Lists all worktrees for the current project, indicating the main worktree, your current location, and any active terminal sessions. Running `autowt` with no arguments is equivalent to `autowt ls`.

The @ symbol indicates that there is an active terminal session for a worktree.

```txt
> autowt ls

  Worktrees:
→ ~/dev/my-project (main worktree)                         main ←
  ~/dev/my-project-worktrees/feature-new-ui @   feature-new-ui
  ~/dev/my-project-worktrees/hotfix-bug              hotfix-bug
```

### `autowt cleanup [WORKTREES...]`

_(Aliases: `cl`, `clean`, `prune`)_

Safely removes worktrees, their directories, and associated local git branches. By default, it launches an interactive TUI to let you select which worktrees to remove. For more on cleanup strategies, see the [Branch Management](branchmanagement.md) guide.

You can optionally specify one or more worktrees to remove by passing their branch names or paths as arguments. When worktrees are specified, the command skips the interactive TUI and mode-based selection, and instead prompts for simple yes/no confirmation.

<div class="autowt-clitable-wrapper"></div>

| Option          | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--mode <mode>` | Sets the cleanup mode. Ignored when specific worktrees are provided. If not specified in a non-interactive environment (like CI), the command will exit. <br> • `interactive`: Opens a TUI to let you choose what to remove. <br> • `all`: Non-interactively selects all merged and remoteless branches. <br> • `merged`: Selects branches that have been merged into your main branch. <br> • `remoteless`: Selects local branches that don't have an upstream remote. <br> • `github`: Uses the GitHub CLI (`gh`) to identify branches with merged or closed pull requests. Requires `gh` to be installed. <br><br> **First-run behavior**: If you haven't configured a preferred cleanup mode, autowt will prompt you to select one on first use. Your selection is saved for future use. <br><br> **Default behavior in TTY**: For GitHub repositories (origin remote contains github.com), defaults to `github` mode. For other repositories, uses your configured default mode. |
| `--dry-run`     | Previews which worktrees and branches would be removed without actually deleting anything.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `--force`       | Force-removes worktrees even if they contain uncommitted changes or untracked files. Without this flag, git will refuse to remove worktrees that have any modified tracked files or untracked files (which is common - e.g., build artifacts, `.DS_Store`, etc.).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

### `autowt config`

_(Aliases: `configure`, `settings`, `cfg`, `conf`)_

Opens an interactive TUI to configure global `autowt` settings, such as the default terminal mode. Learn more in the [Configuration](configuration.md) guide.

<div class="autowt-clitable-wrapper"></div>

| Option   | Description                                                                                                            |
| -------- | ---------------------------------------------------------------------------------------------------------------------- |
| `--show` | Display current configuration values from all sources (global and project). Useful for debugging configuration issues. |

### `autowt shellconfig`

!!! warning

    This feature is experimental.

_(Alias: `shconf`)_

Displays a function you could choose to add to your shell config to cd to worktrees without needing autowt to control your terminal program.

<div class="autowt-clitable-wrapper"></div>

| Option            | Description                                                                                              |
| ----------------- | -------------------------------------------------------------------------------------------------------- |
| `--shell <shell>` | Override shell detection. Supported shells: `bash`, `zsh`, `fish`, `tcsh`, `csh`, `nu`, `oil`, `elvish`. |

For example, if you use zsh, you'd see this:

```zsh
# Shell Integration for autowt
# Add this function to your shell configuration for convenient worktree switching:

# Add to ~/.zshrc:
# Example usage: autowt_cd feature-branch
autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }
```

Once added to your shell's config, you can run `autowt_cd my-branch` to change the directory of your _current_ terminal session, which is useful in terminals that don't support advanced control.

### Global options

These options can be used with any `autowt` command.

<div class="autowt-clitable-wrapper"></div>

| Option         | Description                                                   |
| -------------- | ------------------------------------------------------------- |
| `-y`, `--yes`  | Automatically answers "yes" to all confirmation prompts.      |
| `--debug`      | Enables verbose debug logging for troubleshooting.            |
| `-h`, `--help` | Shows the help message for `autowt` or a specific subcommand. |
| `--version`    | Shows the autowt version and exits.                           |
