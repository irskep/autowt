# Branch Management and Cleanup

`autowt` simplifies the entire lifecycle of your git branches, from creation to cleanup. This guide covers how `autowt` manages worktrees and how to use its powerful cleanup features to maintain a tidy repository.

## How `autowt` Organizes Your Worktrees

When you create a worktree with `autowt`, it follows a consistent and predictable organizational strategy.

### Automatic Branch Resolution

When you run `autowt <branch-name>`, it intelligently determines the best way to create the worktree:

1.  **Existing Local Branch**: If the branch already exists locally, `autowt` will use it.
2.  **Existing Remote Branch**: If the branch exists on your remote (e.g., `origin/branch-name`), `autowt` will check it out for you.
3.  **New Branch**: If the branch doesn't exist anywhere, `autowt` will create it from your repository's main branch (`main` or `master`).

### Directory Structure

All worktrees are created in a dedicated directory adjacent to your main project folder, keeping your primary project directory clean. For example, if your project is in `~/dev/my-project`, `autowt` will create a `~/dev/my-project-worktrees/` directory to house all its worktrees.

Branch names are sanitized for the filesystem. A branch named `feature/user-auth` will be created in the directory `~/dev/my-project-worktrees/feature-user-auth/`.

---

## Cleaning Up Worktrees

`autowt cleanup` attempts to remove all traces of stale worktrees from your system, including:
- The worktree directory
- The branch
- Processes running in the worktree directory, including shells

Branch and process behaviors are configurable to your level of comfort with things being deleted and killed automatically.

FIXME: write cleanup docs. cleanup is now interactive. briefly discuss how processes are killed.