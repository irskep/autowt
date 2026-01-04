# autowt: a better git worktree experience

[**Full documentation**](https://steveasleep.com/autowt/)

<!-- BEGIN SYNCED CONTENT -->
<!-- This content is synced from docs/index.md - do not edit directly -->
<!-- Run 'mise run sync-readme' to update -->

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

**What autowt can do for you:**

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


<!-- END SYNCED CONTENT -->

## Contributing

PRs, GitHub issues, discussion topics, bring 'em on!

## License

This project is licensed under the MIT License.
