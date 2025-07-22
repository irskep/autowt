# AI agents with autowt

`autowt` provides powerful capabilities for working with command-line AI agents like Claude Code, enabling you to monitor their activity and manage multiple development sessions effectively. By creating isolated environments for each task, autowt prevents agents from interfering with each other while providing real-time visibility into their status.

## Why autowt for AI agents?

Running multiple AI agents in a single directory creates chaos. One agent might overwrite files from another, or you might lose track of which changes belong to which task. autowt solves these problems through context isolation, where each agent operates in its own worktree with its own directory. This eliminates context pollution and file conflicts entirely.

The parallel execution capabilities allow you to spin up multiple agents on different tasks simultaneously. One agent can write tests while another develops a new feature, all without interference. When you need to switch between tasks, autowt preserves the state of each worktree so you can pick up exactly where you left off. Once an agent completes its task, you can easily clean up its worktree to keep your project organized.

## Setting up agent monitoring

autowt requires [hooks](https://docs.anthropic.com/en/docs/claude-code/hooks-guide) to monitor agent activity. Install them using the interactive setup command:

```bash
autowt hooks-install
```

You'll be prompted to install hooks at the user level (affecting all projects), the project level (current project only), or have the JSON configuration printed for manual installation. User-level installation is recommended for consistent monitoring across all your projects.

To check which hooks are currently installed and whether they need updating:

```bash
autowt hooks-install --show
```

## Understanding agent status

Once hooks are installed, autowt automatically tracks Claude Code agents running in your worktrees through integration with Claude's hook system. This provides real-time visibility into what each agent is doing.

When you run `autowt ls`, agent status indicators appear alongside terminal session markers:

```txt
  Worktrees:
→ ~/dev/my-project (main worktree)                            main ←
  ~/dev/my-project-worktrees/feature-new-ui @C?     feature-new-ui  
  ~/dev/my-project-worktrees/hotfix-bug     @C…         hotfix-bug
  ~/dev/my-project-worktrees/refactor-auth  @        refactor-auth
```

The status indicators reveal agent activity at a glance. `C?` indicates a Claude agent waiting for your input, while `C…` shows an agent actively working on a task. `C~` means the agent is processing (between user input and tool execution), and `C*` indicates a subagent task has completed. A simple `@` shows an active terminal session without an agent.

## Live monitoring dashboard

For comprehensive agent oversight, the live monitoring dashboard provides real-time updates:

```bash
autowt agents
```

This interactive terminal interface shows all your worktrees with automatic status refreshes every few seconds. The dashboard displays live status updates, activity timelines showing when each agent was last active, and provides quick switching to any worktree with a simple keypress.

Navigation within the dashboard uses intuitive keyboard shortcuts. Use the arrow keys or `j`/`k` to move between worktrees, press Enter to switch to the selected worktree, or press `w` to jump directly to the first agent waiting for input. Press `r` to manually refresh status and `q` to quit the dashboard.

## Agent workflows

The most effective pattern for AI agent development involves parallel feature development using the `--after-init` flag to launch agents immediately after worktree creation.

Assign different types of work to appropriate agents. For feature development, create a worktree and launch Claude directly:

```bash
autowt feature/bubbles \
    --after-init 'claude "Add bubbles coming out of the mouse cursor"'
```

This creates the feature branch worktree and immediately starts the Claude agent in a new terminal. For documentation tasks where different AI models excel, you might use:

```bash
autowt docs/api-reference \
    --after-init 'gemini "Write comprehensive documentation for the new API endpoints, including examples."'
```

When you need to work on sensitive code without agents, simply create worktrees without the after-init command:

```bash
autowt feature/payment-gateway
```

This approach creates three parallel development streams, each in an isolated environment with dedicated terminal sessions for monitoring progress independently.

### Automating environment setup

The `--init` flag or autowt configuration files can automate agent environment preparation. Setting an init script in your `.autowt.toml` file ensures consistent setup:

```toml
# .autowt.toml
init = "npm install"
```

With this configuration, dependency installation runs automatically in every new worktree. Combining init scripts with after-init commands creates fully automated workflows where the init script prepares the environment before the agent begins its task.

## Smart agent switching

autowt extends switching capabilities with agent-aware options for efficient session management. When multiple agents are running, quickly jump to those needing attention:

```bash
autowt switch --waiting
```

This command switches to the first agent waiting for input, presenting an interactive choice if multiple agents need attention. To jump to the most recently active agent:

```bash
autowt switch --latest
```

These commands integrate seamlessly with the monitoring system to provide intelligent navigation based on actual agent activity rather than manual tracking.

---
*[Claude Code]: Anthropic's AI-powered development assistant
*[hook system]: Claude Code's event-driven automation system for custom workflows