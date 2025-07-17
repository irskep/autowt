"""
MkDocs plugin to automatically insert program --help output as code blocks.

This plugin processes markdown files looking for comments in the format:
<!-- program subcommand --help -->

And replaces the following code block with the actual help output,
including the original command string.
"""

import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.structure.pages import Page

logger = logging.getLogger(__name__)


class HelpOutputConfig(config_options.Config):
    """Configuration for the help output plugin."""

    command_prefix = config_options.Type(str, default="uv run")
    """Command prefix to use when executing help commands (e.g., 'uv run', 'python -m')"""

    path_replacements = config_options.Type(dict, default={})
    """Dictionary of path replacements to make output more generic"""

    filter_patterns = config_options.Type(
        list,
        default=[
            r"Installing dependencies\.\.\.",
            r"^\[deps:sync\]",
            r"^\s*\+\s+\w+==",  # + package==version
            r"^\s*\$\s+uv\s+sync",  # $ uv sync commands
            r"mise WARN",  # mise warnings
        ],
    )
    """Regex patterns to filter out from command output"""


class HelpOutputPlugin(BasePlugin[HelpOutputConfig]):
    """Plugin to insert command help output into markdown files."""

    def __init__(self):
        super().__init__()
        self.processed_commands = {}  # Cache for command outputs

    def _get_help_text(self, command: str) -> str:
        """
        Execute a command with --help and return the output.

        Args:
            command: The command to execute (without --help)

        Returns:
            The filtered help output
        """
        if command in self.processed_commands:
            return self.processed_commands[command]

        logger.info(f"Fetching help for: {command}")

        # Build command array
        if self.config.command_prefix:
            cmd_array = (
                self.config.command_prefix.split() + command.split() + ["--help"]
            )
        else:
            cmd_array = command.split() + ["--help"]

        try:
            result = subprocess.run(
                cmd_array,
                capture_output=True,
                text=True,
                check=True,
                timeout=30,  # 30 second timeout
            )

            # Filter stdout
            filtered_lines = self._filter_output_lines(result.stdout.splitlines())
            output = "\n".join(filtered_lines)

            # Filter stderr if present
            if result.stderr:
                stderr_filtered = self._filter_output_lines(result.stderr.splitlines())
                if stderr_filtered:
                    output += "\n" + "\n".join(stderr_filtered)

            # Apply path replacements
            output = self._apply_path_replacements(output)

            # Cache the result
            self.processed_commands[command] = output.strip()
            return self.processed_commands[command]

        except subprocess.CalledProcessError as e:
            error_msg = f"Error: Could not get help for command '{command}'"
            logger.error(f"Command failed: {' '.join(cmd_array)}, error: {e}")
            self.processed_commands[command] = error_msg
            return error_msg
        except subprocess.TimeoutExpired:
            error_msg = f"Error: Timeout getting help for command '{command}'"
            logger.error(f"Command timed out: {' '.join(cmd_array)}")
            self.processed_commands[command] = error_msg
            return error_msg

    def _filter_output_lines(self, lines: list) -> list:
        """Filter out unwanted lines from command output."""
        filtered_lines = []
        for line in lines:
            should_filter = False
            for pattern in self.config.filter_patterns:
                if re.search(pattern, line):
                    should_filter = True
                    break
            if not should_filter:
                filtered_lines.append(line)
        return filtered_lines

    def _apply_path_replacements(self, text: str) -> str:
        """Apply path replacements to make output more generic."""
        # Get user's home directory for smart replacement
        home = str(Path.home())

        # Smart replacements that work for any user
        replacements = {
            home: "~",  # Replace full home path with ~
        }

        # Add user-configured replacements
        replacements.update(self.config.path_replacements)

        # Apply replacements (order matters - longest paths first)
        for old_path, new_path in sorted(
            replacements.items(), key=lambda x: len(x[0]), reverse=True
        ):
            text = text.replace(old_path, new_path)

        # Additional smart replacements for common patterns
        # Replace any remaining user-specific paths in common locations

        # Replace /Users/username/ patterns with ~/
        text = re.sub(r"/Users/[^/]+/", "~/", text)

        # Replace /home/username/ patterns with ~/
        text = re.sub(r"/home/[^/]+/", "~/", text)

        return text

    def on_page_markdown(
        self, markdown: str, page: Page, config: dict[str, Any], files
    ) -> str:
        """
        Process markdown content to replace help output comments with actual output.

        Args:
            markdown: The markdown content
            page: The page object
            config: MkDocs configuration
            files: All site files

        Returns:
            The processed markdown content
        """
        # Pattern to match help output comments
        # Examples: <!-- autowt --help --> or <!-- autowt init --help -->
        help_comment_pattern = r"<!--\s*([^-]+?)\s*--help\s*-->"

        def replace_help_block(match):
            command = match.group(1).strip()
            logger.debug(f"Processing help comment for command: {command}")

            # Get the help text
            help_output = self._get_help_text(command)

            # Format the output with command line and help text
            full_command = f"{command} --help"
            formatted_output = f"> {full_command}\n\n{help_output}"

            return f"<!-- {command} --help -->\n```\n{formatted_output}\n```"

        # Find and process all help comments followed by code blocks
        lines = markdown.split("\n")
        processed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this line has a help comment
            help_match = re.search(help_comment_pattern, line)
            if help_match:
                command = help_match.group(1).strip()

                # Add the comment line
                processed_lines.append(line)
                i += 1

                # Look for the opening code fence
                if i < len(lines) and lines[i].strip() == "```":
                    # Process the help block
                    help_output = self._get_help_text(command)
                    full_command = f"{command} --help"
                    formatted_output = f"> {full_command}\n\n{help_output}"

                    # Add opening fence and new content
                    processed_lines.append("```")
                    processed_lines.extend(formatted_output.split("\n"))

                    # Skip existing content until closing fence
                    i += 1
                    while i < len(lines) and lines[i].strip() != "```":
                        i += 1

                    # Add closing fence if found
                    if i < len(lines):
                        processed_lines.append(lines[i])
                    else:
                        processed_lines.append("```")
                else:
                    # No immediate code block, just continue
                    continue
            else:
                processed_lines.append(line)

            i += 1

        return "\n".join(processed_lines)
