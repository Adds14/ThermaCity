"""
ThermaCity — Google Earth Engine Authentication

Handles the personal ee.Authenticate() / ee.Initialize() flow.
For the MVP, we use interactive browser-based authentication
rather than a GCP service account.

Usage:
    from utils.auth import initialize_gee
    initialize_gee(project_id="your-gee-cloud-project")
"""

import logging

import ee
from pathlib import Path

logger = logging.getLogger(__name__)


def initialize_gee(project_id: str | None = None) -> None:
    """
    Authenticate and initialize the Earth Engine Python API.

    Attempts to use a Service Account JSON key from the credentials folder.
    Falls back to interactive browser authentication if needed.
    """
    import os
    import glob

    cred_dir = Path(__file__).resolve().parent.parent.parent / "credentials"
    json_keys = glob.glob(str(cred_dir / "*.json"))

    if json_keys:
        key_path = json_keys[0]
        logger.info(f"Found service account key: {key_path}")
        import json
        with open(key_path, 'r') as f:
            key_data = json.load(f)
            client_email = key_data.get('client_email')
        
        try:
            credentials = ee.ServiceAccountCredentials(client_email, key_path)
            ee.Initialize(credentials, project=project_id or key_data.get('project_id'))
            logger.info("Earth Engine initialized using Service Account.")
            return
        except Exception as e:
            logger.error(f"Service Account auth failed: {e}")
            # Fall back to personal auth
    
    try:
        # Try initializing with cached personal credentials
        if project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()
        logger.info("Earth Engine initialized with cached credentials.")
    except Exception as init_error:
        logger.info(
            "Cached credentials not found or expired. "
            "Opening browser for authentication..."
        )
        try:
            # Interactive browser-based authentication
            ee.Authenticate()
            if project_id:
                ee.Initialize(project=project_id)
            else:
                ee.Initialize()
            logger.info("Earth Engine authenticated and initialized successfully.")
        except Exception as auth_error:
            logger.error(f"GEE authentication failed: {auth_error}")
            raise RuntimeError(
                "Could not authenticate with Google Earth Engine. "
                "Ensure you have a valid GEE account and internet connection. "
                "Visit https://earthengine.google.com/ to register."
            ) from auth_error


def verify_gee_connection() -> dict:
    """
    Verify that GEE is connected and return basic info.

    Returns:
        dict with 'status' and optional 'asset_roots'.

    Raises:
        RuntimeError if GEE is not initialized.
    """
    try:
        # Simple server-side computation to verify connectivity
        result = ee.Number(1).add(1).getInfo()
        assert result == 2, f"Unexpected result: {result}"

        info = {"status": "connected", "test_result": result}

        # Try to list asset roots (may not be available for all accounts)
        try:
            roots = ee.data.getAssetRoots()
            info["asset_roots"] = [r["id"] for r in roots]
        except Exception:
            info["asset_roots"] = []

        logger.info(f"GEE connection verified: {info}")
        return info

    except Exception as e:
        raise RuntimeError(
            f"GEE connection test failed: {e}. Call initialize_gee() first."
        ) from e
