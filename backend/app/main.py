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
from fastapi.responses import HTMLResponse

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
    from app.routers import grid, hvi, reports, scenario, wards

    app.include_router(grid.router, prefix=settings.api_v1_prefix)
    app.include_router(hvi.router, prefix=settings.api_v1_prefix)
    app.include_router(wards.router, prefix=settings.api_v1_prefix)
    app.include_router(reports.router, prefix=settings.api_v1_prefix)
    app.include_router(scenario.router, prefix=settings.api_v1_prefix)

    # ── Root page — shows backend is running ──
    @app.get("/", tags=["System"], response_class=HTMLResponse)
    async def root():
        model_status = "✅ Loaded" if ml_predictor else "❌ Not loaded"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ThermaCity Backend</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #0b0f19; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    .card {{ background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 3rem; max-width: 480px; text-align: center; }}
    h1 {{ font-size: 1.75rem; margin-bottom: 0.5rem; background: linear-gradient(90deg, #ff4d00, #ff8c00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .subtitle {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 2rem; }}
    .status {{ display: flex; align-items: center; gap: 8px; justify-content: center; margin-bottom: 1rem; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; background: #22c55e; animation: pulse 2s infinite; }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
    .info {{ font-size: 0.85rem; color: #94a3b8; margin-top: 1.5rem; }}
    .info a {{ color: #60a5fa; text-decoration: none; }}
    .model {{ margin-top: 0.5rem; font-size: 0.8rem; color: #64748b; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>🌡️ ThermaCity</h1>
    <p class="subtitle">Heat Vulnerability Intelligence Engine</p>
    <div class="status"><div class="dot"></div> <strong>Backend is running</strong></div>
    <p class="model">ML Model: {model_status}</p>
    <p class="info">
      <a href="/docs">API Documentation (Swagger)</a><br>
      <a href="/health">Health Check (JSON)</a>
    </p>
  </div>
</body>
</html>"""

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

