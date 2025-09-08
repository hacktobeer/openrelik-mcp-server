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
"""Utilities for OpenRelik MCP server."""

import os

from openrelik_api_client.api_client import APIClient


def get_openrelik_client() -> APIClient:
    """Get an instance of the OpenRelik API client.

    Returns:
        APIClient: The API client instance.
    """
    OPENRELIK_API_URL = os.getenv("OPENRELIK_API_URL")
    OPENRELIK_API_KEY = os.getenv("OPENRELIK_API_KEY")

    if not OPENRELIK_API_URL or not OPENRELIK_API_KEY:
        raise RuntimeError("OPENRELIK_API_URL or OPENRELIK_API_KEY not set!")

    return APIClient(OPENRELIK_API_URL, OPENRELIK_API_KEY)
