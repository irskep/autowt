# Troubleshooting

Encountering an issue? This guide provides solutions to common problems. If you don't find your issue here, consider running your command with the `--debug` flag to get more detailed output.

## First Steps: Debugging

When something goes wrong, the `--debug` flag is your best friend. It provides a verbose output of what `autowt` is doing behind the scenes.

```bash
autowt --debug <command-that-is-failing>
```

This can often reveal the source of the problem, such as a permissions issue or a failed git command.

---

## Common Problems

### Terminal and Session Issues

**Symptom**: `autowt` doesn't open a new terminal tab/window, or it doesn't switch to an existing session.

*   **macOS Permissions**: On macOS, `autowt` requires permission to control your terminal via AppleScript. Go to `System Preferences > Security & Privacy > Privacy` and ensure your terminal application (iTerm2, Terminal.app) is checked under both `Accessibility` and `Automation`.

*   **Unsupported Terminal**: If you are using a terminal with basic or experimental support, session management may not be reliable. Consider using a fully supported terminal or falling back to `tmux` for session management. See the [Terminal Support](terminalsupport.md) page for more details.

*   **Stale Session State**: If your terminal sessions get out of sync, you can reset the session state. To do this, delete the `sessionids.toml` file from your `autowt` state directory and restart your terminal.

### Cleanup Failures

**Symptom**: `autowt cleanup` fails to remove a worktree.

*   **Running Processes**: The most common cause of cleanup failure is a process running in the worktree's directory. `autowt` will attempt to terminate these processes, but it may fail if the process is stuck or running with elevated privileges.

    *   **Solution**: Manually identify and stop the processes in the worktree directory, then run `autowt cleanup` again. You can use `lsof +D /path/to/worktree` to find the processes.

*   **Uncommitted Changes**: By default, `autowt` will not remove a worktree that has uncommitted changes. 

    *   **Solution**: Commit or stash the changes in the worktree, or use the `--force` flag to override this safety check.

!!! danger "Using `--force`"

    The `--force` flag can result in data loss. Only use it if you are sure you don't need the uncommitted changes in the worktree.

### Git and Worktree Errors

**Symptom**: `autowt` reports errors related to git, such as "not a git repository" or worktree corruption.

*   **Corrupt Worktree**: If a worktree becomes corrupted, you may need to intervene manually.
    1.  Try to prune the worktree with `git worktree prune`.
    2.  If that doesn't work, you can manually remove the worktree directory and then run `git worktree prune` again.

*   **Permission Denied**: `autowt` needs write permissions in the parent directory of your project to create the `...-worktrees` directory. Ensure you have the necessary permissions.

### State File Corruption

**Symptom**: `autowt` fails with errors about invalid TOML files or corrupted state.

If your `autowt` state files become corrupted, you can reset them. 

!!! warning "This will reset your `autowt` configuration and session state, but it will not affect your git repository or worktrees."

1.  **Backup your state**: Before deleting anything, it's a good idea to back up your `autowt` state directory.
2.  **Delete the state directory**: The location varies by OS:
    *   **macOS**: `~/Library/Application Support/autowt/`
    *   **Linux**: `~/.local/share/autowt/`
    *   **Windows**: `~/.autowt/`
3.  **Use autowt**: The next time you run any `autowt` command, it will automatically create a fresh state.
