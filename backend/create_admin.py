import asyncio
import sys
from pathlib import Path
from getpass import getpass

sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session
from app.models import User
from app.auth import hash_password

async def create_admin():
    email = input("Admin email: ")
    password = getpass("Admin password: ")
    name = input("Admin name: ")
    
    from sqlalchemy import select
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print("User already exists")
            return
        
        user = User(
            email=email,
            password_hash=hash_password(password),
            name=name,
            role="admin"
        )
        session.add(user)
        await session.commit()
        print(f"Admin user created: {email}")

if __name__ == "__main__":
    asyncio.run(create_admin())
