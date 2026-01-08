"""Main project analyzer that coordinates all sub-analyzers."""

from pathlib import Path

from mega_ai.analyzers.databases import DATABASE_ANALYZERS
from mega_ai.analyzers.frameworks import FRAMEWORK_ANALYZERS
from mega_ai.analyzers.models import MODEL_ANALYZERS
from mega_ai.orchestrator.models import (
    AnalysisResult,
    DatabaseInfo,
    FrameworkInfo,
    ModelInfo,
    ProjectInfo,
)


class ProjectAnalyzer:
    """Main analyzer that coordinates all sub-analyzers.

    Runs framework, database, and model analyzers in sequence and returns
    a unified AnalysisResult containing all detected information.
    """

    def __init__(self) -> None:
        """Initialize all sub-analyzers."""
        self.framework_analyzers = [analyzer() for analyzer in FRAMEWORK_ANALYZERS]
        self.database_analyzers = [analyzer() for analyzer in DATABASE_ANALYZERS]
        self.model_analyzers = [analyzer() for analyzer in MODEL_ANALYZERS]

    def analyze(self, project_path: Path) -> AnalysisResult:
        """Run all analyzers and return unified AnalysisResult.

        Args:
            project_path: Path to the project root directory.

        Returns:
            AnalysisResult containing ProjectInfo and DatabaseInfo.
        """
        project_path = project_path.resolve()

        # 1. Detect framework first (provides context for other analyzers)
        framework_info = self._detect_framework(project_path)

        # 2. Detect database configuration
        database_info = self._detect_database(project_path, framework_info)

        # 3. Detect ORM models
        orm_models, orm_type = self._detect_models(project_path, framework_info)

        # 4. Detect package manager
        package_manager = self._detect_package_manager(project_path)

        # Build ProjectInfo
        project_info = ProjectInfo(
            path=project_path,
            framework=framework_info.name if framework_info else None,
            framework_version=framework_info.version if framework_info else None,
            framework_info=framework_info,
            orm_models=orm_models,
            orm=orm_type,
            package_manager=package_manager,
        )

        return AnalysisResult(
            project_info=project_info,
            database_info=database_info or DatabaseInfo(),
        )

    def _detect_framework(self, project_path: Path) -> FrameworkInfo | None:
        """Run framework analyzers and return first successful detection."""
        for analyzer in self.framework_analyzers:
            try:
                result = analyzer.analyze(project_path)
                if isinstance(result, FrameworkInfo):
                    return result
            except Exception:
                # Silently skip failed analyzers
                continue
        return None

    def _detect_database(
        self, project_path: Path, framework_info: FrameworkInfo | None
    ) -> DatabaseInfo | None:
        """Run database analyzers and merge results.

        Uses framework context to prioritize framework-specific analyzers.
        """
        results: list[DatabaseInfo] = []

        for analyzer in self.database_analyzers:
            try:
                result = analyzer.analyze(project_path)
                if result:
                    results.append(result)
            except Exception:
                continue

        if not results:
            return None

        # Merge results, preferring more complete info
        return self._merge_database_info(results)

    def _merge_database_info(self, results: list[DatabaseInfo]) -> DatabaseInfo:
        """Merge multiple DatabaseInfo results into one.

        Prefers non-None values from earlier results.
        """
        merged = DatabaseInfo()

        for result in results:
            if merged.type is None and result.type:
                merged.type = result.type
            if merged.host is None and result.host:
                merged.host = result.host
            if merged.port is None and result.port:
                merged.port = result.port
            if merged.name is None and result.name:
                merged.name = result.name
            if merged.connection_string_pattern is None and result.connection_string_pattern:
                merged.connection_string_pattern = result.connection_string_pattern

        return merged

    def _detect_models(
        self, project_path: Path, framework_info: FrameworkInfo | None
    ) -> tuple[list[ModelInfo], str | None]:
        """Run model analyzers based on detected framework.

        Returns tuple of (models list, orm type name).
        """
        # If we know the framework, prioritize its ORM analyzer
        if framework_info:
            framework_to_orm = {
                "laravel": "eloquent",
                "django": "django",
                "fastapi": "sqlalchemy",
                "rails": "activerecord",
            }
            preferred_orm = framework_to_orm.get(framework_info.name or "")

            for analyzer in self.model_analyzers:
                if analyzer.get_name() == preferred_orm:
                    try:
                        models = analyzer.analyze(project_path)
                        if models:
                            return models, preferred_orm
                    except Exception:
                        pass

        # Try all model analyzers
        for analyzer in self.model_analyzers:
            try:
                models = analyzer.analyze(project_path)
                if models:
                    return models, analyzer.get_name()
            except Exception:
                continue

        return [], None

    def _detect_package_manager(self, project_path: Path) -> str | None:
        """Detect the package manager used by the project."""
        # Check for various lock files and configs
        if (project_path / "composer.json").exists():
            return "composer"
        if (project_path / "package.json").exists():
            # Check for specific package managers
            if (project_path / "pnpm-lock.yaml").exists():
                return "pnpm"
            if (project_path / "yarn.lock").exists():
                return "yarn"
            if (project_path / "bun.lockb").exists():
                return "bun"
            return "npm"
        if (project_path / "Gemfile").exists():
            return "bundler"
        if (project_path / "pyproject.toml").exists():
            return "poetry" if (project_path / "poetry.lock").exists() else "pip"
        if (project_path / "requirements.txt").exists():
            return "pip"
        if (project_path / "go.mod").exists():
            return "go"
        if (project_path / "Cargo.toml").exists():
            return "cargo"

        return None
