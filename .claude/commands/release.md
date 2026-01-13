1. Ensure you're on a fully updated main branch
2. Remove the '.dev0' (or '.devN') suffix from the version in pyproject.toml, then run 'uv sync'.
3. Update CHANGELOG.md with the release notes and date for the current version. Remove empty sections.
4. Commit the version and changelog changes.
5. Make a vx.y.z tag for the release (using the version from pyproject.toml) and push it to origin.
6. Create the GitHub release using `gh release create vX.Y.Z` with the `--notes` flag. The notes should contain only the content under the version header (the ### sections and their bullet points), not the version header itself, since the release title already shows the version.
7. Do a final commit-and-push-to-main with these changes:
    - Bump the patch version in pyproject.toml to the next version with '.dev0' suffix
    - run 'uv sync'
    - update CHANGELOG.md with the new unreleased section
8. Use `gh run list` to find the "Publish to PyPI" workflow run waiting for approval, and provide the user with the link: `https://github.com/irskep/autowt/actions/runs/<run_id>`
