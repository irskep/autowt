"""
MkDocs plugin to automatically insert the contents of CHANGELOG.md into documentation.

This plugin processes markdown files looking for comments in the format:
<!-- CHANGELOG_INSERT -->

And replaces the entire file content with the contents of CHANGELOG.md from the repo root.
"""

import logging
from pathlib import Path
from typing import Any

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from mkdocs.structure.pages import Page

logger = logging.getLogger(__name__)


class ChangelogInsertConfig(config_options.Config):
    """Configuration for the changelog insert plugin."""

    changelog_path = config_options.Type(str, default="CHANGELOG.md")
    """Path to the changelog file relative to the project root"""

    insert_marker = config_options.Type(str, default="<!-- CHANGELOG_INSERT -->")
    """Marker to look for in markdown files to insert changelog content"""


class ChangelogInsertPlugin(BasePlugin[ChangelogInsertConfig]):
    """Plugin to insert changelog content into markdown files."""

    def __init__(self):
        super().__init__()
        self._changelog_content = None

    def _get_changelog_content(self, config_file_path: str) -> str:
        """
        Read and cache the changelog content.

        Args:
            config_file_path: Path to the mkdocs config file to determine project root

        Returns:
            The changelog content
        """
        if self._changelog_content is not None:
            return self._changelog_content

        # Determine project root from config file location
        config_path = Path(config_file_path)
        project_root = config_path.parent

        # Build path to changelog
        changelog_path = project_root / self.config.changelog_path

        logger.info(f"Looking for changelog at: {changelog_path}")

        if not changelog_path.exists():
            logger.warning(f"Changelog file not found at: {changelog_path}")
            self._changelog_content = (
                f"<!-- Changelog file not found at {changelog_path} -->"
            )
            return self._changelog_content

        try:
            with open(changelog_path, encoding="utf-8") as f:
                self._changelog_content = f.read().strip()
                logger.info(f"Successfully loaded changelog from: {changelog_path}")
                return self._changelog_content
        except Exception as e:
            logger.error(f"Error reading changelog file: {e}")
            self._changelog_content = f"<!-- Error reading changelog: {e} -->"
            return self._changelog_content

    def on_page_markdown(
        self, markdown: str, page: Page, config: dict[str, Any], files
    ) -> str:
        """
        Process markdown content to replace changelog insert markers with actual content.

        Args:
            markdown: The markdown content
            page: The page object
            config: MkDocs configuration
            files: All site files

        Returns:
            The processed markdown content
        """
        # Check if this markdown contains the insert marker
        if self.config.insert_marker not in markdown:
            return markdown

        logger.debug(f"Processing changelog insert for page: {page.file.src_path}")

        # Get changelog content
        changelog_content = self._get_changelog_content(
            config.get("config_file_path", "mkdocs.yml")
        )

        # Replace the marker with the changelog content
        processed_markdown = markdown.replace(
            self.config.insert_marker, changelog_content
        )

        return processed_markdown
