from __future__ import annotations
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Table, Column, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from datetime import datetime
from ..db import Base


# Association tables
client_groups = Table(
    "client_groups",
    Base.metadata,
    Column("client_id", Integer, ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)

client_firewall_rulesets = Table(
    "client_firewall_rulesets",
    Base.metadata,
    Column("client_id", Integer, ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
    Column("firewall_ruleset_id", Integer, ForeignKey("firewall_rulesets.id", ondelete="CASCADE"), primary_key=True),
)

ruleset_rules = Table(
    "ruleset_rules",
    Base.metadata,
    Column("ruleset_id", Integer, ForeignKey("firewall_rulesets.id", ondelete="CASCADE"), primary_key=True),
    Column("rule_id", Integer, ForeignKey("firewall_rules.id", ondelete="CASCADE"), primary_key=True),
)

firewall_rule_groups = Table(
    "firewall_rule_groups",
    Base.metadata,
    Column("rule_id", Integer, ForeignKey("firewall_rules.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
)


class Group(Base):
    __tablename__ = "groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)  # Increased for hierarchical names like "parent:child:grandchild"
    owner_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    
    clients = relationship("Client", secondary=client_groups, back_populates="groups", lazy="selectin")
    owner = relationship("User", foreign_keys=[owner_user_id])


class FirewallRule(Base):
    """Individual firewall rule with structured fields matching Nebula firewall config."""
    __tablename__ = "firewall_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    direction: Mapped[str] = mapped_column(String(20))  # 'inbound' or 'outbound'
    port: Mapped[str] = mapped_column(String(100))  # 'any', '80', '200-901', 'fragment'
    proto: Mapped[str] = mapped_column(String(20))  # 'any', 'tcp', 'udp', 'icmp'
    host: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 'any' or hostname
    cidr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # '0.0.0.0/0' or specific CIDR
    local_cidr: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # for unsafe_routes
    ca_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ca_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Many-to-many: a rule can reference multiple groups (AND'd together)
    groups = relationship("Group", secondary=firewall_rule_groups, backref="firewall_rules")
    rulesets = relationship("FirewallRuleset", secondary=ruleset_rules, back_populates="rules")


class FirewallRuleset(Base):
    """Named collection of firewall rules that can be applied to clients."""
    __tablename__ = "firewall_rulesets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    rules = relationship("FirewallRule", secondary=ruleset_rules, back_populates="rulesets")
    clients = relationship("Client", secondary=client_firewall_rulesets, back_populates="firewall_rulesets")


class Client(Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    is_lighthouse: Mapped[bool] = mapped_column(Boolean, default=False)
    public_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    # Ownership
    owner_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # Tracking config lifecycle
    last_config_download_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    config_last_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Blocking state
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Version tracking
    client_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nebula_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_version_report_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    groups = relationship("Group", secondary=client_groups, back_populates="clients", lazy="selectin")
    firewall_rulesets = relationship("FirewallRuleset", secondary=client_firewall_rulesets, back_populates="clients")
    # Note: owner relationship added via selectinload in queries to avoid circular imports


class ClientToken(Base):
    __tablename__ = "client_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    owner_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    client: Mapped[Client] = relationship("Client")


class ClientCertificate(Base):
    __tablename__ = "client_certificates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    pem_cert: Mapped[str] = mapped_column(String(10000))
    # lazy owner relationship
    # from .user import User  # avoid circular import
    # owner: Mapped["User" | None] = relationship("User")
    # Changed to DateTime for proper date arithmetic
    not_before: Mapped[datetime] = mapped_column(DateTime)
    not_after: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=func.now())
    # Metadata for lifecycle and revocation
    fingerprint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    issued_for_ip_cidr: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    issued_for_groups_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    client: Mapped[Client] = relationship("Client")


class IPPool(Base):
    __tablename__ = "ip_pools"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cidr: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class IPGroup(Base):
    __tablename__ = "ip_groups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pool_id: Mapped[int] = mapped_column(Integer, ForeignKey("ip_pools.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    start_ip: Mapped[str] = mapped_column(String(64))
    end_ip: Mapped[str] = mapped_column(String(64))


class IPAssignment(Base):
    __tablename__ = "ip_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    ip_address: Mapped[str] = mapped_column(String(64), unique=True)
    pool_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ip_pools.id"), nullable=True)
    ip_group_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("ip_groups.id"), nullable=True)
