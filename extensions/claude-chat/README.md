# Claude Chat

A basic chat interface powered by the Claude Agent SDK. This extension serves as a building block for exploring Claude's capabilities on Posit Connect.

## Overview

This extension provides a simple chat interface for asking general questions using the Claude Agent SDK. It demonstrates how to authenticate and interact with Claude models on Connect, supporting both direct Anthropic API access and AWS Bedrock.

## Features

- **Simple Chat Interface**: Clean Shiny-based UI for conversational interactions
- **Claude Agent SDK**: Uses Anthropic's official SDK for Claude interactions
- **Flexible Authentication**: Supports Anthropic API keys or AWS Bedrock
- **Multi-Turn Conversations**: Persistent sessions maintain conversation context across messages
- **Conversation Export**: Download conversation history as formatted markdown
- **Automatic Session Cleanup**: Stale sessions are cleaned up to prevent memory leaks
- **Cost Tracking**: Optional per-request and cumulative session cost display
- **Tool Support**: Configurable access to Claude Code tools (Read, Write, Edit, Bash, etc.)

## Prerequisites

### Authentication Methods

The Claude Agent SDK requires an API key. It does **not** use OAuth credentials from the Claude Code CLI.

#### Option 1: Anthropic API Key (Recommended)
```bash
ANTHROPIC_API_KEY="sk-ant-..."
```
Get your API key from the [Anthropic Console](https://console.anthropic.com/).

#### Option 2: AWS Bedrock
```bash
CLAUDE_CODE_USE_BEDROCK="1"
AWS_REGION="us-east-2"
```
If running on an EC2 instance with an IAM role that has Bedrock access, AWS credentials are injected automatically. Otherwise, configure:
```bash
AWS_ACCESS_KEY_ID="..."
AWS_SECRET_ACCESS_KEY="..."
```

For local development with AWS SSO:
```bash
aws sso login --profile your-profile
AWS_PROFILE=your-profile CLAUDE_CODE_USE_BEDROCK=1 uv run python app.py
```

### Model Configuration

The default model is `us.anthropic.claude-sonnet-4-5-20250929-v1:0` for Bedrock. Override with:
```bash
CLAUDE_MODEL="us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

For Bedrock, the regional prefix (`us.`, `eu.`, etc.) is required.

### Optional Configuration

These environment variables allow you to customize behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_SYSTEM_PROMPT` | (see below) | Custom system prompt for Claude |
| `CLAUDE_MAX_TURNS` | None (unlimited) | Maximum conversation turns per request |
| `CLAUDE_MAX_BUDGET_USD` | None (unlimited) | Maximum cost in USD per request |
| `CLAUDE_PARTIAL_MESSAGES` | `true` | Enable real-time text streaming |
| `CLAUDE_SHOW_THINKING` | `false` | Display extended thinking blocks |
| `CLAUDE_SHOW_COST` | `false` | Show cost after each response |
| `CLAUDE_PERMISSION_MODE` | `acceptEdits` | Tool permission mode (see below) |
| `CLAUDE_TOOLS` | `all` | Tools to enable (see below) |
| `CLAUDE_DISALLOWED_TOOLS` | None | Comma-separated list of tools to block |
| `CLAUDE_SESSION_TIMEOUT_MINUTES` | `60` | Inactivity timeout before session cleanup |
| `CLAUDE_CLEANUP_INTERVAL_MINUTES` | `15` | How often to check for stale sessions |

**Permission modes:**
- `acceptEdits` - Auto-accept file edits (default, recommended for this UI)
- `bypassPermissions` - Allow all tools without prompting
- `default` - Prompt for dangerous tools (not supported in this UI)

**Tools configuration:**
- `all` or `claude_code` - Enable all Claude Code tools (Read, Write, Edit, Bash, etc.)
- Comma-separated list - Enable specific tools, e.g., `Read,Write,Edit,Bash`
- Unset - Use SDK defaults

**Default system prompt:**
```
You are a helpful assistant. Answer questions clearly and concisely.
You are running as part of a Posit Connect extension.
```

**Example configuration for cost control:**
```bash
CLAUDE_MAX_TURNS="10"
CLAUDE_MAX_BUDGET_USD="0.50"
CLAUDE_SHOW_COST="true"
```

### Connect Requirements

1. **Minimum Connect Version**: 2025.04.0 or later
2. **Minimum Python Version**: 3.10 or later

## Local Development

```bash
cd extensions/claude-chat

# Install dependencies with uv (recommended)
uv sync

# Run the app
uv run python app.py
```

To regenerate `requirements.txt` after changing `pyproject.toml`:
```bash
uv pip compile pyproject.toml -o requirements.txt
```

## Usage

### 1. Deploy the Extension
Deploy this extension to your Connect server with the required environment variables configured.

### 2. Start Chatting
Once deployed, open the application and start asking questions. Claude maintains conversation context across messages within your session.

### 3. Export Conversations
After sending at least one message, an "Export Conversation" button appears. Click it to download your conversation history as a formatted markdown file, including timestamps, message content, and cost information (if enabled).

## Architecture

The application uses:
- **Shiny for Python**: Chat UI components with reactive state management
- **Claude Agent SDK**: Uses `ClaudeSDKClient` for bidirectional, streaming conversations
- **Per-Session Client Management**: Each user session maintains its own `ClaudeSDKClient` instance for conversation continuity
- **Async Streaming**: Real-time text display via `StreamEvent` partial messages
- **Conversation History**: Messages are tracked per-session for export functionality
- **Cost Tracking**: Captures and optionally displays per-request and cumulative session costs
- **Automatic Cleanup**: Background task periodically removes inactive sessions to prevent memory leaks
- **Graceful Shutdown**: Properly disconnects all clients when the application stops

## Extending This Extension

This extension is designed as a starting point. You can extend it by:
- Customizing available tools via the `CLAUDE_TOOLS` environment variable
- Connecting MCP servers for external capabilities
- Adding database-backed conversation persistence (currently in-memory only)
- Implementing user-specific context based on Connect user identity
- Adding file upload capabilities for document analysis

See the [Claude Agent SDK documentation](https://platform.claude.com/docs/en/agent-sdk/overview) for more capabilities.

## Troubleshooting

### Setup Screen Appears
If you see the setup screen instead of the chat interface:
1. Verify environment variables are correctly set
2. For Bedrock, ensure `CLAUDE_CODE_USE_BEDROCK=1` is set
3. Check Connect logs for authentication errors

### Response Errors
- Verify your API key is valid and has available credits
- For Bedrock, confirm the Claude model is enabled in your AWS region
- Check that Python 3.10+ is available on the Connect server

## Related Resources

- [Claude Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Anthropic Console](https://console.anthropic.com/)
- [Shiny for Python Chat Components](https://shiny.posit.co/py/components/display-messages/chat/)
- [Posit Connect Extension Gallery](https://docs.posit.co/connect/admin/connect-gallery/index.html)

## Support

For issues with this extension, see the [Connect Extensions repository](https://github.com/posit-dev/connect-extensions).
