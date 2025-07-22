# Lifecycle Hooks and Init Scripts

`autowt` allows you to run custom commands at specific points during worktree operations. This enables powerful automation for everything from dependency installation to resource management and service orchestration.

## Getting Started with Init Scripts

The most common hook is the **init script**, which runs after creating a new worktree. This is perfect for automating setup tasks like installing dependencies or copying configuration files.

### Configuration

You can specify an init script in two ways:

1. **Command-line flag**: Use the `--init` flag for a one-time script
2. **Configuration file**: Set the `scripts.init` key in your `.autowt.toml` file for a project-wide default

The init script is executed in the worktree's directory *after* `autowt` has switched to it, but *before* any `--after-init` script is run.

### Installing dependencies

The most common use case for init scripts is to ensure dependencies are always up-to-date when you create a worktree.

**With the `--init` flag:**

```bash
autowt feature/new-ui --init "npm install"
```

**With `.autowt.toml`:**

```toml
# .autowt.toml
[scripts]
init = "npm install"
```

Now, `npm install` will run automatically every time you create a new worktree in this project.

### Copying `.env` files

Worktrees start as clean checkouts, which means untracked files like `.env` are not automatically carried over. You can use an init script to copy these files from your main worktree.

autowt provides environment variables that make this easier, including `AUTOWT_MAIN_REPO_DIR` which points to the main repository directory.

```toml
# .autowt.toml
[scripts]
# Copy .env file from main worktree if it exists
init = """
if [ -f "$AUTOWT_MAIN_REPO_DIR/.env" ]; then
  cp "$AUTOWT_MAIN_REPO_DIR/.env" .;
fi
"""
```

**Combining commands:**

```toml
# .autowt.toml
[scripts]
init = """
if [ -f "$AUTOWT_MAIN_REPO_DIR/.env" ]; then
  cp "$AUTOWT_MAIN_REPO_DIR/.env" .;
fi;
npm install
"""
```

!!! tip "Overriding the Default"

    If you have a `scripts.init` script in your `.autowt.toml` but want to do something different for a specific worktree, the `--init` flag will always take precedence.

    ```bash
    # This will run *only* `npm ci`, ignoring the default init script.
    autowt feature/performance --init "npm ci"
    ```

## Complete Lifecycle Hooks

Beyond init scripts, autowt supports 6 lifecycle hooks that run at specific points during worktree operations:

| Hook | When it runs | Common use cases |
|------|-------------|------------------|
| `init` | After creating worktree (not when switching) | Install deps, copy configs |
| `pre_cleanup` | Before cleaning up worktrees | Release ports, backup data |
| `pre_process_kill` | Before killing processes | Graceful shutdown |
| `post_cleanup` | After worktrees are removed | Clean volumes, update state |
| `pre_switch` | Before switching worktrees | Stop current services |  
| `post_switch` | After switching worktrees | Start new services |

## Configuration

### Project-level hooks

Configure hooks in your project's `.autowt.toml` file:

```toml
# .autowt.toml
[scripts]
init = "npm install"
pre_cleanup = "./scripts/release-ports.sh"
pre_process_kill = "docker-compose down"
post_cleanup = "./scripts/cleanup-volumes.sh"
pre_switch = "pkill -f 'npm run dev'"
post_switch = "npm run dev &"
```

### Global hooks

Configure hooks globally in `~/.config/autowt/config.toml` (Linux) or `~/Library/Application Support/autowt/config.toml` (macOS):

```toml
# Global config
[scripts]
pre_cleanup = "echo 'Cleaning up worktree...'"
post_cleanup = "echo 'Worktree cleanup complete'"
```

### Hook execution order

**Both global and project hooks run** - global hooks execute first, then project hooks. This allows you to set up global defaults while still customizing behavior per project.

## Environment Variables and Arguments

All hooks receive the following environment variables:

- `AUTOWT_WORKTREE_DIR`: Path to the worktree directory
- `AUTOWT_MAIN_REPO_DIR`: Path to the main repository directory
- `AUTOWT_BRANCH_NAME`: Name of the branch
- `AUTOWT_HOOK_TYPE`: Type of hook being executed

### Example hook script

```bash
# Hook script using environment variables
echo "Hook type: $AUTOWT_HOOK_TYPE"
echo "Worktree: $AUTOWT_WORKTREE_DIR" 
echo "Branch: $AUTOWT_BRANCH_NAME"

cd "$AUTOWT_WORKTREE_DIR"
# Do work here...

# Multi-line scripts work naturally
for file in *.txt; do
    echo "Processing $file"
done
```

**How hook scripts are executed**: Hook scripts are executed by passing the script text directly to the system shell (`/bin/sh` on Unix systems) rather than creating a temporary file. This is equivalent to running `/bin/sh -c "your_script_here"`.

This execution model means:
- **Multi-line scripts work naturally** - the shell handles newlines and command separation
- **All shell features are available** - variables, conditionals, loops, pipes, redirections, etc.
- **Shebangs are ignored** - since no file is created, `#!/bin/bash` lines are treated as comments

```toml
[scripts]
# This works - shell script commands
post_create = """
echo "Setting up worktree"
npm install
mkdir -p logs
"""

# This works - calls external script file (shebang will work here)
post_create = "./setup-script.py"

# This doesn't work - shebang is ignored, shell tries to run Python code
post_create = """#!/usr/bin/env python3
import sys  # Shell doesn't understand this!
"""
```

If you need to use a different programming language, create a separate script file and call it from your hook. The external file can use shebangs normally.

*Technical note: This uses Python's [`subprocess.run()`](https://docs.python.org/3/library/subprocess.html#subprocess.run) with `shell=True`.*

## Hook Details

### `init` Hook

**Timing**: After worktree creation, before after-init commands  
**Use cases**: Dependency installation, configuration setup

```toml
[scripts]
init = """
npm install
cp .env.example .env
"""
```

The init hook is special - it's the only hook that runs **inside the terminal session**. While other lifecycle hooks run as background subprocesses, init scripts are literally pasted/typed into the terminal using terminal automation (AppleScript on macOS, tmux send-keys, etc.). This allows init scripts to:

- Set environment variables that persist in your shell session
- Activate virtual environments (conda, venv, etc.)  
- Start interactive processes
- Inherit your shell configuration and aliases

Other hooks run in isolated subprocesses and are better suited for file operations, Git commands, and non-interactive automation tasks.

### `pre_cleanup` Hook

**Timing**: Before any cleanup operations begin  
**Use cases**: Resource cleanup, data backup, external service notifications

```toml
[scripts]
pre_cleanup = """
# Release allocated ports
./scripts/release-ports.sh $AUTOWT_BRANCH_NAME

# Backup important data
rsync -av data/ ../backup/
"""
```

### `pre_process_kill` Hook

**Timing**: Before autowt terminates processes in worktrees being cleaned up  
**Use cases**: Graceful service shutdown, connection cleanup

```toml
[scripts]
pre_process_kill = """
# Gracefully stop docker containers
docker-compose down --timeout 30

# Close database connections
./scripts/cleanup-db-connections.sh
"""
```

This hook runs before autowt's built-in process termination, giving your services a chance to shut down gracefully.

### `post_cleanup` Hook

**Timing**: After worktrees and branches are removed  
**Use cases**: Volume cleanup, global state updates

```toml
[scripts]
post_cleanup = """
# Clean up docker volumes
docker volume rm ${AUTOWT_BRANCH_NAME}_db_data 2>/dev/null || true

# Update external tracking systems
curl -X DELETE "https://api.example.com/branches/$AUTOWT_BRANCH_NAME"
"""
```

**Note**: The worktree directory no longer exists when this hook runs, but the path is still provided for reference.

### `pre_switch` Hook

**Timing**: Before switching away from current worktree  
**Use cases**: Stop services, save state

```toml
[scripts]
pre_switch = """
# Stop development server
pkill -f "npm run dev" || true

# Save current state
./scripts/save-session-state.sh
"""
```

### `post_switch` Hook

**Timing**: After switching to new worktree  
**Use cases**: Start services, restore state

```toml
[scripts]
post_switch = """
# Start development server in background
nohup npm run dev > dev.log 2>&1 &

# Restore session state
./scripts/restore-session-state.sh
"""
```

## Advanced Patterns

### Conditional execution

Use environment variables to create conditional hooks:

```toml
[scripts]
init = """
if [ "$AUTOWT_BRANCH_NAME" = "main" ]; then
  npm ci  # Use clean install for main branch
else
  npm install  # Regular install for feature branches
fi
"""
```

### Multi-line scripts

TOML supports multi-line strings for complex scripts:

```toml
[scripts]
pre_cleanup = """
echo "Starting cleanup for $AUTOWT_BRANCH_NAME"

# Release port assignments
PORT_FILE="$AUTOWT_WORKTREE_DIR/.dev-port"
if [ -f "$PORT_FILE" ]; then
  PORT=$(cat "$PORT_FILE")
  echo "Releasing port $PORT"
  ./scripts/release-port.sh "$PORT"
fi

# Clean up temporary files
rm -rf "$AUTOWT_WORKTREE_DIR/tmp/"

echo "Pre-cleanup complete"
"""
```

### External scripts

Reference external scripts for better maintainability:

```toml
[scripts]
pre_cleanup = "./scripts/pre-cleanup.sh"
pre_process_kill = "./scripts/graceful-shutdown.sh"
post_cleanup = "./scripts/post-cleanup.sh"
```

### Error handling

Hooks that fail (exit with non-zero status) will log an error but won't stop the autowt operation:

```bash
#!/bin/bash
# Robust hook script

set -e  # Exit on error

# Your hook logic here
if ! ./my-command; then
    echo "Command failed, but continuing..." >&2
    exit 0  # Don't fail the hook
fi
```

## Common Workflows

See [Common Workflows](common-workflows.md) for real-world examples of using hooks for:

- Docker port management
- Database per worktree
- Service orchestration
- External tool integration

## Troubleshooting

### Hook not running

1. Verify hook is defined in correct configuration file
2. Check file permissions for external script files
3. Use absolute paths or ensure scripts are in `PATH`

### Hook failing

1. Check autowt logs for error messages
2. Test hook script independently by running it in a terminal with the same environment variables autowt would provide:
   ```bash
   cd /path/to/your/worktree
   AUTOWT_BRANCH_NAME=test-branch \
   AUTOWT_WORKTREE_DIR=/path/to/worktree \
   AUTOWT_MAIN_REPO_DIR=/path/to/main \
   AUTOWT_HOOK_TYPE=post_create \
   /bin/sh -c 'your_script_here'
   ```
3. Add debug output to your hooks with `echo` statements