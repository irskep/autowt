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

All worktrees are created in a dedicated directory adjacent to your main project folder. This keeps your main project directory clean and uncluttered.

*   **Project Directory**: `~/dev/my-project`
*   **Worktree Directory**: `~/dev/my-project-worktrees/`

Branch names are sanitized for the filesystem. For example, a branch named `feature/user-auth` will be created in the directory `~/dev/my-project-worktrees/feature-user-auth/`.

---

## The Cleanup System

The `autowt cleanup` command is a powerful tool for keeping your repository free of stale branches and worktrees. It analyzes your worktrees and gives you an opportunity to remove them and their corresponding branches.

### Cleanup Categories

`autowt` groups branches into three main categories for cleanup:

*   **Merged**: These branches have been fully merged into your main branch. Their changes are already incorporated, so they are generally safe to remove.
*   **Identical**: These branches are identical to your main branch, meaning they have no new commits. They are also safe to remove, but maybe you just haven't committed yet.
*   **Remoteless**: These are local branches that do not have a corresponding remote branch. These can represent branches that were squash-merged, and so wouldn't share history with the main branch, but maybe just haven't been pushed yet.

### Cleanup Modes

`autowt` provides several cleanup modes to suit your needs:

*   `--mode=all` (Default): Removes branches from all three categories.
*   `--mode=merged`: A safer mode that only removes `merged` and `identical` branches.
*   `--mode=remoteless`: Only removes branches that don't have a remote counterpart.
*   `--mode=interactive`: Launches a TUI (Text-based User Interface) that lets you review and select branches for removal individually.

!!! warning "Safety First: Dry Run"

    Before running any cleanup command, it's always a good idea to use the `--dry-run` flag:

    ```bash
    autowt cleanup --dry-run
    ```

    This will show you a list of the branches that would be removed, without actually deleting anything. This lets you verify the changes before they are made.

### The Cleanup Process

When you run `autowt cleanup`, it performs the following steps to ensure a safe and thorough cleanup:

1.  **Fetches** the latest changes from your remote to ensure the merge analysis is up-to-date.
2.  **Analyzes** all worktrees and categorizes them.
3.  **Identifies** any running processes in the worktrees that will be removed.
4.  **Terminates** these processes gracefully (with a SIGINT, followed by a SIGKILL if necessary).
5.  **Removes** the worktree directories and their associated git metadata.
6.  **Asks** if you want to delete the local git branches for the removed worktrees.

---

## Best Practices for Branch Management

*   **Use Descriptive Names**: Adopt a consistent naming convention for your branches, such as `feature/add-login-page` or `bugfix/fix-auth-error`. This makes it easier to manage your worktrees.
*   **Clean Up Regularly**: Run `autowt cleanup --mode=merged` weekly to keep your repository tidy without deleting potentially important experimental branches.
*   **Use Interactive Mode for Reviews**: Periodically use `autowt cleanup --mode=interactive` to conduct a more thorough review of all your branches and decide which ones to keep or remove.
*   **Automate with Care**: You can automate cleanup with `--yes`, but be cautious. A command like `autowt cleanup --mode=remoteless --yes` can be useful, but make sure you understand what it will remove.
