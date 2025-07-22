# Common Workflows with Lifecycle Hooks

This guide provides real-world examples of using autowt's lifecycle hooks to solve common development challenges. Each workflow addresses practical problems developers face when working with multiple worktrees.

## Docker Port Management

**Problem**: Running multiple Docker development environments simultaneously causes port conflicts.

**Solution**: Use hooks to allocate and release unique ports per worktree.

### Implementation

Create port management scripts:

```bash
# scripts/allocate-ports.sh
#!/bin/bash
BRANCH_NAME="$1"
WORKTREE_DIR="$2"

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
BRANCH_NAME="$1"
WORKTREE_DIR="$2"

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

## Database Per Worktree

**Problem**: Feature branches need isolated database environments to avoid data conflicts.

**Solution**: Create and destroy databases automatically per worktree.

### Implementation

```bash
# scripts/setup-db.sh
#!/bin/bash
BRANCH_NAME="$1"
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
BRANCH_NAME="$1"
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

## Service Orchestration

**Problem**: Development requires multiple services (API, frontend, background jobs) to run in coordination.

**Solution**: Use hooks to manage service lifecycle across worktree switches.

### Implementation

```bash
# scripts/start-services.sh
#!/bin/bash
WORKTREE_DIR="$1"
BRANCH_NAME="$2"

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
WORKTREE_DIR="$1" 
BRANCH_NAME="$2"

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

## External Tool Integration

**Problem**: Need to integrate with external tools like monitoring, deployment pipelines, or team notifications.

**Solution**: Use hooks to trigger external integrations.

### Implementation

```bash
# scripts/notify-team.sh
#!/bin/bash
BRANCH_NAME="$1"
HOOK_TYPE="$2"
WORKTREE_DIR="$3"

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

```bash
# scripts/deployment-webhook.sh
#!/bin/bash
BRANCH_NAME="$1"
REPO_URL="$(git remote get-url origin)"

# Trigger preview deployment
curl -X POST "https://deploy.company.com/api/preview" \
    -H "Content-Type: application/json" \
    -d "{
        \"branch\": \"$BRANCH_NAME\",
        \"repo\": \"$REPO_URL\",
        \"action\": \"create\"
    }"
```

```toml
# .autowt.toml
[scripts] 
init = "./scripts/deployment-webhook.sh"
post_switch = "./scripts/notify-team.sh"
pre_cleanup = "./scripts/notify-team.sh"
```

## Resource Monitoring

**Problem**: Track resource usage across multiple worktrees to identify performance issues.

**Solution**: Use hooks to collect and report metrics.

### Implementation

```bash
# scripts/collect-metrics.sh
#!/bin/bash
BRANCH_NAME="$1"
WORKTREE_DIR="$2"
HOOK_TYPE="$3"

METRICS_FILE="$HOME/.autowt/metrics.log"
mkdir -p "$(dirname "$METRICS_FILE")"

# Collect system metrics
CPU_USAGE=$(ps -o %cpu -p $$ | tail -n 1 | tr -d ' ')
MEMORY_USAGE=$(ps -o %mem -p $$ | tail -n 1 | tr -d ' ')
DISK_USAGE=$(df -h "$WORKTREE_DIR" | tail -n 1 | awk '{print $5}')

# Log metrics
echo "$(date -Iseconds),$BRANCH_NAME,$HOOK_TYPE,$CPU_USAGE,$MEMORY_USAGE,$DISK_USAGE" >> "$METRICS_FILE"

# Send to monitoring service
if [ "$MONITORING_ENDPOINT" ]; then
    curl -X POST "$MONITORING_ENDPOINT/metrics" \
        -H "Content-Type: application/json" \
        -d "{
            \"timestamp\": \"$(date -Iseconds)\",
            \"branch\": \"$BRANCH_NAME\",
            \"hook\": \"$HOOK_TYPE\",
            \"cpu_usage\": $CPU_USAGE,
            \"memory_usage\": $MEMORY_USAGE,
            \"disk_usage\": \"$DISK_USAGE\"
        }"
fi
```

```toml
# .autowt.toml
[scripts]
init = "./scripts/collect-metrics.sh"
pre_cleanup = "./scripts/collect-metrics.sh"
post_switch = "./scripts/collect-metrics.sh"
```

## Environment Synchronization

**Problem**: Keep configuration and secrets synchronized across worktrees while maintaining security.

**Solution**: Use hooks to safely copy and update environment configurations.

### Implementation

```bash
# scripts/sync-env.sh
#!/bin/bash
WORKTREE_DIR="$1"
MAIN_REPO_DIR="$2" 
BRANCH_NAME="$3"

cd "$WORKTREE_DIR"

# Copy environment template
if [ -f "$MAIN_REPO_DIR/.env.template" ]; then
    cp "$MAIN_REPO_DIR/.env.template" .env
fi

# Add branch-specific overrides
cat >> .env << EOF

# Branch-specific configuration
BRANCH_NAME=$BRANCH_NAME
LOG_PREFIX=[$BRANCH_NAME]
CACHE_PREFIX=${BRANCH_NAME//\//_}
EOF

# Source secrets from secure location (not in git)
if [ -f "$HOME/.autowt/secrets.env" ]; then
    echo "# Secrets (not committed)" >> .env
    cat "$HOME/.autowt/secrets.env" >> .env
fi

# Generate unique identifiers
echo "SESSION_SECRET=$(openssl rand -hex 32)" >> .env
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env

echo "Environment configured for $BRANCH_NAME"
```

```bash
# scripts/cleanup-env.sh
#!/bin/bash
WORKTREE_DIR="$1"
BRANCH_NAME="$2"

# Remove sensitive environment files
rm -f "$WORKTREE_DIR/.env" "$WORKTREE_DIR/.env.local"

# Clear any cached credentials
rm -rf "$WORKTREE_DIR/.credentials"

echo "Environment cleaned up for $BRANCH_NAME"
```

```toml
# .autowt.toml
[scripts]
init = """
npm install
./scripts/sync-env.sh "$AUTOWT_WORKTREE_DIR" "$AUTOWT_MAIN_REPO_DIR" "$AUTOWT_BRANCH_NAME"
"""

post_cleanup = "./scripts/cleanup-env.sh"
```

## Testing Automation

**Problem**: Ensure each worktree runs the appropriate tests without manual intervention.

**Solution**: Use hooks to trigger automated testing based on branch patterns and changes.

### Implementation

```bash
# scripts/auto-test.sh
#!/bin/bash
BRANCH_NAME="$1"
WORKTREE_DIR="$2"

cd "$WORKTREE_DIR"

# Determine test strategy based on branch name
case "$BRANCH_NAME" in
    "main"|"master")
        echo "Running full test suite for $BRANCH_NAME"
        npm run test:all
        npm run test:e2e
        ;;
    "hotfix/"*)
        echo "Running critical tests for hotfix"
        npm run test:critical
        ;;
    "feature/"*)
        echo "Running feature tests"
        npm run test:unit
        npm run test:integration
        ;;
    *)
        echo "Running basic tests"
        npm run test:unit
        ;;
esac

# Check test results
if [ $? -eq 0 ]; then
    echo "✅ Tests passed for $BRANCH_NAME"
else
    echo "❌ Tests failed for $BRANCH_NAME"
    # Optionally fail the hook to prevent worktree creation
    # exit 1
fi
```

```toml
# .autowt.toml
[scripts]
init = """
npm install
./scripts/auto-test.sh "$AUTOWT_BRANCH_NAME" "$AUTOWT_WORKTREE_DIR"
"""
```

## Tips for Workflow Implementation

### 1. Make scripts idempotent
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

### 2. Add error handling
```bash
#!/bin/bash
set -e  # Exit on error

# Your script logic here
if ! command_that_might_fail; then
    echo "Warning: Command failed, continuing anyway" >&2
    exit 0  # Don't fail the hook
fi
```

### 3. Use configuration files
Store settings in dedicated config files:

```bash
# .autowt/config.sh
export DEFAULT_API_PORT=3000
export DB_HOST=localhost
export REDIS_URL=redis://localhost:6379
```

### 4. Log hook execution
Add logging to debug issues:

```bash
LOG_FILE="$HOME/.autowt/hooks.log"
echo "$(date): Running $AUTOWT_HOOK_TYPE for $AUTOWT_BRANCH_NAME" >> "$LOG_FILE"
```

### 5. Test hooks independently
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

These workflows demonstrate how lifecycle hooks can automate complex development scenarios while maintaining clean, predictable behavior across your team.