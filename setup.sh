#!/bin/bash
set -e

echo "Setting up autowt development environment..."

echo "Trusting mise configuration..."
mise trust

echo "Installing mise dependencies..."
mise install

echo "Installing dependencies..."
uv sync

echo "Installing pre-commit hooks..."
mise x -- uv run pre-commit install

echo "Copying .env from main clone if it exists..."
MAIN_CLONE_DIR=$(git rev-parse --path-format=absolute --git-common-dir)/..
if [ -f "$MAIN_CLONE_DIR/.env" ]; then
    cp "$MAIN_CLONE_DIR/.env" .env
    echo "✓ Copied .env from main clone"
else
    echo "No .env file found in main clone"
fi

echo "Setup complete!"
