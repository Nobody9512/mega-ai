"""Task management utilities for orchestrator."""

import json
import uuid
from pathlib import Path

from mega_ai.orchestrator.models import TaskConfig, TaskStatus


def generate_task_uuid() -> str:
    """Generate a short, readable UUID for a task."""
    # Use first 8 characters of UUID4 for brevity
    return uuid.uuid4().hex[:8]


def get_tasks_dir(project_path: Path) -> Path:
    """Get the .mega-ai/tasks directory path."""
    return project_path / ".mega-ai" / "tasks"


def create_task_folder(project_path: Path, task_uuid: str) -> Path:
    """Create task folder structure and return the path."""
    task_path = get_tasks_dir(project_path) / task_uuid

    # Create directory structure
    task_path.mkdir(parents=True, exist_ok=True)
    (task_path / "backups").mkdir(exist_ok=True)
    (task_path / "logs").mkdir(exist_ok=True)

    return task_path


def save_task_config(task_path: Path, config: TaskConfig) -> None:
    """Save task configuration to config.json."""
    config_path = task_path / "config.json"

    # Convert to dict with proper serialization
    data = json.loads(config.model_dump_json(exclude_none=True))

    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_task_config(task_path: Path) -> TaskConfig:
    """Load task configuration from config.json."""
    config_path = task_path / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Task config not found: {config_path}")

    data = json.loads(config_path.read_text())
    return TaskConfig(**data)


def update_task_status(task_path: Path, status: TaskStatus) -> None:
    """Update the status field in task config."""
    config = load_task_config(task_path)
    config.status = status
    save_task_config(task_path, config)


def list_tasks(project_path: Path) -> list[TaskConfig]:
    """List all tasks in the project."""
    tasks_dir = get_tasks_dir(project_path)
    if not tasks_dir.exists():
        return []

    tasks = []
    for task_folder in tasks_dir.iterdir():
        if task_folder.is_dir():
            try:
                config = load_task_config(task_folder)
                tasks.append(config)
            except Exception:
                continue

    # Sort by creation date, newest first
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    return tasks


def get_task_path(project_path: Path, task_uuid: str) -> Path:
    """Get the path to a specific task folder."""
    return get_tasks_dir(project_path) / task_uuid
