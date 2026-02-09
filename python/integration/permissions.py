"""
Permission decorators for role-based access control.
Supports: admin, viewer, normal, guest
"""

from functools import wraps
from fastapi import HTTPException, Depends
from python.integration.auth import get_current_user

def require_write_permission(current_user: dict = Depends(get_current_user)):
    """
    Dependency that ensures the user has write permissions.
    Viewers can only read, not modify.
    """
    privilege = current_user.get("privilege", "guest")
    
    # Viewers cannot perform write operations
    if privilege == "viewer":
        raise HTTPException(
            status_code=403, 
            detail="Read-only access: Viewers cannot modify data. Contact admin for write permissions."
        )
    
    return current_user

def require_admin(current_user: dict = Depends(get_current_user)):
    """
    Dependency that ensures the user is an admin.
    """
    if current_user.get("privilege") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    return current_user

def get_user_permissions(privilege: str) -> dict:
    """
    Returns a dictionary of permissions for a given privilege level.
    """
    permissions = {
        "admin": {
            "can_read": True,
            "can_write": True,
            "can_delete": True,
            "can_manage_users": True,
            "can_manage_settings": True,
            "can_train_model": True,
            "can_optimize": True,
        },
        "viewer": {
            "can_read": True,
            "can_write": False,
            "can_delete": False,
            "can_manage_users": False,
            "can_manage_settings": False,
            "can_train_model": False,
            "can_optimize": False,  # Viewers can't trigger optimizations
        },
        "normal": {
            "can_read": True,
            "can_write": True,
            "can_delete": False,
            "can_manage_users": False,
            "can_manage_settings": False,
            "can_train_model": False,
            "can_optimize": True,
        },
        "guest": {
            "can_read": True,
            "can_write": False,
            "can_delete": False,
            "can_manage_users": False,
            "can_manage_settings": False,
            "can_train_model": False,
            "can_optimize": False,
        },
    }
    
    return permissions.get(privilege, permissions["guest"])
