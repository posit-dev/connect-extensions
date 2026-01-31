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

import uvicorn
from dotenv import load_dotenv
from shiny import App, Inputs, Outputs, reactive, render, ui
from shiny.session._session import AppSession

load_dotenv()

# Model configuration - can be overridden via environment variable
# For Bedrock, use the regional prefix (e.g., us.anthropic.claude-sonnet-4-5-20250929-v1:0)
DEFAULT_BEDROCK_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL")


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

# Log which auth method will be used
if HAS_ANTHROPIC_KEY:
    print("Using ANTHROPIC_API_KEY for authentication")
elif HAS_BEDROCK:
    print("Using AWS Bedrock for authentication")
else:
    print("No authentication method available - set ANTHROPIC_API_KEY or configure Bedrock")


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

        shiny-chat-messages > * {
            background: white;
            border-radius: 8px;
            padding: 8px;
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
            from claude_agent_sdk import ClaudeAgentOptions, query

            # Get conversation history from the chat UI
            messages = chat_ui.messages()

            # Build conversation context from history
            # messages is a tuple of dicts with 'role' and 'content'
            conversation_context = ""
            if messages:
                conversation_context = "Previous conversation:\n"
                for msg in messages:
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")
                    if role == "user":
                        conversation_context += f"User: {content}\n"
                    elif role == "assistant":
                        conversation_context += f"Assistant: {content}\n"
                conversation_context += "\nNow respond to the user's latest message."

            # Build the full prompt with context
            if conversation_context:
                full_prompt = f"{conversation_context}\n\nUser: {user_input}"
            else:
                full_prompt = user_input

            print(f"Sending prompt with {len(messages) if messages else 0} previous messages")

            options = ClaudeAgentOptions(
                allowed_tools=[],
                model=model,
                system_prompt=(
                    "You are a helpful assistant. Answer questions clearly and concisely. "
                    "You are running as part of a Posit Connect extension. "
                    "When given conversation history, continue the conversation naturally."
                ),
            )

            # Stream response - the SDK yields messages as they arrive
            async def generate_response():
                from claude_agent_sdk import AssistantMessage, ResultMessage
                from claude_agent_sdk.types import TextBlock, ToolUseBlock

                text_block_count = 0
                tool_use_count = 0

                async for message in query(prompt=full_prompt, options=options):
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                text_block_count += 1
                                yield block.text

                            elif isinstance(block, ToolUseBlock):
                                tool_use_count += 1
                                if tool_use_count == 1:
                                    yield "\n\n*Working...*\n\n"

                    elif isinstance(message, ResultMessage):
                        if message.is_error:
                            print(f"Agent error: {message.result}")

                print(f"=== Completed: {tool_use_count} tool uses, {text_block_count} text blocks ===")

                if text_block_count == 0:
                    yield "No response received from Claude."

            await chat_ui.append_message_stream(generate_response())

        except Exception as e:
            import traceback
            # Log full error for debugging
            print(f"Error: {traceback.format_exc()}")
            # Show sanitized error to user
            error_msg = str(e)
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            await chat_ui.append_message(f"Sorry, an error occurred: {error_msg}")


app = App(screen_ui, server)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
