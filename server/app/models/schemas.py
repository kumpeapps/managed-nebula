"""Pydantic schemas for API request/response models."""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


# ============ Shared/Common Schemas ============

class GroupRef(BaseModel):
    """Reference to a Group for nested responses."""
    id: int
    name: str


class RoleRef(BaseModel):
    """Reference to a Role for nested responses."""
    id: int
    name: str


class UserRef(BaseModel):
    """Reference to a User for nested responses."""
    id: int
    email: str


class UserGroupRef(BaseModel):
    """Reference to a UserGroup for nested responses."""
    id: int
    name: str


# ============ Client Schemas ============

class FirewallRulesetRef(BaseModel):
    id: int
    name: str


class ClientResponse(BaseModel):
    """Response model for Client."""
    id: int
    name: str
    ip_address: str | None
    pool_id: int | None = None  # Current IP pool assignment
    ip_group_id: int | None = None  # Current IP group assignment
    is_lighthouse: bool
    public_ip: str | None
    is_blocked: bool
    created_at: datetime
    config_last_changed_at: datetime | None
    last_config_download_at: datetime | None
    owner: UserRef | None  # Owner of the client
    groups: List[GroupRef]
    firewall_rulesets: List[FirewallRulesetRef] = []
    token: str | None  # Only included for admins or owner

    class Config:
        from_attributes = True


class ClientCreate(BaseModel):
    """Create model for Client."""
    name: str
    is_lighthouse: bool = False
    public_ip: Optional[str] = None
    is_blocked: bool = False
    group_ids: List[int] = []
    firewall_ruleset_ids: List[int] = []
    pool_id: Optional[int] = None
    ip_group_id: Optional[int] = None
    ip_address: Optional[str] = None  # Optional: specify exact IP instead of auto-allocation


class ClientUpdate(BaseModel):
    """Update model for Client."""
    name: Optional[str] = None
    is_lighthouse: Optional[bool] = None
    public_ip: Optional[str] = None
    is_blocked: Optional[bool] = None
    group_ids: Optional[List[int]] = None
    firewall_ruleset_ids: Optional[List[int]] = None  # Changed from firewall_rule_ids
    ip_address: Optional[str] = None  # Change IP address
    pool_id: Optional[int] = None  # Change IP pool
    ip_group_id: Optional[int] = None  # Change IP group


# ============ Group Schemas ============

class GroupCreate(BaseModel):
    """Create model for Group. Supports hierarchical naming with colons (e.g., 'parent:child')."""
    name: str  # Can include colons for hierarchy: "kumpeapps:waf:www"


class GroupUpdate(BaseModel):
    """Update model for Group."""
    name: str | None = None


class GroupResponse(BaseModel):
    """Response model for Group with ownership and hierarchy info."""
    id: int
    name: str
    owner: UserRef | None = None
    created_at: datetime
    client_count: int
    parent_name: str | None = None  # Extracted from hierarchical name (e.g., "parent:child" -> parent="parent")
    is_subgroup: bool = False  # True if name contains colons

    class Config:
        from_attributes = True


class GroupPermissionGrant(BaseModel):
    """Grant permission for a group to a user or user group."""
    user_id: int | None = None
    user_group_id: int | None = None
    can_add_to_client: bool = True
    can_remove_from_client: bool = False
    can_create_subgroup: bool = False


class GroupPermissionResponse(BaseModel):
    """Response model for group permissions."""
    id: int
    group_id: int
    user: UserRef | None = None
    user_group: UserGroupRef | None = None
    can_add_to_client: bool
    can_remove_from_client: bool
    can_create_subgroup: bool

    class Config:
        from_attributes = True


# ============ Firewall Rule Schemas ============

class FirewallRuleCreate(BaseModel):
    """Create model for individual FirewallRule with structured fields."""
    direction: str  # 'inbound' or 'outbound'
    port: str  # 'any', '80', '200-901', 'fragment'
    proto: str  # 'any', 'tcp', 'udp', 'icmp'
    host: Optional[str] = None  # 'any' or hostname
    cidr: Optional[str] = None  # '0.0.0.0/0' or specific CIDR
    local_cidr: Optional[str] = None
    ca_name: Optional[str] = None
    ca_sha: Optional[str] = None
    group_ids: Optional[List[int]] = None  # List of group IDs for this rule


class FirewallRuleUpdate(BaseModel):
    """Update model for FirewallRule."""
    direction: Optional[str] = None
    port: Optional[str] = None
    proto: Optional[str] = None
    host: Optional[str] = None
    cidr: Optional[str] = None
    local_cidr: Optional[str] = None
    ca_name: Optional[str] = None
    ca_sha: Optional[str] = None
    group_ids: Optional[List[int]] = None


class FirewallRuleResponse(BaseModel):
    """Response model for FirewallRule."""
    id: int
    direction: str
    port: str
    proto: str
    host: Optional[str]
    cidr: Optional[str]
    local_cidr: Optional[str]
    ca_name: Optional[str]
    ca_sha: Optional[str]
    groups: List[GroupRef]

    class Config:
        from_attributes = True


# ============ Firewall Ruleset Schemas ============

class FirewallRulesetCreate(BaseModel):
    """Create model for FirewallRuleset with nested rules."""
    name: str
    description: Optional[str] = None
    rules: List[FirewallRuleCreate]


class FirewallRulesetUpdate(BaseModel):
    """Update model for FirewallRuleset."""
    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[List[FirewallRuleCreate]] = None  # Replace all rules


class FirewallRulesetResponse(BaseModel):
    """Response model for FirewallRuleset."""
    id: int
    name: str
    description: Optional[str]
    rules: List[FirewallRuleResponse]
    client_count: int

    class Config:
        from_attributes = True


# ============ IP Pool Schemas ============

class IPPoolCreate(BaseModel):
    """Create model for IPPool."""
    cidr: str
    description: Optional[str] = None


class IPPoolUpdate(BaseModel):
    """Update model for IPPool."""
    cidr: Optional[str] = None
    description: Optional[str] = None


class IPPoolResponse(BaseModel):
    """Response model for IPPool."""
    id: int
    cidr: str
    description: Optional[str]
    allocated_count: int

    class Config:
        from_attributes = True


# ============ IP Group Schemas ============

class IPGroupCreate(BaseModel):
    """Create model for IPGroup."""
    pool_id: int
    name: str
    start_ip: str
    end_ip: str


class IPGroupUpdate(BaseModel):
    """Update model for IPGroup."""
    name: Optional[str] = None
    start_ip: Optional[str] = None
    end_ip: Optional[str] = None


class IPGroupResponse(BaseModel):
    """Response model for IPGroup."""
    id: int
    pool_id: int
    name: str
    start_ip: str
    end_ip: str
    client_count: int = 0

    class Config:
        from_attributes = True


class AvailableIPResponse(BaseModel):
    """Response model for available IP addresses."""
    ip_address: str
    is_available: bool = True


# ============ CA Certificate Schemas ============

class CACreate(BaseModel):
    """Create model for CA Certificate."""
    name: str
    validity_months: int = 18  # Default 18 months per copilot-instructions


class CAImport(BaseModel):
    """Import model for CA Certificate."""
    name: str
    pem_cert: str
    pem_key: Optional[str] = None


class CAResponse(BaseModel):
    """Response model for CA Certificate."""
    id: int
    name: str
    not_before: datetime
    not_after: datetime
    is_active: bool
    is_previous: bool
    can_sign: bool
    include_in_config: bool
    created_at: datetime
    status: str  # "current", "previous", "expired", "inactive"

    class Config:
        from_attributes = True


# ============ User Schemas ============

class UserCreate(BaseModel):
    """Create model for User."""
    email: str
    password: str
    role_name: str = "user"  # Default role
    is_active: bool = True


class UserUpdate(BaseModel):
    """Update model for User."""
    email: Optional[str] = None
    password: Optional[str] = None
    role_name: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Response model for User."""
    id: int
    email: str
    is_active: bool
    role: Optional[RoleRef]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Certificate Schemas ============

class ClientCertificateResponse(BaseModel):
    """Response model for ClientCertificate."""
    id: int
    client_id: int
    not_before: datetime
    not_after: datetime
    created_at: datetime
    fingerprint: str | None
    issued_for_ip_cidr: str | None
    issued_for_groups_hash: str | None
    revoked: bool
    revoked_at: datetime | None

    class Config:
        from_attributes = True


class ClientConfigDownloadResponse(BaseModel):
    """Response model for admin config download."""
    config_yaml: str
    client_cert_pem: str
    ca_chain_pems: List[str]


# ============ Client Agent Schema ============

class ClientConfigRequest(BaseModel):
    """Request model for client config download (used by client agent)."""
    token: str
    public_key: str


# ============ Settings Schemas ============

class SettingsResponse(BaseModel):
    punchy_enabled: bool
    client_docker_image: str
    server_url: str

class SettingsUpdate(BaseModel):
    punchy_enabled: bool | None = None
    client_docker_image: str | None = None
    server_url: str | None = None


# ============ Client Permissions Schemas ============

class ClientPermissionGrant(BaseModel):
    """Grant permission to a user for a client."""
    user_id: int
    can_view: bool = True
    can_update: bool = False
    can_download_config: bool = False
    can_view_token: bool = False
    can_download_docker_config: bool = False


class ClientPermissionResponse(BaseModel):
    """Response model for client permissions."""
    id: int
    user: UserRef
    can_view: bool
    can_update: bool
    can_download_config: bool
    can_view_token: bool
    can_download_docker_config: bool

    class Config:
        from_attributes = True


class ClientOwnerUpdate(BaseModel):
    """Update client owner."""
    owner_user_id: int


# ============ User Group Schemas ============

class UserGroupCreate(BaseModel):
    """Create model for User Group."""
    name: str
    description: str | None = None


class UserGroupUpdate(BaseModel):
    """Update model for User Group."""
    name: str | None = None
    description: str | None = None


class UserGroupResponse(BaseModel):
    """Response model for User Group."""
    id: int
    name: str
    description: str | None
    owner: UserRef | None
    created_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True


class UserGroupMembershipAdd(BaseModel):
    """Add user(s) to a user group."""
    user_ids: List[int]


class UserGroupMembershipResponse(BaseModel):
    """Response model for user group membership."""
    id: int
    user: UserRef | None = None
    user_group: UserGroupRef | None = None
    added_at: datetime

    class Config:
        from_attributes = True
