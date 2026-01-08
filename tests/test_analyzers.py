"""Tests for the analyzers module."""

import json
from pathlib import Path

import pytest

from mega_ai.analyzers import AnalysisResult, ProjectAnalyzer
from mega_ai.analyzers.databases import (
    DjangoDatabaseAnalyzer,
    EnvDatabaseAnalyzer,
    LaravelDatabaseAnalyzer,
    PrismaDatabaseAnalyzer,
    RailsDatabaseAnalyzer,
)
from mega_ai.analyzers.frameworks import (
    DjangoAnalyzer,
    ExpressAnalyzer,
    FastAPIAnalyzer,
    LaravelAnalyzer,
    RailsAnalyzer,
)
from mega_ai.analyzers.models import (
    DjangoModelAnalyzer,
    EloquentModelAnalyzer,
    PrismaModelAnalyzer,
    SQLAlchemyModelAnalyzer,
    TypeORMModelAnalyzer,
)
from mega_ai.orchestrator.models import DatabaseInfo, FrameworkInfo, ModelInfo


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    return tmp_path


# =============================================================================
# Framework Analyzer Tests
# =============================================================================


class TestLaravelAnalyzer:
    """Tests for Laravel framework detection."""

    def test_detect_laravel(self, tmp_project: Path) -> None:
        """Test detection of Laravel framework."""
        # Create composer.json with Laravel
        composer = {
            "require": {
                "laravel/framework": "^10.0"
            }
        }
        (tmp_project / "composer.json").write_text(json.dumps(composer))
        (tmp_project / "artisan").touch()
        (tmp_project / "config").mkdir()
        (tmp_project / "config" / "database.php").touch()

        analyzer = LaravelAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.name == "laravel"
        assert result.version == "^10.0"
        assert "artisan" in result.entry_points
        assert "config/database.php" in result.config_paths

    def test_no_laravel(self, tmp_project: Path) -> None:
        """Test no detection when Laravel not present."""
        composer = {"require": {"some/package": "1.0"}}
        (tmp_project / "composer.json").write_text(json.dumps(composer))

        analyzer = LaravelAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is None


class TestDjangoAnalyzer:
    """Tests for Django framework detection."""

    def test_detect_django(self, tmp_project: Path) -> None:
        """Test detection of Django framework."""
        manage_py = """
#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
"""
        (tmp_project / "manage.py").write_text(manage_py)
        (tmp_project / "requirements.txt").write_text("Django==4.2.0\n")
        (tmp_project / "myproject").mkdir()
        (tmp_project / "myproject" / "settings.py").touch()

        analyzer = DjangoAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.name == "django"
        assert result.version == "4.2.0"
        assert "manage.py" in result.entry_points

    def test_no_django(self, tmp_project: Path) -> None:
        """Test no detection when Django not present."""
        (tmp_project / "manage.py").write_text("# Just a Python file")

        analyzer = DjangoAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is None


class TestFastAPIAnalyzer:
    """Tests for FastAPI framework detection."""

    def test_detect_fastapi(self, tmp_project: Path) -> None:
        """Test detection of FastAPI framework."""
        main_py = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
"""
        (tmp_project / "main.py").write_text(main_py)
        (tmp_project / "requirements.txt").write_text("fastapi>=0.100.0\nuvicorn\n")

        analyzer = FastAPIAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.name == "fastapi"
        assert "main.py" in result.entry_points


class TestExpressAnalyzer:
    """Tests for Express.js framework detection."""

    def test_detect_express(self, tmp_project: Path) -> None:
        """Test detection of Express.js framework."""
        package = {
            "name": "myapp",
            "dependencies": {
                "express": "^4.18.0"
            },
            "main": "app.js",
            "scripts": {
                "start": "node app.js"
            }
        }
        (tmp_project / "package.json").write_text(json.dumps(package))
        (tmp_project / "app.js").touch()

        analyzer = ExpressAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.name == "express"
        assert result.version == "4.18.0"
        assert "app.js" in result.entry_points


class TestRailsAnalyzer:
    """Tests for Rails framework detection."""

    def test_detect_rails(self, tmp_project: Path) -> None:
        """Test detection of Rails framework."""
        gemfile = """
source 'https://rubygems.org'
gem 'rails', '~> 7.0.0'
gem 'pg'
"""
        (tmp_project / "Gemfile").write_text(gemfile)
        (tmp_project / "config").mkdir()
        (tmp_project / "config" / "database.yml").touch()
        (tmp_project / "bin").mkdir()
        (tmp_project / "bin" / "rails").touch()

        analyzer = RailsAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.name == "rails"
        assert result.version == "~> 7.0.0"
        assert "bin/rails" in result.entry_points


# =============================================================================
# Database Analyzer Tests
# =============================================================================


class TestEnvDatabaseAnalyzer:
    """Tests for .env database detection."""

    def test_detect_database_url(self, tmp_project: Path) -> None:
        """Test detection from DATABASE_URL."""
        env_content = """
DATABASE_URL=postgresql://user:pass@localhost:5432/mydb
SECRET_KEY=abc123
"""
        (tmp_project / ".env").write_text(env_content)

        analyzer = EnvDatabaseAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.type == "postgresql"
        assert result.host == "localhost"
        assert result.port == 5432
        assert result.name == "mydb"

    def test_detect_laravel_env(self, tmp_project: Path) -> None:
        """Test detection from Laravel-style DB_* variables."""
        env_content = """
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=laravel
DB_USERNAME=root
DB_PASSWORD=secret
"""
        (tmp_project / ".env").write_text(env_content)

        analyzer = EnvDatabaseAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.type == "mysql"
        assert result.host == "127.0.0.1"
        assert result.port == 3306
        assert result.name == "laravel"

    def test_no_database_env(self, tmp_project: Path) -> None:
        """Test no detection when no DB config in .env."""
        env_content = """
SECRET_KEY=abc123
DEBUG=true
"""
        (tmp_project / ".env").write_text(env_content)

        analyzer = EnvDatabaseAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is None


class TestDjangoDatabaseAnalyzer:
    """Tests for Django database detection."""

    def test_detect_django_db(self, tmp_project: Path) -> None:
        """Test detection from Django settings.py."""
        settings = """
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
"""
        (tmp_project / "myproject").mkdir()
        (tmp_project / "myproject" / "settings.py").write_text(settings)

        analyzer = DjangoDatabaseAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.type == "postgresql"
        assert result.name == "mydb"


class TestPrismaDatabaseAnalyzer:
    """Tests for Prisma database detection."""

    def test_detect_prisma_db(self, tmp_project: Path) -> None:
        """Test detection from Prisma schema."""
        schema = """
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id    Int    @id @default(autoincrement())
  name  String
}
"""
        (tmp_project / "prisma").mkdir()
        (tmp_project / "prisma" / "schema.prisma").write_text(schema)

        analyzer = PrismaDatabaseAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.type == "postgresql"


class TestRailsDatabaseAnalyzer:
    """Tests for Rails database detection."""

    def test_detect_rails_db(self, tmp_project: Path) -> None:
        """Test detection from Rails database.yml."""
        db_yml = """
development:
  adapter: postgresql
  database: myapp_development
  host: localhost
  port: 5432

production:
  adapter: postgresql
  database: myapp_production
"""
        (tmp_project / "config").mkdir()
        (tmp_project / "config" / "database.yml").write_text(db_yml)

        analyzer = RailsDatabaseAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result is not None
        assert result.type == "postgresql"
        assert result.name == "myapp_development"


# =============================================================================
# Model Analyzer Tests
# =============================================================================


class TestEloquentModelAnalyzer:
    """Tests for Eloquent model detection."""

    def test_detect_eloquent_model(self, tmp_project: Path) -> None:
        """Test detection of Eloquent models."""
        model_php = """<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;

class User extends Model
{
    protected $table = 'users';
    protected $fillable = ['name', 'email', 'password'];

    public function posts()
    {
        return $this->hasMany(Post::class);
    }
}
"""
        (tmp_project / "app" / "Models").mkdir(parents=True)
        (tmp_project / "app" / "Models" / "User.php").write_text(model_php)

        analyzer = EloquentModelAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert len(result) == 1
        assert result[0].name == "User"
        assert result[0].table_name == "users"
        assert "name" in result[0].fields
        assert "email" in result[0].fields
        assert "posts" in result[0].relationships


class TestDjangoModelAnalyzer:
    """Tests for Django model detection."""

    def test_detect_django_model(self, tmp_project: Path) -> None:
        """Test detection of Django models."""
        models_py = """
from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    profile = models.OneToOneField('Profile', on_delete=models.CASCADE)

    class Meta:
        db_table = 'custom_users'

class Profile(models.Model):
    bio = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
"""
        (tmp_project / "myapp").mkdir()
        (tmp_project / "myapp" / "models.py").write_text(models_py)

        analyzer = DjangoModelAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert len(result) == 2
        user_model = next(m for m in result if m.name == "User")
        assert user_model.table_name == "custom_users"
        assert "name" in user_model.fields
        assert "profile" in user_model.relationships


class TestSQLAlchemyModelAnalyzer:
    """Tests for SQLAlchemy model detection."""

    def test_detect_sqlalchemy_model(self, tmp_project: Path) -> None:
        """Test detection of SQLAlchemy models."""
        models_py = """
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(255))

    posts = relationship("Post", back_populates="author")
"""
        (tmp_project / "models.py").write_text(models_py)

        analyzer = SQLAlchemyModelAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert len(result) == 1
        assert result[0].name == "User"
        assert result[0].table_name == "users"
        assert "id" in result[0].fields
        assert "posts" in result[0].relationships


class TestPrismaModelAnalyzer:
    """Tests for Prisma model detection."""

    def test_detect_prisma_model(self, tmp_project: Path) -> None:
        """Test detection of Prisma models."""
        schema = """
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  name      String?
  posts     Post[]
  profile   Profile?
}

model Post {
  id        Int     @id @default(autoincrement())
  title     String
  content   String?
  author    User    @relation(fields: [authorId], references: [id])
  authorId  Int
}
"""
        (tmp_project / "prisma").mkdir()
        (tmp_project / "prisma" / "schema.prisma").write_text(schema)

        analyzer = PrismaModelAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert len(result) == 2
        user_model = next(m for m in result if m.name == "User")
        assert "id" in user_model.fields
        assert "email" in user_model.fields
        assert "posts" in user_model.relationships


class TestTypeORMModelAnalyzer:
    """Tests for TypeORM model detection."""

    def test_detect_typeorm_model(self, tmp_project: Path) -> None:
        """Test detection of TypeORM entities."""
        entity_ts = """
import { Entity, Column, PrimaryGeneratedColumn, OneToMany } from 'typeorm';
import { Post } from './post.entity';

@Entity('users')
export class User {
    @PrimaryGeneratedColumn()
    id: number;

    @Column()
    name: string;

    @Column()
    email: string;

    @OneToMany(() => Post, post => post.author)
    posts: Post[];
}
"""
        (tmp_project / "src" / "entities").mkdir(parents=True)
        (tmp_project / "src" / "entities" / "user.entity.ts").write_text(entity_ts)

        analyzer = TypeORMModelAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert len(result) == 1
        assert result[0].name == "User"
        assert result[0].table_name == "users"


# =============================================================================
# ProjectAnalyzer Integration Tests
# =============================================================================


class TestProjectAnalyzer:
    """Tests for the main ProjectAnalyzer class."""

    def test_analyze_laravel_project(self, tmp_project: Path) -> None:
        """Test full analysis of a Laravel project."""
        # Setup Laravel project
        composer = {"require": {"laravel/framework": "^10.0"}}
        (tmp_project / "composer.json").write_text(json.dumps(composer))
        (tmp_project / "artisan").touch()

        env_content = """
DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=laravel
"""
        (tmp_project / ".env").write_text(env_content)

        model_php = """<?php
namespace App\\Models;
use Illuminate\\Database\\Eloquent\\Model;
class User extends Model {
    protected $fillable = ['name'];
}
"""
        (tmp_project / "app" / "Models").mkdir(parents=True)
        (tmp_project / "app" / "Models" / "User.php").write_text(model_php)

        analyzer = ProjectAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert isinstance(result, AnalysisResult)
        assert result.project_info.framework == "laravel"
        assert result.project_info.package_manager == "composer"
        assert result.database_info.type == "mysql"
        assert result.database_info.host == "127.0.0.1"
        assert len(result.project_info.orm_models) == 1

    def test_analyze_django_project(self, tmp_project: Path) -> None:
        """Test full analysis of a Django project."""
        # Setup Django project
        manage_py = """
import django
from django.core.management import execute_from_command_line
"""
        (tmp_project / "manage.py").write_text(manage_py)
        (tmp_project / "requirements.txt").write_text("Django==4.2.0\n")

        settings = """
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'mydb',
    }
}
"""
        (tmp_project / "myproject").mkdir()
        (tmp_project / "myproject" / "settings.py").write_text(settings)

        analyzer = ProjectAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert result.project_info.framework == "django"
        assert result.project_info.framework_version == "4.2.0"
        assert result.project_info.package_manager == "pip"
        assert result.database_info.type == "postgresql"

    def test_analyze_empty_project(self, tmp_project: Path) -> None:
        """Test analysis of an empty project."""
        analyzer = ProjectAnalyzer()
        result = analyzer.analyze(tmp_project)

        assert isinstance(result, AnalysisResult)
        assert result.project_info.framework is None
        assert result.project_info.orm is None
        assert result.database_info.type is None

    def test_package_manager_detection(self, tmp_project: Path) -> None:
        """Test detection of various package managers."""
        # Test npm
        (tmp_project / "package.json").write_text("{}")
        analyzer = ProjectAnalyzer()
        result = analyzer.analyze(tmp_project)
        assert result.project_info.package_manager == "npm"

        # Test yarn
        (tmp_project / "yarn.lock").touch()
        result = analyzer.analyze(tmp_project)
        assert result.project_info.package_manager == "yarn"

        # Cleanup and test pip
        (tmp_project / "package.json").unlink()
        (tmp_project / "yarn.lock").unlink()
        (tmp_project / "requirements.txt").write_text("Django>=4.0\n")
        result = analyzer.analyze(tmp_project)
        assert result.project_info.package_manager == "pip"
