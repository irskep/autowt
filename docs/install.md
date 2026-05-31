# Installing autowt

## Requirements

Before you begin, make sure you have:

-   **mise**: autowt is installed as a release binary through mise's GitHub backend.
-   **Git 2.5+**: autowt relies on git worktree support.

## Install autowt

Install the autowt release binary globally with mise:

```bash
mise use -g github:irskep/autowt
```

Verify the installation:

```bash
autowt --version
```

## Project-scoped install

If you want everyone working in a repository to use the same autowt toolchain, add it to that repository's `mise.toml` instead:

```bash
mise use github:irskep/autowt
```

Then run:

```bash
mise install
```

## Shell integration (optional)

By default, autowt opens new terminal tabs when you switch worktrees. If you'd prefer worktree switches to `cd` in your current shell, add shell integration to your shell config:

```bash
# bash (~/.bashrc)
eval "$(autowt shell-init bash)"

# zsh (~/.zshrc)
eval "$(autowt shell-init zsh)"

# fish (~/.config/fish/config.fish)
autowt shell-init fish | source
```

See [Terminal Support](terminalsupport.md#shell-integration-alternative-to-terminal-automation) for details.
