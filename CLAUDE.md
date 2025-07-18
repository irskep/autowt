# Project conventions

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

## The scratchpad directory

ENCOURAGED: Use scratch/ directory for all temporary files or non-documentation Markdown files.
FORBIDDEN: Using /tmp
FORBIDDEN: deleting the entire scratch/ directory
