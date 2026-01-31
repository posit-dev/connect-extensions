# Claude Chat

A basic chat interface powered by the Claude Agent SDK. This extension serves as a building block for exploring Claude's capabilities on Posit Connect.

## Overview

This extension provides a simple chat interface for asking general questions using the Claude Agent SDK. It demonstrates how to authenticate and interact with Claude models on Connect, supporting both direct Anthropic API access and AWS Bedrock.

## Features

- **Simple Chat Interface**: Clean Shiny-based UI for conversational interactions
- **Claude Agent SDK**: Uses Anthropic's official SDK for Claude interactions
- **Flexible Authentication**: Supports Anthropic API keys or AWS Bedrock
- **Building Block**: Foundation for more complex Claude-powered extensions

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
Once deployed, open the application and start asking questions. Claude will respond conversationally without tool access - this is intentionally minimal to serve as a foundation.

## Architecture

The application uses:
- **Shiny for Python**: Chat UI components
- **Claude Agent SDK**: Handles Claude conversations with the bundled Claude Code runtime
- **Async Streaming**: Messages are processed asynchronously for responsiveness

## Extending This Extension

This extension is designed as a starting point. You can extend it by:
- Adding tools via `ClaudeAgentOptions(allowed_tools=[...])`
- Connecting MCP servers for external capabilities
- Adding session persistence for multi-turn conversations
- Implementing user-specific context

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
