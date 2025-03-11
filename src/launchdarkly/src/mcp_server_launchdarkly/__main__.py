#!/usr/bin/env python3
"""
Entry point for the LaunchDarkly MCP server.
"""

import asyncio
import os
import sys
import click
from mcp.shared.exceptions import McpError

from mcp_server_launchdarkly.server import serve


@click.command()
@click.option(
    "--sdk-key",
    envvar="LAUNCHDARKLY_SDK_KEY",
    required=True,
    help="LaunchDarkly SDK key",
)
@click.option(
    "--environment",
    envvar="LAUNCHDARKLY_ENVIRONMENT",
    default="production",
    help="LaunchDarkly environment (default: production)",
)
def main(sdk_key: str, environment: str):
    """Run the LaunchDarkly MCP server."""
    if not sdk_key:
        print("Error: LaunchDarkly SDK key is required", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(_run(sdk_key, environment))
    except McpError as e:
        print(f"MCP Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


async def _run(sdk_key: str, environment: str):
    """Run the server with the given configuration."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        server = await serve(sdk_key, environment)
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    main()
