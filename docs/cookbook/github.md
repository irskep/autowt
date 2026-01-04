# Integrating autowt with GitHub Issues

Use the GitHub CLI (`gh`) to turn an issue number into a branch name. `autowt`'s `branch_name` field runs the command, captures stdout, and normalizes it into a valid Git ref (lowercase, dashes, no spaces).

## Example `.autowt.toml`

```toml
[scripts.custom.ghissue]
description = "Create a branch that matches the GitHub issue title"
branch_name = "gh issue view $1 --json number,title --template '{{.number}}-{{.title}}'"
```

Now `autowt ghissue 1234` asks GitHub for issue `#1234`, builds a string like `1234-improve-login`, and creates a worktree on that branch. All other lifecycle hooks (such as `session_init`) continue to run the same as when you pass a plain branch name.
