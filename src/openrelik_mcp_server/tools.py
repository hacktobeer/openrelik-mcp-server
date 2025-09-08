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
"""Tools for OpenRelik MCP server."""

import base64
from typing import Any

from fastmcp import FastMCP

from .utils import get_openrelik_client

mcp = FastMCP("OpenRelik MCP Server")


def _read_file_metadata(file_id: int) -> dict[str, Any]:
    """Reads a file metadata from a file in OpenRelik. Always returns a JSON string with the file metadata.

    Args:
        file_id: The ID of the file to get the metadata from.

    Returns:
        A dictionary containing file metadata.
    """
    response = get_openrelik_client().get(f"/files/{file_id}")
    return response.json()


@mcp.tool()
def list_folder(folder_id: int) -> list[dict[str, Any]]:
    """Lists files in an OpenRelik folder. Always returns a JSON string with the list of files with
    their metadata.

    Args:
        folder_id: The ID of the folder to list the files from.

    Returns:
        A list of dictionaries containing file metadata, including:
        - display_name: The name of the file
        - filesize: The size of the file in bytes
        - magic_mime: The mime type of the file
    """
    api_client = get_openrelik_client()
    response = api_client.get(f"/folders/{folder_id}/files/")
    return response.json()


@mcp.tool()
def read_file_metadata(file_id: int) -> dict[str, Any]:
    """Reads a file metadata from a file in OpenRelik. Always returns a JSON string with the file metadata.

    Args:
        file_id: The ID of the file to get the metadata from.

    Returns:
        A dictionary containing file metadata, including:
        - display_name: The name of the file
        - filesize: The size of the file in bytes
        - extension: The extension of the file
        - original_path: The original path of the file where it was found on disk
        - magic_mime: The mime type of the file
        - hash_*: Several calculated unique forensic file hashes
    """
<<<<<<< HEAD
    response = _read_file_metadata(file_id)
    return response
=======
    api_client = get_openrelik_client()
    response = api_client.get(f"/files/{file_id}")
    return response.json()
>>>>>>> upstream/main


@mcp.tool()
def read_file_content(file_id: int) -> bytes | str:
    """Reads the content of a file in OpenRelik. Returns the file content or
    an error if the filesize is too big (> 5MB)

    Args:
        file_id: The ID of the file to read the content from.

    Returns:
        The content of the file.
    """
<<<<<<< HEAD
    metadata = _read_file_metadata(file_id)
    filesize = metadata.get("filesize")
    if filesize and int(filesize) > 5_000_000:  # 5MB
        return f"Error read_file_content: Filesize too big (max 5MB) - {filesize}"

    response = get_openrelik_client().get(f"/files/{file_id}/download")
=======
    MAX_FILESIZE = 5_000_000  # 5MB

    api_client = get_openrelik_client()
    metadata = api_client.get(f"/files/{file_id}")
    filesize = metadata.get("filesize")
    if filesize and int(filesize) > MAX_FILESIZE:
        return f"Error read_file_content: Filesize too big (max 5MB) - {filesize}"

    response = api_client.get(f"/files/{file_id}/download")
>>>>>>> upstream/main
    return base64.b64decode(response.content)
