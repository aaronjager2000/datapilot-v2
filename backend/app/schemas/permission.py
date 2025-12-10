"""
Permission Pydantic schemas for API validation.
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class PermissionBase(BaseModel):
    """Base permission schema with common fields."""
    
    code: str = Field(..., description="Permission code (e.g., 'data:import')")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="What this permission allows")
    category: str = Field(..., description="Category: data, org, dashboard, user, billing")


class PermissionCreate(PermissionBase):
    """Schema for creating a permission (admin only)."""
    pass


class PermissionUpdate(BaseModel):
    """Schema for updating a permission."""
    
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class PermissionResponse(PermissionBase):
    """Schema for permission response."""
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PermissionListResponse(BaseModel):
    """Schema for list of permissions."""
    
    permissions: list[PermissionResponse]
    total: int
