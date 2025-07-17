# autowt: git worktree manager

autowt manages git worktrees with automatic terminal switching and cleanup. Each branch gets its own working directory, letting you switch between features without stashing changes or losing context.

## Why worktrees? Why autowt?

<!-- This section reflects the human author's purpose in writing this program. It all comes back to this. -->

Why worktrees: Multitask without switching branches, great for long-running agents like Claude Code

Why autowt:
- Worktrees don't get initialized with untracked files; this is annoying. `.env` is common, as is the need to install dependencies with `uv sync` or `npm install`.
- It takes a lot of typing to set up a worktree and cd into it

Core use case is running multiple Claude Code instances on different problems and submitting independent PRs. I can call `autowt feature1 --after-init='claude "add a pony and submit a PR"'` and it opens a new tab in my terminal with Claude off to the races.

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

**Creating worktrees:** When you run `autowt branch-name`, it fetches the latest branches, creates a worktree at `../reponame-worktrees/branch-name`, and switches to it. New branches are created from the latest main branch. Branch names with slashes like `steve/bugfix` become `steve-bugfix` in the filesystem.

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
  feature-auth      ~/dev/myproject-worktrees/feature-auth 💻
  steve/bugfix      ~/dev/myproject-worktrees/steve-bugfix
  refactor-core     ~/dev/myproject-worktrees/refactor-core 💻

Use 'autowt <branch>' to switch to a worktree or create a new one.
```

The 💻 icon indicates branches with active terminal sessions.

## Cleanup

```bash
autowt cleanup
```

Analyzes your worktrees and categorizes them:

- **Without remotes:** Branches that don't track a remote branch
- **Identical to main:** Branches pointing to the same commit as main/master
- **Merged:** Branches that have been merged into main/master

By default, cleanup removes all categories. Use `--mode` to be selective:

```bash
autowt cleanup --mode all         # All categories (default)
autowt cleanup --mode merged      # Only merged and identical branches
autowt cleanup --mode remoteless  # Only branches without remotes
autowt cleanup --mode interactive # Choose individually with TUI
```

Use `--dry-run` to see what would be removed without actually removing:

```bash
autowt cleanup --dry-run
```

Before removing worktrees, autowt finds running processes in those directories and terminates them with SIGINT, followed by SIGKILL after 10 seconds if needed.

## Terminal Modes

Control how autowt opens terminals:

```bash
autowt branch-name --terminal=tab     # Switch to existing session or new tab (default)
autowt branch-name --terminal=window  # Switch to existing session or new window
autowt branch-name --terminal=inplace # Change directory in current terminal
```

**Smart terminal switching:** When using `tab` or `window` modes, autowt first checks if the worktree already has a terminal session. If it does, it prompts whether to switch to the existing session or create a new one. Use `--yes` to automatically switch to existing sessions without prompting.

With `--terminal=inplace`, autowt outputs shell commands that can be evaluated:

```bash
eval "$(autowt branch-name --terminal=inplace)"
```

Configure the default behavior:

```bash
autowt config
```

This opens an interactive TUI to set your preferred terminal mode.

## Init Scripts

Run custom commands when switching to a worktree:

```bash
autowt branch-name --init "npm install && npm run dev"
```

The init script runs after changing to the worktree directory.

### Project Configuration

Create an `autowt.toml` or `.autowt.toml` file in your project root to set a default init script:

```toml
init = "npm install && npm run dev"
```

This eliminates the need to pass `--init` every time. The command-line `--init` flag still overrides the config file setting.

## State Management

autowt stores its state in platform-appropriate directories:

- **macOS:** `~/Library/Application Support/autowt/`
- **Linux:** `~/.local/share/autowt/` (or `$XDG_DATA_HOME/autowt/`)
- **Windows:** `~/.autowt/`

The state includes worktree locations, current branch tracking, and terminal session mappings for seamless switching.

## Command Reference

- `autowt` - List all worktrees (same as `autowt ls`)
- `autowt init` - Initialize state management
- `autowt [branch]` - Create or switch to worktree for any branch name
- `autowt switch <branch>` - Explicitly switch to a branch (useful when branch name conflicts with commands)
- `autowt ls` - List all worktrees and current location  
- `autowt cleanup` - Remove merged, identical, or remoteless worktrees
- `autowt config` - Configure terminal behavior using interactive TUI

All commands support `-h` for help, `-y/--yes` for auto-confirmation, and `--debug` for verbose logging.

## Installation

```bash
pip install autowt
```

For development:

```bash
git clone https://github.com/your-username/autowt
cd autowt
uv sync
```

## Requirements

- Python 3.10+
- git with worktree support
- iTerm2 on macOS for best terminal integration (falls back to generic methods on other platforms)