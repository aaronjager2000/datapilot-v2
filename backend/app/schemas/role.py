"""
Role Pydantic schemas for API validation.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.permission import PermissionResponse


class RoleBase(BaseModel):
    """Base role schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, max_length=500, description="Role description")
    is_default: bool = Field(default=False, description="Assigned to new users automatically")


class RoleCreate(RoleBase):
    """Schema for creating a role."""
    
    permission_codes: list[str] = Field(
        default_factory=list,
        description="List of permission codes to assign to this role"
    )


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: Optional[bool] = None


class RoleResponse(RoleBase):
    """Schema for role response."""
    
    id: UUID
    organization_id: UUID
    is_system: bool = Field(description="System roles cannot be deleted")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """Schema for role with its permissions."""
    
    permissions: list[PermissionResponse] = Field(default_factory=list)


class RoleListResponse(BaseModel):
    """Schema for list of roles."""
    
    roles: list[RoleResponse]
    total: int


class AssignRoleRequest(BaseModel):
    """Schema for assigning role to user."""
    
    role_id: UUID


class AssignPermissionRequest(BaseModel):
    """Schema for assigning permission to role."""
    
    permission_code: str
