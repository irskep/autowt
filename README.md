# autowt: a better git worktree experience

**autowt** is a [git worktree](https://git-scm.com/docs/git-worktree) manager designed for developers who juggle multiple tasks. It automates the creation, management, and cleanup of git worktrees, giving each branch its own dedicated directory and terminal tab or window.

[**Full documentation**](https://steveasleep.com/autowt/)

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

## Contributing

PRs, GitHub issues, discussion topics, bring 'em on!

## License

This project is licensed under the MIT License.
