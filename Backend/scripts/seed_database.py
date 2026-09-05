#!/usr/bin/env python3
"""Seed the database with a demo user so the frontend's auto-login works
immediately, without waiting for the /auth/register bootstrap on first load.

Usage:
    python scripts/seed_database.py
"""
import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select  # noqa: E402
from app.core.database import async_session, engine, Base  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402

DEMO_EMAIL = "demo@recoveryagent.dev"
DEMO_PASSWORD = "demo12345"


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == DEMO_EMAIL))
        if result.scalar_one_or_none():
            print(f"Demo user already exists: {DEMO_EMAIL}")
            return

        user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD), role="admin")
        session.add(user)
        await session.commit()
        print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print("(matches the frontend's default VITE_DEMO_EMAIL / VITE_DEMO_PASSWORD)")


if __name__ == "__main__":
    asyncio.run(main())
