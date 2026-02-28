"""Tests for the claude-chat extension."""

import os
from unittest.mock import patch

import pytest


class TestEnvironmentParsing:
    """Tests for environment variable parsing functions."""

    def test_parse_int_env_valid(self):
        """Test parsing valid integer environment variables."""
        from app import _parse_int_env

        with patch.dict(os.environ, {"TEST_INT": "42"}):
            assert _parse_int_env("TEST_INT") == 42

    def test_parse_int_env_missing(self):
        """Test parsing missing integer returns default."""
        from app import _parse_int_env

        with patch.dict(os.environ, {}, clear=True):
            assert _parse_int_env("NONEXISTENT") is None
            assert _parse_int_env("NONEXISTENT", default=10) == 10

    def test_parse_int_env_invalid(self):
        """Test parsing invalid integer returns default."""
        from app import _parse_int_env

        with patch.dict(os.environ, {"TEST_INT": "not_a_number"}):
            assert _parse_int_env("TEST_INT") is None
            assert _parse_int_env("TEST_INT", default=5) == 5

    def test_parse_float_env_valid(self):
        """Test parsing valid float environment variables."""
        from app import _parse_float_env

        with patch.dict(os.environ, {"TEST_FLOAT": "3.14"}):
            assert _parse_float_env("TEST_FLOAT") == 3.14

    def test_parse_float_env_missing(self):
        """Test parsing missing float returns default."""
        from app import _parse_float_env

        with patch.dict(os.environ, {}, clear=True):
            assert _parse_float_env("NONEXISTENT") is None
            assert _parse_float_env("NONEXISTENT", default=1.5) == 1.5

    def test_parse_float_env_invalid(self):
        """Test parsing invalid float returns default."""
        from app import _parse_float_env

        with patch.dict(os.environ, {"TEST_FLOAT": "not_a_float"}):
            assert _parse_float_env("TEST_FLOAT") is None

    def test_parse_bool_env_true_values(self):
        """Test parsing boolean true values."""
        from app import _parse_bool_env

        for val in ("1", "true", "yes", "TRUE", "Yes"):
            with patch.dict(os.environ, {"TEST_BOOL": val}):
                assert _parse_bool_env("TEST_BOOL") is True

    def test_parse_bool_env_false_values(self):
        """Test parsing boolean false values."""
        from app import _parse_bool_env

        for val in ("0", "false", "no", "FALSE", "No"):
            with patch.dict(os.environ, {"TEST_BOOL": val}):
                assert _parse_bool_env("TEST_BOOL") is False

    def test_parse_bool_env_default(self):
        """Test parsing boolean with default."""
        from app import _parse_bool_env

        with patch.dict(os.environ, {}, clear=True):
            assert _parse_bool_env("NONEXISTENT") is False
            assert _parse_bool_env("NONEXISTENT", default=True) is True


class TestToolsParsing:
    """Tests for tools configuration parsing."""

    def test_parse_tools_config_all(self):
        """Test parsing 'all' enables claude_code preset."""
        from app import _parse_tools_config

        result = _parse_tools_config("all")
        assert result == {"type": "preset", "preset": "claude_code"}

    def test_parse_tools_config_claude_code(self):
        """Test parsing 'claude_code' enables preset."""
        from app import _parse_tools_config

        result = _parse_tools_config("claude_code")
        assert result == {"type": "preset", "preset": "claude_code"}

    def test_parse_tools_config_list(self):
        """Test parsing comma-separated tool list."""
        from app import _parse_tools_config

        result = _parse_tools_config("Read,Write,Edit")
        assert result == ["Read", "Write", "Edit"]

    def test_parse_tools_config_list_with_spaces(self):
        """Test parsing handles whitespace."""
        from app import _parse_tools_config

        result = _parse_tools_config("Read , Write , Edit")
        assert result == ["Read", "Write", "Edit"]

    def test_parse_tools_config_empty(self):
        """Test parsing empty returns None."""
        from app import _parse_tools_config

        assert _parse_tools_config("") is None
        assert _parse_tools_config(None) is None

    def test_parse_tools_list(self):
        """Test parsing disallowed tools list."""
        from app import _parse_tools_list

        result = _parse_tools_list("Bash,Execute")
        assert result == ["Bash", "Execute"]

    def test_parse_tools_list_empty(self):
        """Test parsing empty disallowed tools."""
        from app import _parse_tools_list

        assert _parse_tools_list("") == []
        assert _parse_tools_list(None) == []


class TestCredentialChecking:
    """Tests for credential checking functions."""

    def test_check_anthropic_api_key_present(self):
        """Test detection of Anthropic API key."""
        from app import check_anthropic_api_key

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123"}):
            assert check_anthropic_api_key() is True

    def test_check_anthropic_api_key_missing(self):
        """Test missing Anthropic API key."""
        from app import check_anthropic_api_key

        with patch.dict(os.environ, {}, clear=True):
            assert check_anthropic_api_key() is False

    def test_check_anthropic_api_key_empty(self):
        """Test empty Anthropic API key."""
        from app import check_anthropic_api_key

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            assert check_anthropic_api_key() is False

    def test_check_aws_bedrock_not_enabled(self):
        """Test Bedrock check when not enabled."""
        from app import check_aws_bedrock_credentials

        with patch.dict(os.environ, {}, clear=True):
            assert check_aws_bedrock_credentials() is False

    def test_check_aws_bedrock_enabled_flag_only(self):
        """Test Bedrock check with just the flag (assumes IAM role)."""
        from app import check_aws_bedrock_credentials

        with patch.dict(os.environ, {"CLAUDE_CODE_USE_BEDROCK": "1"}, clear=True):
            assert check_aws_bedrock_credentials() is True

    def test_check_aws_bedrock_with_explicit_creds(self):
        """Test Bedrock check with explicit AWS credentials."""
        from app import check_aws_bedrock_credentials

        env = {
            "CLAUDE_CODE_USE_BEDROCK": "true",
            "AWS_ACCESS_KEY_ID": "AKIA...",
            "AWS_SECRET_ACCESS_KEY": "secret...",
        }
        with patch.dict(os.environ, env, clear=True):
            assert check_aws_bedrock_credentials() is True


class TestSDKImports:
    """Tests for SDK availability and imports."""

    def test_sdk_types_available(self):
        """Test that SDK types are importable."""
        from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        from claude_agent_sdk.types import (
            AssistantMessage,
            ResultMessage,
            StreamEvent,
            TextBlock,
            ThinkingBlock,
            ToolUseBlock,
        )

        # Verify these are actual classes/types
        assert ClaudeAgentOptions is not None
        assert ClaudeSDKClient is not None
        assert TextBlock is not None
        assert ThinkingBlock is not None
        assert StreamEvent is not None

class TestConfiguration:
    """Tests for configuration defaults and loading."""

    def test_default_models(self):
        """Test default model configuration."""
        from app import DEFAULT_ANTHROPIC_MODEL, DEFAULT_BEDROCK_MODEL

        assert "claude" in DEFAULT_ANTHROPIC_MODEL.lower()
        assert "anthropic" in DEFAULT_BEDROCK_MODEL.lower()
        # Bedrock model should have regional prefix
        assert DEFAULT_BEDROCK_MODEL.startswith("us.")

    def test_default_system_prompt(self):
        """Test default system prompt is set."""
        from app import DEFAULT_SYSTEM_PROMPT, SYSTEM_PROMPT

        assert len(DEFAULT_SYSTEM_PROMPT) > 0
        assert "helpful" in DEFAULT_SYSTEM_PROMPT.lower()
        # SYSTEM_PROMPT should equal default if env var not set
        assert SYSTEM_PROMPT == DEFAULT_SYSTEM_PROMPT or len(SYSTEM_PROMPT) > 0


class TestClaudeAgentOptions:
    """Tests for ClaudeAgentOptions configuration."""

    def test_options_with_all_settings(self):
        """Test creating options with all configurable settings."""
        from claude_agent_sdk import ClaudeAgentOptions

        options = ClaudeAgentOptions(
            allowed_tools=[],
            model="test-model",
            system_prompt="Test prompt",
            max_turns=10,
            max_budget_usd=0.50,
            include_partial_messages=True,
        )

        assert options.model == "test-model"
        assert options.system_prompt == "Test prompt"
        assert options.max_turns == 10
        assert options.max_budget_usd == 0.50
        assert options.include_partial_messages is True
        assert options.allowed_tools == []

    def test_options_with_none_limits(self):
        """Test options work with None limits (unlimited)."""
        from claude_agent_sdk import ClaudeAgentOptions

        options = ClaudeAgentOptions(
            max_turns=None,
            max_budget_usd=None,
        )

        assert options.max_turns is None
        assert options.max_budget_usd is None


class TestMessageTypes:
    """Tests for message type handling."""

    def test_text_block_structure(self):
        """Test TextBlock has expected attributes."""
        from claude_agent_sdk.types import TextBlock

        # TextBlock should be a dataclass with a text field
        import dataclasses
        assert dataclasses.is_dataclass(TextBlock)
        fields = {f.name for f in dataclasses.fields(TextBlock)}
        assert "text" in fields

    def test_thinking_block_structure(self):
        """Test ThinkingBlock has expected attributes."""
        from claude_agent_sdk.types import ThinkingBlock

        import dataclasses
        assert dataclasses.is_dataclass(ThinkingBlock)
        fields = {f.name for f in dataclasses.fields(ThinkingBlock)}
        assert "thinking" in fields

    def test_result_message_structure(self):
        """Test ResultMessage has cost tracking fields."""
        from claude_agent_sdk.types import ResultMessage

        import dataclasses
        assert dataclasses.is_dataclass(ResultMessage)
        fields = {f.name for f in dataclasses.fields(ResultMessage)}
        assert "total_cost_usd" in fields
        assert "is_error" in fields

    def test_stream_event_structure(self):
        """Test StreamEvent has expected attributes."""
        from claude_agent_sdk.types import StreamEvent

        import dataclasses
        assert dataclasses.is_dataclass(StreamEvent)
        fields = {f.name for f in dataclasses.fields(StreamEvent)}
        assert "event" in fields


class TestShinyApp:
    """Tests for Shiny app structure."""

    def test_app_created(self):
        """Test that the Shiny app is created."""
        from app import app

        from shiny import App
        assert isinstance(app, App)

    def test_ui_components_defined(self):
        """Test that UI components are defined."""
        from app import app_ui, screen_ui, setup_ui

        assert app_ui is not None
        assert setup_ui is not None
        assert screen_ui is not None
