#!/usr/bin/env python3
"""
Claude Code hook to prevent writing to docs/CHANGELOG.md
Only allows modifications to the root CHANGELOG.md
"""

import json
import os
import sys


def main():
    # Read JSON input from stdin
    try:
        stdin_data = sys.stdin.read()

        if not stdin_data.strip():
            sys.exit(0)

        hook_data = json.loads(stdin_data)

        # Extract file path from tool input
        tool_input = hook_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if not file_path:
            sys.exit(0)

        paths = [file_path]

    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    for path in paths:
        # Normalize the path to handle relative paths
        normalized_path = os.path.normpath(path)

        # Check if trying to write to docs/CHANGELOG.md
        if (
            normalized_path.endswith("docs/CHANGELOG.md")
            or "/docs/CHANGELOG.md" in normalized_path
        ):
            error_msg = (
                "Error: Cannot modify docs/CHANGELOG.md. "
                "Only the repository root CHANGELOG.md may be modified. "
                f"Attempted to modify: {path}"
            )
            print(error_msg, file=sys.stderr)
            sys.exit(2)  # Exit code 2 blocks the operation

    # All paths are valid
    sys.exit(0)


if __name__ == "__main__":
    main()
