# Lifecycle Hooks

Lifecycle hooks allow you to run custom scripts at specific points during autowt operations. They provide fine-grained control over your development workflow, enabling everything from resource management to service orchestration.

## Overview

Autowt supports 6 lifecycle hooks that run at different stages:

| Hook | Trigger | Execution Context | Common Use Cases |
|------|---------|-------------------|------------------|
| `init` | After creating/switching to worktree | In terminal session | Install dependencies, copy configs |
| `pre_cleanup` | Before cleaning up worktrees | Before process termination | Release resources, backup data |
| `pre_process_kill` | Before killing processes in worktrees | Before `SIGINT`/`SIGKILL` | Graceful service shutdown |
| `post_cleanup` | After worktrees are removed | After directory cleanup | Remove volumes, update global state |
| `pre_switch` | Before switching to a worktree | Before terminal switch | Stop services in current worktree |
| `post_switch` | After switching to a worktree | After terminal switch | Start services in new worktree |

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

### Environment variables

All hooks receive the following environment variables:

- `AUTOWT_WORKTREE_DIR`: Path to the worktree directory
- `AUTOWT_MAIN_REPO_DIR`: Path to the main repository directory
- `AUTOWT_BRANCH_NAME`: Name of the branch
- `AUTOWT_HOOK_TYPE`: Type of hook being executed

### Positional arguments

Hooks also receive positional arguments in this order:

1. Worktree directory path
2. Main repository directory path  
3. Branch name

### Example hook script

```bash
#!/bin/bash
# my-hook.sh

# Access via environment variables
echo "Hook type: $AUTOWT_HOOK_TYPE"
echo "Worktree: $AUTOWT_WORKTREE_DIR"
echo "Branch: $AUTOWT_BRANCH_NAME"

# Or access via positional arguments
WORKTREE_DIR="$1"
MAIN_REPO_DIR="$2"
BRANCH_NAME="$3"

cd "$WORKTREE_DIR"
# Do work here...
```

## Hook Details

### `init` Hook

**Timing**: After worktree creation/switch, before after-init commands  
**Use cases**: Dependency installation, configuration setup

```toml
[scripts]
init = """
npm install
cp .env.example .env
"""
```

The init hook is special - it's the only hook that runs in the terminal session context, allowing it to affect the user's environment.

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

## Environment Variables

### Available in all hooks

- `AUTOWT_WORKTREE_DIR`: Absolute path to worktree directory
- `AUTOWT_MAIN_REPO_DIR`: Absolute path to main repository  
- `AUTOWT_BRANCH_NAME`: Branch name
- `AUTOWT_HOOK_TYPE`: One of: `init`, `pre_cleanup`, `pre_process_kill`, `post_cleanup`, `pre_switch`, `post_switch`

### Standard environment

Hooks also inherit your standard shell environment, so you can access:

- `PATH`, `HOME`, `USER` etc.
- Project-specific variables from `.env` files (if loaded)
- CI/CD environment variables

## Troubleshooting

### Hook not running

1. Verify hook is defined in correct configuration file
2. Check file permissions for external script files
3. Use absolute paths or ensure scripts are in `PATH`

### Hook failing

1. Check autowt logs for error messages
2. Test hook script independently: `AUTOWT_BRANCH_NAME=test ./my-hook.sh /path/to/worktree /path/to/main test`
3. Add debug output to your hooks with `echo` statements

### Performance

Hooks run synchronously and can slow down autowt operations. For long-running tasks:

1. Run tasks in background with `&`
2. Use external job queues
3. Keep hooks focused and fast