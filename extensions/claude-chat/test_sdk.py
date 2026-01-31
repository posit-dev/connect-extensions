#!/usr/bin/env python
"""Quick test script to debug Claude Agent SDK issues."""

import asyncio
import os


async def main():
    print("Testing Claude Agent SDK...")
    print(f"CLAUDE_CODE_USE_BEDROCK: {os.getenv('CLAUDE_CODE_USE_BEDROCK')}")
    print(f"AWS_REGION: {os.getenv('AWS_REGION')}")
    print(f"AWS_PROFILE: {os.getenv('AWS_PROFILE')}")
    print(f"AWS_DEFAULT_REGION: {os.getenv('AWS_DEFAULT_REGION')}")

    try:
        from claude_agent_sdk import ClaudeAgentOptions, query

        options = ClaudeAgentOptions(
            allowed_tools=[],
            system_prompt="You are a helpful assistant.",
            model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        )

        print("Sending test message (timeout in 30s)...")

        async def run_with_timeout():
            async for message in query(prompt="Say hello in exactly 3 words.", options=options):
                print(f"Message type: {type(message).__name__}")
                print(f"Message: {message}")
                if hasattr(message, "result"):
                    print(f"Result: {message.result}")

        await asyncio.wait_for(run_with_timeout(), timeout=30.0)

    except asyncio.TimeoutError:
        print("TIMEOUT: Query took longer than 30 seconds")
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
