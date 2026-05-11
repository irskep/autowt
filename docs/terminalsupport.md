# Terminal support

## autowt automates your terminal by default

`autowt`'s intended user experience is that it will open terminal tabs on your behalf. It uses [`automate-terminal`](https://github.com/irskep/automate-terminal) to accomplish this, so check that project out to find out if your terminal is supported.

## What to do if your terminal isn't supported or you don't want this behavior

Add this to your `.autowt.toml` or set it at the user level with `autowt config`:

```
[terminal]
mode = 'echo'
```

This will cause autowt to print commands to the console instead of having your terminal run them automatically. You can then manually run the printed commands to navigate to the worktree.

## Shell integration (alternative to terminal automation)

Instead of opening new tabs or windows, you can have `autowt` change directories directly in your current shell. This is useful if your terminal isn't supported by `automate-terminal`, or if you prefer staying in one session.

Add the appropriate line to your shell config:

```bash
# ~/.bashrc or ~/.zshrc
eval "$(autowt shell-init bash)"

# ~/.config/fish/config.fish
autowt shell-init fish | source
```

Once configured, running `autowt my-branch` will `cd` into the worktree in your current shell. Any `session_init` scripts (like `source .env` or `conda activate`) also run in your shell, so environment changes take effect immediately.

Commands that don't switch worktrees (`ls`, `cleanup`, `config`, etc.) continue to work normally.

To preview what the shell function would do without actually changing directories:

```bash
eval "$(autowt shell-init bash --dry-run)"
autowt my-branch  # prints the cd command instead of running it
```
