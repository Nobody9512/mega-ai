"""OpenAI (GPT) provider implementation."""

import json
from typing import Any

from openai import OpenAI

from mega_ai.providers.base import AIResponse, BaseProvider, Message, ToolCall


class OpenAIProvider(BaseProvider):
    """OpenAI GPT API provider."""

    DEFAULT_MODELS = {
        "orchestrator": "gpt-4o",
        "worker": "gpt-4o-mini",
    }

    def __init__(
        self,
        api_key: str,
        orchestrator_model: str | None = None,
        worker_model: str | None = None,
    ):
        self.client = OpenAI(api_key=api_key)
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
        """Send chat completion request to OpenAI."""
        model = self.models.get(model_type, self.models["worker"])

        # Build messages with system prompt
        openai_messages = []
        if system:
            openai_messages.append({"role": "system", "content": system})

        for m in messages:
            openai_messages.append({"role": m.role, "content": m.content})

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": openai_messages,
        }

        if tools:
            # Convert tools to OpenAI format
            openai_tools = []
            for tool in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {}),
                    },
                })
            kwargs["tools"] = openai_tools

        response = self.client.chat.completions.create(**kwargs)

        # Parse response
        message = response.choices[0].message
        content = message.content
        tool_calls = []

        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments)
                        if tc.function.arguments
                        else {},
                    )
                )

        return AIResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.choices[0].finish_reason or "stop",
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    def get_model_name(self, model_type: str) -> str:
        """Get the configured model name."""
        return self.models.get(model_type, self.models["worker"])
