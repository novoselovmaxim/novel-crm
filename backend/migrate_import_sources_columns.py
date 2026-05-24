import asyncio
from sqlalchemy import text
from app.database import async_session


async def migrate():
    async with async_session() as db:
        cols = [
            ("total_rows", "INTEGER DEFAULT 0"),
            ("processed_rows", "INTEGER DEFAULT 0"),
            ("added_count", "INTEGER DEFAULT 0"),
            ("updated_count", "INTEGER DEFAULT 0"),
            ("skipped_count", "INTEGER DEFAULT 0"),
            ("error_message", "TEXT"),
        ]
        for name, dtype in cols:
            try:
                await db.execute(text(f"ALTER TABLE import_sources ADD COLUMN IF NOT EXISTS {name} {dtype}"))
                print(f"  + {name} {dtype}")
            except Exception as e:
                print(f"  ! {name}: {e}")
        await db.commit()
        print("Done")


if __name__ == "__main__":
    asyncio.run(migrate())
