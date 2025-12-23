"""
Reset Admin Password

Resets the admin user password to default
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.user import User
from app.core.security import get_password_hash


async def reset_admin_password(new_password: str = "admin123"):
    """Reset admin password"""
    
    # Create async engine
    engine = create_async_engine(str(settings.DATABASE_URL))
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Find admin user
        result = await session.execute(
            select(User).where(User.email == "admin@datapilot.com")
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("❌ Admin user not found!")
            print("Run 'python scripts/create_admin.py' first")
            return
        
        # Update password
        admin.hashed_password = get_password_hash(new_password)
        await session.commit()
        
        print("✅ Admin password reset successfully!")
        print("\n" + "="*50)
        print("🔐 NEW ADMIN CREDENTIALS")
        print("="*50)
        print(f"Email:    admin@datapilot.com")
        print(f"Password: {new_password}")
        print("="*50)
        print("\n")


if __name__ == "__main__":
    import sys
    
    # Allow custom password via command line
    new_password = sys.argv[1] if len(sys.argv) > 1 else "admin123"
    
    asyncio.run(reset_admin_password(new_password))
