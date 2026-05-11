# Installing autowt

Before you begin, make sure you have the following installed:

-   **Python 3.10+**: You can check your version with `python3 --version`.
-   **Git 2.5+**: `autowt` relies on modern git worktree functionality. Check your version with `git --version`. Git 2.5 was released in 2015, so this shouldn’t be a problem.
-   **A supported terminal (recommended)**: For the best experience, use a terminal with good tab and window management, like tmux, or iTerm2 on macOS. See the [Terminal Support](terminalsupport.md) page for more details.

### uv (preferred)

```sh
# note the 'tool' subcommand!
uv tool install autowt
```

### Mise

You can install autowt in its own virtualenv with Mise and pipx:

```bash
mise use -g pipx:autowt
```

### Pip

If you have a global pip environment, you can install there.

```sh
pip install autowt
```

### uvx

`uvx` lets you install and execute in a single command.

```bash
uvx autowt
```

## Shell integration (optional)

By default, autowt opens new terminal tabs when you switch worktrees. If you'd prefer worktree switches to `cd` in your current shell, add shell integration to your shell config:

```bash
# bash (~/.bashrc) or zsh (~/.zshrc) — shell is auto-detected
eval "$(autowt shell-init)"

# fish (~/.config/fish/config.fish)
autowt shell-init | source
```

This also means `session_init` scripts like `source .env` or `conda activate` take effect in your shell directly. See [Terminal Support](terminalsupport.md#shell-integration-alternative-to-terminal-automation) for details.
