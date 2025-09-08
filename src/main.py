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
"""MCP server for OpenRelik."""

import argparse
import os
import warnings

from fastmcp import FastMCP

from openrelik_mcp_server import tools

mcp = FastMCP("OpenRelik MCP Server")
mcp.mount(server=tools.mcp)


def main():
    parser = argparse.ArgumentParser(description="MCP server for OpenRelik")
    parser.add_argument(
        "--transport",
        type=str,
        help="Transport protocol: stdio, http, or sse. Deprecated: sse.",
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Host to run the MCP server on, default: 127.0.0.1",
        default=os.environ.get("MCP_HTTP_HOST", "127.0.0.1"),
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port to run the MCP server on, default: 7070",
        default=int(os.environ.get("MCP_HTTP_PORT", 7070)),
    )
    args = parser.parse_args()

    # Deprecate SSE transport
    if args.transport == "sse":
        warnings.warn(
            "The 'sse' transport is deprecated and will be removed in a future release. Please use 'http' instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Default kwargs for mcp.run()
    mcp_kwargs = dict(transport=args.transport)

    # http and sse transports need host and port
    if args.transport == "http" or args.transport == "sse":
        mcp_kwargs["host"] = args.host
        mcp_kwargs["port"] = args.port

    try:
        mcp.run(**mcp_kwargs)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
