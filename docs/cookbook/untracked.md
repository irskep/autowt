# Copying Untracked Files Like `.env`

You can configure autowt to copy important untracked files from your main worktree into all new worktrees using either the `post_create` or the `post_create_async` hook. Common files that need to be copied like this include `.env`, `.pem` files for SSL certificates, and `.claude` directories if you don't check those into git.

The features of autowt that make this easy are the `post_create`/`post_create_async` hooks which run scripts at worktree creation time, and the `$AUTOWT_MAIN_REPO_DIR` env var, which is available in scripts for use cases just like this one.

`post_create` will do the copy _before_ opening the new terminal:

```toml
[scripts]
post_create = "cp $AUTOWT_MAIN_REPO_DIR/.env .env"
```

`post_create_async` will do the copy _after_ opening the new terminal, which can be good for expensive operations:

```toml
[scripts]
post_create_async = "cp $AUTOWT_MAIN_REPO_DIR/.env .env"
```

But for copying untracked files, usually you want `post_create`, not `post_create_async`.

## Multiple files

Use `cp -r`, or `rsync`:

```toml
[scripts]
post_create = "cp -r $AUTOWT_MAIN_REPO_DIR/.claude .claude"
```
