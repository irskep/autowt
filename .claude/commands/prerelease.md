1. Verify you're on the main branch and it's up to date
2. Parse the current version from pyproject.toml
3. Validate the version is in format `X.Y.Z.devN` (e.g., `0.5.0.dev0`)
   - If not in this format, ERROR and tell the user to manually fix it first
4. Increment the dev number: `.dev0` → `.dev1`, `.dev1` → `.dev2`, etc.
5. Update the version in pyproject.toml with the new version
6. Run `uv sync` to update the lock file
7. Commit the changes:
   ```bash
   git add pyproject.toml uv.lock
   git commit -m "Prerelease v<new-version>"
   ```
8. Create and push the tag:
   ```bash
   git tag v<new-version>
   git push origin main
   git push origin v<new-version>
   ```

Example: `0.5.0.dev0` → `0.5.0.dev1` → `0.5.0.dev2`
