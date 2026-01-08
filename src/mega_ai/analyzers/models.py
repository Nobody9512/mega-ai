"""ORM model detection analyzers."""

import re
from pathlib import Path

from mega_ai.analyzers.base import AnalyzerBase
from mega_ai.orchestrator.models import ModelInfo


class EloquentModelAnalyzer(AnalyzerBase):
    """Detect Laravel Eloquent ORM models."""

    def get_name(self) -> str:
        return "eloquent"

    def get_priority(self) -> int:
        return 30

    def analyze(self, project_path: Path) -> list[ModelInfo]:
        """Find and parse Eloquent models in app/Models/*.php."""
        models: list[ModelInfo] = []

        # Look for models in app/Models directory
        models_dir = project_path / "app" / "Models"
        if not models_dir.exists():
            # Try older Laravel structure
            models_dir = project_path / "app"

        for php_file in self._find_files(project_path, "app/Models/**/*.php"):
            model = self._parse_model(php_file, project_path)
            if model:
                models.append(model)

        # Also check app/*.php for older Laravel versions
        for php_file in self._find_files(project_path, "app/*.php"):
            content = self._read_file_safe(php_file)
            if content and "extends Model" in content:
                model = self._parse_model(php_file, project_path)
                if model:
                    models.append(model)

        return models

    def _parse_model(self, file_path: Path, project_path: Path) -> ModelInfo | None:
        """Parse a PHP model file."""
        content = self._read_file_safe(file_path)
        if not content:
            return None

        # Check if it's an Eloquent model
        if "extends Model" not in content and "Illuminate\\Database" not in content:
            return None

        # Extract class name
        class_match = re.search(r"class\s+(\w+)\s+extends", content)
        if not class_match:
            return None

        class_name = class_match.group(1)

        # Extract table name (if explicitly set)
        table_match = re.search(
            r"protected\s+\$table\s*=\s*['\"](\w+)['\"]", content
        )
        table_name = table_match.group(1) if table_match else None

        # Extract fillable fields
        fillable_match = re.search(
            r"protected\s+\$fillable\s*=\s*\[([\s\S]*?)\]", content
        )
        fields: list[str] = []
        if fillable_match:
            fields = re.findall(r"['\"](\w+)['\"]", fillable_match.group(1))

        # Extract relationships
        relationships: list[str] = []
        for rel_type in ["hasOne", "hasMany", "belongsTo", "belongsToMany", "morphTo"]:
            rel_matches = re.findall(
                rf"function\s+(\w+)\s*\([^)]*\)\s*\{{[^}}]*{rel_type}\s*\(", content
            )
            relationships.extend(rel_matches)

        return ModelInfo(
            name=class_name,
            table_name=table_name,
            file_path=str(file_path.relative_to(project_path)),
            fields=fields,
            relationships=relationships,
        )


class DjangoModelAnalyzer(AnalyzerBase):
    """Detect Django ORM models."""

    def get_name(self) -> str:
        return "django"

    def get_priority(self) -> int:
        return 30

    def analyze(self, project_path: Path) -> list[ModelInfo]:
        """Find and parse Django models in **/models.py files."""
        models: list[ModelInfo] = []

        for models_file in self._find_files(project_path, "**/models.py"):
            # Skip venv and migrations
            rel_path = str(models_file.relative_to(project_path))
            if "venv" in rel_path or ".venv" in rel_path or "migrations" in rel_path:
                continue

            file_models = self._parse_models_file(models_file, project_path)
            models.extend(file_models)

        return models

    def _parse_models_file(
        self, file_path: Path, project_path: Path
    ) -> list[ModelInfo]:
        """Parse a Django models.py file."""
        content = self._read_file_safe(file_path)
        if not content:
            return []

        models: list[ModelInfo] = []

        # Find all model class definitions
        # Match: class ModelName(models.Model): or class ModelName(SomeBase, models.Model):
        class_pattern = re.compile(
            r"class\s+(\w+)\s*\([^)]*models\.Model[^)]*\)\s*:", re.MULTILINE
        )

        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            class_start = match.end()

            # Find the end of the class (next class definition or EOF)
            next_class = class_pattern.search(content, class_start)
            class_end = next_class.start() if next_class else len(content)
            class_body = content[class_start:class_end]

            # Extract Meta class for table name
            table_name = None
            meta_match = re.search(
                r"class\s+Meta\s*:[^}]*db_table\s*=\s*['\"](\w+)['\"]", class_body
            )
            if meta_match:
                table_name = meta_match.group(1)

            # Extract fields
            fields = self._extract_fields(class_body)

            # Extract relationships
            relationships = self._extract_relationships(class_body)

            models.append(
                ModelInfo(
                    name=class_name,
                    table_name=table_name,
                    file_path=str(file_path.relative_to(project_path)),
                    fields=fields,
                    relationships=relationships,
                )
            )

        return models

    def _extract_fields(self, class_body: str) -> list[str]:
        """Extract field names from Django model class body."""
        fields: list[str] = []
        # Match: field_name = models.CharField(...) or models.IntegerField(...)
        field_pattern = re.compile(r"^\s*(\w+)\s*=\s*models\.\w+Field", re.MULTILINE)
        for match in field_pattern.finditer(class_body):
            fields.append(match.group(1))
        return fields

    def _extract_relationships(self, class_body: str) -> list[str]:
        """Extract relationship field names from Django model class body."""
        relationships: list[str] = []
        # Match ForeignKey, OneToOneField, ManyToManyField
        rel_pattern = re.compile(
            r"^\s*(\w+)\s*=\s*models\.(ForeignKey|OneToOneField|ManyToManyField)",
            re.MULTILINE,
        )
        for match in rel_pattern.finditer(class_body):
            relationships.append(match.group(1))
        return relationships


class SQLAlchemyModelAnalyzer(AnalyzerBase):
    """Detect SQLAlchemy ORM models."""

    def get_name(self) -> str:
        return "sqlalchemy"

    def get_priority(self) -> int:
        return 30

    def analyze(self, project_path: Path) -> list[ModelInfo]:
        """Find and parse SQLAlchemy models."""
        models: list[ModelInfo] = []

        for py_file in self._find_files(project_path, "**/*.py"):
            # Skip venv and tests
            rel_path = str(py_file.relative_to(project_path))
            if "venv" in rel_path or ".venv" in rel_path or "test" in rel_path.lower():
                continue

            content = self._read_file_safe(py_file)
            if not content:
                continue

            # Check for SQLAlchemy imports
            if "sqlalchemy" not in content.lower():
                continue

            file_models = self._parse_models(content, py_file, project_path)
            models.extend(file_models)

        return models

    def _parse_models(
        self, content: str, file_path: Path, project_path: Path
    ) -> list[ModelInfo]:
        """Parse SQLAlchemy models from file content."""
        models: list[ModelInfo] = []

        # Find classes with __tablename__
        class_pattern = re.compile(
            r"class\s+(\w+)\s*\([^)]+\)\s*:", re.MULTILINE
        )

        for match in class_pattern.finditer(content):
            class_name = match.group(1)
            class_start = match.end()

            # Find the end of the class
            next_class = class_pattern.search(content, class_start)
            class_end = next_class.start() if next_class else len(content)
            class_body = content[class_start:class_end]

            # Check for __tablename__
            tablename_match = re.search(
                r"__tablename__\s*=\s*['\"](\w+)['\"]", class_body
            )
            if not tablename_match:
                continue

            table_name = tablename_match.group(1)

            # Extract Column definitions
            fields = self._extract_columns(class_body)

            # Extract relationship definitions
            relationships = self._extract_relationships(class_body)

            models.append(
                ModelInfo(
                    name=class_name,
                    table_name=table_name,
                    file_path=str(file_path.relative_to(project_path)),
                    fields=fields,
                    relationships=relationships,
                )
            )

        return models

    def _extract_columns(self, class_body: str) -> list[str]:
        """Extract column names from SQLAlchemy model."""
        fields: list[str] = []
        # Match: column_name = Column(...) or column_name: Mapped[...] = mapped_column(...)
        col_pattern = re.compile(
            r"^\s*(\w+)\s*(?::\s*Mapped\[[^\]]+\])?\s*=\s*(?:Column|mapped_column)",
            re.MULTILINE,
        )
        for match in col_pattern.finditer(class_body):
            fields.append(match.group(1))
        return fields

    def _extract_relationships(self, class_body: str) -> list[str]:
        """Extract relationship names from SQLAlchemy model."""
        relationships: list[str] = []
        # Match: rel_name = relationship(...)
        rel_pattern = re.compile(
            r"^\s*(\w+)\s*(?::\s*[^\n=]+)?\s*=\s*relationship", re.MULTILINE
        )
        for match in rel_pattern.finditer(class_body):
            relationships.append(match.group(1))
        return relationships


class PrismaModelAnalyzer(AnalyzerBase):
    """Detect Prisma schema models."""

    def get_name(self) -> str:
        return "prisma"

    def get_priority(self) -> int:
        return 30

    def analyze(self, project_path: Path) -> list[ModelInfo]:
        """Parse Prisma schema.prisma for model definitions."""
        models: list[ModelInfo] = []

        # Find schema.prisma
        schema_paths = [
            project_path / "prisma" / "schema.prisma",
            project_path / "schema.prisma",
        ]

        for schema_path in schema_paths:
            content = self._read_file_safe(schema_path)
            if content:
                models = self._parse_schema(content, schema_path, project_path)
                break

        return models

    def _parse_schema(
        self, content: str, schema_path: Path, project_path: Path
    ) -> list[ModelInfo]:
        """Parse models from Prisma schema content."""
        models: list[ModelInfo] = []

        # Find all model blocks
        model_pattern = re.compile(r"model\s+(\w+)\s*\{([^}]+)\}", re.DOTALL)

        for match in model_pattern.finditer(content):
            model_name = match.group(1)
            block = match.group(2)

            fields: list[str] = []
            relationships: list[str] = []

            for line in block.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("//") or line.startswith("@@"):
                    continue

                # Parse field: fieldName Type @attributes
                field_match = re.match(r"(\w+)\s+(\w+)(\[\])?\s*", line)
                if field_match:
                    field_name = field_match.group(1)
                    field_type = field_match.group(2)

                    # Check if it's a relation (type is another model, not a scalar)
                    scalar_types = {
                        "String",
                        "Int",
                        "Float",
                        "Boolean",
                        "DateTime",
                        "Json",
                        "Bytes",
                        "Decimal",
                        "BigInt",
                    }
                    if field_type not in scalar_types:
                        relationships.append(field_name)
                    else:
                        fields.append(field_name)

            models.append(
                ModelInfo(
                    name=model_name,
                    table_name=model_name.lower(),  # Prisma uses model name as table
                    file_path=str(schema_path.relative_to(project_path)),
                    fields=fields,
                    relationships=relationships,
                )
            )

        return models


class TypeORMModelAnalyzer(AnalyzerBase):
    """Detect TypeORM entity models."""

    def get_name(self) -> str:
        return "typeorm"

    def get_priority(self) -> int:
        return 30

    def analyze(self, project_path: Path) -> list[ModelInfo]:
        """Find and parse TypeORM entities."""
        models: list[ModelInfo] = []

        # Look for entity files
        for ts_file in self._find_files(project_path, "**/*.entity.ts"):
            model = self._parse_entity(ts_file, project_path)
            if model:
                models.append(model)

        # Also check for @Entity decorator in other TS files
        for ts_file in self._find_files(project_path, "**/*.ts"):
            # Skip node_modules and already processed entity files
            rel_path = str(ts_file.relative_to(project_path))
            if "node_modules" in rel_path or ".entity.ts" in rel_path:
                continue

            content = self._read_file_safe(ts_file)
            if content and "@Entity(" in content:
                model = self._parse_entity(ts_file, project_path)
                if model:
                    models.append(model)

        return models

    def _parse_entity(self, file_path: Path, project_path: Path) -> ModelInfo | None:
        """Parse a TypeORM entity file."""
        content = self._read_file_safe(file_path)
        if not content or "@Entity" not in content:
            return None

        # Extract class name
        class_match = re.search(r"class\s+(\w+)", content)
        if not class_match:
            return None

        class_name = class_match.group(1)

        # Extract table name from @Entity('table_name') or @Entity({ name: 'table_name' })
        table_name = None
        entity_match = re.search(r"@Entity\(\s*['\"](\w+)['\"]", content)
        if entity_match:
            table_name = entity_match.group(1)
        else:
            entity_obj_match = re.search(
                r"@Entity\(\s*\{[^}]*name\s*:\s*['\"](\w+)['\"]", content
            )
            if entity_obj_match:
                table_name = entity_obj_match.group(1)

        # Extract @Column fields
        fields: list[str] = []
        column_pattern = re.compile(r"@(?:Column|PrimaryColumn|PrimaryGeneratedColumn)")
        for match in column_pattern.finditer(content):
            # Find the next property name after the decorator
            after_decorator = content[match.end() :]
            prop_match = re.search(r"^\s*(?:\([^)]*\))?\s*(\w+)\s*[;:]", after_decorator)
            if prop_match:
                fields.append(prop_match.group(1))

        # Extract relationship fields
        relationships: list[str] = []
        rel_pattern = re.compile(r"@(?:OneToOne|OneToMany|ManyToOne|ManyToMany)")
        for match in rel_pattern.finditer(content):
            after_decorator = content[match.end() :]
            prop_match = re.search(r"^\s*\([^)]*\)\s*(\w+)\s*[;:]", after_decorator)
            if prop_match:
                relationships.append(prop_match.group(1))

        return ModelInfo(
            name=class_name,
            table_name=table_name,
            file_path=str(file_path.relative_to(project_path)),
            fields=fields,
            relationships=relationships,
        )


# List of all model analyzers
MODEL_ANALYZERS: list[type[AnalyzerBase]] = [
    EloquentModelAnalyzer,
    DjangoModelAnalyzer,
    SQLAlchemyModelAnalyzer,
    PrismaModelAnalyzer,
    TypeORMModelAnalyzer,
]
