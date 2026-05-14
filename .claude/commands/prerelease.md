1. Ensure you're on the branch you want to prerelease from (does not need to be main).
2. Look at existing tags to determine the next prerelease tag. If there are already rc tags for the current version (e.g. v0.2.0-rc0), increment the rc number (v0.2.0-rc1). If there are no rc tags yet, ask the user what version to prerelease.
3. Create the tag and push it and the branch to origin. The release workflow builds binaries and creates a GitHub Release.
4. Mark the GitHub Release as a prerelease using `gh release edit <tag> --prerelease`.
