# Installing autowt

Before you begin, make sure you have at least git 2.5.

## With brew

Installing with Homebrew will install `autowt` and its alias `awt`.

```bash
brew tap irskep/tap
brew trust irskep/tap
brew install autowt
```

## With mise

The mise install path provides `autowt`. If you want the shorter `awt` command with mise, install shell integration; it defines `awt` as an alias or function.

### For a repo

If you want everyone working in a repository to use the same autowt toolchain, install autowt through mise's GitHub backend:

```toml
[tools]
"github:irskep/autowt" = "0.6.0"
```

Then run:

```bash
mise install
```

### For yourself, globally

```bash
mise use -g github:irskep/autowt
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
