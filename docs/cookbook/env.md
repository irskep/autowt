# Copying `.env` files into new git worktrees

You can configure autowt to copy important untracked files from your main worktree into all new worktrees using either the `post_create` or the `post_create_async` hook.

`post_create` will do the copy _before_ opening the new terminal:

```toml
[scripts]
post_create = "cp $AUTOWT_MAIN_REPO_DIR/.env .env"
```

`post_create_async` will do the copy _after_ opening the new terminal:

```toml
[scripts]
post_create_async = "cp $AUTOWT_MAIN_REPO_DIR/.env .env"
```

For cheap operations, it doesn't matter which you choose. It matters if the operations are expensive, when you might prefer to get an interactive terminal before the expensive operation is over. Copying `.env` files is typically cheap.
