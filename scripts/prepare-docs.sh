#!/bin/bash
set -e

# Copy README.md to docs/index.md
cp README.md docs/index.md

# Copy CHANGELOG.md to docs/ if it exists
if [ -f "CHANGELOG.md" ]; then
    cp CHANGELOG.md docs/
    echo "✅ CHANGELOG.md copied to docs/"
else
    echo "ℹ️  No CHANGELOG.md found, skipping"
fi

# Remove any 'full docs:' link lines (common pattern in READMEs)
sed -i.bak '/> Full docs:/d' docs/index.md

# Remove backup file if it exists
[ -f docs/index.md.bak ] && rm docs/index.md.bak


echo "✅ Documentation preparation complete"