# Automating setup with init scripts

`autowt` allows you to run custom commands every time you create or switch to a worktree. This is useful for automating repetitive setup tasks like installing dependencies or copying configuration files.

## How it works

You can specify an "init script" in two ways:

1.  **Command-line flag**: Use the `--init` flag for a one-time script.
2.  **Configuration file**: Set the `scripts.init` key in your `.autowt.toml` file for a project-wide default.

The init script is executed in the worktree's directory *after* `autowt` has switched to it, but *before* any `--after-init` script is run.

## Use case 1: Installing dependencies

The most common use case for init scripts is to ensure dependencies are always up-to-date when you switch to a worktree.

### With the `--init` flag:

You can pass the command directly when you create a worktree:

```bash
autowt feature/new-ui --init "npm install"
```

This will run `npm install` in the `feature/new-ui` worktree right after it's created.

### With `.autowt.toml`:

For a more permanent solution, create a `.autowt.toml` file in the root of your repository:

```toml
# .autowt.toml
[scripts]
init = "npm install"
```

Now, `npm install` will run automatically every time you use `autowt` to switch to any worktree in this project, ensuring your dependencies are always in sync.

## Use case 2: Copying `.env` files

Worktrees start as clean checkouts, which means untracked files like `.env` are not automatically carried over. You can use an init script to copy these files from your main worktree.

Git doesn't have a direct command to find the "main" worktree's path, but you can reliably get it by finding the repository's common `.git` directory and then navigating up to the parent directory.

Here is a robust example for your `.autowt.toml` that copies the `.env` file if it exists in the main worktree:

```toml
# .autowt.toml

[scripts]
# 1. Find the main worktree's root directory.
# 2. If an .env file exists there, copy it to the current worktree.
init = """
MAIN_WORKTREE_DIR=$(git rev-parse --path-format=absolute --git-common-dir)/..;
if [ -f "$MAIN_WORKTREE_DIR/.env" ]; then
  cp "$MAIN_WORKTREE_DIR/.env" .;
fi
"""
```

#### Combining commands

You can combine this with other commands. For example, to copy the `.env` file *and* install dependencies:

```toml
# .autowt.toml
[scripts]
init = """
MAIN_WORKTREE_DIR=$(git rev-parse --path-format=absolute --git-common-dir)/..;
if [ -f "$MAIN_WORKTREE_DIR/.env" ]; then
  cp "$MAIN_WORKTREE_DIR/.env" .;
fi;
npm install
"""
```

This multi-line script will be executed as a single command, automating your entire setup process.

!!! tip "Overriding the Default"

    If you have a `scripts.init` script in your `.autowt.toml` but want to do something different for a specific worktree, the `--init` flag will always take precedence.

    ```bash
    # This will run *only* `npm ci`, ignoring the default init script.
    autowt feature/performance --init "npm ci"
    ```

## Advanced: Lifecycle hooks

Beyond init scripts, autowt supports additional **lifecycle hooks** that run at specific points during worktree operations:

| Hook | When it runs | Common use cases |
|------|-------------|------------------|
| `init` | After creating/switching to worktree | Install deps, copy configs |
| `pre_cleanup` | Before cleaning up worktrees | Release ports, backup data |
| `pre_process_kill` | Before killing processes | Graceful shutdown |
| `post_cleanup` | After worktrees are removed | Clean volumes, update state |
| `pre_switch` | Before switching worktrees | Stop current services |  
| `post_switch` | After switching worktrees | Start new services |

### Quick example

```toml
# .autowt.toml
[scripts]
init = "npm install"
pre_cleanup = "./scripts/release-ports.sh"
pre_process_kill = "docker-compose down"
```

For detailed information on lifecycle hooks, see the [Lifecycle Hooks](lifecycle-hooks.md) documentation.

---
*[git worktree]: A native Git feature that allows you to have multiple working trees attached to the same repository, enabling you to check out multiple branches at once.
*[main worktree]: The original repository directory, as opposed to the worktree directories managed by `autowt`.