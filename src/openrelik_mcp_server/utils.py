import logging
import os

from openrelik_api_client.api_client import APIClient

logger = logging.getLogger(__name__)


def get_openrelik_client() -> APIClient:
    """
    Get an instance of the OpenRelik API client.
    """
    host_uri = os.getenv("OPENRELIK_API_URL")
    api_key = os.getenv("OPENRELIK_API_KEY")

    if host_uri is None or api_key is None:
        raise RuntimeError("OPENRELIK_API_URL or OPENRELIK_API_KEY not set!")

    return APIClient(host_uri, api_key)
