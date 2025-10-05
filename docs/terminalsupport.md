# Terminal support

`autowt`'s intended user experience is that it will open terminal tabs on your behalf. However, the author only has a Mac and only so much energy for testing terminals, so support varies by terminal.

tl;dr iTerm2, Terminal.app, Ghostty, VSCode, and Cursor work great on macOS. Other terminals fall back to echo mode.

## macOS terminals

All macOS terminals listed below work well with `autowt`. The main difference is whether they support session tracking.

| Terminal | Session Tracking | Notes |
| --- | --- | --- |
| **iTerm2** | ✅ Yes | The recommended terminal. Full session management with precise tracking. |
| **Terminal.app** | ✅ Yes | Apple's built-in terminal with excellent support. |
| **VSCode** | ⚠️ Window detection only | Opens worktrees in new VSCode windows. Can switch to existing windows on macOS. Use `--terminal=vscode`. |
| **Cursor** | ⚠️ Window detection only | Opens worktrees in new Cursor windows. Can switch to existing windows on macOS. Use `--terminal=cursor`. |
| **Ghostty** | ❌ No | Tab and window creation works via AppleScript (requires accessibility permissions). |

!!! info "Permissions on macOS"

    The first time you run `autowt` on macOS, you may be prompted to grant Accessibility and Automation permissions for your terminal application. This is necessary for `autowt` to control your terminal.

## Linux and Windows

All Linux and Windows terminals use echo mode. `autowt` will print commands for you to run instead of controlling the terminal directly.

## Fallback and overrides

If your preferred terminal is not well-supported, you can still use `autowt` by following the instructions printed by `autowt shellconfig`, which helps you configure an appropriate `eval` alias for your shell.

## Disabling terminal control

If you prefer to avoid any terminal automation (tab/window creation), you can configure `autowt` to only provide directory navigation without controlling your terminal program:

### Option 1: Global configuration

Set the default terminal mode to `echo` prevent automation, either using `autowt config`, or in `.autowt.toml`.

### Option 2: Shell integration

Use the shell function from `autowt shellconfig` for manual directory switching:

```bash
> autowt shellconfig
# Add to your shell config (e.g., ~/.zshrc)
autowt_cd() { eval "$(autowt "$@" --terminal=echo)"; }

# Usage: autowt_cd my-branch
```

With these approaches, `autowt` will manage worktrees and provide navigation commands, but won't attempt to control your terminal application. You get the git worktree management benefits without any automation concerns.
