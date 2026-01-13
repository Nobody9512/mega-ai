"""Tests for WorkerAI helper module."""

from unittest.mock import MagicMock, patch

import pytest

from mega_ai.providers.base import AIResponse
from mega_ai.worker.ai_helper import WorkerAI


class TestWorkerAIInit:
    """Test WorkerAI initialization."""

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_init_loads_config(self, mock_load_config, mock_get_provider):
        """WorkerAI should load config on init."""
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider

        ai = WorkerAI()

        mock_load_config.assert_called_once()
        mock_get_provider.assert_called_once_with(mock_config)
        assert ai.provider == mock_provider

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_init_custom_retry_settings(self, mock_load_config, mock_get_provider):
        """WorkerAI should accept custom retry settings."""
        mock_load_config.return_value = MagicMock()
        mock_get_provider.return_value = MagicMock()

        ai = WorkerAI(max_retries=5, retry_delay=1.0)

        assert ai.max_retries == 5
        assert ai.retry_delay == 1.0


class TestWorkerAITransform:
    """Test WorkerAI.transform method."""

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_transform_single_text(self, mock_load_config, mock_get_provider):
        """transform() should call provider with correct arguments."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = AIResponse(
            content="Transformed Text",
            tool_calls=[],
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        mock_get_provider.return_value = mock_provider
        mock_load_config.return_value = MagicMock()

        ai = WorkerAI()
        result = ai.transform("System prompt", "Original text")

        assert result == "Transformed Text"
        mock_provider.chat.assert_called_once()
        call_kwargs = mock_provider.chat.call_args
        assert call_kwargs.kwargs["system"] == "System prompt"
        assert call_kwargs.kwargs["model_type"] == "worker"

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_transform_returns_empty_on_none_content(
        self, mock_load_config, mock_get_provider
    ):
        """transform() should return empty string if content is None."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = AIResponse(
            content=None,
            tool_calls=[],
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 0},
        )
        mock_get_provider.return_value = mock_provider
        mock_load_config.return_value = MagicMock()

        ai = WorkerAI()
        result = ai.transform("System prompt", "Text")

        assert result == ""


class TestWorkerAIBatchTransform:
    """Test WorkerAI.batch_transform method."""

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_batch_transform_empty_list(self, mock_load_config, mock_get_provider):
        """batch_transform() should return empty list for empty input."""
        mock_get_provider.return_value = MagicMock()
        mock_load_config.return_value = MagicMock()

        ai = WorkerAI()
        result = ai.batch_transform("System prompt", [])

        assert result == []

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_batch_transform_multiple_texts(self, mock_load_config, mock_get_provider):
        """batch_transform() should transform multiple texts."""
        mock_provider = MagicMock()
        mock_provider.chat.return_value = AIResponse(
            content="1. Result One\n2. Result Two\n3. Result Three",
            tool_calls=[],
            stop_reason="end_turn",
            usage={"input_tokens": 30, "output_tokens": 15},
        )
        mock_get_provider.return_value = mock_provider
        mock_load_config.return_value = MagicMock()

        ai = WorkerAI()
        result = ai.batch_transform(
            "System prompt", ["Text one", "Text two", "Text three"]
        )

        assert len(result) == 3
        assert result[0] == "Result One"
        assert result[1] == "Result Two"
        assert result[2] == "Result Three"


class TestParseNumberedResponse:
    """Test _parse_numbered_response method."""

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_parse_numbered_lines(self, mock_load_config, mock_get_provider):
        """Should correctly parse numbered response lines."""
        mock_get_provider.return_value = MagicMock()
        mock_load_config.return_value = MagicMock()

        ai = WorkerAI()
        result = ai._parse_numbered_response(
            "1. First\n2. Second\n3. Third",
            expected_count=3,
            originals=["a", "b", "c"],
        )

        assert result == ["First", "Second", "Third"]

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_parse_pads_with_originals(self, mock_load_config, mock_get_provider):
        """Should pad with originals if AI returns fewer items."""
        mock_get_provider.return_value = MagicMock()
        mock_load_config.return_value = MagicMock()

        ai = WorkerAI()
        result = ai._parse_numbered_response(
            "1. First\n2. Second",
            expected_count=4,
            originals=["a", "b", "c", "d"],
        )

        assert len(result) == 4
        assert result[0] == "First"
        assert result[1] == "Second"
        assert result[2] == "c"  # Original
        assert result[3] == "d"  # Original

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_parse_trims_extra_items(self, mock_load_config, mock_get_provider):
        """Should trim if AI returns more items than expected."""
        mock_get_provider.return_value = MagicMock()
        mock_load_config.return_value = MagicMock()

        ai = WorkerAI()
        result = ai._parse_numbered_response(
            "1. First\n2. Second\n3. Third\n4. Fourth",
            expected_count=2,
            originals=["a", "b"],
        )

        assert len(result) == 2
        assert result == ["First", "Second"]


class TestWorkerAIGetModelName:
    """Test get_model_name method."""

    @patch("mega_ai.worker.ai_helper.get_provider")
    @patch("mega_ai.worker.ai_helper.load_config")
    def test_get_model_name(self, mock_load_config, mock_get_provider):
        """get_model_name() should return worker model name."""
        mock_provider = MagicMock()
        mock_provider.get_model_name.return_value = "claude-sonnet-4-5-20250929"
        mock_get_provider.return_value = mock_provider
        mock_load_config.return_value = MagicMock()

        ai = WorkerAI()
        result = ai.get_model_name()

        assert result == "claude-sonnet-4-5-20250929"
        mock_provider.get_model_name.assert_called_once_with("worker")
