1. Update CHANGELOG.md with the release notes and date for the current version in pyproject.toml.
2. Commit the changelog changes.
3. Make a vx.y.z tag for the release (using the current version from pyproject.toml) and push it to origin.
4. Use pbcopy to copy the relevant release notes from CHANGELOG.md to the clipboard.
5. Bump the patch version in pyproject.toml to the next version, commit, and push that to main, updating CHANGELOG.md with the new unreleased section.
