# autowt: a better git worktree experience

Consider what it takes to set up a fresh worktree in a typical workflow:

1. Make a decision about where to put the worktree
2. `git worktree add <worktree_path> -b <branch>`
3. Open a new terminal tab
4. `cd <worktree path>`
5. `uv sync` or `npm install` or whatever your dependency setup is
6. `cp <repo_dir>/.env .` to copy secrets

Congrats, you're done! Type type type, open a PR, and merge it. Now you need to clean up:

1. `git worktree rm .`
2. Close the tab

Of course, you might close the tab and forget to clean up the worktree, and your set of worktrees will grow.

On the other hand, with autowt, it looks like this:

```sh
autowt <branch>
# there is no step 2
```

And deleting branches that have been merged or are associated with closed PRs looks like this:

```sh
autowt cleanup
```

A lot nicer, right?

**Type less**

The built-in worktree commands are verbose. `autowt` makes them shorter, and adds automation hooks.

**Terminal program automation**

If you like to keep multiple tabs open, `autowt` can create tabs for new worktrees, and switch to the correct tab for a worktree if you already have it open.

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
