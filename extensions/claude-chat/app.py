"""
Claude Chat - Basic chat interface using the Claude Agent SDK.

This extension provides a simple chat interface for asking general questions
using the Claude Agent SDK. It supports authentication via:
- ANTHROPIC_API_KEY environment variable
- AWS Bedrock credentials (CLAUDE_CODE_USE_BEDROCK=1)

Note: The SDK does NOT use OAuth credentials from the Claude Code CLI.
You must provide an API key.
"""

import os
import sys

import uvicorn
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, reactive, render, ui
from shiny.session._session import AppSession

load_dotenv()

# =============================================================================
# SDK Import (conditional)
# =============================================================================
try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    from claude_agent_sdk.types import (
        AssistantMessage,
        ResultMessage,
        StreamEvent,
        TextBlock,
        ThinkingBlock,
        ToolUseBlock,
    )

    SDK_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Claude Agent SDK not available: {e}", file=sys.stderr)
    SDK_AVAILABLE = False

# =============================================================================
# Configuration via Environment Variables
# =============================================================================

# Model configuration
# For Bedrock, use the regional prefix (e.g., us.anthropic.claude-sonnet-4-5-20250929-v1:0)
DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL")

# System prompt - configurable via environment variable
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer questions clearly and concisely. "
    "You are running as part of a Posit Connect extension."
)
SYSTEM_PROMPT = os.getenv("CLAUDE_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)

# Safety limits - None means no limit
def _parse_int_env(key: str, default: int | None = None) -> int | None:
    """Parse an integer environment variable, returning None if not set or invalid."""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        print(f"Warning: Invalid integer for {key}: {val}", file=sys.stderr)
        return default


def _parse_float_env(key: str, default: float | None = None) -> float | None:
    """Parse a float environment variable, returning None if not set or invalid."""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        print(f"Warning: Invalid float for {key}: {val}", file=sys.stderr)
        return default


def _parse_bool_env(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    val = os.getenv(key, "").lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


# Max turns per conversation (None = unlimited)
MAX_TURNS = _parse_int_env("CLAUDE_MAX_TURNS", default=None)

# Max budget in USD per request (None = unlimited)
MAX_BUDGET_USD = _parse_float_env("CLAUDE_MAX_BUDGET_USD", default=None)

# Enable partial message streaming for real-time text display
INCLUDE_PARTIAL_MESSAGES = _parse_bool_env("CLAUDE_PARTIAL_MESSAGES", default=True)

# Show thinking blocks in output (for extended thinking models)
SHOW_THINKING = _parse_bool_env("CLAUDE_SHOW_THINKING", default=False)

# Show cost information after each response
SHOW_COST = _parse_bool_env("CLAUDE_SHOW_COST", default=False)

# Permission mode for tool usage:
# - "default": Prompts for dangerous tools (not supported in this UI)
# - "acceptEdits": Auto-accept file edits
# - "bypassPermissions": Allow all tools without prompting
# Default to "acceptEdits" since we can't surface permission prompts in the chat UI
PERMISSION_MODE = os.getenv("CLAUDE_PERMISSION_MODE", "acceptEdits")

# Tools configuration:
# - "all" or "claude_code": Enable all Claude Code tools
# - Comma-separated list: Enable specific tools (e.g., "Read,Write,Edit,Bash")
# - Empty or unset: Use SDK defaults
def _parse_tools_config(val: str | None) -> list[str] | dict | None:
    """Parse tools configuration from environment variable."""
    if not val:
        return None
    val = val.strip()
    if val.lower() in ("all", "claude_code"):
        return {"type": "preset", "preset": "claude_code"}
    # Parse comma-separated list
    tools = [t.strip() for t in val.split(",") if t.strip()]
    return tools if tools else None


TOOLS_CONFIG = _parse_tools_config(os.getenv("CLAUDE_TOOLS", "all"))

# Disallowed tools (comma-separated list of tools to block)
def _parse_tools_list(val: str | None) -> list[str]:
    """Parse comma-separated tools list."""
    if not val:
        return []
    return [t.strip() for t in val.split(",") if t.strip()]


DISALLOWED_TOOLS = _parse_tools_list(os.getenv("CLAUDE_DISALLOWED_TOOLS"))


def check_anthropic_api_key() -> bool:
    """Check if ANTHROPIC_API_KEY is set."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def check_aws_bedrock_credentials() -> bool:
    """Check if AWS Bedrock credentials are available."""
    # Check for CLAUDE_CODE_USE_BEDROCK flag and AWS credentials
    use_bedrock = os.getenv("CLAUDE_CODE_USE_BEDROCK", "").lower() in ("1", "true")
    if not use_bedrock:
        return False

    # Check for AWS credentials (either explicit or from IAM role)
    has_explicit_creds = bool(
        os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    # On Connect with IAM role, credentials are injected automatically
    # We'll assume if CLAUDE_CODE_USE_BEDROCK is set, the admin knows what they're doing
    return has_explicit_creds or use_bedrock


# Check for credentials
# Note: The SDK does NOT use OAuth credentials from local Claude Code CLI (~/.claude/)
# It requires explicit API key or Bedrock credentials
HAS_ANTHROPIC_KEY = check_anthropic_api_key()
HAS_BEDROCK = check_aws_bedrock_credentials()
HAS_CREDENTIALS = SDK_AVAILABLE and (HAS_ANTHROPIC_KEY or HAS_BEDROCK)

# Log startup status
if not SDK_AVAILABLE:
    print("Claude Agent SDK not available - install claude-agent-sdk package")
elif HAS_ANTHROPIC_KEY:
    print("Using ANTHROPIC_API_KEY for authentication")
elif HAS_BEDROCK:
    print("Using AWS Bedrock for authentication")
else:
    print("No authentication method available - set ANTHROPIC_API_KEY or configure Bedrock")

# Log configuration
print(f"Configuration: max_turns={MAX_TURNS}, max_budget_usd={MAX_BUDGET_USD}, "
      f"partial_messages={INCLUDE_PARTIAL_MESSAGES}, show_thinking={SHOW_THINKING}, "
      f"show_cost={SHOW_COST}, permission_mode={PERMISSION_MODE}, "
      f"tools={TOOLS_CONFIG}, disallowed_tools={DISALLOWED_TOOLS}")


# Setup UI shown when credentials are missing
setup_ui = ui.page_fillable(
    ui.tags.style(
        """
        body {
            padding: 0;
            margin: 0;
            background: linear-gradient(135deg, #d97706 0%, #ea580c 100%);
        }

        .setup-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .setup-card {
            background: white;
            border-radius: 16px;
            padding: 3rem;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            width: 100%;
        }
        .setup-title {
            color: #2d3748;
            font-weight: 700;
            margin-bottom: 2rem;
            text-align: center;
            font-size: 2.5rem;
        }
        .setup-section-title {
            color: #4a5568;
            font-weight: 600;
            margin-top: 2.5rem;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            border-left: 4px solid #d97706;
            padding-left: 1rem;
        }
        .setup-description {
            color: #718096;
            line-height: 1.6;
            margin-bottom: 1.5rem;
        }
        .setup-code-block {
            background: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1.5rem;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9rem;
            color: #2d3748;
            margin: 1rem 0;
            overflow-x: auto;
        }
        .setup-link {
            color: #d97706;
            text-decoration: none;
            font-weight: 500;
        }
        .setup-link:hover {
            color: #ea580c;
            text-decoration: underline;
        }
        @media (max-width: 768px) {
            .setup-container {
                padding: 1rem;
            }
            .setup-card {
                padding: 2rem;
            }
            .setup-title {
                font-size: 2rem;
            }
        }
        """
    ),
    ui.div(
        ui.div(
            ui.h1("Setup Required", class_="setup-title"),
            ui.h2("Claude Agent SDK Authentication", class_="setup-section-title"),
            ui.div(
                ui.HTML(
                    "This app requires an API key to use the Claude Agent SDK. "
                    "Note: The SDK does not use OAuth credentials from the Claude Code CLI."
                ),
                class_="setup-description",
            ),
            ui.h3("Option 1: Anthropic API Key", class_="setup-section-title"),
            ui.div(
                ui.HTML(
                    'Set the <code>ANTHROPIC_API_KEY</code> environment variable. '
                    'Get your key from the <a href="https://console.anthropic.com/" class="setup-link">Anthropic Console</a>.'
                ),
                class_="setup-description",
            ),
            ui.pre(
                'ANTHROPIC_API_KEY = "sk-ant-..."',
                class_="setup-code-block",
            ),
            ui.h3("Option 2: AWS Bedrock", class_="setup-section-title"),
            ui.div(
                "Set the following environment variables to use Claude via AWS Bedrock:",
                class_="setup-description",
            ),
            ui.pre(
                """CLAUDE_CODE_USE_BEDROCK = "1"
AWS_REGION = "us-east-1"
# AWS credentials are typically injected via IAM role on Connect""",
                class_="setup-code-block",
            ),
            class_="setup-card",
        ),
        class_="setup-container",
    ),
    fillable_mobile=True,
    fillable=True,
)

# Main chat UI
app_ui = ui.page_fillable(
    ui.div(
        ui.h1("Claude Chat", style="color: white; margin-bottom: 0.5rem;"),
        ui.p(
            "Ask me anything! Powered by the Claude Agent SDK.",
            style="color: rgba(255,255,255,0.8); margin-bottom: 1rem;",
        ),
        ui.chat_ui("chat", placeholder="What would you like to know?", height="100%"),
        style="height: 100%; display: flex; flex-direction: column; padding: 1rem;",
    ),
    ui.tags.style(
        """
        body {
            background: linear-gradient(135deg, #d97706 0%, #ea580c 100%);
        }

        /* Make chat container use full width */
        shiny-chat-container {
            max-width: 100% !important;
            width: 100% !important;
        }

        shiny-chat-messages {
            max-width: 100% !important;
            width: 100% !important;
        }

        /* Make individual messages wider */
        shiny-chat-message {
            max-width: 100% !important;
            width: 100% !important;
        }

        /* Style the message content */
        shiny-chat-message > * {
            background: white;
            border-radius: 8px;
            padding: 8px;
        }

        /* User messages - allow full width */
        shiny-user-message,
        shiny-chat-message[data-role="user"] {
            max-width: 90% !important;
        }

        /* Assistant messages - use full width */
        shiny-chat-message[data-role="assistant"] {
            max-width: 100% !important;
        }

        /* Markdown content should use available space */
        shiny-markdown-stream {
            max-width: 100% !important;
            width: 100% !important;
        }

        /* Ensure code blocks don't cause overflow */
        shiny-chat-messages pre {
            max-width: 100%;
            overflow-x: auto;
        }

        shiny-chat-messages code {
            word-break: break-word;
        }
        """
    ),
    fillable=True,
    fillable_mobile=True,
)

screen_ui = ui.page_output("screen")


def server(input: Inputs, output: Outputs, app_session: AppSession):
    chat_ui = ui.Chat("chat")

    # Determine which model to use
    if CLAUDE_MODEL:
        model = CLAUDE_MODEL
    elif HAS_BEDROCK:
        model = DEFAULT_BEDROCK_MODEL
    else:
        model = DEFAULT_ANTHROPIC_MODEL

    print(f"Using model: {model}")

    @render.ui
    def screen():
        if not HAS_CREDENTIALS:
            return setup_ui
        return app_ui

    @chat_ui.on_user_submit
    async def handle_user_message(user_input: str):
        if not HAS_CREDENTIALS:
            return

        try:
            # Get conversation history from the chat UI for context
            messages = chat_ui.messages()

            # Build conversation context from history
            # The SDK's ClaudeSDKClient doesn't persist state between requests,
            # so we need to include history in the prompt
            conversation_parts = []
            if messages:
                conversation_parts.append("Previous conversation:")
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    if role == "user":
                        conversation_parts.append(f"User: {content}")
                    elif role == "assistant":
                        conversation_parts.append(f"Assistant: {content}")
                conversation_parts.append("\nContinue the conversation naturally.")

            # Build the full prompt with context
            if conversation_parts:
                full_prompt = "\n".join(conversation_parts) + f"\n\nUser: {user_input}"
            else:
                full_prompt = user_input

            print(f"Sending prompt with {len(messages) if messages else 0} previous messages")

            # Configure SDK options with all settings
            options = ClaudeAgentOptions(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                max_turns=MAX_TURNS,
                max_budget_usd=MAX_BUDGET_USD,
                include_partial_messages=INCLUDE_PARTIAL_MESSAGES,
                permission_mode=PERMISSION_MODE,
                tools=TOOLS_CONFIG,
                disallowed_tools=DISALLOWED_TOOLS,
            )

            # Stream response using ClaudeSDKClient for better control
            async def generate_response():
                text_yielded = False
                total_cost = None
                stats = {"text_blocks": 0, "tool_uses": 0, "thinking_blocks": 0}

                async with ClaudeSDKClient(options) as client:
                    await client.query(full_prompt)

                    # Use receive_response() which terminates after ResultMessage
                    # (receive_messages() continues indefinitely)
                    async for message in client.receive_response():
                        # Handle partial streaming events (real-time text)
                        if isinstance(message, StreamEvent):
                            event = message.event
                            # Extract text delta from streaming event
                            if event.get("type") == "content_block_delta":
                                delta = event.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        text_yielded = True
                                        yield text

                        # Handle complete assistant messages
                        elif isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, TextBlock):
                                    stats["text_blocks"] += 1
                                    # Only yield if not using partial messages
                                    # (to avoid duplication)
                                    if not INCLUDE_PARTIAL_MESSAGES:
                                        text_yielded = True
                                        yield block.text

                                elif isinstance(block, ThinkingBlock):
                                    stats["thinking_blocks"] += 1
                                    if SHOW_THINKING:
                                        yield f"\n\n<details><summary>Thinking...</summary>\n\n{block.thinking}\n\n</details>\n\n"

                                elif isinstance(block, ToolUseBlock):
                                    stats["tool_uses"] += 1
                                    if stats["tool_uses"] == 1:
                                        yield "\n\n*Working...*\n\n"

                        # Handle result message (includes cost info)
                        elif isinstance(message, ResultMessage):
                            if message.is_error:
                                print(f"Agent error: {message.result}")
                                yield f"\n\n*Error: {message.result}*"

                            # Capture cost information
                            if message.total_cost_usd is not None:
                                total_cost = message.total_cost_usd

                # Log completion stats
                print(f"=== Completed: {stats['text_blocks']} text blocks, "
                      f"{stats['tool_uses']} tool uses, "
                      f"{stats['thinking_blocks']} thinking blocks ===")

                if total_cost is not None:
                    print(f"Request cost: ${total_cost:.6f}")
                    if SHOW_COST:
                        yield f"\n\n---\n*Cost: ${total_cost:.6f}*"

                if not text_yielded:
                    yield "No response received from Claude."

            await chat_ui.append_message_stream(generate_response())

        except Exception as e:
            import traceback
            # Log full error for debugging
            print(f"Error: {traceback.format_exc()}")
            # Show sanitized error to user
            error_msg = str(e)
            # Provide more helpful error messages for common issues
            if "rate_limit" in error_msg.lower():
                await chat_ui.append_message(
                    "Rate limit reached. Please wait a moment and try again."
                )
            elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                await chat_ui.append_message(
                    "Authentication error. Please check your API credentials."
                )
            elif "billing" in error_msg.lower() or "credit" in error_msg.lower():
                await chat_ui.append_message(
                    "Billing error. Please check your account has available credits."
                )
            else:
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                await chat_ui.append_message(f"Sorry, an error occurred: {error_msg}")


app = App(screen_ui, server)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
