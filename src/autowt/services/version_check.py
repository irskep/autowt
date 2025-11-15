"""Version checking service for autowt."""

import json
import logging
from datetime import datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from typing import NamedTuple
from urllib.error import URLError
from urllib.request import urlopen

logger = logging.getLogger(__name__)


class VersionInfo(NamedTuple):
    """Information about version comparison."""

    current: str
    latest: str
    update_available: bool
    install_command: str | None
    changelog_url: str | None


class InstallationMethod(NamedTuple):
    """Information about detected installation method."""

    name: str
    command: str


class VersionCheckService:
    """Service for checking and notifying about autowt version updates."""

    def __init__(self, app_dir: Path, package_name: str = "autowt"):
        """Initialize version check service."""
        self.app_dir = app_dir
        self.package_name = package_name
        self.version_cache_file = app_dir / "version_check.json"
        self._setup_done = False

    def setup(self) -> None:
        """Ensure app directory exists. Called lazily when needed."""
        if not self._setup_done:
            self.app_dir.mkdir(parents=True, exist_ok=True)
            self._setup_done = True
            logger.debug(f"Version check service setup complete: {self.app_dir}")

    def _get_current_version(self) -> str:
        """Get the currently installed version."""
        try:
            return version(self.package_name)
        except (ImportError, ValueError) as e:
            logger.debug(f"Failed to get current version: {e}")
            return "unknown"

    def _fetch_latest_version(self) -> str | None:
        """Fetch the latest version from PyPI."""
        try:
            url = f"https://pypi.org/pypi/{self.package_name}/json"
            with urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                return data["info"]["version"]
        except (URLError, json.JSONDecodeError, KeyError) as e:
            logger.debug(f"Failed to fetch latest version from PyPI: {e}")
            return None

    def _detect_installation_method(self) -> InstallationMethod:
        """Detect Python package manager and return appropriate upgrade command."""
        cwd = Path.cwd()

        # Check current directory and up to 5 parent directories for project files
        current_dir = cwd
        for _ in range(6):  # Current + 5 parents
            # 1. Check for UV (uv.lock is the definitive indicator)
            if (current_dir / "uv.lock").exists():
                return InstallationMethod("uv", f"uv add --upgrade {self.package_name}")

            # 2. Check for Poetry (poetry.lock or [tool.poetry] in pyproject.toml)
            if (current_dir / "poetry.lock").exists():
                return InstallationMethod(
                    "poetry", f"poetry update {self.package_name}"
                )

            pyproject_file = current_dir / "pyproject.toml"
            if pyproject_file.exists():
                try:
                    content = pyproject_file.read_text(encoding="utf-8")
                    # Poetry uses [tool.poetry] section
                    if "[tool.poetry]" in content:
                        return InstallationMethod(
                            "poetry", f"poetry update {self.package_name}"
                        )
                    # Modern pyproject.toml with [project] section (not poetry)
                    elif "[project]" in content:
                        return InstallationMethod(
                            "pip", f"pip install --upgrade {self.package_name}"
                        )
                except (OSError, UnicodeDecodeError):
                    # Skip corrupted or binary files, continue checking other directories
                    logger.debug(f"Could not read {pyproject_file}: skipping")
                    pass

            # 4. Check for traditional pip with requirements.txt
            if (current_dir / "requirements.txt").exists():
                return InstallationMethod(
                    "pip", f"pip install --upgrade {self.package_name}"
                )

            # Move to parent directory
            current_dir = current_dir.parent
            if current_dir == current_dir.parent:  # Reached filesystem root
                break

        # 5. Default to pip (most common global install method)
        return InstallationMethod("pip", f"pip install --upgrade {self.package_name}")

    def _load_cache(self) -> dict:
        """Load version check cache."""
        if not self.version_cache_file.exists():
            return {}

        try:
            with self.version_cache_file.open("r") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.debug(f"Failed to load version cache: {e}")
            return {}

    def _save_cache(self, cache: dict) -> None:
        """Save version check cache."""
        self.setup()  # Ensure directory exists
        try:
            with self.version_cache_file.open("w") as f:
                json.dump(cache, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save version cache: {e}")

    def _should_check_version(self) -> bool:
        """Check if we should perform a version check (rate limited to once per hour)."""
        cache = self._load_cache()
        last_check = cache.get("last_check_time")

        if not last_check:
            return True

        try:
            last_check_dt = datetime.fromisoformat(last_check)
            return datetime.now() - last_check_dt > timedelta(hours=1)
        except ValueError:
            # Invalid datetime format, assume we should check
            return True

    def check_for_updates(self, force: bool = False) -> VersionInfo | None:
        """
        Check for version updates.

        Args:
            force: If True, bypass rate limiting and check immediately

        Returns:
            VersionInfo if check was performed, None if rate limited
        """
        if not force and not self._should_check_version():
            logger.debug("Version check skipped due to rate limiting")
            return None

        current = self._get_current_version()
        latest = self._fetch_latest_version()

        # Update cache with check time
        cache = self._load_cache()
        cache["last_check_time"] = datetime.now().isoformat()
        if latest:
            cache["latest_version"] = latest
        self._save_cache(cache)

        if not latest:
            logger.debug("Could not fetch latest version")
            return None

        # Compare versions (simple string comparison for now)
        update_available = latest != current and current != "unknown"

        install_command = None
        if update_available:
            method = self._detect_installation_method()
            install_command = method.command

        # Generate changelog URL (GitHub releases page)
        changelog_url = (
            "https://github.com/irskep/autowt/releases" if update_available else None
        )

        return VersionInfo(
            current=current,
            latest=latest,
            update_available=update_available,
            install_command=install_command,
            changelog_url=changelog_url,
        )

    def get_cached_version_info(self) -> dict | None:
        """Get cached version information without performing a new check."""
        cache = self._load_cache()
        if not cache.get("latest_version"):
            return None

        current = self._get_current_version()
        latest = cache["latest_version"]
        update_available = latest != current and current != "unknown"

        result = {
            "current": current,
            "latest": latest,
            "update_available": update_available,
            "last_check": cache.get("last_check_time"),
        }

        if update_available:
            method = self._detect_installation_method()
            result["install_command"] = method.command
            result["changelog_url"] = "https://github.com/irskep/autowt/releases"

        return result
