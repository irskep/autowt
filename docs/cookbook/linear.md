# Integrating autowt with Linear

Linear already suggests the branch slug it wants to see when you open a pull request. The [`linearis`](https://github.com/czottmann/linearis) CLI exposes that suggestion as the `branchName` field on every `issues read` response, so you can hand it directly to `autowt` and get automatic ticket association when the PR opens.

## Example `.autowt.toml`

```toml
[scripts.custom.linear]
description = "Create a branch from Linear's suggested slug"
branch_name = "linearis issues read $1 | jq -r '.branchName // empty'"
```

`branchName` already includes the team key, issue number, and slug scrubbed for Git usage. When you run `autowt linear ABC-123`, the command above:

1. Calls `linearis issues read ABC-123`
2. Extracts `.branchName` with `jq`
3. Hands that exact string to autowt, so the worktree is created on Linear's suggested branch

Because Linear watches for that slug, any PR pushed from the branch automatically links back to the ticket.
