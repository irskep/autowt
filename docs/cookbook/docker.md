# Starting and Stopping Docker Containers

Start a PostgreSQL container per worktree, stop it on cleanup.

## Start container in post_create

Use the branch name to create a unique container name and port:

```bash
CONTAINER_NAME="pg-$AUTOWT_BRANCH_NAME"
# Calculate unique port (same technique as uniqueports.md)
BASE_PORT=5432
PORT_RANGE=1000
HASH=$(echo "$AUTOWT_BRANCH_NAME" | md5sum | cut -c1-4)
OFFSET=$((16#$HASH % $PORT_RANGE))
PORT=$((BASE_PORT + OFFSET))

docker run -d \
  --name "$CONTAINER_NAME" \
  -e POSTGRES_PASSWORD=postgres \
  -p "$PORT:5432" \
  postgres:16

echo "DATABASE_URL=postgres://postgres:postgres@localhost:$PORT/postgres" >> .env
```

## Stop container in pre_cleanup

```bash
CONTAINER_NAME="pg-$AUTOWT_BRANCH_NAME"
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true
```

## Complete config

```toml
# .autowt.toml
[scripts]
post_create = """
CONTAINER_NAME="pg-$AUTOWT_BRANCH_NAME"
BASE_PORT=5432
PORT_RANGE=1000
HASH=$(echo "$AUTOWT_BRANCH_NAME" | md5sum | cut -c1-4)
OFFSET=$((16#$HASH % $PORT_RANGE))
PORT=$((BASE_PORT + OFFSET))

docker run -d \
  --name "$CONTAINER_NAME" \
  -e POSTGRES_PASSWORD=postgres \
  -p "$PORT:5432" \
  postgres:16

echo "DATABASE_URL=postgres://postgres:postgres@localhost:$PORT/postgres" >> .env
"""

pre_cleanup = """
CONTAINER_NAME="pg-$AUTOWT_BRANCH_NAME"
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true
"""
```

## Try it out

```bash
# Create worktree - container starts automatically
autowt my-feature

# Verify container is running
docker ps | grep pg-my-feature

# Connect to database
source .env
psql "$DATABASE_URL"

# Cleanup - container stops and removes
autowt cleanup my-feature

# Verify container is gone
docker ps -a | grep pg-my-feature  # should return nothing
```
