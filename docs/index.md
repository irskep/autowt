# autowt: a better git worktree experience

## What are worktrees?

[Worktrees](https://git-scm.com/docs/git-worktree) are a built-in feature of git, which are essentially free clones of a local git repo. History is shared and synced across all worktrees for a given repo. Creating a new worktree is cheap, and you can list all your worktrees with a single command. This makes them a great fit for doing work “in parallel,” or not worrying about having uncommitted changes before working on another branch.

## How autowt simplifies common workflows

While worktrees are powerful, the built-in tooling is minimalistic. Consider what it takes to set up a fresh worktree in a typical workflow:

1. Make a decision about where to put the worktree
2. `git worktree add <worktree_path> -b <branch>`
3. Open a new terminal tab
4. `cd <worktree path>`
5. `uv sync` or `npm install` or whatever your dependency setup is
6. `cp <repo_dir>/.env .` to copy secrets

Congrats, you're done! Type type type, open a PR, and merge it. Now you need to clean up:

1. `git worktree rm .`
2. Close the tab

On the other hand, **with autowt, it looks like this:**

```sh
autowt <branch>
```

And deleting branches that have been merged or are associated with closed PRs looks like this:

```sh
autowt cleanup
```

A lot nicer, right?

Now suppose your team uses an issue tracker like Linear which can suggest branch names based on issue IDs. You could configure autowt to have a custom command to automatically open worktrees for tickets instead of passing a branch name:

```sh
autowt linear ABC-1234 # opens yourname/abc-1234-title-of-the-ticket or whatever
```

## What autowt can do for you

<div class="grid cards" markdown>

-   **:lucide-hand: Worktree ergonomics**

    ***

    It's not hard to learn the commands to manage worktrees, but autowt shortens the most common ones. And autowt integrates with your terminal program to automate opening new sessions. It supports everything [automate-terminal](https://github.com/irskep/automate-terminal), including iTerm2, tmux, Ghostty, and more.

-   **:lucide-factory: Deep, customizable automation**

    ***

    You can define scripts in `.autowt.toml` to run at various points, like after creating a worktree but before switching to it, or before a worktree is cleaned up. Check out [Lifecycle Hooks](./lifecyclehooks.md) for more information.

-   **:lucide-brush-cleaning: Smart cleanup**

    ***

    You can configure autowt to automatically clean up worktrees whose branches have been merged, or even branches which are associated with closed pull requests on GitHub.

-   **:lucide-square-terminal: Friendly TUIs**

    ***

    autowt uses interactive terminal-based UIs where it makes sense. For example, `autowt config` gives you an easy way to edit global settings. `autowt switch` lets you review your worktrees and pick which one to navigate to.

</div>

## Getting started

You'll need Python 3.10+ and a version of `git` released less than ten years ago (2.5+).

First, install autowt:

```bash
pip install autowt
```

Then, make a new worktree for a new or existing branch in your current repo:

```bash
autowt my-new-feature
```

Watch as `autowt` creates a new worktree and opens it in a new terminal tab or window.
