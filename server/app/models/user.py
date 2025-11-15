from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from ..db import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    role: Mapped[Role | None] = relationship("Role")
    
    async def has_permission(self, session: AsyncSession, resource: str, action: str) -> bool:
        """
        Check if user has a specific permission through their group memberships or admin role.
        Returns True if:
        - User has admin role (role.name == 'admin')
        - User belongs to any group with is_admin=True
        - User has the specific permission through any group
        """
        from .permissions import UserGroup, UserGroupMembership, Permission, user_group_permissions
        from sqlalchemy.orm import selectinload
        
        # Check if user has admin role (legacy admin system)
        if self.role and self.role.name == 'admin':
            return True
        
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
