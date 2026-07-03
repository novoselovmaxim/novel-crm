"""
Add director_gender column to companies table.

Usage:
    python migrate_director_gender.py
"""

import asyncio
from sqlalchemy import text
from app.database import async_session


async def migrate():
    async with async_session() as db:
        result = await db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'companies' AND column_name = 'director_gender'
        """))
        if result.fetchone():
            print("Column 'director_gender' already exists. Nothing to do.")
            return

        await db.execute(text("""
            ALTER TABLE companies
            ADD COLUMN director_gender VARCHAR
        """))
        await db.commit()
        print("Column 'director_gender' added to companies table.")


if __name__ == "__main__":
    asyncio.run(migrate())
