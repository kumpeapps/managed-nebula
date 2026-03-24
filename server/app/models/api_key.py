from __future__ import annotations
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, func, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import datetime
from ..db import Base


# Association tables for API key scope restrictions
api_key_groups = Table(
    "api_key_groups",
    Base.metadata,
    Column("api_key_id", Integer, ForeignKey("user_api_keys.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)

api_key_ip_pools = Table(
    "api_key_ip_pools",
    Base.metadata,
    Column("api_key_id", Integer, ForeignKey("user_api_keys.id", ondelete="CASCADE"), primary_key=True),
    Column("ip_pool_id", Integer, ForeignKey("ip_pools.id", ondelete="CASCADE"), primary_key=True),
)


class UserAPIKey(Base):
    """User API key for programmatic access to the API."""
    __tablename__ = "user_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string of permissions (legacy/future use)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='1', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default='0', nullable=False)
    
    # Scope restriction fields
    restrict_to_created_clients: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0', nullable=False)
    parent_key_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("user_api_keys.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    allowed_groups = relationship("Group", secondary=api_key_groups, lazy="selectin")
    allowed_ip_pools = relationship("IPPool", secondary=api_key_ip_pools, lazy="selectin")
    parent_key: Mapped[Optional["UserAPIKey"]] = relationship("UserAPIKey", remote_side=[id], foreign_keys=[parent_key_id])
