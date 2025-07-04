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

import json
import logging
import os
import sys
import time

from fastmcp import FastMCP
from openrelik_api_client.api_client import APIClient
import openrelik_api_client.folders as folderapi
import openrelik_api_client.workflows as workflowapi

import requests

logger = logging.getLogger(__name__)

# Workaround for https://github.com/google/adk-python/issues/743
# TODO: Remove this workaround when the issue is fixed and use env variables directly.
OPENRELIK_API_URL = sys.argv[1] if len(sys.argv) > 1 else os.getenv("OPENRELIK_API_URL")
OPENRELIK_API_KEY = sys.argv[2] if len(sys.argv) > 2 else os.getenv("OPENRELIK_API_KEY")

# Create the API client. It will handle token refreshes automatically.
api_client = APIClient(OPENRELIK_API_URL, OPENRELIK_API_KEY)

mcp = FastMCP(
    "OpenRelik MCP Server",
)

# This URL contains the artifacts that image_export.py supports. We load them in at the start of the MCP server.
ARTIFACT_URL = (
    "https://gist.githubusercontent.com/hacktobeer/174882f8d9cbbd2b0728ca90cad04cfa/raw"
)
ARTIFACTS_SUPPORTED = requests.get(ARTIFACT_URL).content

## Define the below templates in your OpenRelik setup and update the template IDs below
## TODO(rbdebeer) - implement dynamic template creation based on json specs once Relik API lands.
# Yara-worker (with mount option enabled)
TEMPLATE_ID_YARA = 9
# Extraction worker with dummy SshdConfigFile artifact selected.
TEMPLATE_ID_ARTIFACT_EXTRACT = 5
# Extraction worker with "<FILEPATH>" marker in filename field
TEMPLATE_ID_FILE_EXTRACT = 6
# plaso timeline worker -> timesketch worker
TEMPLATE_ID_TIMELINE = 7
# Extraction worker (WindowsSystemRegistryFiles, WindowsActiveDirectoryDatabase, UnixShadowFile, UnixShadowBackupFile) -> os-cred worker.
TEMPLATE_ID_WEAK_PASSWORDS = 8


def execute_workflow(template_id, source_ids, template_data={}):
    # Get folder_id from 1st source_id
    response = api_client.get(f"/files/{source_ids[0]}")
    file = json.loads(response.content)
    folder_id = int(file["folder"]["id"])

    # # Create folder
    # folder_id = folderapi.FoldersAPI(api_client).create_subfolder(
    #     root_folder_id, "extract_files"
    # )
    # logger.info(f"Folder created {folder_id}")

    # Create workflow from TEMPLATE_ID
    workflow_id = workflowapi.WorkflowsAPI(api_client).create_workflow(
        folder_id, source_ids, template_id
    )
    logger.info(f"Workflow ID: {workflow_id}")

    # Get workflow
    workflow = workflowapi.WorkflowsAPI(api_client).get_workflow(folder_id, workflow_id)

    # Update workflow with template markers to be replaced
    for key, value in template_data.items():
        workflow["spec_json"] = workflow["spec_json"].replace(key, value)
    workflowapi.WorkflowsAPI(api_client).update_workflow(
        folder_id, workflow_id, workflow
    )

    # Run workflow
    workflowapi.WorkflowsAPI(api_client).run_workflow(folder_id, workflow_id)

    # Poll workflow until finished
    while True:
        workflow = workflowapi.WorkflowsAPI(api_client).get_workflow(
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


@mcp.tool(
    name="list_folder",
    description="""
    Lists files in an OpenRelik folder. Always returns a JSON string with the list of files with
    their metadata.
    """,
)
def list_folder(folder_id: int) -> str:
    """Lists files in an OpenRelik folder."""
    response = api_client.get(f"/folders/{folder_id}/files/")
    return response.text


@mcp.tool(
    name="read_file_metadata",
    description="""
    Reads a file metadata from a file in OpenRelik. Always returns a JSON string with the file metadata.
    """,
)
def read_file_metadata(file_id: int) -> str:
    """Reads a file metadata from a file in OpenRelik."""
    response = api_client.get(f"/files/{file_id}")
    return response.json()


@mcp.tool(
    name="read_file_content",
    description="""
    Reads the content of a file in OpenRelik. Always returns a JSON string with the file content.
    """,
)
def read_file_content(file_id: int) -> str:
    """Reads a file content from a file in OpenRelik."""
    response = api_client.get(f"/files/{file_id}/content/")
    # Bug workaround: file content api returns content with html tags around it for several mime types ...
    # This would not work if a file is indeed a HTML file...lol
    return response.text


@mcp.tool(
    name="extract_files_from_disk_image",
    description="""
    Extracts a files from a disk image.
    You can give one or more filenames (comma seperated) to be extracted from a disk 
    image referenced with a file_id.
    NOTE: the filename should be a filename only, without the path component. For example, if you want
    to extract "/etc/ssh/sshd_config" you would give the file_name "sshd_config".
    On success returns a JSON string with the workflow results including output files (output_files)
    with their file id (id), folder location (folder_id) and display name (display_name).
    On failure returns a JSON string with the error (error_exception).
    """,
)
def extract_file_from_disk_image(file_names: str, file_id: int):
    TEMPLATE_ID = TEMPLATE_ID_FILE_EXTRACT

    template_data = {"<FILEPATH>": file_names}

    return execute_workflow(TEMPLATE_ID, [file_id], template_data)


@mcp.tool(
    name="extract_artifacts_from_disk_image",
    description="""
    Extracts artifacts from a disk image.

    NOTE: This tool ONLY SUPPORTS artifact names provided by the tool get_supported_extraction_artifacts!

    The artifact names should be one or more (comma seperated) supported artifact names as returned 
    by tool `get_supported_extraction_artifacts`
    
    You can give one or more artifact names (artifact_names) to be extracted from a disk image referenced
    with a file_id.
    On success returns a JSON string with the workflow results including output files (output_files)
    with their file id (id), folder location (folder_id) and display name (display_name).
    On failure returns a JSON string with the error (error_exception).
    """,
)
def extract_artifacts_from_disk_image(artifact_names: str, file_id: int):
    TEMPLATE_ID = TEMPLATE_ID_ARTIFACT_EXTRACT

    template_data = {"SshdConfigFile": artifact_names}

    return execute_workflow(TEMPLATE_ID, [file_id], template_data)


@mcp.tool(
    name="get_supported_extraction_artifacts",
    description="""
    Gets the supported artifact (artifact_name) that can be used by the 
    `extract_artifact_from_disk_image` tool.
    Always returns a list of supported artifact names.
    """,
)
def get_supported_extraction_artifacts():
    return ARTIFACTS_SUPPORTED


def _parse_sketch_id(result):
    """Parse and return the sketch id from a Timesketch MCP call result"""
    result_dict = json.loads(result)
    result_status = result_dict["tasks"][1]["status_short"]
    if result_status == "SUCCESS":
        task_result = result_dict["tasks"][1]["result"]
        task_results_dict = json.loads(task_result)
        sketch_url = task_results_dict["meta"]["sketch"]
        sketch_url_id = sketch_url.split("/")[-1]

        return sketch_url_id

    return None


@mcp.tool(
    name="create_forensic_timeline_from_forensic_artifact",
    description="""
    Creates a forensic timeline from a forensic artifact and upload it to timesketch.
    The output will be the Timesketch Sketch ID (sketch_id).
    On success returns a JSON string with the Timesketch Sketch ID (sketch_id).
    On failure returns a JSON string with the error (error_exception).
    """,
)
def create_forensic_timeline_from_forensic_artifact(file_id: int):
    TEMPLATE_ID = TEMPLATE_ID_TIMELINE
    result = execute_workflow(TEMPLATE_ID, [file_id])

    sketch_id = _parse_sketch_id(result)
    if sketch_id:
        data = {"sketch_id": sketch_id}
        return json.dumps(data)

    return result


@mcp.tool(
    name="check_disk_image_for_weak_account_passwords",
    description="""
    Check a disk image for weak account passwords.

    On success returns a JSON string with the workflow results including output files (output_files)
    with the results of the account passwords checks with their file id (id), folder location (folder_id) 
    and display name (display_name).   
    On failure returns a JSON string with the error (error_exception).
    """,
)
def check_disk_image_for_weak_account_passwords(file_id: int):
    TEMPLATE_ID = TEMPLATE_ID_WEAK_PASSWORDS

    return execute_workflow(TEMPLATE_ID, [file_id])


@mcp.tool(
    name="run_yara_malware_scanner_on_disk_image",
    description="""
    Run the Yara malware scanner on a disk image. This scanner will scan for malware
    on a disk image. 

    On success returns a JSON string with the workflow results including output files (output_files)
    with their file id (id), folder location (folder_id) and display name (display_name).
    On failure returns a JSON string with the error (error_exception).
    """,
)
def run_yara_malware_scanner_on_disk_image(file_id: int):
    TEMPLATE_ID = TEMPLATE_ID_YARA

    return execute_workflow(TEMPLATE_ID, [file_id])


if __name__ == "__main__":
    mcp.run(
      transport="http",
      host="0.0.0.0",
      port=8081,
      log_level="debug"
    )
