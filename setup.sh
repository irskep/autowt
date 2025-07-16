#!/bin/bash
set -e

echo "Setting up autowt development environment..."

echo "Trusting mise configuration..."
mise trust

echo "Installing dependencies..."
uv sync

echo "Installing pre-commit hooks..."
uv run pre-commit install

echo "Setup complete!"