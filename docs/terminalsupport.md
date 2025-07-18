# Terminal Support

`autowt`’s intended user experience is that it will open terminal tabs on your behalf. However, the author only has a Mac and only so much energy for testing terminals, so a lot of support is “experimental,” i.e. vibecoded. This page captures explicitly how well each terminal has been tested.

tl;dr iTerm2 and Terminal.app on macOS work great, everything else is experimental.

## Support Levels

| Level | Description | Terminals |
| --- | --- | --- |
| ✅ **Fully Supported** | Full integration, including session management, and tab/window control. | iTerm2 (macOS), Terminal.app (macOS) |
| ⚠️ **Experimental** | Basic integration is in place, but with limited testing. May be unstable. | tmux, Linux terminals, Windows Terminal |
| 📋 **Basic** | `autowt` can open new terminal processes, but without session tracking. | Alacritty, Kitty, WezTerm, Hyper |

## macOS

| Terminal | Support Level | Notes |
| --- | --- | --- |
| **iTerm2** | ✅ Fully Supported | The recommended terminal for `autowt`. Offers precise session tracking and robust control. |
| **Terminal.app** | ✅ Fully Supported | Excellent support for the built-in macOS terminal. |

!!! info "Permissions on macOS"

    The first time you run `autowt` on macOS, you may be prompted to grant Accessibility and Automation permissions for your terminal application. This is necessary for `autowt` to control your terminal.

## Linux

Support for Linux terminals is experimental. While basic functionality should work, session management may not be reliable.

| Terminal | Support Level | Notes |
| --- | --- | --- |
| **tmux** | ⚠️ Experimental | In theory, provides robust, cross-platform session management. |
| **GNOME Terminal** | ⚠️ Experimental | Basic integration is available. |
| **Konsole** | ⚠️ Experimental | Basic integration is available. |

## Windows

Windows support is in the early experimental stages.

| Terminal | Support Level | Notes |
| --- | --- | --- |
| **Windows Terminal** | ⚠️ Experimental | Basic integration is available. |

## Fallback and Overrides

If your preferred terminal is not well-supported, you can still use `autowt` by following the instructions printed by `autowt shellconfig`, which helps you configure an appropriate `eval` alias for your shell.
