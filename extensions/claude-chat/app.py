"""
Claude Chat - Basic chat interface using the Claude Agent SDK.

This extension provides a simple chat interface for asking general questions
using the Claude Agent SDK. It supports authentication via:
- Posit Connect AWS Integration (automatic on Connect with configured integration)
- ANTHROPIC_API_KEY environment variable
- AWS Bedrock credentials (CLAUDE_CODE_USE_BEDROCK=1)

Note: The SDK does NOT use OAuth credentials from the Claude Code CLI.
You must provide an API key or configure an AWS integration.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import uvicorn
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, reactive, render, ui
from shiny.session._session import AppSession

load_dotenv()

# =============================================================================
# Logging Configuration
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# Posit Connect AWS Integration
# =============================================================================
# When running on Posit Connect with an AWS integration configured,
# automatically obtain credentials via the integration. This must happen
# before importing the Claude SDK so environment variables are set.
CONNECT_INTEGRATION_USED = False


def setup_connect_aws_integration() -> bool:
    """
    Set up AWS credentials from Posit Connect integration if available.

    Returns True if credentials were obtained from Connect integration.
    """
    global CONNECT_INTEGRATION_USED

    # Only attempt on Connect
    if os.getenv("POSIT_PRODUCT") != "CONNECT":
        return False

    # Skip if explicit credentials are already set
    if os.getenv("ANTHROPIC_API_KEY"):
        logger.info("ANTHROPIC_API_KEY set, skipping Connect AWS integration")
        return False

    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        logger.info("AWS credentials already set, skipping Connect AWS integration")
        return False

    try:
        from posit.connect import Client
        from posit.connect.external import aws

        client = Client()
        credentials = aws.get_content_credentials(client)

        # Set environment variables for the Claude SDK to use
        os.environ["AWS_ACCESS_KEY_ID"] = credentials["aws_access_key_id"]
        os.environ["AWS_SECRET_ACCESS_KEY"] = credentials["aws_secret_access_key"]
        if credentials.get("aws_session_token"):
            os.environ["AWS_SESSION_TOKEN"] = credentials["aws_session_token"]

        # Enable Bedrock mode automatically
        os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"

        CONNECT_INTEGRATION_USED = True
        logger.info("AWS credentials obtained from Posit Connect integration")
        return True

    except ImportError:
        logger.debug("posit-sdk not available, skipping Connect AWS integration")
        return False
    except Exception as e:
        # Integration may not be configured - this is not an error
        logger.debug("Connect AWS integration not available: %s", e)
        return False


# Attempt to set up Connect integration before SDK import
setup_connect_aws_integration()

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
        logger.warning("Invalid integer for %s: %s", key, val)
        return default


def _parse_float_env(key: str, default: float | None = None) -> float | None:
    """Parse a float environment variable, returning None if not set or invalid."""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        logger.warning("Invalid float for %s: %s", key, val)
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


# Permission mode for tool usage
class PermissionMode(str, Enum):
    """Permission modes for Claude tool usage."""

    DEFAULT = "default"  # Prompts for dangerous tools (not supported in this UI)
    ACCEPT_EDITS = "acceptEdits"  # Auto-accept file edits
    BYPASS = "bypassPermissions"  # Allow all tools without prompting


# Default to ACCEPT_EDITS since we can't surface permission prompts in the chat UI
PERMISSION_MODE = os.getenv("CLAUDE_PERMISSION_MODE", PermissionMode.ACCEPT_EDITS.value)


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
HAS_CREDENTIALS = HAS_ANTHROPIC_KEY or HAS_BEDROCK

# Log startup status
if HAS_ANTHROPIC_KEY:
    logger.info("Using ANTHROPIC_API_KEY for authentication")
elif HAS_BEDROCK:
    if CONNECT_INTEGRATION_USED:
        logger.info("Using AWS Bedrock via Posit Connect integration")
    else:
        logger.info("Using AWS Bedrock for authentication")
else:
    logger.warning(
        "No authentication method available - set ANTHROPIC_API_KEY or configure Bedrock"
    )

# Log configuration
logger.info(
    "Configuration: max_turns=%s, max_budget_usd=%s, partial_messages=%s, "
    "show_thinking=%s, show_cost=%s, permission_mode=%s, tools=%s, disallowed_tools=%s",
    MAX_TURNS,
    MAX_BUDGET_USD,
    INCLUDE_PARTIAL_MESSAGES,
    SHOW_THINKING,
    SHOW_COST,
    PERMISSION_MODE,
    TOOLS_CONFIG,
    DISALLOWED_TOOLS,
)

# =============================================================================
# Per-Session Client Management with Automatic Cleanup
# =============================================================================
# Store persistent ClaudeSDKClient instances per session for conversation continuity.
# The SDK maintains conversation state across query() calls, so we reuse the client.
if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeSDKClient

_session_clients: dict[str, "ClaudeSDKClient"] = {}
_session_costs: dict[str, float] = {}
_session_last_active: dict[str, datetime] = {}
_session_conversations: dict[str, list[dict]] = {}  # Store conversation history
_clients_lock = asyncio.Lock()
_cleanup_task: asyncio.Task[None] | None = None
_cleanup_started = False  # Flag to prevent race condition on startup

# Configuration for session cleanup
SESSION_TIMEOUT_MINUTES = _parse_int_env("CLAUDE_SESSION_TIMEOUT_MINUTES", default=60)
CLEANUP_INTERVAL_MINUTES = _parse_int_env("CLAUDE_CLEANUP_INTERVAL_MINUTES", default=15)


async def cleanup_stale_sessions() -> None:
    """
    Background task to clean up sessions that have been inactive for too long.
    Runs periodically to prevent memory leaks from abandoned sessions.
    """
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_MINUTES * 60)

            now = datetime.now()
            timeout_threshold = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            stale_sessions = []

            async with _clients_lock:
                # Find stale sessions
                for session_id, last_active in _session_last_active.items():
                    if now - last_active > timeout_threshold:
                        stale_sessions.append(session_id)

                # Clean up stale sessions
                for session_id in stale_sessions:
                    try:
                        inactive_minutes = (
                            now - _session_last_active[session_id]
                        ).total_seconds() / 60
                        logger.info(
                            "Cleaning up stale session %s (inactive for %.1f minutes)",
                            session_id,
                            inactive_minutes,
                        )

                        # Disconnect client
                        if session_id in _session_clients:
                            await _session_clients[session_id].disconnect()
                            del _session_clients[session_id]

                        # Clean up costs
                        if session_id in _session_costs:
                            total_cost = _session_costs.pop(session_id)
                            logger.info(
                                "Session %s total cost: $%.6f", session_id, total_cost
                            )

                        # Clean up last active timestamp
                        if session_id in _session_last_active:
                            del _session_last_active[session_id]

                        # Clean up conversation history
                        if session_id in _session_conversations:
                            del _session_conversations[session_id]

                    except Exception as e:
                        logger.exception(
                            "Error cleaning up stale session %s", session_id
                        )

                if stale_sessions:
                    logger.info(
                        "Cleaned up %d stale session(s). Active sessions: %d",
                        len(stale_sessions),
                        len(_session_clients),
                    )

        except asyncio.CancelledError:
            logger.info("Session cleanup task cancelled")
            break
        except Exception as e:
            logger.exception("Error in cleanup task")
            # Continue running despite errors


def start_cleanup_task() -> None:
    """Start the background cleanup task if not already running.

    Uses a flag to prevent race conditions when multiple sessions
    connect simultaneously.
    """
    global _cleanup_task, _cleanup_started
    if _cleanup_started:
        return
    _cleanup_started = True
    _cleanup_task = asyncio.create_task(cleanup_stale_sessions())
    logger.info(
        "Started session cleanup task (timeout: %dmin, interval: %dmin)",
        SESSION_TIMEOUT_MINUTES,
        CLEANUP_INTERVAL_MINUTES,
    )


async def stop_cleanup_task() -> None:
    """Stop the background cleanup task."""
    global _cleanup_task, _cleanup_started
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
    _cleanup_task = None
    _cleanup_started = False
    logger.info("Stopped session cleanup task")


def update_session_activity(session_id: str) -> None:
    """Update the last active timestamp for a session.

    Note: This is intentionally not locked - dict assignment is atomic
    in Python (GIL), and this is always called either within a locked
    section (get_or_create_client) or for a simple timestamp update
    where eventual consistency is acceptable.
    """
    _session_last_active[session_id] = datetime.now()


async def get_or_create_client(
    session_id: str, model: str, system_prompt: str
) -> "ClaudeSDKClient":
    """
    Get existing client or create a new one for the session.
    Updates last active timestamp.
    """
    async with _clients_lock:
        update_session_activity(session_id)

        if session_id not in _session_clients:
            logger.info("Creating new ClaudeSDKClient for session %s", session_id)
            options = ClaudeAgentOptions(
                model=model,
                system_prompt=system_prompt,
                max_turns=MAX_TURNS,
                max_budget_usd=MAX_BUDGET_USD,
                include_partial_messages=INCLUDE_PARTIAL_MESSAGES,
                permission_mode=PERMISSION_MODE,
                tools=TOOLS_CONFIG,
                disallowed_tools=DISALLOWED_TOOLS,
            )
            client = ClaudeSDKClient(options)
            await client.connect()
            _session_clients[session_id] = client
            _session_costs[session_id] = 0.0
            _session_conversations[session_id] = []

        return _session_clients[session_id]


async def cleanup_session(session_id: str) -> None:
    """
    Clean up a specific session's client and data.
    Called when a session ends or needs to be reset.
    """
    async with _clients_lock:
        if session_id in _session_clients:
            try:
                logger.info("Cleaning up client for session %s", session_id)
                await _session_clients[session_id].disconnect()
            except Exception:
                logger.exception("Error disconnecting client during cleanup")
            finally:
                del _session_clients[session_id]

        if session_id in _session_costs:
            total_cost = _session_costs.pop(session_id, 0.0)
            logger.info("Session %s ended. Total cost: $%.6f", session_id, total_cost)

        if session_id in _session_last_active:
            del _session_last_active[session_id]

        if session_id in _session_conversations:
            del _session_conversations[session_id]


def get_session_stats() -> dict:
    """Get current session statistics for monitoring/debugging."""
    return {
        "active_sessions": len(_session_clients),
        "total_tracked_costs": sum(_session_costs.values()),
        "sessions_with_activity": len(_session_last_active),
    }


async def add_conversation_message(
    session_id: str, role: str, content: str, timestamp: str | None = None
) -> None:
    """
    Add a message to the conversation history in a thread-safe manner.

    Args:
        session_id: The session ID
        role: Message role ('user' or 'assistant')
        content: The message content
        timestamp: Optional timestamp string; uses current time if not provided
    """
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with _clients_lock:
        if session_id not in _session_conversations:
            _session_conversations[session_id] = []
        _session_conversations[session_id].append(
            {
                "role": role,
                "content": content,
                "timestamp": timestamp,
            }
        )


async def get_conversation_snapshot(session_id: str) -> tuple[list[dict], float]:
    """
    Get a thread-safe snapshot of conversation history and cost.

    Args:
        session_id: The session ID

    Returns:
        Tuple of (conversation list copy, total cost)
    """
    async with _clients_lock:
        conversation = list(_session_conversations.get(session_id, []))
        cost = _session_costs.get(session_id, 0.0)
    return conversation, cost


def export_conversation_to_markdown(
    conversation: list[dict], model: str, total_cost: float = 0.0
) -> str:
    """
    Export a conversation history to markdown format.

    Args:
        conversation: List of message dictionaries with 'role', 'content', 'timestamp'
        model: The model name used for the conversation
        total_cost: Total cost of the conversation in USD

    Returns:
        Markdown-formatted conversation history
    """
    if not conversation:
        return "# Claude Chat Export\n\n*No messages in this conversation yet.*"

    # Build markdown document
    lines = [
        "# Claude Chat Export",
        "",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Model**: {model}",
        f"**Messages**: {len(conversation)}",
        "",
    ]

    # Add cost information if available
    if total_cost > 0:
        lines.append(f"**Total Cost**: ${total_cost:.6f}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Add each message
    for i, msg in enumerate(conversation, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")

        # Format role as header
        if role == "user":
            lines.append(f"## 👤 User")
        elif role == "assistant":
            lines.append(f"## 🤖 Assistant")
        else:
            lines.append(f"## {role.title()}")

        if timestamp:
            lines.append(f"*{timestamp}*")
            lines.append("")

        lines.append(content)
        lines.append("")

        # Add separator between messages (but not after the last one)
        if i < len(conversation):
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


# =============================================================================
# Static Assets
# =============================================================================
STYLESHEET = ui.tags.link(rel="stylesheet", href="style.css")

# =============================================================================
# UI Definitions
# =============================================================================

# Setup UI shown when credentials are missing
setup_ui = ui.page_fillable(
    STYLESHEET,
    ui.div(
        ui.div(
            ui.h1("Setup Required", class_="setup-title"),
            ui.h2("Claude Agent SDK Authentication", class_="setup-section-title"),
            ui.div(
                ui.HTML(
                    "This app requires credentials to use the Claude Agent SDK. "
                    "Choose one of the options below."
                ),
                class_="setup-description",
            ),
            ui.h3("Option 1: Posit Connect AWS Integration (Recommended)", class_="setup-section-title"),
            ui.div(
                ui.HTML(
                    "Associate an AWS Integration with this content that has a role granting Bedrock access. "
                    "Credentials will be obtained automatically at runtime. "
                    'See <a href="https://docs.posit.co/connect/admin/integrations/aws/" class="setup-link">Connect AWS Integration docs</a>.'
                ),
                class_="setup-description",
            ),
            ui.h3("Option 2: Anthropic API Key", class_="setup-section-title"),
            ui.div(
                ui.HTML(
                    "Set the <code>ANTHROPIC_API_KEY</code> environment variable. "
                    'Get your key from the <a href="https://console.anthropic.com/" class="setup-link">Anthropic Console</a>.'
                ),
                class_="setup-description",
            ),
            ui.pre(
                'ANTHROPIC_API_KEY = "sk-ant-..."',
                class_="setup-code-block",
            ),
            ui.h3("Option 3: AWS Bedrock (Manual)", class_="setup-section-title"),
            ui.div(
                "Set environment variables to use Claude via AWS Bedrock:",
                class_="setup-description",
            ),
            ui.pre(
                """CLAUDE_CODE_USE_BEDROCK = "1"
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "..."
AWS_SECRET_ACCESS_KEY = "...\"""",
                class_="setup-code-block",
            ),
            class_="setup-card",
        ),
        class_="setup-container",
    ),
    fillable_mobile=True,
    fillable=True,
)

def get_auth_status() -> str:
    """Get a human-readable authentication status string."""
    if HAS_ANTHROPIC_KEY:
        return "Anthropic API Key"
    elif HAS_BEDROCK:
        if CONNECT_INTEGRATION_USED:
            return "AWS Bedrock (via Posit Connect Integration)"
        else:
            return "AWS Bedrock"
    else:
        return "Not configured"


def get_config_info() -> list[tuple[str, str, str]]:
    """
    Get configuration information for display.

    Returns list of (name, value, description) tuples.
    Sensitive values are masked.
    """
    # Determine effective model
    if CLAUDE_MODEL:
        effective_model = CLAUDE_MODEL
    elif HAS_BEDROCK:
        effective_model = DEFAULT_BEDROCK_MODEL
    else:
        effective_model = DEFAULT_ANTHROPIC_MODEL

    config = [
        # Authentication
        ("Authentication", get_auth_status(), "How Claude API credentials are provided"),
        ("Model", effective_model, "Claude model being used"),
        # Limits
        (
            "CLAUDE_MAX_TURNS",
            str(MAX_TURNS) if MAX_TURNS else "Unlimited",
            "Maximum conversation turns per request",
        ),
        (
            "CLAUDE_MAX_BUDGET_USD",
            f"${MAX_BUDGET_USD:.2f}" if MAX_BUDGET_USD else "Unlimited",
            "Maximum cost per request",
        ),
        # Features
        (
            "CLAUDE_PARTIAL_MESSAGES",
            str(INCLUDE_PARTIAL_MESSAGES),
            "Real-time text streaming enabled",
        ),
        (
            "CLAUDE_SHOW_THINKING",
            str(SHOW_THINKING),
            "Display extended thinking blocks",
        ),
        ("CLAUDE_SHOW_COST", str(SHOW_COST), "Show cost after responses"),
        # Tools
        ("CLAUDE_PERMISSION_MODE", PERMISSION_MODE, "Tool permission mode"),
        (
            "CLAUDE_TOOLS",
            "All tools" if TOOLS_CONFIG == {"type": "preset", "preset": "claude_code"} else str(TOOLS_CONFIG or "Default"),
            "Enabled tools",
        ),
        (
            "CLAUDE_DISALLOWED_TOOLS",
            ", ".join(DISALLOWED_TOOLS) if DISALLOWED_TOOLS else "None",
            "Blocked tools",
        ),
        # Session management
        (
            "CLAUDE_SESSION_TIMEOUT_MINUTES",
            str(SESSION_TIMEOUT_MINUTES),
            "Session inactivity timeout",
        ),
        (
            "CLAUDE_CLEANUP_INTERVAL_MINUTES",
            str(CLEANUP_INTERVAL_MINUTES),
            "Cleanup check interval",
        ),
    ]
    return config

# Main chat UI
app_ui = ui.page_fillable(
    STYLESHEET,
    ui.div(
        ui.div(
            ui.div(
                ui.h1("Claude Chat", style="color: white; margin: 0;"),
                ui.input_action_button(
                    "show_config",
                    "Settings",
                    class_="header-button",
                ),
                style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;",
            ),
            ui.p(
                "Ask me anything! Powered by the Claude Agent SDK.",
                style="color: rgba(255,255,255,0.8); margin-bottom: 0.5rem;",
            ),
            # Export button rendered dynamically (only shown when conversation exists)
            ui.output_ui("export_button_ui"),
        ),
        ui.chat_ui("chat", placeholder="What would you like to know?", height="100%"),
        style="height: 100%; display: flex; flex-direction: column; padding: 1rem;",
    ),
    fillable=True,
    fillable_mobile=True,
)

screen_ui = ui.page_output("screen")


def server(input: Inputs, output: Outputs, app_session: AppSession):
    chat_ui = ui.Chat("chat")

    # Start cleanup task when first server instance is created
    start_cleanup_task()

    # Determine which model to use
    if CLAUDE_MODEL:
        model = CLAUDE_MODEL
    elif HAS_BEDROCK:
        model = DEFAULT_BEDROCK_MODEL
    else:
        model = DEFAULT_ANTHROPIC_MODEL

    logger.info("Using model: %s", model)

    # Track conversation state for UI updates
    has_messages = reactive.value(False)

    @render.ui
    def screen():
        if not HAS_CREDENTIALS:
            return setup_ui
        return app_ui

    @render.ui
    def export_button_ui():
        """Conditionally render export button only when conversation has messages."""
        if has_messages():
            return ui.download_button(
                "export_chat",
                "Export Conversation",
                class_="header-button",
                style="margin-right: 0.5rem;",
            )
        return None

    @reactive.effect
    @reactive.event(input.show_config)
    def show_config_modal():
        """Show the configuration modal when the settings button is clicked."""
        config_info = get_config_info()

        # Build table rows
        table_rows = [
            ui.tags.tr(
                ui.tags.td(name),
                ui.tags.td(value),
                ui.tags.td(desc),
            )
            for name, value, desc in config_info
        ]

        modal = ui.modal(
            ui.tags.p(
                "Current configuration for this Claude Chat instance. "
                "These settings are controlled via environment variables.",
                class_="config-description",
            ),
            ui.tags.table(
                ui.tags.thead(
                    ui.tags.tr(
                        ui.tags.th("Setting"),
                        ui.tags.th("Value"),
                        ui.tags.th("Description"),
                    ),
                ),
                ui.tags.tbody(*table_rows),
                class_="config-table",
            ),
            ui.tags.p(
                ui.tags.a(
                    "View documentation",
                    href="https://github.com/posit-dev/connect-extensions",
                    target="_blank",
                ),
                class_="config-footer",
            ),
            title="Configuration",
            easy_close=True,
            size="l",
        )
        ui.modal_show(modal)

    @render.download(
        filename=lambda: f"claude_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    async def export_chat():
        """Export conversation history to markdown."""
        session_id = app_session.id
        conversation, total_cost = await get_conversation_snapshot(session_id)
        markdown_content = export_conversation_to_markdown(
            conversation, model, total_cost
        )
        yield markdown_content

    @chat_ui.on_user_submit
    async def handle_user_message(user_input: str):
        if not HAS_CREDENTIALS:
            return

        session_id = app_session.id

        # Track user message in conversation history (thread-safe)
        await add_conversation_message(session_id, "user", user_input)

        # Show export button now that we have messages
        has_messages.set(True)

        try:
            # Get or create persistent client for this session
            # This also updates the last active timestamp
            client = await get_or_create_client(session_id, model, SYSTEM_PROMPT)

            # Send just the new user message - the SDK maintains conversation state
            logger.debug(
                "Sending message to existing client for session %s", session_id
            )
            await client.query(user_input)

            # Stream response using the persistent client
            async def generate_response():
                text_yielded = False
                total_cost = None
                stats = {"text_blocks": 0, "tool_uses": 0, "thinking_blocks": 0}
                assistant_response = (
                    []
                )  # Collect response parts for conversation history

                try:
                    # Use receive_response() which terminates after ResultMessage
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
                                        assistant_response.append(text)
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
                                        assistant_response.append(block.text)
                                        yield block.text

                                elif isinstance(block, ThinkingBlock):
                                    stats["thinking_blocks"] += 1
                                    if SHOW_THINKING:
                                        thinking_text = f"\n\n<details><summary>Thinking...</summary>\n\n{block.thinking}\n\n</details>\n\n"
                                        assistant_response.append(thinking_text)
                                        yield thinking_text

                                elif isinstance(block, ToolUseBlock):
                                    stats["tool_uses"] += 1
                                    if stats["tool_uses"] == 1:
                                        working_text = "\n\n*Working...*\n\n"
                                        assistant_response.append(working_text)
                                        yield working_text

                        # Handle result message (includes cost info)
                        elif isinstance(message, ResultMessage):
                            if message.is_error:
                                logger.error("Agent error: %s", message.result)
                                yield f"\n\n*Error: {message.result}*"

                            # Capture cost information
                            if message.total_cost_usd is not None:
                                total_cost = message.total_cost_usd

                    if not text_yielded:
                        no_response_text = "No response received from Claude."
                        assistant_response.append(no_response_text)
                        yield no_response_text

                finally:
                    # Always update session activity and log stats
                    update_session_activity(session_id)

                    logger.info(
                        "Completed: %d text blocks, %d tool uses, %d thinking blocks",
                        stats["text_blocks"],
                        stats["tool_uses"],
                        stats["thinking_blocks"],
                    )

                    if total_cost is not None:
                        logger.info("Request cost: $%.6f", total_cost)
                        # Track cumulative cost for session (use lock for thread safety)
                        async with _clients_lock:
                            _session_costs[session_id] = (
                                _session_costs.get(session_id, 0.0) + total_cost
                            )
                            session_total = _session_costs[session_id]
                        if SHOW_COST:
                            cost_text = f"\n\n---\n*Cost: ${total_cost:.6f} | Session: ${session_total:.6f}*"
                            assistant_response.append(cost_text)
                            yield cost_text

                    # Save assistant response to conversation history (thread-safe)
                    if assistant_response:
                        await add_conversation_message(
                            session_id, "assistant", "".join(assistant_response)
                        )

            await chat_ui.append_message_stream(generate_response())

        except Exception as e:
            # Log full error for debugging
            logger.exception("Error handling user message")

            # On error, reset the client for this session
            await cleanup_session(session_id)

            # Show sanitized error to user
            error_msg = str(e)
            user_error_msg = ""

            # Provide more helpful error messages for common issues
            if "rate_limit" in error_msg.lower():
                user_error_msg = (
                    "Rate limit reached. Please wait a moment and try again."
                )
            elif (
                "authentication" in error_msg.lower() or "api_key" in error_msg.lower()
            ):
                user_error_msg = (
                    "Authentication error. Please check your API credentials."
                )
            elif "billing" in error_msg.lower() or "credit" in error_msg.lower():
                user_error_msg = (
                    "Billing error. Please check your account has available credits."
                )
            else:
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                user_error_msg = f"Sorry, an error occurred: {error_msg}"

            # Track error in conversation history (thread-safe)
            await add_conversation_message(
                session_id, "assistant", f"*Error: {user_error_msg}*"
            )

            await chat_ui.append_message(user_error_msg)

    # Clean up client when session ends
    @app_session.on_ended
    async def cleanup_session_handler():
        """Clean up Claude client when user session ends."""
        try:
            session_id = app_session.id
            await cleanup_session(session_id)
        except Exception:
            logger.exception("Error in session cleanup handler")


app = App(screen_ui, server, static_assets=Path(__file__).parent / "www")


# =============================================================================
# Graceful Shutdown
# =============================================================================
async def shutdown_cleanup() -> None:
    """Clean up all sessions and stop background tasks on shutdown."""
    logger.info("Shutting down - cleaning up %d active sessions", len(_session_clients))
    await stop_cleanup_task()

    # Disconnect all remaining clients
    async with _clients_lock:
        for session_id in list(_session_clients.keys()):
            try:
                await _session_clients[session_id].disconnect()
            except Exception:
                logger.exception(
                    "Error disconnecting session %s during shutdown", session_id
                )
        _session_clients.clear()
        _session_costs.clear()
        _session_last_active.clear()
        _session_conversations.clear()

    logger.info("Shutdown complete")


@app.on_shutdown
def on_app_shutdown():
    """Handle app shutdown event."""
    asyncio.ensure_future(shutdown_cleanup())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
