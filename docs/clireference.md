# CLI guide

This page explains the main command-line workflows. For exact flags, aliases, and generated Cobra help, use the [Command Reference](cli/autowt.md) or run `autowt <command> --help`.

## Command forms

Homebrew installs two equivalent binary names:

```sh
brew tap irskep/tap
brew trust irskep/tap
brew install autowt
```

```sh
autowt ls
awt ls
```

The mise install path provides `autowt`; install shell integration if you want the shorter `awt` command with mise.

Running `autowt` with no arguments lists worktrees. Running `autowt <branch>` is shorthand for switching to a branch or creating a worktree for it:

```sh
autowt
autowt feature/my-change
autowt switch feature/my-change
```

Use the explicit `switch` command if a branch name conflicts with a built-in command name.

## Switch and Create

`autowt switch [branch]` switches to an existing worktree or creates a new one. It accepts branch names, branch names without a configured prefix, and paths to existing worktree directories. With no branch argument, it opens an interactive picker for existing worktrees.

When creating a worktree, autowt checks local branches first, then remote branches, then offers to create a new branch from the repository's main branch. Use `--from` to choose a specific source revision.

Terminal behavior comes from configuration by default. Override it per command with `--terminal`, or use shell integration when you want switching to `cd` in the current shell instead of opening another terminal session.

Worktree directories use `worktree.directory_pattern`. The `{branch}` template value is controlled by `worktree.flatten_worktree_directories`: `true` replaces branch path separators with hyphens, while `false` preserves them as nested directories.

## List

`autowt ls` lists worktrees for the current repository. The main worktree appears first, the current worktree is marked, and active terminal sessions are indicated when autowt can detect them.

```txt
> autowt ls

  Worktrees:
-> ~/dev/my-project (main worktree)                         main <-
  ~/dev/my-project-worktrees/feature-new-ui @   feature-new-ui
  ~/dev/my-project-worktrees/hotfix-bug              hotfix-bug
```

## Cleanup

`autowt cleanup` removes secondary worktrees and can also delete their local branches. With no arguments it uses the configured cleanup mode, or prompts for a default the first time you run it.

Cleanup modes:

- `interactive`: choose worktrees in a TUI.
- `merged`: select branches already merged into the main branch.
- `remoteless`: select branches without upstream tracking.
- `github`: use the GitHub CLI (`gh`) to select branches with merged or closed pull requests.
- `gitlab`: use the GitLab CLI (`glab`) to select branches with merged or closed merge requests.
- `all`: combine merged and remoteless cleanup.

You can also pass branch names or worktree paths directly:

```sh
autowt cleanup feature/my-change
autowt cleanup ../my-project-worktrees/feature-my-change
```

Use `--dry-run` to preview removals and `--force` when git should remove a worktree with local file changes.

## Configuration

`autowt config` opens an interactive editor for global configuration. `autowt config --show` prints resolved values from defaults, config files, environment variables, and command-line overrides.

See [Configuration](configuration.md) for every setting and its precedence.

## Shell Integration

`autowt shell-init` prints shell code for bash, zsh, or fish. When installed, switching commands can change the current shell directory directly.

```sh
# bash or zsh
eval "$(autowt shell-init)"

# fish
autowt shell-init fish | source
```

Commands that do not switch worktrees, such as `ls`, `cleanup`, and `config`, continue to print normally.

## Hooks

`autowt hook <hook_name>` runs the configured global and project lifecycle hooks for the current repository and worktree. This lets other tools reuse autowt hook configuration instead of duplicating it.

Hook names are `pre_create`, `post_create`, `post_create_async`, `session_init`, `pre_cleanup`, `post_cleanup`, `pre_switch`, and `post_switch`.

## Built-In Docs

`autowt docs` opens the built-in documentation in a terminal man-page viewer when possible. Use `autowt docs --plain` for plain text output, or `autowt docs --roff` to print the generated roff source.

## Global Options

Global options can be used with any command:

- `-y`, `--yes`: automatically confirm prompts.
- `--debug`: enable verbose debug logging.
- `-h`, `--help`: show help.
- `--version`: print the version.
