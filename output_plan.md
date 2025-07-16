# Rich Library Styling Strategy for autowt

## Current State Analysis

The codebase has several output points where styling would be beneficial:

### Command Strings (should be gray)
- `utils.py:78` - `command_logger.info(f"> {cmd_str}")` - run_command_visible function
- `process.py:120,169` - Commands shown during process termination
- `terminal.py:86` - Shell commands in inplace mode

### Raw Command Output (should be gray)  
- `process.py:120,169,224` - Process termination output
- Various print statements showing command execution results

### Prompts and Section Markers (should be bold)
- `ls.py:39,56,63,92` - Status and section headers
- `checkout.py:109,116,123,131,150` - Progress messages
- Various confirmation prompts throughout

## Proposed Architecture

### 1. Styled Console Module
Create `src/autowt/console.py` with a centralized rich console instance and consistent theming:

```python
from rich.console import Console
from rich.theme import Theme

# Theme for consistent styling across autowt
AUTOWT_THEME = Theme({
    "command": "dim grey50",           # Command strings
    "output": "dim grey50",            # Raw command output  
    "prompt": "bold cyan",             # User prompts
    "section": "bold white",           # Section headers
    "success": "green",                # Success messages
    "warning": "yellow",               # Warnings
    "error": "bold red",               # Errors
    "info": "dim cyan"                 # General info
})

# Single console instance for the entire application
console = Console(theme=AUTOWT_THEME)
```

### 2. Wrapper Functions
Provide convenient wrapper functions for common styling patterns:

```python
def print_command(cmd_str: str) -> None:
    """Print a command string in gray styling."""
    console.print(f"> {cmd_str}", style="command")

def print_section(text: str) -> None:
    """Print a section header in bold."""
    console.print(text, style="section")

def print_prompt(text: str) -> None:
    """Print a prompt in bold cyan."""
    console.print(text, style="prompt")
```

### 3. Integration Points
Replace existing print statements and logging output:

- **utils.py**: Replace `command_logger.info(f"> {cmd_str}")` with styled version
- **process.py**: Style process termination messages
- **All commands**: Replace print statements with styled equivalents
- **Terminal service**: Style shell command output

### 4. Test-Friendly Design
- Console instance can be mocked for testing
- Styles are defined in theme, easily modified
- Wrapper functions provide clean API boundaries
- Rich supports file output and no-color modes for CI

### 5. Migration Strategy
1. Add rich to dependencies in `pyproject.toml`
2. Create `console.py` module with theme and wrappers
3. Update `utils.py` command logging to use styled output
4. Gradually replace print statements in commands with styled versions
5. Add tests for styled output functionality

This approach provides:
- **Consistent styling** across the application
- **Easy testing** with mockable console
- **Maintainable code** with centralized theming
- **Performance** with single console instance
- **Flexibility** for future style changes