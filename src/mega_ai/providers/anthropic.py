"""Anthropic (Claude) provider implementation."""

from typing import Any

from anthropic import Anthropic

from mega_ai.providers.base import AIResponse, BaseProvider, Message, ToolCall


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""

    DEFAULT_MODELS = {
        "orchestrator": "claude-opus-4-5-20251101",
        "worker": "claude-sonnet-4-5-20250929",
    }

    def __init__(
        self,
        api_key: str,
        orchestrator_model: str | None = None,
        worker_model: str | None = None,
    ):
        self.client = Anthropic(api_key=api_key)
        self.models = {
            "orchestrator": orchestrator_model or self.DEFAULT_MODELS["orchestrator"],
            "worker": worker_model or self.DEFAULT_MODELS["worker"],
        }

    def chat(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        model_type: str = "worker",
    ) -> AIResponse:
        """Send chat completion request to Claude."""
        model = self.models.get(model_type, self.models["worker"])

        # Convert messages to Anthropic format
        anthropic_messages = [{"role": m.role, "content": m.content} for m in messages]

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": anthropic_messages,
        }

        if system:
            kwargs["system"] = system

        if tools:
            # Convert tools to Anthropic format
            anthropic_tools = []
            for tool in tools:
                anthropic_tools.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters", {}),
                })
            kwargs["tools"] = anthropic_tools

        response = self.client.messages.create(**kwargs)

        # Parse response
        content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input if isinstance(block.input, dict) else {},
                    )
                )

        return AIResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    def get_model_name(self, model_type: str) -> str:
        """Get the configured model name."""
        return self.models.get(model_type, self.models["worker"])
