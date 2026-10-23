"""
ResourceShift AI - Model Context Protocol (MCP) Server Entrypoint
------------------------------------------------------------------
Starts the ResourceShift AI FastMCP server over standard I/O (stdio)
or Server-Sent Events (SSE) for integration with LLM agents (Gemini).

Usage:
  python backend/mcp_server.py              # Runs over stdio transport
  python backend/mcp_server.py --sse        # Runs over SSE transport
"""

from __future__ import annotations

import argparse
import sys
from backend.app.mcp.server import create_mcp_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the ResourceShift AI MCP Server.")
    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP Transport mechanism (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for SSE/HTTP transport")
    parser.add_argument("--port", type=int, default=8001, help="Port for SSE/HTTP transport")
    args = parser.parse_args()

    server = create_mcp_server()
    print(f"Starting ResourceShift MCP Server ({args.transport} transport)...", file=sys.stderr)

    if args.transport == "sse":
        server.run(transport="sse")
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
