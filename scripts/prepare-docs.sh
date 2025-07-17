#!/bin/bash
set -e

# Copy CHANGELOG.md to docs/ if it exists
if [ -f "CHANGELOG.md" ]; then
    cp CHANGELOG.md docs/
    echo "✅ CHANGELOG.md copied to docs/"
else
    echo "ℹ️  No CHANGELOG.md found, skipping"
fi

echo "✅ Documentation preparation complete"
