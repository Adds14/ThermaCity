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

logger = logging.getLogger(__name__)


def initialize_gee(project_id: str | None = None) -> None:
    """
    Authenticate and initialize the Earth Engine Python API.

    Attempts to initialize with cached credentials first.
    Falls back to interactive browser authentication if needed.

    Args:
        project_id: Google Cloud project ID registered with Earth Engine.
                     Required for newer GEE API versions. If None, attempts
                     initialization without a project (legacy mode).
    """
    try:
        # Try initializing with cached credentials first
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
