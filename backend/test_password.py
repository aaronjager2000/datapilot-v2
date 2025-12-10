#!/usr/bin/env python3
"""Test password verification for the superuser."""

import asyncio
import sys
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import verify_password

async def test_password():
    async with AsyncSessionLocal() as db:
        # Get the admin user
        result = await db.execute(
            select(User).where(User.email == "admin@datapilot.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("❌ Admin user not found!")
            return

        print(f"✓ Found user: {user.email}")
        print(f"✓ Is active: {user.is_active}")
        print(f"✓ Is superuser: {user.is_superuser}")
        print(f"✓ Hash: {user.hashed_password[:20]}...")

        # Test password verification
        password = "changethis"
        print(f"\n Testing password: '{password}'")

        try:
            result = verify_password(password, user.hashed_password)
            if result:
                print(f"✅ Password verification SUCCESSFUL")
            else:
                print(f"❌ Password verification FAILED")
        except Exception as e:
            print(f"❌ Password verification ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_password())
