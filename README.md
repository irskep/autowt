# autowt: a better git worktree experience

**autowt** is a git worktree manager designed for developers who juggle multiple tasks. It automates the creation, management, and cleanup of git worktrees, giving each branch its own dedicated directory and terminal session. This eliminates context-switching friction, letting you focus on your code.

While powerful for any developer, `autowt` is a game-changer for those working with command-line AI agents like Claude Code, Gemini CLI, or Codex. It provides the perfect environment for running multiple agents in parallel without interference.

## Core features

**Automated Worktree Management**

`autowt` handles the entire lifecycle of your worktrees. It automatically creates them in a consistent directory structure, runs your setup scripts, and provides powerful cleanup tools to keep your workspace tidy.

**Seamless Terminal Integration**

Switching branches is as simple as typing `autowt <branch-name>`. `autowt` intelligently manages your terminal sessions, automatically switching to the correct tab or window, or creating a new one if needed.

**AI Agent Ready**

Isolate your AI agents in their own worktrees. Run multiple agents on different tasks simultaneously without them tripping over each other's work. `autowt` provides the perfect sandbox for parallel development and experimentation.

**Effortless Cleanup**

Keep your repository clean with `autowt cleanup`. It identifies and removes branches that are merged or have no remote counterpart, ensuring your workspace remains clutter-free.

## Getting started

You'll need Python 3.10+ and a version of `git` released in the last decade (2.5+).

First, install autowt:

```bash
pip install autowt
```

Then, from within a git repository, create a new worktree for a new or existing branch:

```bash
autowt my-new-feature
```

Watch as `autowt` creates a new worktree and opens it in a new terminal tab or window, ready for you to start coding.

## A typical workflow

1.  **Start a new feature**: Run `autowt new-feature`. A new terminal tab opens in an isolated directory for that branch.
2.  **Get an urgent request**: Don't stash! Just run `autowt hotfix/urgent-bug`. A different terminal tab opens for the hotfix.
3.  **Finish the hotfix**: Commit, push, and close the hotfix tab.
4.  **Return to your feature**: Run `autowt new-feature` again, and `autowt` will switch you right back to the existing terminal tab for that feature.
5.  **Clean up**: Once the hotfix branch is merged, run `autowt cleanup` to remove the old worktree and local branch.

## Dive deeper

For detailed guides on commands, configuration, and advanced workflows, check out the [**full documentation**](https://steveasleep.com/autowt/).

-   [**Getting Started Guide**](https://steveasleep.com/autowt/gettingstarted/)
-   [**AI Agents**](https://steveasleep.com/autowt/agents/)
-   [**CLI Reference**](https://steveasleep.com/autowt/clireference/)
-   [**Configuration**](https://steveasleep.com/autowt/configuration/)

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
