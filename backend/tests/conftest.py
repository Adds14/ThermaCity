import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator
import json

from app.main import app, lifespan
from app.services.ml_predictor import MLPredictor

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with lifespan(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client
