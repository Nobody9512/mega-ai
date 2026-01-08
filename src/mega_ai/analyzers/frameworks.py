"""Framework detection analyzers."""

import re
from pathlib import Path

from mega_ai.analyzers.base import AnalyzerBase
from mega_ai.orchestrator.models import FrameworkInfo


class LaravelAnalyzer(AnalyzerBase):
    """Detect Laravel PHP framework."""

    def get_name(self) -> str:
        return "laravel"

    def get_priority(self) -> int:
        return 10

    def analyze(self, project_path: Path) -> FrameworkInfo | None:
        """Detect Laravel framework from composer.json and project structure."""
        composer_json = self._parse_json_safe(project_path / "composer.json")
        if composer_json is None:
            return None

        # Check for laravel/framework in require or require-dev
        require = composer_json.get("require", {})
        require_dev = composer_json.get("require-dev", {})

        laravel_version = require.get("laravel/framework") or require_dev.get(
            "laravel/framework"
        )
        if not laravel_version:
            return None

        # Gather config paths
        config_paths: list[str] = []
        if (project_path / "config" / "database.php").exists():
            config_paths.append("config/database.php")
        if (project_path / "config" / "app.php").exists():
            config_paths.append("config/app.php")
        if (project_path / ".env").exists():
            config_paths.append(".env")

        # Gather entry points
        entry_points: list[str] = []
        if (project_path / "artisan").exists():
            entry_points.append("artisan")
        if (project_path / "public" / "index.php").exists():
            entry_points.append("public/index.php")

        return FrameworkInfo(
            name="laravel",
            version=laravel_version,
            config_paths=config_paths,
            entry_points=entry_points,
        )


class DjangoAnalyzer(AnalyzerBase):
    """Detect Django Python framework."""

    def get_name(self) -> str:
        return "django"

    def get_priority(self) -> int:
        return 10

    def analyze(self, project_path: Path) -> FrameworkInfo | None:
        """Detect Django framework from manage.py and settings."""
        # Check for manage.py with django reference
        manage_py = project_path / "manage.py"
        manage_content = self._read_file_safe(manage_py)
        if not manage_content or "django" not in manage_content.lower():
            return None

        version = self._get_django_version(project_path)
        config_paths = self._find_config_paths(project_path)
        entry_points = ["manage.py"]

        # Look for wsgi.py or asgi.py
        for pattern in ["**/wsgi.py", "**/asgi.py"]:
            for f in self._find_files(project_path, pattern):
                rel_path = str(f.relative_to(project_path))
                if rel_path not in entry_points:
                    entry_points.append(rel_path)

        return FrameworkInfo(
            name="django",
            version=version,
            config_paths=config_paths,
            entry_points=entry_points,
        )

    def _get_django_version(self, project_path: Path) -> str | None:
        """Extract Django version from requirements files."""
        for req_file in ["requirements.txt", "requirements/base.txt", "pyproject.toml"]:
            content = self._read_file_safe(project_path / req_file)
            if content:
                # Match patterns like: django==4.2.0, Django>=4.0, django~=4.2
                match = re.search(
                    r"[Dd]jango\s*[=~><]+\s*([\d.]+)", content, re.IGNORECASE
                )
                if match:
                    return match.group(1)
        return None

    def _find_config_paths(self, project_path: Path) -> list[str]:
        """Find Django settings files."""
        config_paths: list[str] = []

        # Look for settings.py files
        for settings_file in self._find_files(project_path, "**/settings.py"):
            config_paths.append(str(settings_file.relative_to(project_path)))

        # Look for settings directory
        for settings_dir in self._find_files(project_path, "**/settings/__init__.py"):
            config_paths.append(str(settings_dir.parent.relative_to(project_path)))

        if (project_path / ".env").exists():
            config_paths.append(".env")

        return config_paths


class FastAPIAnalyzer(AnalyzerBase):
    """Detect FastAPI Python framework."""

    def get_name(self) -> str:
        return "fastapi"

    def get_priority(self) -> int:
        return 10

    def analyze(self, project_path: Path) -> FrameworkInfo | None:
        """Detect FastAPI framework from imports and requirements."""
        # Check requirements.txt or pyproject.toml for fastapi
        version = self._get_fastapi_version(project_path)

        # Also check for FastAPI import in Python files
        has_fastapi_import = False
        entry_points: list[str] = []

        for py_file in self._find_files(project_path, "**/*.py"):
            # Skip test files and venv
            rel_path = str(py_file.relative_to(project_path))
            if "test" in rel_path.lower() or "venv" in rel_path or ".venv" in rel_path:
                continue

            content = self._read_file_safe(py_file)
            if content and ("from fastapi import" in content or "import fastapi" in content):
                has_fastapi_import = True
                # Check if this file creates a FastAPI app
                if "FastAPI(" in content:
                    entry_points.append(rel_path)

        if not version and not has_fastapi_import:
            return None

        config_paths: list[str] = []
        if (project_path / ".env").exists():
            config_paths.append(".env")
        if (project_path / "pyproject.toml").exists():
            config_paths.append("pyproject.toml")

        return FrameworkInfo(
            name="fastapi",
            version=version,
            config_paths=config_paths,
            entry_points=entry_points,
        )

    def _get_fastapi_version(self, project_path: Path) -> str | None:
        """Extract FastAPI version from requirements files."""
        for req_file in ["requirements.txt", "pyproject.toml"]:
            content = self._read_file_safe(project_path / req_file)
            if content:
                match = re.search(
                    r"fastapi\s*[=~><]+\s*([\d.]+)", content, re.IGNORECASE
                )
                if match:
                    return match.group(1)
        return None


class ExpressAnalyzer(AnalyzerBase):
    """Detect Express.js Node framework."""

    def get_name(self) -> str:
        return "express"

    def get_priority(self) -> int:
        return 10

    def analyze(self, project_path: Path) -> FrameworkInfo | None:
        """Detect Express.js framework from package.json."""
        package_json = self._parse_json_safe(project_path / "package.json")
        if package_json is None:
            return None

        # Check for express in dependencies or devDependencies
        deps = package_json.get("dependencies", {})
        dev_deps = package_json.get("devDependencies", {})

        express_version = deps.get("express") or dev_deps.get("express")
        if not express_version:
            return None

        config_paths: list[str] = ["package.json"]
        if (project_path / ".env").exists():
            config_paths.append(".env")

        # Find entry points from package.json main or scripts
        entry_points: list[str] = []
        if "main" in package_json:
            entry_points.append(package_json["main"])

        scripts = package_json.get("scripts", {})
        start_script = scripts.get("start", "")
        # Extract file from "node app.js" or "node src/index.js"
        match = re.search(r"node\s+(\S+\.js)", start_script)
        if match and match.group(1) not in entry_points:
            entry_points.append(match.group(1))

        # Common entry point patterns
        for common in ["app.js", "server.js", "index.js", "src/index.js", "src/app.js"]:
            if (project_path / common).exists() and common not in entry_points:
                entry_points.append(common)

        return FrameworkInfo(
            name="express",
            version=express_version.lstrip("^~"),
            config_paths=config_paths,
            entry_points=entry_points,
        )


class RailsAnalyzer(AnalyzerBase):
    """Detect Ruby on Rails framework."""

    def get_name(self) -> str:
        return "rails"

    def get_priority(self) -> int:
        return 10

    def analyze(self, project_path: Path) -> FrameworkInfo | None:
        """Detect Rails framework from Gemfile."""
        gemfile = project_path / "Gemfile"
        content = self._read_file_safe(gemfile)
        if not content:
            return None

        # Look for rails gem
        match = re.search(r"gem\s+['\"]rails['\"](?:,\s*['\"]([^'\"]+)['\"])?", content)
        if not match:
            return None

        version = match.group(1) if match.lastindex else None

        config_paths: list[str] = ["Gemfile"]
        if (project_path / "config" / "database.yml").exists():
            config_paths.append("config/database.yml")
        if (project_path / "config" / "application.rb").exists():
            config_paths.append("config/application.rb")
        if (project_path / ".env").exists():
            config_paths.append(".env")

        entry_points: list[str] = []
        if (project_path / "bin" / "rails").exists():
            entry_points.append("bin/rails")
        if (project_path / "config.ru").exists():
            entry_points.append("config.ru")

        return FrameworkInfo(
            name="rails",
            version=version,
            config_paths=config_paths,
            entry_points=entry_points,
        )


# List of all framework analyzers
FRAMEWORK_ANALYZERS: list[type[AnalyzerBase]] = [
    LaravelAnalyzer,
    DjangoAnalyzer,
    FastAPIAnalyzer,
    ExpressAnalyzer,
    RailsAnalyzer,
]
