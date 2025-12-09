from enum import Enum

class Permission(str, Enum):
    #user management
    USER_READ = "user.read"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    #organization management
    ORG_READ = "org.read"
    ORG_UPDATE = "org.update"
    ORG_DELETE = "org.delete"
    ORG_SETTINGS = "org.settings"

    #dataset management
    DATASET_READ = "dataset.read"
    DATASET_CREATE = "dataset.create"
    DATASET_UPDATE = "dataset.update"
    DATASET_DELETE = "dataset.delete"
    DATASET_UPLOAD = "dataset.upload"
    DATASET_EXPORT = "dataset.export"

    # Query management
    QUERY_READ = "query.read"
    QUERY_CREATE = "query.create"
    QUERY_UPDATE = "query.update"
    QUERY_DELETE = "query.delete"
    QUERY_EXECUTE = "query.execute"

    # Dashboard management
    DASHBOARD_READ = "dashboard.read"
    DASHBOARD_CREATE = "dashboard.create"
    DASHBOARD_UPDATE = "dashboard.update"
    DASHBOARD_DELETE = "dashboard.delete"

    # Report management
    REPORT_READ = "report.read"
    REPORT_CREATE = "report.create"
    REPORT_UPDATE = "report.update"
    REPORT_DELETE = "report.delete"
    REPORT_EXPORT = "report.export"

    # Role management (admin only)
    ROLE_READ = "role.read"
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"
    ROLE_ASSIGN = "role.assign"

    # AI Insights
    AI_INSIGHTS_READ = "ai.insights.read"
    AI_INSIGHTS_CREATE = "ai.insights.create"

    # Webhooks
    WEBHOOK_READ = "webhook.read"
    WEBHOOK_CREATE = "webhook.create"
    WEBHOOK_UPDATE = "webhook.update"
    WEBHOOK_DELETE = "webhook.delete"
    

    #Billing (admin only)
    BILLING_READ = "billing.read"
    BILLING_UPDATE = "billing.update"

    # Audit logs (admin only)
    AUDIT_READ = "audit.read"


class RolePermissions:
    VIEWER = [
        Permission.USER_READ,
        Permission.ORG_READ,
        Permission.DATASET_READ,
        Permission.QUERY_READ,
        Permission.QUERY_EXECUTE,
        Permission.DASHBOARD_READ,
        Permission.REPORT_READ,
        Permission.AI_INSIGHTS_READ,
    ]
    
    ANALYST = VIEWER + [
        Permission.DATASET_CREATE,
        Permission.DATASET_UPDATE,
        Permission.DATASET_UPLOAD,
        Permission.DATASET_EXPORT,
        Permission.QUERY_CREATE,
        Permission.QUERY_UPDATE,
        Permission.QUERY_DELETE,
        Permission.DASHBOARD_CREATE,
        Permission.DASHBOARD_UPDATE,
        Permission.REPORT_CREATE,
        Permission.REPORT_UPDATE,
        Permission.REPORT_EXPORT,
        Permission.AI_INSIGHTS_CREATE,
    ]
    
    MANAGER = ANALYST + [
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.DATASET_DELETE,
        Permission.DASHBOARD_DELETE,
        Permission.REPORT_DELETE,
        Permission.WEBHOOK_READ,
        Permission.WEBHOOK_CREATE,
        Permission.WEBHOOK_UPDATE,
        Permission.ROLE_READ,
    ]
    
    ADMIN = MANAGER + [
        Permission.USER_DELETE,
        Permission.ORG_UPDATE,
        Permission.ORG_DELETE,
        Permission.ORG_SETTINGS,
        Permission.ROLE_CREATE,
        Permission.ROLE_UPDATE,
        Permission.ROLE_DELETE,
        Permission.ROLE_ASSIGN,
        Permission.WEBHOOK_DELETE,
        Permission.BILLING_READ,
        Permission.BILLING_UPDATE,
        Permission.AUDIT_READ,
    ]

def get_role_permissions(role_name: str) -> list[Permission]:
    role_map = {
        "Viewer": RolePermissions.VIEWER,
        "Analyst": RolePermissions.ANALYST,
        "Manager": RolePermissions.MANAGER,
        "Admin": RolePermissions.ADMIN,
    }
    return role_map.get(role_name, [])


def check_permission(user_permissions: list[str], required_permission: Permission) -> bool:
    return required_permission.value in user_permissions


async def has_permission(user, permission_code: str) -> bool:
    # Superusers bypass all permission checks
    if user.is_superuser:
        return True

    # TODO: Query user's permissions through roles when RBAC is implemented
    # For now, return True as placeholder
    return True

