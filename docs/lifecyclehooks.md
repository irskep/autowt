# Lifecycle Hooks and Init Scripts

`autowt` allows you to run custom commands at specific points during worktree operations. This enables powerful automation for everything from dependency installation to resource management and service orchestration.

## Getting Started with Init Scripts

The most common hook is the **session_init script**, which runs in your terminal session after creating a new worktree. This is perfect for setting up your shell environment, activating virtual environments, and running interactive setup tasks.

### Configuration

You can specify a session_init script in two ways:

1. **Command-line flag**: Use the `--init` flag for a one-time script (maps to session_init)
2. **Configuration file**: Set the `scripts.session_init` key in your `.autowt.toml` file for a project-wide default

The session_init script is executed in your terminal session *after* `autowt` has switched to the worktree, but *before* any `--after-init` script is run.

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
session_init = "npm install"
```

Now, `npm install` will run automatically every time you create a new worktree in this project.

### Copying `.env` files

Worktrees start as clean checkouts, which means untracked files like `.env` are not automatically carried over. You can use an init script to copy these files from your main worktree.

autowt provides environment variables that make this easier, including `AUTOWT_MAIN_REPO_DIR` which points to the main repository directory.

```toml
# .autowt.toml
[scripts]
# Copy .env file from main worktree if it exists
session_init = """
if [ -f "$AUTOWT_MAIN_REPO_DIR/.env" ]; then
  cp "$AUTOWT_MAIN_REPO_DIR/.env" .;
fi
"""
```

**Combining commands:**

```toml
# .autowt.toml
[scripts]
session_init = """
if [ -f "$AUTOWT_MAIN_REPO_DIR/.env" ]; then
  cp "$AUTOWT_MAIN_REPO_DIR/.env" .;
fi;
npm install
"""
```

!!! tip "Overriding the Default"

    If you have a `scripts.session_init` script in your `.autowt.toml` but want to do something different for a specific worktree, the `--init` flag will always take precedence.

    ```bash
    # This will run *only* `npm ci`, ignoring the default session_init script.
    autowt feature/performance --init "npm ci"
    ```

## Complete Lifecycle Hooks

Beyond session_init scripts, autowt supports 7 lifecycle hooks that run at specific points during worktree operations:

| Hook | When it runs | Execution Context | Common use cases |
|------|-------------|------------------|------------------|
| `post_create` | After creating worktree, before terminal switch | Subprocess | File operations, git setup, dependency installation |
| `session_init` | In terminal session after switching to worktree | Terminal session | Environment setup, virtual env activation, shell config |
| `pre_cleanup` | Before cleaning up worktrees | Subprocess | Release ports, backup data |
| `pre_process_kill` | Before killing processes | Subprocess | Graceful shutdown |
| `post_cleanup` | After worktrees are removed | Subprocess | Clean volumes, update state |
| `pre_switch` | Before switching worktrees | Subprocess | Stop current services |  
| `post_switch` | After switching worktrees | Subprocess | Start new services |

## Configuration

### Project-level hooks

Configure hooks in your project's `.autowt.toml` file:

```toml
# .autowt.toml
[scripts]
post_create = "npm install && cp .env.example .env"
session_init = "source .env && npm run dev"
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

**Both global and project hooks run**—global hooks execute first, then project hooks. This allows you to set up global defaults while still customizing behavior per project.

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
- **Multi-line scripts work naturally**—the shell handles newlines and command separation
- **All shell features are available**—variables, conditionals, loops, pipes, redirections, etc.
- **Shebangs are ignored**—since no file is created, `#!/bin/bash` lines are treated as comments

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

### `post_create` Hook

**Timing**: After worktree creation, before terminal switch  
**Execution Context**: Subprocess in worktree directory  
**Use cases**: File operations, git setup, dependency installation, configuration copying

```toml
[scripts]
post_create = """
npm install
cp .env.example .env
git config user.email "dev@example.com"
"""
```

The post_create hook runs as a subprocess after the worktree is created but before switching to the terminal session. It's ideal for:

- Installing dependencies that don't require shell interaction
- Setting up configuration files
- Running git commands
- File operations that don't need shell environment

### `session_init` Hook

**Timing**: In terminal session after switching to worktree  
**Execution Context**: Terminal session (pasted/typed into terminal)  
**Use cases**: Environment setup, virtual environment activation, shell configuration

```toml
[scripts]
session_init = """
source .env
conda activate myproject
export DEV_MODE=true
"""
```

The session_init hook is special—it's the only hook that runs **inside the terminal session**. While other lifecycle hooks run as background subprocesses, session_init scripts are literally pasted/typed into the terminal using terminal automation (AppleScript on macOS, tmux send-keys, etc.). This allows session_init scripts to:

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

## Real-World Examples

### Docker Port Management

**Problem**: Running multiple Docker development environments simultaneously causes port conflicts.

**Solution**: Use hooks to allocate and release unique ports per worktree.

#### Implementation

Create port management scripts:

```bash
# scripts/allocate-ports.sh
#!/bin/bash
BRANCH_NAME="$AUTOWT_BRANCH_NAME"
WORKTREE_DIR="$AUTOWT_WORKTREE_DIR"

# Create a simple port allocation system
PORT_BASE=3000
PORT_FILE="$WORKTREE_DIR/.devports"

# Generate deterministic port from branch name hash
PORT=$(echo "$BRANCH_NAME" | shasum | cut -c1-2)
PORT=$((PORT_BASE + (16#$PORT % 100)))

echo "API_PORT=$PORT" > "$PORT_FILE"
echo "DB_PORT=$((PORT + 1))" >> "$PORT_FILE"
echo "REDIS_PORT=$((PORT + 2))" >> "$PORT_FILE"

echo "Allocated ports for $BRANCH_NAME: $PORT-$((PORT + 2))"
```

```bash
# scripts/release-ports.sh
#!/bin/bash
BRANCH_NAME="$AUTOWT_BRANCH_NAME"
WORKTREE_DIR="$AUTOWT_WORKTREE_DIR"

if [ -f "$WORKTREE_DIR/.devports" ]; then
    echo "Releasing ports for $BRANCH_NAME"
    rm "$WORKTREE_DIR/.devports"
fi
```

Update your configuration:

```toml
# .autowt.toml
[scripts]
init = """
./scripts/allocate-ports.sh "$AUTOWT_BRANCH_NAME" "$AUTOWT_WORKTREE_DIR"
source .devports
docker-compose up -d
"""

pre_cleanup = "./scripts/release-ports.sh"
pre_process_kill = "docker-compose down"
```

Update your `docker-compose.yml`:

```yaml
version: '3.8'
services:
  api:
    ports:
      - "${API_PORT:-3000}:3000"
  db:
    ports:
      - "${DB_PORT:-5432}:5432"
  redis:
    ports:
      - "${REDIS_PORT:-6379}:6379"
```

### Database Per Worktree

**Problem**: Feature branches need isolated database environments to avoid data conflicts.

**Solution**: Create and destroy databases automatically per worktree.

#### Implementation

```bash
# scripts/setup-db.sh
#!/bin/bash
BRANCH_NAME="$AUTOWT_BRANCH_NAME"
DB_NAME="myapp_$(echo "$BRANCH_NAME" | sed 's/[^a-zA-Z0-9]/_/g')"

echo "Creating database: $DB_NAME"
createdb "$DB_NAME" || echo "Database already exists"

# Update environment file
echo "DATABASE_URL=postgresql://localhost:5432/$DB_NAME" > .env.local

# Run migrations
npm run db:migrate
```

```bash
# scripts/cleanup-db.sh  
#!/bin/bash
BRANCH_NAME="$AUTOWT_BRANCH_NAME"
DB_NAME="myapp_$(echo "$BRANCH_NAME" | sed 's/[^a-zA-Z0-9]/_/g')"

echo "Dropping database: $DB_NAME"
dropdb "$DB_NAME" 2>/dev/null || echo "Database not found"
```

```toml
# .autowt.toml
[scripts]
init = """
npm install
./scripts/setup-db.sh "$AUTOWT_BRANCH_NAME"
"""

post_cleanup = "./scripts/cleanup-db.sh"
```

### Service Orchestration

**Problem**: Development requires multiple services (API, frontend, background jobs) to run in coordination.

**Solution**: Use hooks to manage service lifecycle across worktree switches.

#### Implementation

```bash
# scripts/start-services.sh
#!/bin/bash
WORKTREE_DIR="$AUTOWT_WORKTREE_DIR"
BRANCH_NAME="$AUTOWT_BRANCH_NAME"

cd "$WORKTREE_DIR"

# Stop any existing services for this worktree
pkill -f "worktree:$BRANCH_NAME" 2>/dev/null || true

# Start services with branch identifier
echo "Starting services for $BRANCH_NAME"

# Start API server
nohup npm run api -- --name "worktree:$BRANCH_NAME" > logs/api.log 2>&1 &
echo $! > .pids/api.pid

# Start frontend dev server  
nohup npm run dev -- --name "worktree:$BRANCH_NAME" > logs/frontend.log 2>&1 &
echo $! > .pids/frontend.pid

# Start background worker
nohup npm run worker -- --name "worktree:$BRANCH_NAME" > logs/worker.log 2>&1 &
echo $! > .pids/worker.pid

echo "Services started for $BRANCH_NAME"
```

```bash
# scripts/stop-services.sh
#!/bin/bash
WORKTREE_DIR="$AUTOWT_WORKTREE_DIR" 
BRANCH_NAME="$AUTOWT_BRANCH_NAME"

cd "$WORKTREE_DIR"

# Stop services using PID files
for pidfile in .pids/*.pid; do
    if [ -f "$pidfile" ]; then
        PID=$(cat "$pidfile")
        kill "$PID" 2>/dev/null && echo "Stopped process $PID"
        rm "$pidfile"
    fi
done

# Cleanup any remaining processes
pkill -f "worktree:$BRANCH_NAME" 2>/dev/null || true
```

```toml
# .autowt.toml  
[scripts]
init = """
npm install
mkdir -p logs .pids
"""

pre_switch = "./scripts/stop-services.sh"
post_switch = "./scripts/start-services.sh"
pre_cleanup = "./scripts/stop-services.sh"
```

### External Tool Integration

**Problem**: Need to integrate with external tools like monitoring, deployment pipelines, or team notifications.

**Solution**: Use hooks to trigger external integrations.

#### Implementation

```bash
# scripts/notify-team.sh
#!/bin/bash
BRANCH_NAME="$AUTOWT_BRANCH_NAME"
HOOK_TYPE="$AUTOWT_HOOK_TYPE"
WORKTREE_DIR="$AUTOWT_WORKTREE_DIR"

case "$HOOK_TYPE" in
    "post_switch")
        MESSAGE="🚀 Started working on branch: $BRANCH_NAME"
        ;;
    "pre_cleanup")
        MESSAGE="🧹 Cleaning up branch: $BRANCH_NAME"
        ;;
    *)
        exit 0
        ;;
esac

# Send to Slack
curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"$MESSAGE\"}" \
    "$SLACK_WEBHOOK_URL"

# Update development tracking
curl -X POST "https://dev-tracker.company.com/api/branches" \
    -H "Content-Type: application/json" \
    -d "{\"branch\":\"$BRANCH_NAME\",\"status\":\"$HOOK_TYPE\",\"timestamp\":\"$(date -Iseconds)\"}"
```

```toml
# .autowt.toml
[scripts] 
post_switch = "./scripts/notify-team.sh"
pre_cleanup = "./scripts/notify-team.sh"
```

### Tips for Implementation

#### 1. Make scripts idempotent
Ensure scripts can run multiple times safely:

```bash
# Good: Check before creating
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# Good: Use -f to avoid errors
rm -f tempfile

# Good: Use || true for optional commands
pkill myservice || true
```

#### 2. Add error handling
```bash
#!/bin/bash
set -e  # Exit on error

# Your script logic here
if ! command_that_might_fail; then
    echo "Warning: Command failed, continuing anyway" >&2
    exit 0  # Don't fail the hook
fi
```

#### 3. Use configuration files
Store settings in dedicated config files:

```bash
# .autowt/config.sh
export DEFAULT_API_PORT=3000
export DB_HOST=localhost
export REDIS_URL=redis://localhost:6379
```

#### 4. Log hook execution
Add logging to debug issues:

```bash
LOG_FILE="$HOME/.autowt/hooks.log"
echo "$(date): Running $AUTOWT_HOOK_TYPE for $AUTOWT_BRANCH_NAME" >> "$LOG_FILE"
```

#### 5. Test hooks independently
Create a test script:

```bash
#!/bin/bash
# test-hooks.sh
export AUTOWT_BRANCH_NAME="test-branch"
export AUTOWT_WORKTREE_DIR="/tmp/test-worktree"
export AUTOWT_MAIN_REPO_DIR="/tmp/main-repo"
export AUTOWT_HOOK_TYPE="init"

mkdir -p "$AUTOWT_WORKTREE_DIR" "$AUTOWT_MAIN_REPO_DIR"

# Test your hook
./scripts/my-hook.sh "$AUTOWT_WORKTREE_DIR" "$AUTOWT_MAIN_REPO_DIR" "$AUTOWT_BRANCH_NAME"
```

These examples demonstrate how lifecycle hooks can automate complex development scenarios while maintaining clean, predictable behavior across your team.

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