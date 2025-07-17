# Terminal Support

`autowt` offers varying levels of support for different terminal applications. For the best experience, with full session management and automatic terminal switching, we recommend using a fully supported terminal.

## Support Levels

| Level | Description | Terminals |
| --- | --- | --- |
| ✅ **Fully Supported** | Full integration, including session management, and tab/window control. | iTerm2 (macOS), Terminal.app (macOS) |
| ⚠️ **Experimental** | Basic integration is in place, but with limited testing. May be unstable. | tmux, Linux terminals, Windows Terminal |
| 📋 **Basic** | `autowt` can open new terminal processes, but without session tracking. | Alacritty, Kitty, WezTerm, Hyper |

---

## macOS

macOS provides the best experience for `autowt` due to its powerful AppleScript capabilities.

| Terminal | Support Level | Notes |
| --- | --- | --- |
| **iTerm2** | ✅ Fully Supported | The recommended terminal for `autowt`. Offers precise session tracking and robust control. |
| **Terminal.app** | ✅ Fully Supported | Excellent support for the built-in macOS terminal. |

!!! info "Permissions on macOS"

    The first time you run `autowt` on macOS, you may be prompted to grant Accessibility and Automation permissions for your terminal application. This is necessary for `autowt` to control your terminal.

---

## Linux

Support for Linux terminals is experimental. While basic functionality should work, session management may not be reliable.

| Terminal | Support Level | Notes |
| --- | --- | --- |
| **tmux** | ⚠️ Experimental | The most reliable option for Linux. Provides robust, cross-platform session management. |
| **GNOME Terminal** | ⚠️ Experimental | Basic integration is available. |
| **Konsole** | ⚠️ Experimental | Basic integration is available. |
| **Other Terminals** | 📋 Basic | For other terminals, `autowt` will likely fall back to basic process spawning without session management. |

---

## Windows

Windows support is in the early experimental stages.

| Terminal | Support Level | Notes |
| --- | --- | --- |
| **Windows Terminal** | ⚠️ Experimental | Basic integration is available, but with limited testing. |

!!! tip "Best Experience on Windows and Linux"

    For the most reliable session management on Windows and Linux, we recommend using **tmux**. It provides a consistent, cross-platform experience that is independent of the terminal emulator you use.

---

## Fallback and Overrides

If your preferred terminal is not well-supported, you can still use `autowt` effectively:

*   **`--terminal=inplace`**: This mode avoids opening new terminals altogether and instead prints the `cd` command for you to evaluate in your current shell.
*   **`AUTOWT_FORCE_TERMINAL`**: You can use this environment variable to force `autowt` to use a specific terminal integration (e.g., `export AUTOWT_FORCE_TERMINAL=tmux`).
