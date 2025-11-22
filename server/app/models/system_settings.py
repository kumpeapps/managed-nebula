"""System settings and GitHub secret scanning audit models."""
from __future__ import annotations
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import datetime
from ..db import Base


class SystemSettings(Base):
    """Global system settings stored as key-value pairs."""
    __tablename__ = "system_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationship to User (avoid circular import in type hint)
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])


class GitHubSecretScanningLog(Base):
    """Audit log for GitHub secret scanning events."""
    __tablename__ = "github_secret_scanning_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # 'verify' or 'revoke'
    token_preview: Mapped[str] = mapped_column(String(12), nullable=False)  # First 12 chars only for security
    github_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    client_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationship to Client
    client = relationship("Client", foreign_keys=[client_id])
