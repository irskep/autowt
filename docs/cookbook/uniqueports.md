# Assigning Unique Ports

Each worktree gets a unique port written to `.env`, avoiding conflicts when running multiple dev servers.

## Calculate port from branch name

Hash the branch name and map it to a port range:

```bash
BASE_PORT=3000
PORT_RANGE=1000
HASH=$(echo "$AUTOWT_BRANCH_NAME" | md5sum | cut -c1-4)
OFFSET=$((16#$HASH % $PORT_RANGE))
PORT=$((BASE_PORT + OFFSET))
```

This gives ports between 3000-3999 based on the branch name.

## Write to .env in post_create

```toml
# .autowt.toml
[scripts]
post_create = """
BASE_PORT=3000
PORT_RANGE=1000
HASH=$(echo "$AUTOWT_BRANCH_NAME" | md5sum | cut -c1-4)
OFFSET=$((16#$HASH % $PORT_RANGE))
PORT=$((BASE_PORT + OFFSET))
echo "PORT=$PORT" >> .env
"""
```

## Complete config

```toml
# .autowt.toml
[scripts]
post_create = """
BASE_PORT=3000
PORT_RANGE=1000
HASH=$(echo "$AUTOWT_BRANCH_NAME" | md5sum | cut -c1-4)
OFFSET=$((16#$HASH % $PORT_RANGE))
PORT=$((BASE_PORT + OFFSET))
echo "PORT=$PORT" >> .env
"""
```

## Try it out

Create a worktree and start a server. This example uses Python's built-in static file server.

```bash
autowt my-feature
source .env
echo "Server running on port $PORT"
python3 -m http.server $PORT
```

Each worktree will get a consistent port based on its branch name.
