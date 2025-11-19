# Getting started with autowt

This guide will walk you through installing `autowt`, setting it up for a project, and using its core features to streamline your development workflow.

## Prerequisites

Before you begin, make sure you have the following installed:

*   **Python 3.10+**: You can check your version with `python3 --version`.
*   **Git 2.5+**: `autowt` relies on modern git worktree functionality. Check your version with `git --version`. Git 2.5 was released in 2015, so this shouldn’t be a problem.
*   **A supported terminal (recommended)**: For the best experience, use a terminal with good tab and window management, like iTerm2 on macOS. See the [Terminal Support](terminalsupport.md) page for more details.

## Installation

### Pip

First, `pip install autowt`. To verify the installation, run `autowt` in a git repository to see its status:

```txt
  Worktrees:
→ ~/dev/my-project (main worktree)             main ←

Use 'autowt <branch>' to switch to a worktree or create a new one.
```

### Mise

You can install autowt in its own virtualenv with Mise and pipx:

```bash
mise use -g pipx:autowt
```

### uvx

If you have [uv](https://docs.astral.sh/uv/) installed, you can invoke autowt without a separate install step via `uvx`:

```bash
uvx autowt
```

### Optional Guake support

If you use the [Guake](http://guake-project.org/) terminal, you can install autowt with Guake support:

```bash
pip install autowt[guake]
```

## Your first worktree

Let's dive in and see `autowt` in action.

### Step 1: Create a new feature branch

Navigate to the root of any git repository you're working on. For this example, let's say your project is located at `~/dev/my-project`.

```bash
cd ~/dev/my-project
```

Now, let's create a worktree for a new feature.

```bash
autowt new-feature
```

Here’s what `autowt` does behind the scenes:

1.  Fetches the latest changes from your remote repository.
2.  Creates a new directory for your worktree at `../my-project-worktrees/new-feature/`.
3.  Creates a new git worktree for the `new-feature` branch. If the branch doesn't exist, it will be created from your main branch.
4.  Opens a new terminal tab or window and navigates to the new worktree directory.

You now have a clean, isolated environment for your new feature, without disturbing the main branch.

### Step 2: List your worktrees

To see an overview of your worktrees, use the `ls` command:

```bash
autowt ls
```

The output will look something like this, with an arrow `→` indicating your current directory and a `@` icon for active terminal sessions.

```txt
  Worktrees:
→ ~/dev/my-project-worktrees/new-feature @      new-feature ←
  ~/dev/my-project (main worktree)               main
```

!!! info

    `autowt` with no arguments is an alias for `autowt ls`.

!!! tip "Interactive switching"

    You can also use `autowt switch` with no arguments to open an interactive TUI that lets you:
    - Select from existing worktrees to switch to
    - Choose branches without worktrees (automatically creates a new worktree)
    - Create a new branch by entering its name

!!! tip "Additional worktree setup"

    If you want dependencies to be installed automatically when creating new worktrees, or need to copy over git-ignored files like `.env` from the main worktree, you can learn how to configure lifecycle hooks in the [Lifecycle Hooks guide](lifecyclehooks.md).

## A typical workflow

Now that you have the basics down, let's walk through a common development scenario.

### Juggling multiple tasks

Imagine you're working on `new-feature` when you get a request for an urgent bug fix. With `autowt`, you don't need to stash your changes. Just create a new worktree for the hotfix:

```bash
autowt hotfix/urgent-bug
```

A new terminal tab opens for the bug fix. You can now work on the fix without affecting your `new-feature` branch. Once you're done with the bug fix, close your terminal tab and forget about it.

If you prefer to stay in your existing terminal tab the whole time, you can pass `--terminal=inplace`:

```bash
autowt hotfix/urgent-bug --terminal=inplace
# code code code, commit, push
autowt new-feature --terminal=inplace
```

For special cases where you need the worktree in a specific location, you can override the default directory pattern with `--dir`:

```bash
# Place in a custom location
autowt urgent-fix --dir /tmp/quick-fix

# Use a relative path from current directory
autowt feature-demo --dir ../demo-workspace
```

Run `autowt config` to configure the default terminal behavior for switching worktrees.

### Cleaning up

Once your `hotfix/urgent-bug` branch is merged and no longer needed, you can clean it up.

First, use the `--dry-run` flag to see what `autowt` will do:

```bash
autowt cleanup --dry-run
```

This will show you a list of branches that are safe to remove. When you're ready, run the command without the flag:

```bash
autowt cleanup
```

On first run, `autowt` will ask you to select your preferred cleanup mode (interactive, merged, remoteless, or github if the GitHub CLI is available). Your choice will be saved for future use. After that, `autowt` will remove the worktree and, if the branch is merged, will also offer to delete the local git branch.

If `autowt cleanup` doesn't want to automatically clean up your branch, you can run `autowt cleanup <branch-name>` explicitly.

---
*[git worktree]: A native Git feature that allows you to have multiple working trees attached to the same repository, enabling you to check out multiple branches at once.
*[main worktree]: The original repository directory, as opposed to the worktree directories managed by `autowt`.