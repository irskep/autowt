# CLI Reference

This page provides a complete reference for all `autowt` commands, their options, and usage patterns.

## Dynamic Branch Command: `autowt <branch-name>`

This is the primary and most frequently used command in `autowt`. It dynamically handles branch creation and switching.

| Option | Description |
| --- | --- |
| `--terminal [tab|window|inplace]` | Specify the terminal mode for this command. |
| `--init <script>` | Run a script after switching to the worktree. |
| `--after-init <script>` | Run a script after the `--init` script completes. |
| `--ignore-same-session` | Always create a new terminal, even if a session for the worktree already exists. |
| `-y`, `--yes` | Auto-confirm all prompts, such as switching to an existing session. |
| `--debug` | Enable verbose debug logging for this command. |

!!! info "Command-Name Conflicts"

    If you have a branch with a name that conflicts with a built-in `autowt` command (e.g., a branch named `cleanup`), you must use the `switch` command to access it: `autowt switch cleanup`.

---

## Core Commands

### `autowt ls`

Lists all worktrees for the current project.

| Option | Description |
| --- | --- |
| `--debug` | Enable debug logging. |

### `autowt switch <branch-name>`

Explicitly switches to or creates a worktree. This is useful for avoiding command-name conflicts.

| Option | Description |
| --- | --- |
| `--terminal [tab|window|inplace]` | Specify the terminal mode. |
| `--init <script>` | Run a script after switching. |
| `-y`, `--yes` | Auto-confirm all prompts. |
| `--debug` | Enable debug logging. |

### `autowt cleanup`

Removes merged, identical, or remoteless worktrees.

| Option | Description |
| --- | --- |
| `--mode [all|merged|remoteless|interactive]` | Set the cleanup mode (default: `all`). |
| `--dry-run` | Preview the cleanup without deleting anything. |
| `--force` | Force removal of worktrees with uncommitted changes. |
| `--kill` / `--no-kill` | Override the configured process-killing behavior. |
| `-y`, `--yes` | Auto-confirm all prompts. |
| `--debug` | Enable debug logging. |

### `autowt config`

Opens an interactive TUI to configure global `autowt` settings.

| Option | Description |
| --- | --- |
| `--debug` | Enable debug logging. |

---

## Global Flags

These flags can be used with any command.

| Flag | Description |
| --- | --- |
| `--version` | Display the installed version of `autowt`. |
| `-h`, `--help` | Show the help message for a command. |
| `--debug` | Enable verbose debug logging. |

---

## Advanced and Debugging Commands

These commands are for advanced use cases and troubleshooting.

| Command | Description |
| --- | --- |
| `autowt register-session-for-path` | Manually registers the current terminal session for the current directory. |
