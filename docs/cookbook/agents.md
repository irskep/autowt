# Coding Agents

Suppose you want to make it as easy as possible to have an agent like Claude Code start working on a prompt in its own worktree. You could do this:

```toml
[scripts.custom]
claude = 'claude "$1"'

# the above is equivalent to:
[scripts.custom.claude]
session_init = 'claude "$1"'
```

And now you can start it up in a fresh worktree with ease:

```sh
autowt claude 'Add a tutorial'
```

This will create a fresh worktree in a new terminal on a branch called `add-a-tutorial` (or `yourbranchprefix/add-a-tutorial`, if you have a branch prefix configured) and launch `claude` with the argument `"Add a tutorial"`.

## Integrating coding agents with issue trackers

If you trust a coding agent to take the first shot at solving an issue, you can set up autowt to automate plugging it into your issue tracker.

```toml
[scripts.custom.fix]
description = "Have Claude Code fix a GitHub issue and open a PR"
session_init = 'claude "Work on GitHub issue $1. Commit when finished and open a PR. Use the gh command line tool to interact with GitHub."'
branch_name = "gh issue view $1 --json number,title --template '{{.number}}-{{.title}}'"
```
