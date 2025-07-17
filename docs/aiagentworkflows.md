# AI Agent Workflows with autowt

`autowt` is an ideal companion for working with command-line AI agents like Claude Code, Gemini CLI, and Codex. Its ability to create isolated environments for each task makes it possible to run multiple agents in parallel without them interfering with each other. This guide explores effective patterns and workflows for leveraging `autowt` in your AI-assisted development.

## Why `autowt` for AI Agents?

Running multiple AI agents in a single directory can lead to chaos. One agent might overwrite the files of another, or you might lose track of which changes belong to which task. `autowt` solves these problems by providing:

*   **Context Isolation**: Each agent operates in its own worktree, with its own directory. This means no more context pollution or file conflicts.
*   **Parallel Execution**: Spin up multiple agents on different tasks simultaneously. One can be writing tests while another is developing a new feature.
*   **Effortless Context Switching**: Jump between agent tasks without needing to stash changes. `autowt` preserves the state of each worktree, so you can pick up exactly where you left off.
*   **Simplified Cleanup**: Once an agent has completed its task, you can easily clean up its worktree, keeping your project organized.

---

## Core Workflow: Parallel Feature Development

The most common use case for `autowt` with AI agents is developing multiple features in parallel. Here's how you can set it up:

1.  **Assign a feature to your first agent**:
    ```bash
    autowt feature/authentication
    # In the new terminal, start your AI agent
    # e.g., claude "Implement the authentication logic"
    ```

2.  **Assign another feature to a second agent**:
    ```bash
    autowt feature/payment-gateway
    # In this new terminal, start another agent
    # e.g., claude "Integrate the Stripe API for payments"
    ```

3.  **Assign a third task, like documentation**:
    ```bash
    autowt docs/api-reference
    # In this terminal, have an agent write documentation
    # e.g., claude "Document the new API endpoints"
    ```

Now you have three agents working in parallel, each in a clean, isolated environment. You can monitor their progress by switching between the terminal tabs or windows `autowt` has created.

!!! info "Use Init Scripts for Automation"

    You can automate the setup of your agent's environment by using init scripts. For example, you could create a `autowt.toml` file in your project root with:

    ```toml
    init = "npm install"
    ```

    This will automatically run `npm install` in every new worktree, ensuring your agents have the dependencies they need.

---

## Advanced Patterns

Beyond parallel feature development, you can use `autowt` to orchestrate more complex, multi-agent workflows.

### Specialized Agent Roles

Assign different agents to specialized roles, much like a human development team.

*   **Frontend Agent**: `autowt frontend/dashboard`
*   **Backend Agent**: `autowt backend/api`
*   **Testing Agent**: `autowt tests/user-flows`

This allows each agent to focus on a specific part of the codebase, minimizing the chance of conflicting changes.

### Experimental Development

When you're not sure of the best approach to a problem, use `autowt` to let multiple agents experiment in parallel.

```bash
autowt experiment/approach-a
autowt experiment/approach-b
autowt experiment/approach-c
```

You can then review the results of each experiment and choose the most promising one to merge into your main branch. The others can be easily cleaned up with `autowt cleanup`.

### Cross-Agent Collaboration

For complex tasks, you can create a pipeline of agents that build on each other's work.

1.  **Research Agent**: `autowt research/new-feature`
    *   An agent like Gemini CLI can be used to research requirements and gather information.
2.  **Implementation Agent**: `autowt feature/new-feature-impl`
    *   Claude Code can then take the research and implement the feature.
3.  **Review Agent**: `autowt review/new-feature`
    *   Another agent can be used to review the code for bugs and suggest improvements.

---

## Best Practices

To get the most out of `autowt` with AI agents, consider these best practices:

*   **Use Descriptive Branch Names**: Clear branch names like `feature/user-auth` or `bugfix/login-error` make it easy to track what each agent is doing.
*   **Regularly Clean Up**: Use `autowt cleanup` to remove worktrees for completed tasks. This keeps your workspace tidy and prevents clutter.
*   **Commit Frequently**: Encourage your agents to commit their work often. This provides a safety net and makes it easier to review their progress.
*   **Monitor Resource Usage**: Running multiple agents can be resource-intensive. Keep an eye on your system's performance and limit the number of concurrent agents if necessary.
