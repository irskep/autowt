1. Ensure you're on a fully updated main branch.
2. Update CHANGELOG.md: set the date on the current unreleased section. Remove empty sections.
3. Commit the changelog change.
4. Make a vx.y.z tag for the release and push it and the branch to origin. The tag triggers the release workflow which builds binaries and creates a GitHub Release.
5. Use pbcopy to copy the relevant release notes from CHANGELOG.md to the clipboard.
6. Add a new unreleased section to CHANGELOG.md and commit/push to main.
