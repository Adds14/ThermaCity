import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine('postgresql+asyncpg://postgres:ThermaCity123@db.ctjbapfdnyioazajfasp.supabase.co:5432/postgres')
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT COUNT(*), COUNT(population_density) FROM environmental_features;'))
        print("Total features, Features with pop density:")
        print(res.fetchone())

if __name__ == '__main__':
    asyncio.run(check())
