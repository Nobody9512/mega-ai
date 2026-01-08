"""Base class for all analyzers."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class AnalyzerBase(ABC):
    """Abstract base class for all analyzers."""

    @abstractmethod
    def analyze(self, project_path: Path) -> Any:
        """Analyze the project and return results.

        Args:
            project_path: Path to the project root directory.

        Returns:
            Analysis results specific to the analyzer type.
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the analyzer name."""
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """Return priority for ordering (lower = runs first)."""
        pass

    def _read_file_safe(self, path: Path) -> str | None:
        """Safely read file contents.

        Args:
            path: Path to the file to read.

        Returns:
            File contents as string, or None if file doesn't exist or can't be read.
        """
        try:
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass
        return None

    def _parse_json_safe(self, path: Path) -> dict[str, Any] | None:
        """Safely parse a JSON file.

        Args:
            path: Path to the JSON file.

        Returns:
            Parsed JSON as dict, or None if file doesn't exist or is invalid JSON.
        """
        content = self._read_file_safe(path)
        if content is not None:
            try:
                result = json.loads(content)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
        return None

    def _parse_yaml_safe(self, path: Path) -> dict[str, Any] | None:
        """Safely parse a YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            Parsed YAML as dict, or None if file doesn't exist or is invalid YAML.
        """
        content = self._read_file_safe(path)
        if content is not None:
            try:
                import yaml  # type: ignore[import-untyped]

                result = yaml.safe_load(content)
                if isinstance(result, dict):
                    return result
            except Exception:
                pass
        return None

    def _find_files(self, project_path: Path, pattern: str) -> list[Path]:
        """Find files matching a glob pattern.

        Args:
            project_path: Root directory to search from.
            pattern: Glob pattern to match files.

        Returns:
            List of matching file paths.
        """
        try:
            return list(project_path.glob(pattern))
        except (OSError, ValueError):
            return []
