# AI Agent Workflows with autowt

`autowt` is an ideal companion for working with command-line AI agents like Claude Code, Gemini CLI, and Codex. Its ability to create isolated environments for each task makes it possible to run multiple agents in parallel without them interfering with each other. This guide explores effective patterns and workflows for leveraging `autowt` in your AI-assisted development.

## Why `autowt` for Agents?

Running multiple AI agents in a single directory can lead to chaos. One agent might overwrite the files of another, or you might lose track of which changes belong to which task. `autowt` solves these problems by providing:

*   **Context Isolation**: Each agent operates in its own worktree, with its own directory. This means no more context pollution or file conflicts.
*   **Parallel Execution**: Spin up multiple agents on different tasks simultaneously. One can be writing tests while another is developing a new feature.
*   **Effortless Context Switching**: Jump between agent tasks without needing to stash changes. `autowt` preserves the state of each worktree, so you can pick up exactly where you left off.
*   **Simplified Cleanup**: Once an agent has completed its task, you can easily clean up its worktree, keeping your project organized.

---

## Core Workflow: Parallel Feature Development

The most common use case for `autowt` with AI agents is developing multiple features in parallel. The `--after-init` flag is perfect for this, as it can launch your AI agent right after the worktree is ready.

Here's how you can set it up:

1.  **Assign a feature to your first agent** (e.g., with Claude):
    ```bash
    autowt feature/bubbles \
        --after-init 'claude "Add bubbles coming out of the mouse cursor"'
    ```
    This command creates (or switches to) the `feature/authentication` worktree and immediately runs the `claude` agent in the new terminal.

2.  **Assign a documentation task to a second agent**:
    For tasks like writing documentation, an agent like Gemini is often a better choice due to its strong writing abilities.
    ```bash
    autowt docs/api-reference \
        --after-init 'gemini "Write comprehensive documentation for the new API endpoints, including examples."'
    ```

2.  **Work on your own**:
    When you need to write sensitive code without agents, you can let them work on other tasks while you focus.
    ```bash
    autowt feature/payment-gateway # don't start an agent
    ```

Now you have three agents working in parallel, each in a clean, isolated environment. `autowt` opens a new terminal tab or window for each one, so you can monitor their progress independently.

!!! info "Automating Setup with Init Scripts"

    You can automate the setup of your agent's environment using the `--init` flag or by setting `init` in your `autowt.toml` file. This is useful for installing dependencies or preparing the workspace.

    ```toml
    # .autowt.toml
    init = "npm install"
    ```

    With this configuration, `npm install` will run automatically in every new worktree. You can combine this with `--after-init` to create a fully automated workflow:

    ```bash
    # This will run `npm install` first, then launch the agent
    autowt feature/new-ui --after-init 'claude "Build the new UI components"'
    ```

    The `init` script runs first to set up the environment, and then the `after-init` script runs to start the main task.