"""Database detection analyzers."""

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mega_ai.analyzers.base import AnalyzerBase
from mega_ai.orchestrator.models import DatabaseInfo


class EnvDatabaseAnalyzer(AnalyzerBase):
    """Detect database configuration from .env files."""

    def get_name(self) -> str:
        return "env_database"

    def get_priority(self) -> int:
        return 20

    def analyze(self, project_path: Path) -> DatabaseInfo | None:
        """Parse .env file for database configuration."""
        env_content = self._read_file_safe(project_path / ".env")
        if not env_content:
            # Try .env.example as fallback
            env_content = self._read_file_safe(project_path / ".env.example")
        if not env_content:
            return None

        env_vars = self._parse_env(env_content)

        # Try DATABASE_URL first (common in many frameworks)
        database_url = env_vars.get("DATABASE_URL")
        if database_url:
            return self._parse_database_url(database_url)

        # Try individual DB_* variables (Laravel style)
        db_connection = env_vars.get("DB_CONNECTION")
        if db_connection:
            return self._parse_laravel_env(env_vars, db_connection)

        # Try POSTGRES_* variables (Docker/PostgreSQL style)
        if any(k.startswith("POSTGRES_") for k in env_vars):
            return self._parse_postgres_env(env_vars)

        # Try MYSQL_* variables (Docker/MySQL style)
        if any(k.startswith("MYSQL_") for k in env_vars):
            return self._parse_mysql_env(env_vars)

        return None

    def _parse_env(self, content: str) -> dict[str, str]:
        """Parse .env file content into dict."""
        env_vars: dict[str, str] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                # Remove quotes
                value = value.strip().strip("'\"")
                env_vars[key.strip()] = value
        return env_vars

    def _parse_database_url(self, url: str) -> DatabaseInfo | None:
        """Parse DATABASE_URL format."""
        try:
            parsed = urlparse(url)
            db_type = self._normalize_db_type(parsed.scheme)
            if not db_type:
                return None

            return DatabaseInfo(
                type=db_type,
                host=parsed.hostname or "localhost",
                port=parsed.port or self._default_port(db_type),
                name=parsed.path.lstrip("/") if parsed.path else None,
                connection_string_pattern=url,
            )
        except Exception:
            return None

    def _parse_laravel_env(
        self, env_vars: dict[str, str], connection: str
    ) -> DatabaseInfo:
        """Parse Laravel-style DB_* variables."""
        db_type = self._normalize_db_type(connection)
        host = env_vars.get("DB_HOST", "localhost")
        port_str = env_vars.get("DB_PORT", "")
        port = int(port_str) if port_str.isdigit() else self._default_port(db_type)
        name = env_vars.get("DB_DATABASE")

        return DatabaseInfo(
            type=db_type,
            host=host,
            port=port,
            name=name,
        )

    def _parse_postgres_env(self, env_vars: dict[str, str]) -> DatabaseInfo:
        """Parse POSTGRES_* variables."""
        return DatabaseInfo(
            type="postgresql",
            host=env_vars.get("POSTGRES_HOST", "localhost"),
            port=int(env_vars.get("POSTGRES_PORT", "5432")),
            name=env_vars.get("POSTGRES_DB") or env_vars.get("POSTGRES_DATABASE"),
        )

    def _parse_mysql_env(self, env_vars: dict[str, str]) -> DatabaseInfo:
        """Parse MYSQL_* variables."""
        return DatabaseInfo(
            type="mysql",
            host=env_vars.get("MYSQL_HOST", "localhost"),
            port=int(env_vars.get("MYSQL_PORT", "3306")),
            name=env_vars.get("MYSQL_DATABASE"),
        )

    def _normalize_db_type(self, raw_type: str | None) -> str | None:
        """Normalize database type string."""
        if not raw_type:
            return None
        raw_type = raw_type.lower()
        if raw_type in ("mysql", "mariadb"):
            return "mysql"
        if raw_type in ("postgres", "postgresql", "pgsql"):
            return "postgresql"
        if raw_type in ("sqlite", "sqlite3"):
            return "sqlite"
        if raw_type in ("mongo", "mongodb"):
            return "mongodb"
        if raw_type in ("sqlserver", "mssql"):
            return "sqlserver"
        return raw_type

    def _default_port(self, db_type: str | None) -> int | None:
        """Get default port for database type."""
        ports = {
            "mysql": 3306,
            "postgresql": 5432,
            "mongodb": 27017,
            "sqlserver": 1433,
        }
        return ports.get(db_type or "") if db_type else None


class LaravelDatabaseAnalyzer(AnalyzerBase):
    """Detect database configuration from Laravel config/database.php."""

    def get_name(self) -> str:
        return "laravel_database"

    def get_priority(self) -> int:
        return 21

    def analyze(self, project_path: Path) -> DatabaseInfo | None:
        """Parse Laravel database.php for configuration."""
        db_config = project_path / "config" / "database.php"
        content = self._read_file_safe(db_config)
        if not content:
            return None

        # Extract default connection
        default_match = re.search(
            r"['\"]default['\"]\s*=>\s*env\(['\"]DB_CONNECTION['\"],\s*['\"](\w+)['\"]",
            content,
        )
        default_connection = default_match.group(1) if default_match else None

        if not default_connection:
            return None

        return DatabaseInfo(
            type=self._normalize_db_type(default_connection),
            connection_string_pattern=f"config/database.php:{default_connection}",
        )

    def _normalize_db_type(self, raw_type: str | None) -> str | None:
        """Normalize database type string."""
        if not raw_type:
            return None
        mapping = {
            "mysql": "mysql",
            "pgsql": "postgresql",
            "sqlite": "sqlite",
            "sqlsrv": "sqlserver",
        }
        return mapping.get(raw_type.lower(), raw_type.lower())


class DjangoDatabaseAnalyzer(AnalyzerBase):
    """Detect database configuration from Django settings."""

    def get_name(self) -> str:
        return "django_database"

    def get_priority(self) -> int:
        return 21

    def analyze(self, project_path: Path) -> DatabaseInfo | None:
        """Parse Django settings.py for DATABASES configuration."""
        # Find settings.py
        settings_files = list(project_path.glob("**/settings.py"))
        if not settings_files:
            return None

        for settings_file in settings_files:
            # Skip if in venv
            if "venv" in str(settings_file) or ".venv" in str(settings_file):
                continue

            content = self._read_file_safe(settings_file)
            if not content or "DATABASES" not in content:
                continue

            return self._parse_databases(content)

        return None

    def _parse_databases(self, content: str) -> DatabaseInfo | None:
        """Parse DATABASES dict from settings content."""
        # Try to extract ENGINE from DATABASES['default']
        engine_match = re.search(
            r"['\"]ENGINE['\"]\s*:\s*['\"]django\.db\.backends\.(\w+)['\"]",
            content,
        )
        if not engine_match:
            return None

        engine = engine_match.group(1)
        db_type = self._normalize_db_type(engine)

        # Try to extract NAME
        name_match = re.search(r"['\"]NAME['\"]\s*:\s*['\"]?([^'\"]+)['\"]?", content)
        name = name_match.group(1).strip() if name_match else None

        # Try to extract HOST
        host_match = re.search(r"['\"]HOST['\"]\s*:\s*['\"]([^'\"]+)['\"]", content)
        host = host_match.group(1) if host_match else None

        # Try to extract PORT
        port_match = re.search(r"['\"]PORT['\"]\s*:\s*['\"]?(\d+)['\"]?", content)
        port = int(port_match.group(1)) if port_match else None

        return DatabaseInfo(
            type=db_type,
            host=host,
            port=port,
            name=name,
        )

    def _normalize_db_type(self, engine: str) -> str | None:
        """Normalize Django database backend to type."""
        mapping = {
            "mysql": "mysql",
            "postgresql": "postgresql",
            "postgresql_psycopg2": "postgresql",
            "sqlite3": "sqlite",
            "oracle": "oracle",
        }
        return mapping.get(engine.lower())


class PrismaDatabaseAnalyzer(AnalyzerBase):
    """Detect database configuration from Prisma schema."""

    def get_name(self) -> str:
        return "prisma_database"

    def get_priority(self) -> int:
        return 21

    def analyze(self, project_path: Path) -> DatabaseInfo | None:
        """Parse Prisma schema.prisma for datasource."""
        # Common locations for schema.prisma
        schema_paths = [
            project_path / "prisma" / "schema.prisma",
            project_path / "schema.prisma",
        ]

        for schema_path in schema_paths:
            content = self._read_file_safe(schema_path)
            if content:
                return self._parse_schema(content)

        return None

    def _parse_schema(self, content: str) -> DatabaseInfo | None:
        """Parse datasource block from Prisma schema."""
        # Match datasource block
        datasource_match = re.search(
            r"datasource\s+\w+\s*\{([^}]+)\}", content, re.DOTALL
        )
        if not datasource_match:
            return None

        block = datasource_match.group(1)

        # Extract provider
        provider_match = re.search(r'provider\s*=\s*"(\w+)"', block)
        if not provider_match:
            return None

        provider = provider_match.group(1)
        db_type = self._normalize_db_type(provider)

        # Extract url pattern
        url_match = re.search(r'url\s*=\s*env\("(\w+)"\)', block)
        connection_pattern = url_match.group(1) if url_match else None

        return DatabaseInfo(
            type=db_type,
            connection_string_pattern=f"env({connection_pattern})"
            if connection_pattern
            else None,
        )

    def _normalize_db_type(self, provider: str) -> str | None:
        """Normalize Prisma provider to database type."""
        mapping = {
            "mysql": "mysql",
            "postgresql": "postgresql",
            "sqlite": "sqlite",
            "sqlserver": "sqlserver",
            "mongodb": "mongodb",
            "cockroachdb": "cockroachdb",
        }
        return mapping.get(provider.lower())


class RailsDatabaseAnalyzer(AnalyzerBase):
    """Detect database configuration from Rails config/database.yml."""

    def get_name(self) -> str:
        return "rails_database"

    def get_priority(self) -> int:
        return 21

    def analyze(self, project_path: Path) -> DatabaseInfo | None:
        """Parse Rails database.yml for configuration."""
        db_yml = project_path / "config" / "database.yml"
        config = self._parse_yaml_safe(db_yml)
        if not config:
            return None

        # Try development, then default, then production
        for env in ["development", "default", "production"]:
            if env in config and isinstance(config[env], dict):
                return self._parse_config(config[env])

        return None

    def _parse_config(self, config: dict[str, Any]) -> DatabaseInfo | None:
        """Parse database configuration dict."""
        adapter = config.get("adapter")
        if not adapter:
            return None

        db_type = self._normalize_db_type(adapter)

        return DatabaseInfo(
            type=db_type,
            host=config.get("host"),
            port=config.get("port"),
            name=config.get("database"),
        )

    def _normalize_db_type(self, adapter: str) -> str | None:
        """Normalize Rails adapter to database type."""
        mapping = {
            "mysql2": "mysql",
            "mysql": "mysql",
            "postgresql": "postgresql",
            "sqlite3": "sqlite",
        }
        return mapping.get(adapter.lower(), adapter.lower())


# List of all database analyzers
DATABASE_ANALYZERS: list[type[AnalyzerBase]] = [
    EnvDatabaseAnalyzer,
    LaravelDatabaseAnalyzer,
    DjangoDatabaseAnalyzer,
    PrismaDatabaseAnalyzer,
    RailsDatabaseAnalyzer,
]
