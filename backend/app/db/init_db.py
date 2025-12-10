from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
# Import all models to ensure relationships are properly configured
from app.models import Organization, User, Role, Permission, Dataset, Record, File


# Define all system permissions
PERMISSION_DEFINITIONS = [
    # Data permissions
    {"code": "data:view", "name": "View Data", "description": "View datasets and records", "category": "data"},
    {"code": "data:import", "name": "Import Data", "description": "Upload and import datasets", "category": "data"},
    {"code": "data:edit", "name": "Edit Data", "description": "Edit dataset records", "category": "data"},
    {"code": "data:delete", "name": "Delete Data", "description": "Delete datasets and records", "category": "data"},
    {"code": "data:export", "name": "Export Data", "description": "Export data to various formats", "category": "data"},
    
    # Organization permissions
    {"code": "org:view", "name": "View Organization", "description": "View organization info", "category": "org"},
    {"code": "org:manage", "name": "Manage Organization", "description": "Manage organization settings", "category": "org"},
    {"code": "org:billing", "name": "Manage Billing", "description": "Manage billing and subscription", "category": "org"},
    
    # User permissions
    {"code": "user:view", "name": "View Users", "description": "View organization users", "category": "user"},
    {"code": "user:invite", "name": "Invite Users", "description": "Invite new users", "category": "user"},
    {"code": "user:manage", "name": "Manage Users", "description": "Edit and remove users", "category": "user"},
    
    # Dashboard permissions
    {"code": "dashboard:view", "name": "View Dashboards", "description": "View dashboards", "category": "dashboard"},
    {"code": "dashboard:create", "name": "Create Dashboards", "description": "Create new dashboards", "category": "dashboard"},
    {"code": "dashboard:edit", "name": "Edit Dashboards", "description": "Edit dashboards", "category": "dashboard"},
    {"code": "dashboard:delete", "name": "Delete Dashboards", "description": "Delete dashboards", "category": "dashboard"},
    
    # Visualization permissions
    {"code": "viz:view", "name": "View Visualizations", "description": "View visualizations", "category": "visualization"},
    {"code": "viz:create", "name": "Create Visualizations", "description": "Create visualizations", "category": "visualization"},
    {"code": "viz:edit", "name": "Edit Visualizations", "description": "Edit visualizations", "category": "visualization"},
    {"code": "viz:delete", "name": "Delete Visualizations", "description": "Delete visualizations", "category": "visualization"},
    
    # AI/Insights permissions
    {"code": "insights:view", "name": "View Insights", "description": "View AI insights", "category": "ai"},
    {"code": "insights:generate", "name": "Generate Insights", "description": "Generate AI insights", "category": "ai"},
    {"code": "data:analyze", "name": "Analyze Data", "description": "Run AI analysis on data", "category": "ai"},
    
    # Webhook permissions
    {"code": "webhook:view", "name": "View Webhooks", "description": "View webhooks", "category": "webhook"},
    {"code": "webhook:manage", "name": "Manage Webhooks", "description": "Create and manage webhooks", "category": "webhook"},
    
    # Role permissions (admin only)
    {"code": "role:view", "name": "View Roles", "description": "View roles", "category": "admin"},
    {"code": "role:manage", "name": "Manage Roles", "description": "Create and manage roles", "category": "admin"},
]

# Define role -> permission mappings
ROLE_PERMISSION_MAPPINGS = {
    "Viewer": [
        "data:view",
        "org:view",
        "user:view",
        "dashboard:view",
        "viz:view",
        "insights:view",
        "webhook:view",
    ],
    "Analyst": [
        "data:view", "data:import", "data:export", "data:analyze",
        "org:view",
        "user:view",
        "dashboard:view", "dashboard:create", "dashboard:edit",
        "viz:view", "viz:create", "viz:edit",
        "insights:view", "insights:generate",
        "webhook:view",
    ],
    "Manager": [
        "data:view", "data:import", "data:edit", "data:export", "data:analyze",
        "org:view", "org:manage",
        "user:view", "user:invite", "user:manage",
        "dashboard:view", "dashboard:create", "dashboard:edit", "dashboard:delete",
        "viz:view", "viz:create", "viz:edit", "viz:delete",
        "insights:view", "insights:generate",
        "webhook:view", "webhook:manage",
    ],
    "Admin": [
        # All permissions
        "data:view", "data:import", "data:edit", "data:delete", "data:export", "data:analyze",
        "org:view", "org:manage", "org:billing",
        "user:view", "user:invite", "user:manage",
        "dashboard:view", "dashboard:create", "dashboard:edit", "dashboard:delete",
        "viz:view", "viz:create", "viz:edit", "viz:delete",
        "insights:view", "insights:generate",
        "webhook:view", "webhook:manage",
        "role:view", "role:manage",
    ]
}


async def init_db(db: AsyncSession) -> None:
    """Initialize database with default permissions, roles, and superuser."""

    # Check if database is already initialized
    result = await db.execute(select(Permission))
    existing_permissions = result.scalars().all()

    if existing_permissions:
        print("Database already initialized, skipping...")
        return

    print("Initializing database...")

    # 1. Create all permissions (these are global, not org-specific)
    created_permissions = {}
    for perm_def in PERMISSION_DEFINITIONS:
        permission = Permission(
            code=perm_def["code"],
            name=perm_def["name"],
            description=perm_def["description"],
            category=perm_def["category"]
        )
        db.add(permission)
        await db.flush()
        created_permissions[perm_def["code"]] = permission
        print(f"Created permission: {perm_def['code']}")

    # 2. Create default organization for superuser
    default_org = Organization(
        name="Datapilot Admin",
        slug="datapilot-admin",
        settings={}
    )
    db.add(default_org)
    await db.flush()

    # 3. Create default roles
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
        
        # Assign permissions to role
        permission_codes = ROLE_PERMISSION_MAPPINGS.get(role_data["name"], [])
        for perm_code in permission_codes:
            if perm_code in created_permissions:
                role.add_permission(created_permissions[perm_code])
        
        created_roles[role_data["name"]] = role
        print(f"Created role: {role.name} with {len(permission_codes)} permissions")

    # 4. Create superuser if configured
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

        # Assign Admin role to superuser
        admin_role = created_roles["Admin"]
        superuser.roles.append(admin_role)

        print(f"Created superuser: {superuser.email} with Admin role")

    await db.commit()
    print("Database initialization complete!")


async def create_default_roles_for_organization(
    db: AsyncSession,
    organization_id: str
) -> dict[str, Role]:
    """Create default roles for a new organization with proper permissions."""

    # Get all permissions from database
    result = await db.execute(select(Permission))
    all_permissions = result.scalars().all()
    permissions_by_code = {p.code: p for p in all_permissions}

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
        
        # Assign permissions to role based on mappings
        permission_codes = ROLE_PERMISSION_MAPPINGS.get(role_data["name"], [])
        for perm_code in permission_codes:
            if perm_code in permissions_by_code:
                role.add_permission(permissions_by_code[perm_code])
        
        created_roles[role_data["name"]] = role

    await db.commit()
    return created_roles
