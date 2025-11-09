# Terminal support

## autowt automates your terminal by default

`autowt`'s intended user experience is that it will open terminal tabs on your behalf. It uses [`automate-terminal`](https://github.com/irskep/automate-terminal) to accomplish this, so check that project out to find out if your terminal is supported.

## What to do if your terminal isn't supported or you don't want this behavior

Add this to your `.autowt.toml` or set it at the user level with `autowt config`:

```
[terminal]
mode = 'echo'
```

This will cause autowt to print commands to the console instead of having your terminal run them automatically.

You can still benefit from being automatically cd'd into worktrees by adding a shell alias. Run `autowt shellconfig` to have autowt print an appropriate code block to add to your shell config file (`.zshrc`, etc).

```bash
> autowt shellconfig
# Add to your shell config (e.g., ~/.zshrc)
autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }

# Usage: autowt_cd my-branch
```

This functionality isn't battle-tested, but bugs are easy to identify and fix, so please be liberal with [opening GitHub issues](https://github.com/irskep/autowt/issues).
