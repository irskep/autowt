# Project conventions

Always read @mise.toml.

- Python 3.10+ project using uv for dependency management
- Setup: `mise install && uv sync`
- Format: `mise run format` (ruff)
- Lint: `mise run lint` (ruff)
- Test: `mise run test` (pytest)
- Install pre-commit: `uv run pre-commit install`

## Environment setup

- Create `.env` file with `GITHUB_TOKEN=your_token` for cimonitor
- mise automatically loads .env file (already configured)
- Use `uv run cimonitor status --pr <number>` to check CI status

## Code organization

- `src/autowt/cli.py` - Main CLI entry point with command definitions
- `src/autowt/commands/` - Command implementations (checkout, cleanup, etc.)
- `src/autowt/services/` - Core services (git, state, process management)
- `src/autowt/models/` - Data models and types

## How to get up to speed

- Read README.md

# Workflow

## Updating CHANGELOG.md

When describing a new feature in CHANGELOG.md, avoid multiple sibling bullet points about the same feature. Instead, use a single top-level bullet point per feature, with sub-bullets describing its various aspects.

Readers of the changelog do not care about the sequence of events leading up to a feature's release; they want to read about the feature in one shot.

## The scratchpad directory

ENCOURAGED: Use scratch/ directory for all temporary files or non-documentation Markdown files.
FORBIDDEN: Using /tmp
FORBIDDEN: deleting the entire scratch/ directory

## Docs

For mulit-word doc filenames, smush the words together instead of adding _, -, or spaces between words.

# Architectural organization

## Command dispatch pattern
The CLI uses a custom AutowtGroup that dynamically creates branch commands. Any unknown command is treated as a branch name and routed through checkout logic. This means `autowt feature-branch` is equivalent to `autowt switch feature-branch`. The dynamic command creation in cli.py:187-288 maintains identical parameter signatures with the explicit switch command.

## Service layer architecture  
All business logic is encapsulated in services/ with dependency injection through the Services container (models.py:191). Services are stateless and communicate through well-defined interfaces. Key services:
- GitService: Encapsulates all git operations with command builder pattern (GitCommands class)
- StateService: Manages persistent state in platform-specific directories (macOS: ~/Library/Application Support, Linux: XDG, etc.)
- TerminalService: Abstracts terminal manipulation across different terminal emulators
- AgentService: Monitors Claude Code processes using lsof/ps system calls
- ProcessService: Manages background process lifecycle in worktrees

## Configuration cascade system
Configuration follows a strict precedence: CLI args > env vars > project config > global config > defaults. The config.py module implements a frozen dataclass hierarchy that ensures type safety. CLI overrides are handled through cli_config.py which creates temporary override objects that get merged during config initialization.

## Hook system extensibility
Hooks (hooks.py) provide lifecycle injection points with both environment variables and positional arguments. Hook types are defined as constants (HookType class) making new hook points easy to add. Hooks receive standardized context: worktree_dir, main_repo_dir, branch_name, plus hook-specific data.

## Agent monitoring integration
The codebase has deep Claude Code integration through .claude/autowt/status file monitoring. AgentStatus models parse JSON status files to track agent state ("waiting", "working", "idle", etc.). The TUI dashboard (tui/agents.py) provides real-time monitoring with auto-refresh.

## Worktree path resolution
Worktree paths are generated through configurable patterns with variable interpolation: `{repo_name}`, `{branch}`, etc. Branch sanitization handles special characters through configurable rules. Conflict resolution automatically generates alternative paths with numeric suffixes.

## Where to add functionality

**New commands**: Add to commands/ directory following the pattern. Register in cli.py main group. Commands receive Services container and use dataclass command objects for parameters.

**New terminal integrations**: Extend TerminalService with new emulator detection/control logic. Terminal modes are extensible through TerminalMode enum.

**New git operations**: Add to GitService following the GitCommands builder pattern for testability. Complex operations use BranchResolver for strategy determination.

**New lifecycle hooks**: Add hook type constants to HookType class. Extract hook scripts in command implementations using extract_hook_scripts utility.

**New agent integrations**: Extend AgentService with new status file formats or process detection methods. Status indicators are configurable through AgentStatus.status_indicator property.

**New TUI screens**: Follow textual app pattern in tui/ directory. CSS files are co-located with Python files for styling.
