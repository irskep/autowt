# Branch management and cleanup

`autowt` simplifies the entire lifecycle of your git branches, from creation to cleanup. This guide covers how `autowt` manages worktrees and how to use its powerful cleanup features to maintain a tidy repository.

## How `autowt` organizes your worktrees

When you create a worktree with `autowt`, it follows a consistent and predictable organizational strategy.

### Automatic branch resolution

When you run `autowt <branch-name>`, it intelligently determines the best way to create the worktree:

1.  **Existing Local Branch**: If the branch already exists locally, `autowt` will use it.
2.  **Existing Remote Branch**: If the branch exists on your remote (e.g., `origin/branch-name`), `autowt` will check it out for you.
3.  **New Branch**: If the branch doesn't exist anywhere, `autowt` will create it from your repository's main branch (`main` or `master`).

### Directory structure

All worktrees are created in a dedicated directory adjacent to your main project folder, keeping your primary project directory clean. For example, if your project is in `~/dev/my-project`, `autowt` will create a `~/dev/my-project-worktrees/` directory to house all its worktrees.

Branch names are sanitized for the filesystem. A branch named `feature/user-auth` will be created in the directory `~/dev/my-project-worktrees/feature-user-auth/`.

!!! tip "Customize your directory structure"

    You can customize where and how autowt creates worktree directories by configuring the `directory_pattern` setting. This supports template variables like `{repo_name}`, `{branch}`, and `{repo_parent_dir}`, as well as environment variables.

    For example, to organize worktrees by type: `~/worktrees/{repo_name}/{branch}`
    Or to use a flat structure: `~/all-worktrees/{repo_name}-{branch}`

    See [Configuration Guide](configuration.md) for how to set this option globally.

## Cleaning up worktrees

`autowt cleanup` removes worktrees. When you run it, `autowt` identifies branches that are good candidates for removal. Then, with your confirmation, it cleans up the worktree's directory from your filesystem, running any [Lifecycle Hooks](lifecyclehooks.md) you’ve defined, and deletes the git branch if that config option is set.

### Cleanup modes

For non-interactive environments like scripts or CI/CD pipelines, you must specify a `--mode`. You can find more details on these modes in the [CLI Reference](clireference.md).

---
*[git worktree]: A native Git feature that allows you to have multiple working trees attached to the same repository, enabling you to check out multiple branches at once.
*[main worktree]: The original repository directory, as opposed to the worktree directories managed by `autowt`.
