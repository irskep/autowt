1. Ensure you're on a fully updated main branch
2. Remove the '.dev0' (or '.devN') suffix from the version in pyproject.toml, then run 'uv sync'.
3. Update CHANGELOG.md with the release notes and date for the current version. Remove empty sections.
4. Commit the version and changelog changes.
5. Make a vx.y.z tag for the release (using the version from pyproject.toml) and push it to origin.
6. Use pbcopy to copy the relevant release notes from CHANGELOG.md to the clipboard.
7. Do a final commit-and-push-to-main with these changes:
    - Bump the patch version in pyproject.toml to the next version with '.dev0' suffix
    - run 'uv sync'
    - update CHANGELOG.md with the new unreleased section
