# CLI reference

This page provides a comprehensive reference for all `autowt` commands, their options, and usage patterns. For a hands-on introduction, check out the [Getting Started](gettingstarted.md) guide.

## `autowt <branch-name>` / `autowt switch`

_(Aliases: `autowt switch <branch-name>`, `autowt sw <branch-name>`, `autowt checkout <branch-name>`, `autowt co <branch-name>`, `autowt goto <branch-name>`, `autowt go <branch-name>`)_

Switch to a worktree, or create a new one. Accepts:

- A branch name (e.g., `feature-branch`)
- A branch name without prefix (if you've configured `branch_prefix`, you can omit it)
- A path to an existing worktree directory

Intelligently checks out existing branches from your default remote (i.e. `origin`), or offers to create a new one if none exists.

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

### Branch resolution

When creating a new worktree, `autowt` automatically:

1. Fetches the latest branches from your remote
2. Checks if the branch exists locally - if so, uses it
3. Checks if the branch exists on your remote (e.g., `origin/branch-name`) - if so, prompts to create a local worktree tracking the remote
4. If the branch doesn't exist anywhere, prompts to create a new branch from your repository's main branch (`main` or `master`)

### Worktree directory organization

By default, worktrees are created in a dedicated directory adjacent to your main project. For example, if your project is in `~/dev/my-project`, worktrees are created in `~/dev/my-project-worktrees/`.

Branch names are sanitized for the filesystem - slashes become hyphens. For example, `feature/user-auth` creates a directory at `~/dev/my-project-worktrees/feature-user-auth/`.

You can customize this with the `directory_pattern` setting (see [Configuration](configuration.md)), which supports template variables like `{repo_name}`, `{branch}`, `{repo_parent_dir}`, and environment variables. For example, to organize all worktrees in a central location: `~/.worktrees/{repo_name}/{branch}`.

## `autowt ls`

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

## `autowt cleanup [WORKTREES...]`

_(Aliases: `cl`, `clean`, `prune`, `rm`, `remove`, `del`, `delete`)_

Safely removes worktrees, their directories, and associated local git branches. By default, it launches an interactive TUI to let you select which worktrees to remove.

You can optionally specify one or more worktrees to remove by passing:

- Branch names (e.g., `autowt cleanup feature-branch`)
- Branch names without prefix (if you've configured `branch_prefix`)
- Paths to worktree directories (e.g., `autowt cleanup ../my-project-worktrees/feature-branch`)

When worktrees are specified, the command skips the interactive TUI and mode-based selection, and instead prompts for simple yes/no confirmation.

<div class="autowt-clitable-wrapper"></div>

| Option          | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--mode <mode>` | Sets the cleanup mode. Ignored when specific worktrees are provided. If not specified in a non-interactive environment (like CI), the command will exit. <br> • `interactive`: Opens a TUI to let you choose what to remove. <br> • `all`: Non-interactively selects all merged and remoteless branches. <br> • `merged`: Selects branches that have been merged into your main branch. <br> • `remoteless`: Selects local branches that don't have an upstream remote. <br> • `github`: Uses the GitHub CLI (`gh`) to identify branches with merged or closed pull requests. Requires `gh` to be installed. <br><br> **First-run behavior**: If you haven't configured a preferred cleanup mode, autowt will prompt you to select one on first use. Your selection is saved for future use. |
| `--dry-run`     | Previews which worktrees and branches would be removed without actually deleting anything.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `--force`       | Force-removes worktrees even if they contain uncommitted changes or untracked files. Without this flag, git will refuse to remove worktrees that have any modified tracked files or untracked files (which is common - e.g., build artifacts, `.DS_Store`, etc.).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

### How cleanup works

When you run cleanup, `autowt`:

1. Identifies worktrees matching the selected mode criteria
2. Prompts for confirmation (shows list of worktrees to be removed)
3. Runs `pre_cleanup` [Lifecycle Hooks](lifecyclehooks.md) if configured
4. Removes the worktree directories from your filesystem
5. Runs `post_cleanup` hooks if configured
6. Prompts to delete the associated local git branches (can be auto-confirmed with `-y`)

Note: Worktrees with uncommitted changes are automatically skipped in non-interactive modes unless you use `--force`.

## `autowt config`

_(Aliases: `configure`, `settings`, `cfg`, `conf`)_

Opens an interactive TUI to configure global `autowt` settings, such as the default terminal mode. Learn more in the [Configuration](configuration.md) guide.

<div class="autowt-clitable-wrapper"></div>

| Option   | Description                                                                                                            |
| -------- | ---------------------------------------------------------------------------------------------------------------------- |
| `--show` | Display current configuration values from all sources (global and project). Useful for debugging configuration issues. |

## Global options

These options can be used with any `autowt` command.

<div class="autowt-clitable-wrapper"></div>

| Option         | Description                                                   |
| -------------- | ------------------------------------------------------------- |
| `-y`, `--yes`  | Automatically answers "yes" to all confirmation prompts.      |
| `--debug`      | Enables verbose debug logging for troubleshooting.            |
| `-h`, `--help` | Shows the help message for `autowt` or a specific subcommand. |
| `--version`    | Shows the autowt version and exits.                           |
