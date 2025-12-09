from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.models.role import Role


async def init_db(db: AsyncSession) -> None:


    # Check if database is already initialized
    result = await db.execute(select(User))
    existing_users = result.scalars().all()

    if existing_users:
        print("Database already initialized, skipping...")
        return

    print("Initializing database...")

    # Create default organization for superuser
    default_org = Organization(
        name="Datapilot Admin",
        slug="datapilot-admin",
        settings={}
    )
    db.add(default_org)
    await db.flush()

    # Create default roles
    roles_data = [
        {
            "name": "Viewer",
            "description": "Read-only access to data and dashboards",
            "is_default": True,
            "is_system": True
        },
        {
            "name": "Analyst",
            "description": "Can create and manage datasets, queries, and reports",
            "is_default": False,
            "is_system": True
        },
        {
            "name": "Manager",
            "description": "Can manage users and organization settings",
            "is_default": False,
            "is_system": True
        },
        {
            "name": "Admin",
            "description": "Full administrative access to all features",
            "is_default": False,
            "is_system": True
        }
    ]

    created_roles = {}
    for role_data in roles_data:
        role = Role(
            name=role_data["name"],
            description=role_data["description"],
            is_default=role_data["is_default"],
            is_system=role_data["is_system"],
            organization_id=default_org.id
        )
        db.add(role)
        await db.flush()
        created_roles[role_data["name"]] = role
        print(f"Created role: {role.name}")

    # Create superuser if configured
    if settings.FIRST_SUPERUSER_EMAIL:
        superuser = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
            full_name=settings.FIRST_SUPERUSER_NAME if settings.FIRST_SUPERUSER_NAME else "Admin User",
            organization_id=default_org.id,
            is_active=True,
            is_superuser=True
        )
        db.add(superuser)
        await db.flush()

        # TODO: Assign Admin role to superuser when RBAC tables are created
        # admin_role = created_roles["Admin"]
        # user_role = UserRole(user_id=superuser.id, role_id=admin_role.id)
        # db.add(user_role)

        print(f"Created superuser: {superuser.email}")

    await db.commit()
    print("Database initialization complete!")


async def create_default_roles_for_organization(
    db: AsyncSession,
    organization_id: str
) -> dict[str, Role]:

    roles_data = [
        {
            "name": "Viewer",
            "description": "Read-only access to data and dashboards",
            "is_default": True,
            "is_system": False
        },
        {
            "name": "Analyst",
            "description": "Can create and manage datasets, queries, and reports",
            "is_default": False,
            "is_system": False
        },
        {
            "name": "Manager",
            "description": "Can manage users and organization settings",
            "is_default": False,
            "is_system": False
        },
        {
            "name": "Admin",
            "description": "Full administrative access to all features",
            "is_default": False,
            "is_system": False
        }
    ]

    created_roles = {}
    for role_data in roles_data:
        role = Role(
            name=role_data["name"],
            description=role_data["description"],
            is_default=role_data["is_default"],
            is_system=role_data["is_system"],
            organization_id=organization_id
        )
        db.add(role)
        await db.flush()
        created_roles[role_data["name"]] = role

    await db.commit()
    return created_roles
