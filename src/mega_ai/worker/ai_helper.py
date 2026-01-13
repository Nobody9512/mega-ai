"""AI helper module for worker scripts.

This module provides simple AI functions for generated runner.py scripts.
It automatically loads API keys from MEGA-AI config.

Usage:
    from mega_ai.worker.ai_helper import WorkerAI

    ai = WorkerAI()
    result = ai.transform(system_prompt, text)
    results = ai.batch_transform(system_prompt, texts_list, batch_size=20)
"""

import logging
import time
from typing import Any

from mega_ai.providers.base import Message
from mega_ai.utils.config import get_provider, load_config

logger = logging.getLogger(__name__)


class WorkerAI:
    """Simple AI helper for generated runner.py scripts.

    Automatically loads API keys and provider configuration from
    ~/.mega-ai/config.yaml.
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        """Initialize WorkerAI with config.

        Args:
            max_retries: Maximum retry attempts for failed API calls
            retry_delay: Delay in seconds between retries
        """
        self.config = load_config()
        self.provider = get_provider(self.config)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def transform(
        self,
        system_prompt: str,
        text: str,
        max_tokens: int = 2048,
    ) -> str:
        """Transform a single text using AI.

        Args:
            system_prompt: System prompt describing the transformation task
            text: Text to transform
            max_tokens: Maximum tokens in response

        Returns:
            Transformed text

        Raises:
            Exception: If all retry attempts fail
        """
        messages = [Message(role="user", content=text)]

        for attempt in range(self.max_retries):
            try:
                response = self.provider.chat(
                    messages=messages,
                    system=system_prompt,
                    max_tokens=max_tokens,
                    model_type="worker",
                )
                return response.content or ""

            except Exception as e:
                logger.warning(f"AI transform attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise

        return ""

    def batch_transform(
        self,
        system_prompt: str,
        texts: list[str],
        batch_size: int = 20,
        max_tokens: int = 4096,
    ) -> list[str]:
        """Transform multiple texts in a single AI call.

        Sends all texts in a numbered format and parses the response.

        Args:
            system_prompt: System prompt describing the transformation task
            texts: List of texts to transform
            batch_size: Number of texts per API call (for future chunking)
            max_tokens: Maximum tokens in response

        Returns:
            List of transformed texts (same length as input)
        """
        if not texts:
            return []

        # Build numbered prompt
        prompt_lines = []
        for i, text in enumerate(texts, 1):
            prompt_lines.append(f"{i}. {text}")
        prompt = "\n".join(prompt_lines)

        messages = [Message(role="user", content=prompt)]

        for attempt in range(self.max_retries):
            try:
                response = self.provider.chat(
                    messages=messages,
                    system=system_prompt,
                    max_tokens=max_tokens,
                    model_type="worker",
                )

                result_text = response.content or ""
                return self._parse_numbered_response(result_text, len(texts), texts)

            except Exception as e:
                logger.warning(f"AI batch_transform attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    # Return originals on complete failure
                    logger.error(f"All {self.max_retries} attempts failed, returning originals")
                    return texts

        return texts

    def _parse_numbered_response(
        self,
        response_text: str,
        expected_count: int,
        originals: list[str],
    ) -> list[str]:
        """Parse a numbered response from the AI.

        Args:
            response_text: Raw response from AI
            expected_count: Expected number of items
            originals: Original texts (fallback if parsing fails)

        Returns:
            List of parsed results
        """
        lines = response_text.strip().split("\n")
        results = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove numbering (e.g., "1. Text" -> "Text")
            if line and line[0].isdigit():
                parts = line.split(". ", 1)
                if len(parts) > 1:
                    line = parts[1]

            results.append(line)

        # Ensure we have the expected count
        if len(results) < expected_count:
            logger.warning(
                f"AI returned {len(results)} items, expected {expected_count}. "
                "Padding with originals."
            )
            while len(results) < expected_count:
                results.append(originals[len(results)])

        elif len(results) > expected_count:
            logger.warning(
                f"AI returned {len(results)} items, expected {expected_count}. Trimming."
            )
            results = results[:expected_count]

        return results

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        max_tokens: int = 4096,
    ) -> str:
        """General chat method for custom interactions.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response

        Returns:
            AI response content
        """
        msg_objects = [Message(role=m["role"], content=m["content"]) for m in messages]

        for attempt in range(self.max_retries):
            try:
                response = self.provider.chat(
                    messages=msg_objects,
                    system=system_prompt,
                    max_tokens=max_tokens,
                    model_type="worker",
                )
                return response.content or ""

            except Exception as e:
                logger.warning(f"AI chat attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise

        return ""

    def get_model_name(self) -> str:
        """Get the worker model name being used."""
        return self.provider.get_model_name("worker")
