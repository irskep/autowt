# Command Reference

This page documents all autowt commands and their usage.

## `autowt`

Base command that shows list of worktrees (same as `autowt ls`).

<!-- autowt --help -->
```
(help content will be automatically inserted here)
```

## `autowt init`

Initialize autowt state management in the current git repository.

<!-- autowt init --help -->
```
Usage: autowt init [OPTIONS]

  Initialize autowt state management in the current repository.

Options:
  --debug     Enable debug logging
  -h, --help  Show this message and exit.
```

## `autowt ls`

List all worktrees and show current location.

<!-- autowt ls --help -->
```
Usage: autowt ls [OPTIONS]

  List all worktrees and their status.

Options:
  --debug     Enable debug logging
  -h, --help  Show this message and exit.
```

## `autowt cleanup`

Remove merged, identical, or remoteless worktrees.

<!-- autowt cleanup --help -->
```
Usage: autowt cleanup [OPTIONS]

  Clean up merged or remoteless worktrees.

Options:
  --mode [all|remoteless|merged|interactive]
                                  Cleanup mode
  --dry-run                       Show what would be removed without actually
                                  removing
  -y, --yes                       Auto-confirm all prompts
  --force                         Force remove worktrees with modified files
  --debug                         Enable debug logging
  -h, --help                      Show this message and exit.
```

## `autowt config`

Configure terminal behavior using interactive TUI.

<!-- autowt config --help -->
```
Usage: autowt config [OPTIONS]

  Configure autowt settings using interactive TUI.

Options:
  --debug     Enable debug logging
  -h, --help  Show this message and exit.
```

## `autowt switch`

Explicitly switch to a branch worktree.

<!-- autowt switch --help -->
```
Usage: autowt switch [OPTIONS] BRANCH

  Switch to or create a worktree for the specified branch.

Options:
  --terminal [tab|window|inplace|echo]
                                  How to open the worktree terminal
  --init TEXT                     Init script to run in the new terminal
  --debug                         Enable debug logging
  -h, --help                      Show this message and exit.
```