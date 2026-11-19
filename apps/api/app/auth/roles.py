"""Roles and role enforcement."""

from enum import StrEnum

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.db.models import User


class Role(StrEnum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


def require_role(*roles: Role):
    """Dependency factory: allow only users whose role is in ``roles``."""

    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in {role.value for role in roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient role",
            )
        return user

    return _check


require_instructor = require_role(Role.INSTRUCTOR, Role.ADMIN)
require_admin = require_role(Role.ADMIN)
