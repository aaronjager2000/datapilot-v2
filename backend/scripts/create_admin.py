"""
Create Admin User

Creates a default admin/superuser for development and testing
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import User
from app.models.organization import Organization
from app.core.security import get_password_hash
from uuid import uuid4


async def create_admin_user():
    """Create default admin user"""
    
    # Create async engine
    engine = create_async_engine(str(settings.DATABASE_URL))
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Check if admin already exists
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "admin@datapilot.com")
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print("⚠️  Admin user already exists!")
            print(f"Email: admin@datapilot.com")
            return
        
        # Create default organization
        org = Organization(
            id=uuid4(),
            name="DataPilot Admin",
            slug="datapilot-admin",
            description="Default admin organization",
            is_active=True,
            max_users=999,
            max_datasets=9999,
            max_storage_gb=500,
        )
        session.add(org)
        await session.flush()
        
        # Create admin user
        admin = User(
            id=uuid4(),
            email="admin@datapilot.com",
            full_name="Admin User",
            hashed_password=get_password_hash("admin123"),
            organization_id=org.id,
            is_active=True,
            is_superuser=True,
            email_verified=True,
        )
        session.add(admin)
        
        await session.commit()
        
        print("✅ Admin user created successfully!")
        print("\n" + "="*50)
        print("🔐 DEFAULT ADMIN CREDENTIALS")
        print("="*50)
        print(f"Email:    admin@datapilot.com")
        print(f"Password: admin123")
        print("="*50)
        print("\n⚠️  IMPORTANT: Change this password in production!")
        print("\n")


if __name__ == "__main__":
    asyncio.run(create_admin_user())
