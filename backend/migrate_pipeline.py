"""Add pipeline/tg columns to existing companies table."""
import asyncio
from app.database import engine
from sqlalchemy import text

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS pipeline_stage VARCHAR DEFAULT 'new'"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS tg_contact VARCHAR"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS tg_status VARCHAR DEFAULT 'none'"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS messenger VARCHAR"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_companies_pipeline_stage ON companies(pipeline_stage)"))
        print("Migration complete")

asyncio.run(migrate())
