# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""MCP server for accessing files and directories in OpenRelik."""

import argparse
import logging


from fastmcp import FastMCP

from openrelik_mcp_server import tools

logger = logging.getLogger(__name__)


mcp = FastMCP("OpenRelik MCP Server")
mcp.mount(prefix="", server=tools.mcp)


def main():
    parser = argparse.ArgumentParser(description="MCP server for OpenRelik")
    parser.add_argument(
        "--host",
        type=str,
        help="Host to run MCP server, default: 127.0.0.1",
        default="127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port to run MCP server, default: 8081",
        default=8081,
    )
    parser.add_argument(
        "--transport",
        type=str,
        help="Transport protocol: sse or http, default: sse",
        default="sse",
    )
    args = parser.parse_args()

    logger.info(f"Running MCP server on {args.host}:{args.port}")
    try:
        mcp.settings.port = args.port
        mcp.settings.host = args.host
        mcp.run(transport=args.transport)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return


if __name__ == "__main__":
    main()
