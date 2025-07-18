#!/bin/bash
set -euo pipefail

# Claude Code hook for automatic Python formatting and linting
# Reads JSON from stdin and processes Python files with ruff

# Extract file path from Claude Code hook JSON input
file_path=$(jq -r '.tool_input.file_path // empty')

# Only process Python files
if [[ "$file_path" == *.py ]]; then
    echo "Formatting and linting $file_path" >&2
    
    # Run ruff format (always succeeds)
    uv run ruff format "$file_path"
    
    # Run ruff check --fix and capture exit code
    if ! uv run ruff check "$file_path"; then
        echo "Ruff found unfixable lint violations in $file_path:" >&2
        uv run ruff check "$file_path" >&2
        exit 1
    fi
fi
