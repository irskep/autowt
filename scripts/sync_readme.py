#!/usr/bin/env python3
"""Sync README.md from docs/index.md.

This script extracts content from docs/index.md (the canonical source) and updates
README.md between the sync markers, while preserving the custom Contributing and
License sections at the end of README.md.
"""

import re
from pathlib import Path


def transform_docs_content(content: str) -> str:
    """Transform docs/index.md content for README.md.

    - Removes MkDocs-specific syntax (grid cards)
    - Simplifies certain sections for GitHub README
    """
    # Skip the title (first line)
    lines = content.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]

    content = "\n".join(lines).lstrip("\n")

    # Transform the grid cards section into simpler markdown
    # The grid cards section starts with <div class="grid cards"> and ends with </div>
    grid_pattern = r'<div class="grid cards"[^>]*>.*?</div>'

    def replace_grid_cards(match):
        # Extract the content and convert to simple bullet points
        grid_content = match.group(0)

        # Parse out the card titles and content
        simplified = "**What autowt can do for you:**\n\n"

        # Extract each card's title and description (handle varying indentation)
        # Match pattern: optional whitespace, dash, whitespace, __Title__, whitespace, ---, then content
        # Use a more permissive pattern for the content that stops at the next card or </div>
        card_pattern = r"\s*-\s+__([^_]+)__\s+---\s+(.*?)(?=\n\s*-\s+__|\s*</div>)"
        cards = re.findall(card_pattern, grid_content, re.DOTALL)

        for title, description in cards:
            title = title.strip()
            description = description.strip()
            # Clean up the description - remove extra whitespace
            description = re.sub(r"\s+", " ", description)
            simplified += f"- **{title}**: {description}\n"

        return simplified.rstrip()

    content = re.sub(grid_pattern, replace_grid_cards, content, flags=re.DOTALL)

    # Fix relative links for docs (e.g., ./lifecyclehooks.md -> full URL)
    content = re.sub(
        r"\]\(\./([^)]+)\.md\)", r"](https://steveasleep.com/autowt/\1/)", content
    )

    return content


def sync_readme():
    """Sync README.md from docs/index.md."""
    project_root = Path(__file__).parent.parent
    docs_index = project_root / "docs" / "index.md"
    readme = project_root / "README.md"

    # Read docs/index.md
    if not docs_index.exists():
        raise FileNotFoundError(f"docs/index.md not found at {docs_index}")

    docs_content = docs_index.read_text()

    # Transform content
    synced_content = transform_docs_content(docs_content)

    # Read current README.md
    if not readme.exists():
        raise FileNotFoundError(f"README.md not found at {readme}")

    readme_content = readme.read_text()

    # Find markers
    begin_marker = "<!-- BEGIN SYNCED CONTENT -->"
    end_marker = "<!-- END SYNCED CONTENT -->"

    if begin_marker not in readme_content or end_marker not in readme_content:
        raise ValueError(
            f"README.md must contain sync markers:\n  {begin_marker}\n  {end_marker}"
        )

    # Extract before, middle (to replace), and after sections
    before = readme_content.split(begin_marker)[0]
    after = readme_content.split(end_marker)[1]

    # Construct new README
    new_readme = (
        f"{before}{begin_marker}\n"
        f"<!-- This content is synced from docs/index.md - do not edit directly -->\n"
        f"<!-- Run 'mise run sync-readme' to update -->\n\n"
        f"{synced_content}\n\n"
        f"{end_marker}{after}"
    )

    # Write back
    readme.write_text(new_readme)
    print("✓ Synced README.md from docs/index.md")


if __name__ == "__main__":
    sync_readme()
