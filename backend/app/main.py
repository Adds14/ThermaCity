"""
ThermaCity — FastAPI Application Factory

Entry point for the backend. Configures:
  - CORS middleware for frontend dev server
  - Lifespan context: loads ML model at startup, cleans up on shutdown
  - Router registration under /api/v1 prefix
  - OpenAPI metadata for Swagger docs

Usage:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.ml_predictor import MLPredictor

logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# ── Global ML predictor instance (loaded at startup) ─────────
ml_predictor: MLPredictor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan — runs once at startup and shutdown.

    Startup:
      - Loads the serialized Random Forest pipeline from disk.
      - Validates the model can accept our feature columns.

    Shutdown:
      - Releases the model from memory.
    """
    global ml_predictor

    logger.info("=" * 60)
    logger.info("ThermaCity backend starting up...")
    logger.info("=" * 60)

    # ── Load ML model ──
    model_path = Path(settings.ml_model_path)
    if model_path.exists():
        try:
            ml_predictor = MLPredictor(model_path)
            logger.info(f"  ML model loaded: {model_path}")
            logger.info(f"  Features: {ml_predictor.get_feature_names()}")
        except Exception as e:
            logger.warning(
                f"  ML model failed to load: {e}. "
                "Scenario simulator will be unavailable."
            )
            ml_predictor = None
    else:
        logger.warning(
            f"  ML model not found at {model_path}. "
            "Run ml/scripts/train_model.py first. "
            "Scenario simulator will be unavailable."
        )
        ml_predictor = None

    # ── Validate HVI weights ──
    try:
        weights = settings.hvi_weight_dict
        logger.info(f"  HVI weights validated: {weights}")
    except ValueError as e:
        logger.error(f"  HVI weight validation failed: {e}")
        raise

    logger.info("  Startup complete.")

    yield  # ← Application runs here

    # ── Shutdown ──
    logger.info("ThermaCity backend shutting down...")
    ml_predictor = None


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register Routers ──
    from app.routers import grid, hvi, reports, scenario, wards, demo

    app.include_router(grid.router, prefix=settings.api_v1_prefix)
    app.include_router(hvi.router, prefix=settings.api_v1_prefix)
    app.include_router(wards.router, prefix=settings.api_v1_prefix)
    app.include_router(reports.router, prefix=settings.api_v1_prefix)
    app.include_router(scenario.router, prefix=settings.api_v1_prefix)
    app.include_router(demo.router, prefix=settings.api_v1_prefix)

    # ── Health check ──
    @app.get("/health", tags=["System"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "ml_model_loaded": ml_predictor is not None,
        }

    return app


def get_ml_predictor() -> MLPredictor | None:
    """Dependency accessor for the global ML predictor."""
    return ml_predictor


# ── Module-level app instance for `uvicorn app.main:app` ──
app = create_app()
