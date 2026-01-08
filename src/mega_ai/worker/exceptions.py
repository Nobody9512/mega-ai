"""Custom exceptions for worker module."""


class WorkerError(Exception):
    """Base exception for worker errors."""

    pass


class TaskNotReadyError(WorkerError):
    """Raised when task is not in READY status."""

    pass


class ScriptLoadError(WorkerError):
    """Raised when runner.py or backup.py cannot be loaded."""

    pass


class BackupError(WorkerError):
    """Raised when backup creation fails."""

    pass


class ExecutionError(WorkerError):
    """Raised when runner.py execution fails."""

    pass


class RollbackError(WorkerError):
    """Raised when rollback fails."""

    pass
