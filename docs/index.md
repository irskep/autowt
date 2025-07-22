# autowt: a better git worktree experience

**autowt** is a git worktree manager designed for developers who juggle multiple tasks. It automates the creation, management, and cleanup of git worktrees, giving each branch its own dedicated directory and terminal tab or window. This eliminates context-switching friction, letting you focus on your code.

While powerful for any developer, `autowt` is a game-changer for those working with command-line AI agents like Claude Code, Gemini CLI, or Codex. It provides the perfect environment for running multiple agents in parallel without interference.

## Core features

<div class="grid cards" markdown>

-   __Automated Worktree Management__

    ---

    `autowt` handles the entire lifecycle of your worktrees. It automatically creates them in a consistent directory structure, runs your setup scripts, and provides powerful cleanup tools to keep your workspace tidy.

-   __Seamless Terminal Integration__

    ---

    Switching branches is as simple as typing `autowt <branch-name>`. `autowt` intelligently manages your terminal sessions, automatically switching to the correct tab or window, or creating a new one if needed.

-   __AI Agent Ready__

    ---

    Isolate your AI agents in their own worktrees. Run multiple agents on different tasks simultaneously without them tripping over each other's work. `autowt` provides the perfect sandbox for parallel development and experimentation. See [AI Agents](agents.md) for detailed setup and monitoring.

-   __Effortless Cleanup__

    ---

    Keep your repository clean with `autowt cleanup`. It identifies and removes branches that are merged, identical to your main branch, or have no remote counterpart, ensuring your workspace remains clutter-free.

</div>

## Getting started

You'll need Python 3.10+ and a version of `git` released less than ten years ago (2.5+).

First, install autowt:

```bash
pip install autowt
```

Then, make a new worktree for a new or existing branch in your current repo:

```bash
autowt my-new-feature
```

Watch as `autowt` creates a new worktree and opens it in a new terminal tab or window.

## Dive deeper

<div class="grid cards" markdown>

-   [**Getting Started Guide**](gettingstarted.md)

    ---

    A step-by-step tutorial to get you up and running with `autowt`.

-   [**AI Agents**](agents.md)

    ---

    Discover patterns and best practices for using `autowt` with AI development tools.

-   [**CLI Reference**](clireference.md)

    ---

    A complete reference for all `autowt` commands and options.

-   [**Configuration**](configuration.md)

    ---

    Learn how to customize `autowt` to fit your workflow perfectly.

</div>

*[git worktree]: A native Git feature that allows you to have multiple working trees attached to the same repository, enabling you to check out multiple branches at once.
*[main worktree]: The original repository directory, as opposed to the worktree directories managed by `autowt`.