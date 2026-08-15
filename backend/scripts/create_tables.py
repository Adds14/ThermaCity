import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.database import engine
from app.models.base import Base
from app.models.community_report import CommunityReport
from app.models.spatial_grid import SpatialGrid
from app.models.ward_boundary import WardBoundary
from app.models.environmental_features import EnvironmentalFeature

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created.")

if __name__ == "__main__":
    asyncio.run(init())
