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

import json
import logging
import time
from typing import Any

import openrelik_api_client.workflows as workflowapi

from fastmcp import FastMCP

from .artifacts import IMAGE_EXPORT_ARTIFACTS
from .utils import get_openrelik_client

logger = logging.getLogger(__name__)

mcp = FastMCP("OpenRelik MCP Server")

## Create the below workflow templates in your OpenRelik setup and update the template names below
## Templates can be listed at http://[openrelik-server]:8710/api/v1/docs#/workflows/get_workflow_templates_workflows_templates__get
# Yara-worker (with mount option enabled)
TEMPLATE_YARA = "mcp_run_yara_scanner"
# Extraction worker with dummy "SshdConfigFile" artifact selected.
TEMPLATE_ARTIFACT_EXTRACT = "mcp_extract_artifacts"
# Extraction worker with "<FILEPATH>" marker in filename field
TEMPLATE_FILE_EXTRACT = "mcp_extract_filenames"
# Timeline workflow using the log2timeline -> psort workers
TEMPLATE_TIMELINE = "mcp_create_timeline"


def get_template_id_by_name(template_name: str) -> id:
    """Get the template ID from the template name.

    Args:
        template_name: The name of the template to get the ID from.
    Returns:
        The ID of the template.
    """
    response = get_openrelik_client().get("/workflows/templates/")
    decoded = json.loads(response.content)
    templates = [(i["id"], i["display_name"]) for i in decoded if not i["is_deleted"]]
    ids = [i for i, f in templates if f == template_name]
    if ids:
        return ids[0]

    return None


def execute_workflow(template_id, source_ids, template_data={}):
    # Get folder_id from 1st source_id
    response = get_openrelik_client().get(f"/files/{source_ids[0]}")
    file = json.loads(response.content)
    folder_id = int(file["folder"]["id"])

    # Check template ID
    if not template_id:
        return "Error: template_id is None, possibly template does not exist in OpenRelik!!"

    # Create workflow from TEMPLATE_ID
    workflow_id = workflowapi.WorkflowsAPI(get_openrelik_client()).create_workflow(
        folder_id, source_ids, template_id
    )

    if workflow_id is None:
        return "Error creating OpenRelik workflow!"
    logger.info(f"Workflow ID: {workflow_id}")

    # Get workflow
    workflow = workflowapi.WorkflowsAPI(get_openrelik_client()).get_workflow(
        folder_id, workflow_id
    )

    # Update workflow with template markers to be replaced
    for key, value in template_data.items():
        workflow["spec_json"] = workflow["spec_json"].replace(key, value)
    workflowapi.WorkflowsAPI(get_openrelik_client()).update_workflow(
        folder_id, workflow_id, workflow
    )

    # Run workflow
    workflowapi.WorkflowsAPI(get_openrelik_client()).run_workflow(
        folder_id, workflow_id
    )

    # Poll workflow until finished
    while True:
        workflow = workflowapi.WorkflowsAPI(get_openrelik_client()).get_workflow(
            folder_id, workflow_id
        )
        # Check if all tasks are done in the workflow
        workflow_done = True
        for task in workflow["tasks"]:
            if task["status_short"] not in ["SUCCESS", "FAILURE"]:
                workflow_done = False

        if workflow_done:
            return json.dumps(workflow)
        time.sleep(1)


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
    api_client = get_openrelik_client()
    response = api_client.get(f"/files/{file_id}")
    return response.json()


@mcp.tool()
def read_file_content(file_id: int) -> bytes | str:
    """Reads the content of a file in OpenRelik. Returns the file content or
    an error if the filesize is too big (> 5MB)

    Args:
        file_id: The ID of the file to read the content from.

    Returns:
        The content of the file.
    """
    MAX_FILESIZE = 5_000_000  # 5MB

    api_client = get_openrelik_client()
    metadata = api_client.get(f"/files/{file_id}")
    filesize = json.loads(metadata.content).get("filesize")
    if filesize and int(filesize) > MAX_FILESIZE:
        return f"Error read_file_content: Filesize too big (max 5MB) - {filesize}"

    response = api_client.get(f"/files/{file_id}/download")
    return response.content


@mcp.tool()
def extract_file_from_disk_image(file_names: str, file_id: int):
    """
    Extracts files from a disk image.
    You can give one or more filenames (comma separated) to be extracted from a disk
    image referenced with a file_id.
    NOTE: the filename should be a filenames only (multiple filenames can be comma separated),
    without the path component. For example, if you want to extract "/etc/ssh/sshd_config" you
    would give the file_name "sshd_config".
    On success returns a JSON string with the workflow results including output files (output_files)
    with their file id (id), folder location (folder_id) and display name (display_name).
    On failure returns a JSON string with the error (error_exception).

    Args:
        file_names: The files to extract based on filenames. Comma separated for multiple files.
        file_id: The file_id of the disk image to extract files from.

    Returns:
        Returns a JSON string with the workflow results including output files (output_files)
        with their file id (id), folder location (folder_id) and display name (display_name).
    """

    TEMPLATE_ID = get_template_id_by_name(TEMPLATE_FILE_EXTRACT)

    template_data = {"<FILEPATH>": file_names}

    return execute_workflow(TEMPLATE_ID, [file_id], template_data)


@mcp.tool()
def get_supported_extraction_artifacts():
    """
    Gets the supported artifact (artifact_name) that can be used by the
    `extract_artifact_from_disk_image` tool.
    Always returns a list of supported artifact names.

    Returns: A list of supported artifact names.
    """
    return IMAGE_EXPORT_ARTIFACTS


@mcp.tool()
def extract_artifacts_from_disk_image(artifact_names: str, file_id: int):
    """
    Extracts artifacts from a disk image.

    NOTE: This tool ONLY SUPPORTS artifact names provided by the tool get_supported_extraction_artifacts!

    The artifact names should be one or more (comma seperated) supported artifact names as returned
    by tool `get_supported_extraction_artifacts`

    You can give one or more artifact names (artifact_names) to be extracted from a disk image referenced
    with a file_id.
    On success returns a JSON string with the workflow results including output files (output_files)
    with their file id (id), folder location (folder_id) and display name (display_name).
    On failure returns a JSON string with the error (error_exception).

    Args:
        artifact_names:  One or more (comma seperated) supported artifact names as returned
        by tool `get_supported_extraction_artifacts`
        file_id: The file_id of the disk image to extract artifacts from.

    Returns:
        Returns a JSON string with the workflow results including output files (output_files)
        with their file id (id), folder location (folder_id) and display name (display_name).

    """
    TEMPLATE_ID = get_template_id_by_name(TEMPLATE_ARTIFACT_EXTRACT)

    template_data = {"SshdConfigFile": artifact_names}

    return execute_workflow(TEMPLATE_ID, [file_id], template_data)


@mcp.tool()
def run_yara_malware_scanner_on_disk_image(file_id: int):
    """
    Run the Yara malware scanner on a disk image. This scanner will scan for malware
    on a disk image.

    On success returns a JSON string with the workflow results including output files (output_files)
    with their file id (id), folder location (folder_id) and display name (display_name).
    On failure returns a JSON string with the error (error_exception).

    Args:
        file_id: The file_id of the disk image to scan with the Yara scanner.

    Returns:
        A JSON string with the workflow results including the Yara scan report,
        output files (output_files) with their file id (id), folder location (folder_id)
        and display name (display_name).
    """
    TEMPLATE_ID = get_template_id_by_name(TEMPLATE_YARA)

    return execute_workflow(TEMPLATE_ID, [file_id])


@mcp.tool()
def create_forensic_timeline(file_id: int):
    """
    Run log2timeline on a disk image to create a forensic timeline in .plaso and .csv format.

    On success returns a JSON string with the workflow results including output files (output_files)
    with their file id (id), folder location (folder_id) and display name (display_name).
    On failure returns a JSON string with the error (error_exception).

    Args:
        file_id: The file_id of the disk image to create the timeline from.

    Returns:
        A JSON string with the workflow results including the .plaso and .csv timeline output
        files (output_files) with their file id (id), folder location (folder_id)
        and display name (display_name).
    """
    TEMPLATE_ID = get_template_id_by_name(TEMPLATE_TIMELINE)

    return execute_workflow(TEMPLATE_ID, [file_id])
