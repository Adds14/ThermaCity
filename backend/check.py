"""Quick DB connectivity check — uses DATABASE_URL from environment / .env."""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()


async def check():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set. Create a .env file or export it.")
        return
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT COUNT(*), COUNT(population_density) FROM environmental_features;")
        )
        print("Total features, Features with pop density:")
        print(res.fetchone())


if __name__ == "__main__":
    asyncio.run(check())
