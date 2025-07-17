import re
import subprocess
from pathlib import Path


def get_help_text(command):
    """Get help text for an autowt command."""
    print(f"Fetching help for: {command}")
    print("⏳ Running command...", end="", flush=True)

    # Handle base autowt command vs subcommands
    if command.strip() == "autowt":
        cmd_array = ["uv", "run", "autowt", "--help"]
    else:
        # Remove 'autowt' prefix if present, then build command array
        cmd_parts = command.replace("autowt ", "").split()
        cmd_array = ["uv", "run", "autowt"] + cmd_parts + ["--help"]

    try:
        result = subprocess.run(
            cmd_array,
            capture_output=True,
            text=True,
            check=True,
        )
        print(" ✅")  # Complete the progress line

        output_lines = result.stdout.splitlines()

        # Filter out uv/mise dependency installation output if any
        dependency_patterns = [
            r"Installing dependencies\.\.\.",
            r"^\[deps:sync\]",
            r"^\s*\+\s+\w+==",  # + package==version
            r"^\s*\$\s+uv\s+sync",  # $ uv sync commands
            r"mise WARN",  # mise warnings
        ]

        filtered_output_lines = [
            line
            for line in output_lines
            if not any(re.search(pattern, line) for pattern in dependency_patterns)
        ]
        output = "\n".join(filtered_output_lines)

        # Filter out installation messages from stderr
        filtered_stderr_lines = [
            line
            for line in result.stderr.splitlines()
            if not any(
                phrase in line
                for phrase in [
                    "Installing dependencies...",
                    "Audited",
                    "Resolved",
                    "Building",
                    "Built",
                    "Prepared",
                    "Uninstalled",
                    "Installed",
                    "packages in",
                    "package in",
                    "mise WARN",
                ]
            )
        ]
        if filtered_stderr_lines:
            output += "\n" + "\n".join(filtered_stderr_lines)

        # Replace common user data directory paths with generic ones
        home_replacements = [
            (
                "/Users/steve/Library/Application Support/autowt",
                "~/Library/Application Support/autowt",
            ),
            ("/home/", "~/"),
            (str(Path.home()), "~"),
        ]

        for old_path, new_path in home_replacements:
            output = output.replace(old_path, new_path)

        return output.strip()

    except subprocess.CalledProcessError as e:
        print(f" ❌ Error getting help for {command}: {e}")
        return f"Error: Could not get help for command '{command}'"


def main():
    docs_file = Path("docs/commands.md")
    if not docs_file.exists():
        print(f"❌ Documentation file {docs_file} not found")
        return

    lines = docs_file.read_text().splitlines()
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        # Look for autowt help insertion comments
        match = re.search(r"<!-- autowt (.*?) --help -->", line)
        if match:
            command = match.group(1)
            new_lines.append(line)  # Add the comment line
            i += 1  # Move to the next line (should be ```)

            if i < len(lines) and lines[i].strip() == "```":
                new_lines.append(lines[i])  # Add the opening ```
                i += 1  # Move past the opening ```

                try:
                    help_text = get_help_text(f"autowt {command}".strip())
                    new_lines.extend(help_text.splitlines())  # Add the help text
                except Exception as e:
                    print(f" ❌ Error getting help for {command}: {e}")
                    # If error, keep original content or leave empty
                    while i < len(lines) and lines[i].strip() != "```":
                        i += 1  # Skip original content until closing ```

                # Skip existing content until the closing ```
                while i < len(lines) and lines[i].strip() != "```":
                    i += 1

                if i < len(lines) and lines[i].strip() == "```":
                    new_lines.append(lines[i])  # Add the closing ```
                else:
                    # If no closing ``` found, add one to prevent malformed markdown
                    new_lines.append("```")
            else:
                new_lines.append(
                    line
                )  # Add the original line back if format is unexpected
        else:
            new_lines.append(line)
        i += 1

    docs_file.write_text("\n".join(new_lines))


if __name__ == "__main__":
    main()
