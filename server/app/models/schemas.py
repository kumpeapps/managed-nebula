"""Pydantic schemas for API request/response models."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import List, Optional


# ============ Shared/Common Schemas ============

class GroupRef(BaseModel):
    """Reference to a Group for nested responses."""
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


class SecurityAdvisoryInfo(BaseModel):
    """Security advisory information."""
    id: str
    severity: str
    summary: str
    affected_versions: str
    patched_version: Optional[str] = None
    published_at: str
    url: str
    cve_id: Optional[str] = None


class VersionStatus(BaseModel):
    """Version status information for a client."""
    client_version_status: str  # current, outdated, vulnerable, unknown
    nebula_version_status: str  # current, outdated, vulnerable, unknown
    client_advisories: List[SecurityAdvisoryInfo] = Field(default_factory=list)
    nebula_advisories: List[SecurityAdvisoryInfo] = Field(default_factory=list)
    days_behind: Optional[int] = None
    latest_client_version: Optional[str] = None
    latest_nebula_version: Optional[str] = None
    current_client_version: Optional[str] = None
    current_nebula_version: Optional[str] = None


class ClientResponse(BaseModel):
    """Response model for Client."""
    id: int
    name: str
    ip_address: Optional[str]  # Primary IP for backwards compatibility
    pool_id: Optional[int] = None  # Current IP pool assignment
    ip_group_id: Optional[int] = None  # Current IP group assignment
    is_lighthouse: bool
    public_ip: Optional[str]
    is_blocked: bool
    created_at: datetime
    config_last_changed_at: Optional[datetime]
    last_config_download_at: Optional[datetime]
    client_version: Optional[str] = None
    nebula_version: Optional[str] = None
    last_version_report_at: Optional[datetime] = None
    os_type: str = "docker"  # docker, windows, macos
    ip_version: str = "ipv4_only"  # ipv4_only, ipv6_only, dual_stack, multi_ipv4, multi_ipv6, multi_both
    owner: Optional[UserRef]  # Owner of the client
    groups: List[GroupRef]
    firewall_rulesets: List[FirewallRulesetRef] = Field(default_factory=list)
    token: Optional[str]  # Only included for admins or owner
    version_status: Optional[VersionStatus] = None  # Optional computed field
    assigned_ips: List[IPAssignmentResponse] = Field(default_factory=list)  # All assigned IPs (for v2 cert support)
    primary_ipv4: Optional[str] = None  # Extracted from assigned_ips where is_primary=true

    model_config = ConfigDict(from_attributes=True)


class ClientCreate(BaseModel):
    """Create model for Client."""
    name: str
    is_lighthouse: bool = False
    public_ip: Optional[str] = None
    is_blocked: bool = False
    group_ids: List[int] = Field(default_factory=list)
    firewall_ruleset_ids: List[int] = Field(default_factory=list)
    pool_id: Optional[int] = None
    ip_group_id: Optional[int] = None
    ip_address: Optional[str] = None  # Optional: specify exact IP instead of auto-allocation
    os_type: str = "docker"  # docker, windows, macos
    ip_version: str = "ipv4_only"  # ipv4_only, ipv6_only, dual_stack, multi_ipv4, multi_ipv6, multi_both


class ClientUpdate(BaseModel):
    """Update model for Client."""
    name: Optional[str] = None
    is_lighthouse: Optional[bool] = None
    public_ip: Optional[str] = None
    is_blocked: Optional[bool] = None
    os_type: Optional[str] = None  # docker, windows, macos
    ip_version: Optional[str] = None  # ipv4_only, ipv6_only, dual_stack, multi_ipv4, multi_ipv6, multi_both
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
    name: Optional[str] = None


class GroupResponse(BaseModel):
    """Response model for Group with ownership and hierarchy info."""
    id: int
    name: str
    owner: Optional[UserRef] = None
    created_at: datetime
    client_count: int
    parent_name: Optional[str] = None  # Extracted from hierarchical name (e.g., "parent:child" -> parent="parent")
    is_subgroup: bool = False  # True if name contains colons

    model_config = ConfigDict(from_attributes=True)


class GroupPermissionGrant(BaseModel):
    """Grant permission for a group to a user or user group."""
    user_id: Optional[int] = None
    user_group_id: Optional[int] = None
    can_add_to_client: bool = True
    can_remove_from_client: bool = False
    can_create_subgroup: bool = False


class GroupPermissionResponse(BaseModel):
    """Response model for group permissions."""
    id: int
    group_id: int
    user: Optional[UserRef] = None
    user_group: Optional[UserGroupRef] = None
    can_add_to_client: bool
    can_remove_from_client: bool
    can_create_subgroup: bool

    model_config = ConfigDict(from_attributes=True)


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

    @field_validator('group_ids', mode='after')
    @classmethod
    def validate_targeting_fields(cls, v: Optional[List[int]], info) -> Optional[List[int]]:
        """Ensure at least one targeting field is provided."""
        values = info.data
        has_target = (
            values.get('host') or
            values.get('cidr') or
            values.get('local_cidr') or
            values.get('ca_name') or
            values.get('ca_sha') or
            (v and len(v) > 0)
        )
        if not has_target:
            raise ValueError(
                'At least one of host, cidr, local_cidr, ca_name, ca_sha, or group_ids must be provided'
            )
        return v


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
    groups: Optional[List[GroupRef]] = None

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class AvailableIPResponse(BaseModel):
    """Response model for available IP addresses."""
    ip_address: str
    is_available: bool = True


class IPAssignmentResponse(BaseModel):
    """Response model for IP assignments (supports multiple IPs per client for v2 certs)."""
    id: int
    ip_address: str
    ip_version: str  # ipv4 or ipv6
    is_primary: bool  # True if this is the primary IPv4 address
    pool_id: Optional[int] = None
    ip_group_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AlternateIPAdd(BaseModel):
    """Request model for adding an alternate IP to a client."""
    ip_address: str
    ip_version: str = "ipv4"  # ipv4 or ipv6
    pool_id: Optional[int] = None
    ip_group_id: Optional[int] = None


# ============ CA Certificate Schemas ============

class CACreate(BaseModel):
    """Create model for CA Certificate."""
    name: str
    validity_months: int = 18  # Default 18 months per copilot-instructions
    cert_version: str = "v1"  # v1 or v2 (v2 requires Nebula 1.10.0+)


class CAImport(BaseModel):
    """Import model for CA Certificate."""
    name: str
    pem_cert: str
    pem_key: Optional[str] = None
    cert_version: str = "v1"  # v1 or v2


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
    cert_version: str  # v1 or v2
    nebula_version: Optional[str] = None  # Version of Nebula used to create CA

    model_config = ConfigDict(from_attributes=True)


# ============ Nebula Version Schemas ============

class NebulaVersionInfoResponse(BaseModel):
    """Response model for Nebula version information."""
    version: str
    release_date: datetime
    is_stable: bool
    supports_v2: bool
    download_url_linux_amd64: Optional[str] = None
    download_url_linux_arm64: Optional[str] = None
    download_url_darwin_amd64: Optional[str] = None
    download_url_darwin_arm64: Optional[str] = None
    download_url_windows_amd64: Optional[str] = None
    checksum: Optional[str] = None


class NebulaVersionsResponse(BaseModel):
    """Response model for list of available Nebula versions."""
    current_version: str  # Version currently configured in system settings
    available_versions: List[NebulaVersionInfoResponse]
    latest_stable: str  # Latest stable version available
    versions: List[NebulaVersionInfoResponse]  # Alias for available_versions (for frontend compatibility)


class VersionCacheResponse(BaseModel):
    """Response model for version cache status."""
    last_checked: Optional[datetime] = None
    latest_client_version: Optional[str] = None
    latest_nebula_version: Optional[str] = None
    cache_age_hours: Optional[float] = None


class NebulaInstallationStatusResponse(BaseModel):
    """Response model for Nebula installation status."""
    installed_version: Optional[str] = None
    configured_version: str
    is_up_to_date: bool
    message: str


class NebulaInstallationResponse(BaseModel):
    """Response model for Nebula installation operation."""
    success: bool
    message: str
    installed_version: Optional[str] = None
    previous_version: Optional[str] = None


# ============ User Schemas ============

class UserCreate(BaseModel):
    """Create model for User."""
    email: str
    password: str
    is_active: bool = True
    user_group_ids: List[int] = Field(default_factory=list)  # Assign to these user groups at creation


class UserUpdate(BaseModel):
    """Update model for User."""
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    user_group_ids: Optional[List[int]] = None  # Replace memberships with these IDs


class UserResponse(BaseModel):
    """Response model for User."""
    id: int
    email: str
    is_active: bool
    groups: List[UserGroupRef] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Certificate Schemas ============

class ClientCertificateResponse(BaseModel):
    """Response model for ClientCertificate."""
    id: int
    client_id: int
    not_before: datetime
    not_after: datetime
    created_at: datetime
    fingerprint: Optional[str]
    issued_for_ip_cidr: Optional[str]
    issued_for_groups_hash: Optional[str]
    revoked: bool
    revoked_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


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
    client_version: Optional[str] = None
    nebula_version: Optional[str] = None
    os_type: Optional[str] = "docker"  # docker, windows, macos


# ============ Settings Schemas ============

class SettingsResponse(BaseModel):
    punchy_enabled: bool
    client_docker_image: str
    server_url: str
    docker_compose_template: str
    externally_managed_users: bool
    cert_version: str = "v1"  # v1, v2, or hybrid
    nebula_version: str = "1.10.3"  # Nebula binary version
    v2_support_available: bool = False  # Computed: True if nebula_version >= 1.10.0

class SettingsUpdate(BaseModel):
    punchy_enabled: Optional[bool] = None
    client_docker_image: Optional[str] = None
    server_url: Optional[str] = None
    docker_compose_template: Optional[str] = None
    cert_version: Optional[str] = None  # v1, v2, or hybrid
    nebula_version: Optional[str] = None  # Nebula binary version
    auto_install_nebula: Optional[bool] = True  # Auto-install Nebula when version changes


class DockerComposeTemplateResponse(BaseModel):
    """Response model for docker-compose template."""
    template: str


class DockerComposeTemplateUpdate(BaseModel):
    """Update model for docker-compose template."""
    template: str


class PlaceholderInfo(BaseModel):
    """Information about a placeholder."""
    name: str
    description: str
    example: str


class PlaceholdersResponse(BaseModel):
    """Response model listing all available placeholders."""
    placeholders: List[PlaceholderInfo]


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

    model_config = ConfigDict(from_attributes=True)


class ClientOwnerUpdate(BaseModel):
    """Update client owner."""
    owner_user_id: int


# ============ User Group Schemas ============

# ============ Permission Schemas ============

class PermissionResponse(BaseModel):
    """Response model for Permission."""
    id: int
    resource: str
    action: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ============ User Group Schemas ============

class UserGroupCreate(BaseModel):
    """Create model for User Group."""
    name: str
    description: Optional[str] = None
    is_admin: bool = False


class UserGroupUpdate(BaseModel):
    """Update model for User Group."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_admin: Optional[bool] = None


class UserGroupResponse(BaseModel):
    """Response model for User Group."""
    id: int
    name: str
    description: Optional[str]
    is_admin: bool
    owner: Optional[UserRef]
    created_at: datetime
    updated_at: Optional[datetime] = None
    member_count: int = 0
    permission_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class UserGroupMembershipAdd(BaseModel):
    """Add user(s) to a user group."""
    user_ids: List[int]


class UserGroupMembershipResponse(BaseModel):
    """Response model for user group membership."""
    id: int
    user: Optional[UserRef] = None
    user_group: Optional[UserGroupRef] = None
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionGrantRequest(BaseModel):
    """Request to grant permission to a group."""
    permission_id: Optional[int] = None
    resource: Optional[str] = None
    action: Optional[str] = None

    # At least one method must be provided
    def validate_grant(self):
        if not self.permission_id and not (self.resource and self.action):
            raise ValueError("Either permission_id or both resource and action must be provided")


# ============ Token Re-issuance Schemas ============

class ClientTokenReissueResponse(BaseModel):
    """Response when re-issuing a client token."""
    id: int
    token: str  # Full token (only shown once)
    client_id: int
    created_at: datetime
    old_token_id: int  # Reference to deactivated token
    
    model_config = ConfigDict(from_attributes=True)


# ============ System Settings Schemas ============

class SystemSettingResponse(BaseModel):
    """System setting response."""
    key: str
    value: str
    updated_at: datetime
    updated_by: Optional[str] = None  # Username
    
    model_config = ConfigDict(from_attributes=True)


class TokenPrefixUpdate(BaseModel):
    """Request to update token prefix."""
    prefix: str
    
    @field_validator('prefix')
    @classmethod
    def validate_prefix(cls, v: str) -> str:
        if not v or not (3 <= len(v) <= 20):
            raise ValueError("Prefix must be 3-20 characters")
        if not all(c.isalnum() or c == '_' for c in v):
            raise ValueError("Prefix must be alphanumeric with underscores only")
        return v


class GitHubWebhookSecretUpdate(BaseModel):
    """Request to update GitHub webhook secret."""
    secret: str
    
    @field_validator('secret')
    @classmethod
    def validate_secret(cls, v: str) -> str:
        if not v or len(v) < 16:
            raise ValueError("Webhook secret must be at least 16 characters")
        return v


# ============ GitHub Secret Scanning Schemas ============

class GitHubSecretScanningPattern(BaseModel):
    """GitHub secret scanning pattern metadata."""
    type: str
    pattern: str
    description: str


class GitHubSecretVerificationRequest(BaseModel):
    """GitHub secret scanning verification request."""
    type: str
    token: str
    url: str


class GitHubSecretVerificationResponse(BaseModel):
    """GitHub secret scanning verification response."""
    token: str
    type: str
    label: Optional[str] = None
    url: Optional[str] = None
    is_active: bool


class GitHubSecretRevocationRequest(BaseModel):
    """GitHub secret scanning revocation request."""
    type: str
    token: str
    url: str


class GitHubSecretRevocationResponse(BaseModel):
    """GitHub secret scanning revocation response."""
    message: str
    revoked_count: int


# ============ Version Schemas ============

class VersionResponse(BaseModel):
    """Response model for version information."""
    managed_nebula_version: str
    nebula_version: str


class VersionStatusResponse(BaseModel):
    """Response model for version status check."""
    latest_client_version: Optional[str] = None
    latest_nebula_version: Optional[str] = None
    client_advisories: List[SecurityAdvisoryInfo] = Field(default_factory=list)
    nebula_advisories: List[SecurityAdvisoryInfo] = Field(default_factory=list)
    last_checked: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
