"""Custom exceptions for orchestrator module."""


class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""

    pass


class CommandBlockedError(OrchestratorError):
    """Raised when a dangerous command is blocked."""

    pass


class TaskNotFoundError(OrchestratorError):
    """Raised when a task UUID doesn't exist."""

    pass


class AnalysisError(OrchestratorError):
    """Raised when project analysis fails."""

    pass


class ScriptGenerationError(OrchestratorError):
    """Raised when script generation fails."""

    pass


class AIProviderError(OrchestratorError):
    """Raised when AI provider returns an error."""

    pass


class MaxIterationsError(OrchestratorError):
    """Raised when agentic loop exceeds max iterations."""

    pass
