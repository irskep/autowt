# Configuring autowt

`autowt` is designed to work out of the box with sensible defaults, but you can customize its behavior to perfectly match your workflow. This guide covers the different ways you can configure `autowt`, from global settings to project-specific rules.

## Configuration Layers

`autowt` uses a hierarchical configuration system. Settings are applied in the following order of precedence, with later layers overriding earlier ones:

1.  **Global Configuration**: User-wide settings managed via `autowt config`.
2.  **Project Configuration**: Project-specific settings defined in a `autowt.toml` file.
3.  **Environment Variables**: System-wide overrides for specific settings.
4.  **Command-Line Flags**: The highest priority, for on-the-fly adjustments.

## Global Configuration

Global settings apply to all your projects. The easiest way to manage them is with the `autowt config` command, which launches an interactive TUI (Text-based User Interface).

```bash
autowt config
```

This will allow you to set the following options:

*   **Default Terminal Mode**: Choose whether `autowt` should open new tabs, new windows, or switch in place.
*   **Session Switching Behavior**: Decide if `autowt` should always create a new terminal session or ask to switch to an existing one.
*   **Cleanup Process Management**: Configure whether `autowt` should automatically kill processes running in worktrees during cleanup.

Your global settings are stored in a `config.toml` file in a platform-appropriate directory:

*   **macOS**: `~/Library/Application Support/autowt/config.toml`
*   **Linux**: `~/.local/share/autowt/config.toml`
*   **Windows**: `~/.autowt/config.toml`

## Project-Specific Configuration

For settings that should apply to a specific project, you can create a `autowt.toml` or `.autowt.toml` file in the root of your repository.

### Init Scripts

The most common project-specific setting is the `init` script. This is a command that runs automatically in every new worktree created for the project.

For example, in a Node.js project, you could create a `autowt.toml` file with the following content:

```toml
init = "npm install && npm run dev"
```

Now, every time you run `autowt <branch-name>` in this project, `autowt` will automatically install the dependencies and start the development server in the new terminal session.

!!! tip "Overriding Init Scripts"

    You can always override the project's `init` script with the `--init` flag on the command line:

    ```bash
    autowt <branch-name> --init "npm test"
    ```