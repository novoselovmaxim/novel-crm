"""Add pipeline/tg columns + migrate call_status → pipeline_stage."""
import asyncio
from app.database import engine
from sqlalchemy import text

STAGE_MAP = {
    "new": "new",
    "not_reached": "message_sent",
    "no_answer": "message_sent",
    "callback": "message_sent",
    "in_progress": "in_progress",
    "interested": "diagnosis_done",
    "thinking": "diagnosis_done",
    "meeting": "diagnosis_done",
    "refused": "new",
}


async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS pipeline_stage VARCHAR DEFAULT 'new'"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS tg_contact VARCHAR"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS tg_status VARCHAR DEFAULT 'none'"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS messenger VARCHAR"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS ai_suggestions JSONB"))
        await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS ai_summary TEXT"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_companies_pipeline_stage ON companies(pipeline_stage)"))

        print("Migrating call_status → pipeline_stage...")
        for call_status, pipeline_stage in STAGE_MAP.items():
            result = await conn.execute(
                text("UPDATE companies SET pipeline_stage = :to WHERE call_status = :from AND is_deleted = false"),
                {"to": pipeline_stage, "from": call_status},
            )
            if result.rowcount:
                print(f"  {call_status} → {pipeline_stage}: {result.rowcount} companies")

        # Companies with 'new' call_status but assigned → in_progress
        result = await conn.execute(
            text("UPDATE companies SET pipeline_stage = 'in_progress' WHERE call_status = 'new' AND assigned_to IS NOT NULL AND is_deleted = false"),
        )
        if result.rowcount:
            print(f"  assigned+new → in_progress: {result.rowcount} companies")

        # Meeting reminder flags
        await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS reminded_1d BOOLEAN DEFAULT false"))
        await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS reminded_1h BOOLEAN DEFAULT false"))
        await conn.execute(text("ALTER TABLE meetings ADD COLUMN IF NOT EXISTS reminded_10m BOOLEAN DEFAULT false"))

        print("Migration complete")


asyncio.run(migrate())
