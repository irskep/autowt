1. Ensure you're on a fully updated main branch.
2. Update CHANGELOG.md: set the date on the current unreleased section. Remove empty sections.
3. Commit the changelog change.
4. Create a vX.Y.Z tag and push it and the branch to origin. CI builds binaries and creates the GitHub Release automatically.
5. Add a new unreleased section to CHANGELOG.md and commit/push to main.
