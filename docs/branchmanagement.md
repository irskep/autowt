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

## Cleaning Up Worktrees

`autowt cleanup` is a powerful command designed to safely remove all traces of stale worktrees from your system. When you run it, `autowt` identifies branches that are good candidates for removal and, with your confirmation, cleans up:

*   The worktree's directory from your filesystem.
*   The local git branch associated with the worktree.
*   Any processes (like dev servers or shells) running within the worktree's directory.

### Interactive Cleanup

By default, running `autowt cleanup` in a terminal launches an interactive TUI (Text-based User Interface) that lists all potential worktrees to be removed.

This interface allows you to review each branch, see its status (e.g., merged, no remote), and select exactly which ones you want to remove. This is the safest and most recommended way to use the cleanup feature.

### Cleanup Modes

For non-interactive environments like scripts or CI/CD pipelines, you must specify a `--mode`. You can find more details on these modes in the [CLI Reference](clireference.md).

### Process Killing

One of the most common reasons a `git worktree remove` command fails is because a process (like a shell or a development server) is still running in that worktree's directory.

`autowt` handles this by detecting and terminating such processes before attempting to remove the worktree. This behavior is on by default but can be configured:

*   **Globally**: Run `autowt config` to change the default process-killing behavior.
*   **Per-command**: Use the `--kill` or `--no-kill` flags to override the default for a single cleanup run.

This ensures that your cleanup operations are smooth and don't leave behind zombie processes or locked directories.

---
*[git worktree]: A native Git feature that allows you to have multiple working trees attached to the same repository, enabling you to check out multiple branches at once.
*[main worktree]: The original repository directory, as opposed to the worktree directories managed by `autowt`.
