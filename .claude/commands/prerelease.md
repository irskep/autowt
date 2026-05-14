1. Ensure you're on the branch you want to prerelease from (does not need to be main).
2. Look at existing tags to determine the next prerelease tag. If there are already rc tags for the current version (e.g. v1.0.0-rc0), increment the rc number (v1.0.0-rc1). If there are no rc tags yet, ask the user what version to prerelease.
3. Create the tag and push it and the branch to origin. CI builds binaries and creates the GitHub Release with prerelease metadata automatically (any tag containing rc, dev, alpha, or beta is marked as a prerelease).
