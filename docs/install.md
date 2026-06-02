# Installing autowt

## Requirements

Before you begin, make sure you have:

-   **Git 2.5+**: autowt relies on git worktree support.

## Install autowt

Homebrew is the recommended installation method for most users:

```bash
brew tap irskep/tap
brew install autowt
```

Verify the installation:

```bash
autowt --version
awt --version
```

Homebrew installs both `autowt` and `awt`.

## Organization-managed install with mise

If you want everyone working in a repository to use the same autowt toolchain, install autowt through mise's GitHub backend:

```bash
mise use github:irskep/autowt
```

Then run:

```bash
mise install
```

You can also install it globally with mise:

```bash
mise use -g github:irskep/autowt
```

The mise install path provides `autowt`. If you want the shorter `awt` command with mise, install shell integration; it defines `awt` as an alias or function.

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
