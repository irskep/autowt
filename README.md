# autowt: git worktree manager

autowt manages git worktrees with automatic terminal switching and cleanup. Each branch gets its own working directory, letting you switch between features without stashing changes or losing context.

## Quick Start

Initialize autowt in your git repository:

```bash
autowt init
```

Create or switch to a worktree for any branch:

```bash
autowt feature-branch
```

If the branch exists as a worktree, autowt switches to it. Otherwise, it creates a new worktree and opens it in a new terminal tab.

## Core Workflow

**Creating worktrees:** When you run `autowt branch-name`, it fetches the latest branches, creates a worktree at `../reponame-worktrees/branch-name`, and switches to it. Branch names with slashes like `steve/bugfix` become `steve-bugfix` in the filesystem.

**Terminal integration:** On macOS with iTerm2, autowt uses AppleScript to switch between existing terminal sessions or create new ones. It tracks session IDs to find the right tab when switching back to a worktree.

**Integration:** autowt is designed to work alongside existing development tools and workflows without modifying your git repository's hooks or configuration.

## Listing and Navigation

```bash
autowt ls
```

Shows your primary clone, current location, and all worktrees:

```
Primary clone: ~/dev/myproject
You are in: feature-branch

Branches:
feature-auth      ~/dev/myproject-worktrees/feature-auth
steve/bugfix      ~/dev/myproject-worktrees/steve-bugfix
refactor-core     ~/dev/myproject-worktrees/refactor-core
```

## Cleanup

```bash
autowt cleanup
```

Analyzes your worktrees and categorizes them:

- **Without remotes:** Branches that don't track a remote branch
- **With merge commits:** Branches that have been merged into main/master (including squash merges)

By default, cleanup removes both categories. Use `--mode` to be selective:

```bash
autowt cleanup --mode merged      # Only merged branches
autowt cleanup --mode remoteless  # Only branches without remotes
autowt cleanup --mode interactive # Choose individually
```

Before removing worktrees, autowt finds running processes in those directories and terminates them with SIGINT, followed by SIGKILL after 10 seconds if needed.

## Terminal Modes

Control how autowt opens terminals:

```bash
autowt branch-name --terminal=tab     # New tab (default)
autowt branch-name --terminal=window  # New window
autowt branch-name --terminal=same    # Switch to existing session
autowt branch-name --terminal=inplace # Change directory in current terminal
```

Configure the default behavior:

```bash
autowt config
```

This opens an interactive interface to set your preferred terminal mode and whether to always create new terminals instead of switching to existing ones.

## State Management

autowt stores its state in platform-appropriate directories:

- **macOS:** `~/Library/Application Support/autowt/`
- **Linux:** `~/.local/share/autowt/` (or `$XDG_DATA_HOME/autowt/`)
- **Windows:** `~/.autowt/`

The state includes worktree locations, current branch tracking, and terminal session mappings for seamless switching.

## Command Reference

- `autowt init` - Initialize state management
- `autowt [branch]` - Create or switch to worktree
- `autowt switch [branch]` - Explicitly switch to a branch (useful when branch name conflicts with commands)
- `autowt ls` - List all worktrees and current location  
- `autowt cleanup` - Remove merged or remoteless worktrees
- `autowt config` - Configure terminal behavior

All commands support `-h` for help and show the important git operations they perform, so you can see exactly what's happening under the hood.

## Requirements

- Python 3.10+
- git with worktree support
- iTerm2 on macOS for best terminal integration (falls back to generic methods on other platforms)

Install with:

```bash
pip install autowt
```

Or for development:

```bash
git clone <repo>
cd autowt
uv sync
```