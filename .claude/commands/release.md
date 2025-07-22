1. Remove the '-dev' suffix from the version in pyproject.toml, then run 'uv sync'.
2. Update CHANGELOG.md with the release notes and date for the current version.
3. Commit the version and changelog changes.
4. Make a vx.y.z tag for the release (using the version from pyproject.toml) and push it to origin.
5. Use pbcopy to copy the relevant release notes from CHANGELOG.md to the clipboard.
6. Bump the patch version in pyproject.toml to the next version with '-dev' suffix, run 'uv sync', commit, and push that to main, updating CHANGELOG.md with the new unreleased section.
