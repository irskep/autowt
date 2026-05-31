## autowt shell-init

Generate shell integration code

### Synopsis

Generate shell integration code.

Detects your shell automatically from $SHELL, or accepts an
explicit argument.

Prints a shell function that wraps the autowt binary so that
worktree switches cd in your current shell.

Setup:
  bash: eval "$(autowt shell-init)"       # add to ~/.bashrc
  zsh:  eval "$(autowt shell-init)"       # add to ~/.zshrc
  fish: autowt shell-init | source        # add to ~/.config/fish/config.fish

```
autowt shell-init [bash|zsh|fish] [flags]
```

### Options

```
      --dry-run   Print commands instead of eval'ing them
  -h, --help      help for shell-init
```

### Options inherited from parent commands

```
      --debug   Enable debug logging
  -y, --yes     Automatically confirm all prompts
```

### SEE ALSO

* [autowt](autowt.md)	 - Git worktree manager

