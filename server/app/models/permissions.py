from sqlalchemy import Integer, Boolean, ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from ..db import Base


class UserGroup(Base):
    """User groups for collective access management."""
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", foreign_keys=[owner_user_id])


class UserGroupMembership(Base):
    """Maps users to user groups - users can belong to multiple user groups."""
    __tablename__ = "user_group_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    user_group_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_groups.id", ondelete="CASCADE"))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    user_group = relationship("UserGroup")


class GroupPermission(Base):
    """Permissions for Nebula groups - who can add/remove groups to/from clients and create subgroups."""
    __tablename__ = "group_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    user_group_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("user_groups.id", ondelete="CASCADE"), nullable=True)
    can_add_to_client: Mapped[bool] = mapped_column(Boolean, default=True)
    can_remove_from_client: Mapped[bool] = mapped_column(Boolean, default=False)
    can_create_subgroup: Mapped[bool] = mapped_column(Boolean, default=False)

    group = relationship("Group")
    user = relationship("User")
    user_group = relationship("UserGroup")


class ClientPermission(Base):
    """Per-client permissions for users (view, update, download config, view token, download docker config)."""
    __tablename__ = "client_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    can_view: Mapped[bool] = mapped_column(Boolean, default=True)
    can_update: Mapped[bool] = mapped_column(Boolean, default=False)
    can_download_config: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_token: Mapped[bool] = mapped_column(Boolean, default=False)
    can_download_docker_config: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User")
    # client relationship skipped to avoid circular import


# Legacy alias for backwards compatibility
ClientAccess = ClientPermission


# Note: Old UserGroupAssignment table removed - replaced by UserGroupMembership above for user groups
