"""Pydantic models for orchestrator task data."""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of an orchestrator task."""

    # Orchestrator statuses
    PENDING = "pending"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"

    # Worker statuses
    BACKING_UP = "backing_up"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


class ProjectInfo(BaseModel):
    """Detected project information."""

    path: Path
    framework: str | None = None
    framework_version: str | None = None


class DatabaseInfo(BaseModel):
    """Detected database information."""

    type: str | None = None  # mysql, postgresql, mongodb
    version: str | None = None
    host: str | None = None
    name: str | None = None


class TargetInfo(BaseModel):
    """Transformation target information."""

    type: str = "database"
    table: str | None = None
    column: str | None = None
    primary_key: str = "id"
    rows_count: int | None = None


class ExecutionConfig(BaseModel):
    """Execution configuration for worker."""

    batch_strategy: str = "dynamic"
    max_tokens_per_batch: int = 4000
    estimated_cost: float | None = None
    estimated_time: str | None = None


class TaskConfig(BaseModel):
    """Complete task configuration (saved as config.json)."""

    uuid: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    description: str
    status: TaskStatus = TaskStatus.PENDING

    project: ProjectInfo
    database: DatabaseInfo = Field(default_factory=DatabaseInfo)
    target: TargetInfo = Field(default_factory=TargetInfo)

    models: dict[str, str] = Field(default_factory=dict)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)

    class Config:
        json_encoders = {
            Path: str,
            datetime: lambda v: v.isoformat(),
        }


class ToolResult(BaseModel):
    """Result from a tool execution."""

    success: bool
    output: str
    error: str | None = None
