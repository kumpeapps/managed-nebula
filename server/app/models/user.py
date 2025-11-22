from __future__ import annotations
from sqlalchemy import String, Integer, Boolean, DateTime, select, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from ..db import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Note: role_id kept for backward compatibility with existing database schema
    # The roles table and this FK should be removed in a future migration after proper cleanup
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    
    async def has_permission(self, session: AsyncSession, resource: str, action: str) -> bool:
        """
        Check if user has a specific permission through their group memberships.
        Returns True if:
        - User belongs to any group with is_admin=True
        - User has the specific permission through any group
        """
        from .permissions import UserGroup, UserGroupMembership
        from sqlalchemy.orm import selectinload
        
        # Get user's groups with their permissions
        result = await session.execute(
            select(UserGroup)
            .join(UserGroupMembership, UserGroupMembership.user_group_id == UserGroup.id)
            .options(selectinload(UserGroup.permissions))
            .where(UserGroupMembership.user_id == self.id)
        )
        groups = result.scalars().all()
        
        # Check if user belongs to any admin group
        for group in groups:
            if group.is_admin:
                return True
        
        # Check if user has the specific permission through any group
        for group in groups:
            for perm in group.permissions:
                if perm.resource == resource and perm.action == action:
                    return True
        
        return False
