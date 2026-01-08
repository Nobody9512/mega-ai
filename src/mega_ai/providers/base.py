"""Base AI provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    """Represents a chat message."""

    role: str  # "user", "assistant", "system"
    content: str


@dataclass
class ToolCall:
    """Represents an AI tool call."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AIResponse:
    """Standardized AI response."""

    content: str | None
    tool_calls: list[ToolCall]
    stop_reason: str
    usage: dict[str, int]


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """Send chat completion request."""
        pass

    @abstractmethod
    def get_model_name(self, model_type: str) -> str:
        """Get the configured model name for orchestrator/worker."""
        pass
