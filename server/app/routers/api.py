from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

from ..db import get_session
from ..models import ClientToken, Client, IPAssignment, GlobalSettings, CACertificate, IPPool, Permission
from ..models.client import ClientCertificate, IPGroup
from ..models.system_settings import SystemSettings, GitHubSecretScanningLog
logger = logging.getLogger(__name__)

from ..models.schemas import (
    ClientConfigRequest,
    GroupRef,
    ClientResponse,
    ClientUpdate,
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupPermissionGrant,
    GroupPermissionResponse,
    FirewallRuleCreate,
    FirewallRuleUpdate,
    FirewallRuleResponse,
    FirewallRulesetCreate,
    FirewallRulesetUpdate,
    FirewallRulesetResponse,
    FirewallRulesetRef,
    IPPoolCreate,
    IPPoolUpdate,
    IPPoolResponse,
    IPGroupCreate,
    IPGroupUpdate,
    IPGroupResponse,
    AvailableIPResponse,
    IPAssignmentResponse,
    AlternateIPAdd,
    CACreate,
    CAImport,
    CAResponse,
    UserRef,
    UserGroupRef,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserGroupCreate,
    UserGroupUpdate,
    UserGroupResponse,
    UserGroupMembershipAdd,
    VersionResponse,
    VersionStatusResponse,
    VersionStatus,
    SecurityAdvisoryInfo,
    UserGroupMembershipResponse,
    ClientCertificateResponse,
    ClientConfigDownloadResponse,
    SettingsResponse,
    SettingsUpdate,
    DockerComposeTemplateResponse,
    DockerComposeTemplateUpdate,
    PlaceholderInfo,
    PlaceholdersResponse,
    NebulaVersionInfoResponse,
    NebulaVersionsResponse,
    VersionCacheResponse,
    ClientCreate,
    ClientPermissionGrant,
    ClientPermissionResponse,
    ClientOwnerUpdate,
    PermissionResponse,
    PermissionGrantRequest,
    ClientTokenReissueResponse,
    SystemSettingResponse,
    TokenPrefixUpdate,
    GitHubWebhookSecretUpdate,
    GitHubSecretScanningPattern,
    GitHubSecretVerificationRequest,
    GitHubSecretVerificationResponse,
    GitHubSecretRevocationRequest,
    GitHubSecretRevocationResponse,
)
from ..services.cert_manager import CertManager
from ..services.config_builder import build_nebula_config
from ..services.ip_allocator import ensure_default_pool, allocate_ip_from_pool
from ..services.token_manager import generate_client_token, get_token_prefix, get_token_preview
from ..core.auth import require_permission, get_current_user
from ..core.config import settings
from ..core.github_verification import verify_github_signature
from ..models.user import User
from ..models.client import Group, FirewallRule, IPGroup, client_groups, client_firewall_rulesets
from ..models.permissions import ClientPermission, UserGroup, UserGroupMembership
from typing import List, Optional
import secrets
import yaml
import ipaddress


router = APIRouter(prefix="/v1", tags=["api"])


# ============ Helper Functions ============

async def build_client_response(client: Client, session: AsyncSession, user: User, include_token: bool = False) -> ClientResponse:
    """Build ClientResponse with owner, IP, groups, rulesets, and optional token."""
    from sqlalchemy.orm import selectinload

    # Get client token if requested
    token_value = None
    if include_token:
        is_admin = await user.has_permission(session, "users", "delete")
        is_owner = client.owner_user_id == user.id
        can_view_token = False

        # Check if user has can_view_token permission
        if not is_admin and not is_owner:
            perm_result = await session.execute(
                select(ClientPermission).where(
                    ClientPermission.client_id == client.id,
                    ClientPermission.user_id == user.id,
                    ClientPermission.can_view_token == True
                )
            )
            perm = perm_result.scalar_one_or_none()
            can_view_token = perm is not None

        if is_admin or is_owner or can_view_token:
            token_result = await session.execute(
                select(ClientToken).where(ClientToken.client_id ==
                                          client.id, ClientToken.is_active == True)
            )
            token_obj = token_result.scalar_one_or_none()
            token_value = token_obj.token if token_obj else None

    # Get all IP assignments (supports multiple IPs for v2 certs)
    ip_result = await session.execute(
        select(IPAssignment).where(IPAssignment.client_id == client.id).order_by(IPAssignment.is_primary.desc())
    )
    ip_assignments = ip_result.scalars().all()
    
    # Build IP assignment responses
    assigned_ips_list = [
        IPAssignmentResponse(
            id=ip.id,
            ip_address=ip.ip_address,
            ip_version=ip.ip_version,
            is_primary=ip.is_primary,
            pool_id=ip.pool_id,
            ip_group_id=ip.ip_group_id
        )
        for ip in ip_assignments
    ]
    
    # Extract primary IPv4 for backwards compatibility
    primary_ipv4 = None
    primary_ip_obj = next((ip for ip in ip_assignments if ip.is_primary and ip.ip_version == "ipv4"), None)
    if primary_ip_obj:
        primary_ipv4 = primary_ip_obj.ip_address
    elif ip_assignments:
        # Fallback to first IPv4 if no primary marked
        first_ipv4 = next((ip for ip in ip_assignments if ip.ip_version == "ipv4"), None)
        if first_ipv4:
            primary_ipv4 = first_ipv4.ip_address

    # Get owner info
    owner_ref = None
    if client.owner_user_id:
        owner_result = await session.execute(
            select(User).where(User.id == client.owner_user_id)
        )
        owner = owner_result.scalar_one_or_none()
        if owner:
            owner_ref = UserRef(id=owner.id, email=owner.email)

    # Compute version status if versions are available (using cache)
    version_status = None
    if client.client_version or client.nebula_version:
        from ..services.advisory_checker import check_client_version_status_cached
        
        try:
            status_dict = await check_client_version_status_cached(
                session,
                client.client_version,
                client.nebula_version
            )
            if status_dict:
                version_status = VersionStatus(**status_dict)
        except Exception as e:
            logger.warning(f"Failed to compute version status for client {client.id}: {e}")

    return ClientResponse(
        id=client.id,
        name=client.name,
        ip_address=primary_ipv4,  # Backwards compatibility - use primary IPv4
        pool_id=ip_assignments[0].pool_id if ip_assignments else None,
        ip_group_id=ip_assignments[0].ip_group_id if ip_assignments else None,
        ip_version=client.ip_version,
        assigned_ips=assigned_ips_list,
        primary_ipv4=primary_ipv4,
        is_lighthouse=client.is_lighthouse,
        public_ip=client.public_ip,
        is_blocked=client.is_blocked,
        created_at=client.created_at,
        config_last_changed_at=client.config_last_changed_at,
        last_config_download_at=client.last_config_download_at,
        client_version=client.client_version,
        nebula_version=client.nebula_version,
        last_version_report_at=client.last_version_report_at,
        owner=owner_ref,
        groups=[GroupRef(id=g.id, name=g.name) for g in client.groups],
        firewall_rulesets=[FirewallRulesetRef(
            id=rs.id, name=rs.name) for rs in client.firewall_rulesets],
        token=token_value,
        version_status=version_status
    )


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/warnings")
async def get_warnings(
    session: AsyncSession = Depends(get_session),
):
    """Get system-wide warnings for display in UI banner.
    
    Checks for configuration mismatches that require user attention,
    such as v1 clients when server is configured for v2/hybrid mode.
    """
    warnings = []
    
    # Check for v1 clients when server is in v2/hybrid mode
    settings = (await session.execute(select(GlobalSettings))).scalars().first()
    if settings and settings.cert_version in ['v2', 'hybrid']:
        # Find clients with Nebula version < 1.10.0 or unknown
        clients = (await session.execute(
            select(Client).options(selectinload(Client.groups))
        )).scalars().all()
        
        incompatible_clients = []
        for client in clients:
            version = getattr(client, 'nebula_version', None)
            supports_v2 = False
            if version:
                try:
                    version_str = version.lstrip('v')
                    parts = version_str.split('.')
                    if len(parts) >= 2:
                        major = int(parts[0])
                        minor = int(parts[1])
                        supports_v2 = (major > 1) or (major == 1 and minor >= 10)
                except (ValueError, AttributeError):
                    pass
            
            if not supports_v2:
                incompatible_clients.append({
                    'id': client.id,
                    'name': client.name,
                    'version': version or 'unknown'
                })
        
        if incompatible_clients:
            client_list = ', '.join([f"{c['name']} ({c['version']})" for c in incompatible_clients[:5]])
            if len(incompatible_clients) > 5:
                client_list += f" and {len(incompatible_clients) - 5} more"
            
            warnings.append({
                'severity': 'warning',
                'message': f"Server is configured for {settings.cert_version} certificates but {len(incompatible_clients)} "
                          f"client(s) have Nebula < 1.10.0: {client_list}. "
                          f"V2 certificates require Nebula 1.10.0+. Please upgrade clients or change server to v1 mode.",
                'type': 'version_mismatch',
                'count': len(incompatible_clients),
                'clients': incompatible_clients
            })
    
    return {'warnings': warnings}


@router.get("/version", response_model=VersionResponse)
async def get_version():
    """Get server and Nebula versions.
    
    Returns version information for both the Managed Nebula server
    and the installed Nebula binary.
    """
    import asyncio
    from .. import __version__ as server_version
    
    # Get Nebula version
    nebula_version = "unknown"
    try:
        # Run subprocess asynchronously to avoid blocking the event loop
        process = await asyncio.create_subprocess_exec(
            "nebula", "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=5.0
        )
        
        if process.returncode == 0:
            # Parse version from output like "Version: 1.9.7"
            output = stdout.decode('utf-8')
            for line in output.split("\n"):
                if line.startswith("Version:"):
                    nebula_version = line.replace("Version:", "").strip()
                    break
        else:
            nebula_version = "error"
    except asyncio.TimeoutError:
        logger.warning("Timeout getting Nebula version")
        nebula_version = "timeout"
    except FileNotFoundError:
        logger.warning("Nebula binary not found")
        nebula_version = "not_installed"
    except Exception as e:
        logger.warning(f"Failed to get Nebula version: {e}")
        nebula_version = "unavailable"
    
    return VersionResponse(
        managed_nebula_version=server_version,
        nebula_version=nebula_version
    )


@router.get("/version-status", response_model=VersionStatusResponse)
async def get_version_status(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Get version status with latest releases and security advisories.
    
    This endpoint returns information about the latest versions available
    for both managed-nebula and Nebula, as well as any active security
    advisories. Results are cached to avoid excessive GitHub API calls.
    
    Returns:
        VersionStatusResponse: Latest version information and advisories
    """
    from ..services.github_api import get_github_client
    
    # Get GitHub token from system settings if available
    github_token = None
    try:
        github_token_setting = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "github_api_token")
        )
        token_row = github_token_setting.scalar_one_or_none()
        if token_row:
            github_token = token_row.value
    except Exception as e:
        logger.debug(f"Could not fetch GitHub token from settings: {e}")
    
    github_client = get_github_client(token=github_token)
    
    # Get latest releases
    latest_client_release = await github_client.get_latest_release("kumpeapps", "managed-nebula")
    latest_nebula_release = await github_client.get_latest_release("slackhq", "nebula")
    
    # Get security advisories
    client_advisories_raw = await github_client.get_security_advisories("kumpeapps", "managed-nebula")
    nebula_advisories_raw = await github_client.get_security_advisories("slackhq", "nebula")
    
    # Convert to schema format
    def convert_advisory(adv: dict) -> SecurityAdvisoryInfo:
        vulnerabilities = adv.get("vulnerabilities", [])
        affected_versions = "unknown"
        patched_version = None
        
        if vulnerabilities:
            vuln = vulnerabilities[0]
            affected_range = vuln.get("vulnerable_version_range", "")
            if affected_range:
                affected_versions = affected_range
            
            patched = vuln.get("patched_versions", "")
            if patched:
                patched_version = patched
        
        severity_str = adv.get("severity", "unknown").lower()
        
        return SecurityAdvisoryInfo(
            id=adv.get("ghsa_id", adv.get("id", "unknown")),
            severity=severity_str,
            summary=adv.get("summary", "No summary available"),
            affected_versions=affected_versions,
            patched_version=patched_version,
            published_at=adv.get("published_at", ""),
            url=adv.get("html_url", ""),
            cve_id=adv.get("cve_id")
        )
    
    client_advisories = [convert_advisory(a) for a in client_advisories_raw]
    nebula_advisories = [convert_advisory(a) for a in nebula_advisories_raw]
    
    return VersionStatusResponse(
        latest_client_version=latest_client_release.version if latest_client_release else None,
        latest_nebula_version=latest_nebula_release.version if latest_nebula_release else None,
        client_advisories=client_advisories,
        nebula_advisories=nebula_advisories,
        last_checked=datetime.utcnow()
    )


# ============ Settings ============

def _is_v2_compatible(nebula_version: str) -> bool:
    """Check if Nebula version supports v2 certificates (1.10.0+)."""
    if nebula_version.startswith('nightly'):
        return True
    try:
        from ..services.version_parser import compare_versions
        return compare_versions(nebula_version, '1.10.0') >= 0
    except Exception as e:
        # Fallback: assume not compatible if parsing fails
        logger.warning(f"Failed to parse version {nebula_version}: {e}")
        return False


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    row = (await session.execute(select(GlobalSettings))).scalars().first()
    if not row:
        # Create defaults if missing
        row = GlobalSettings()
        session.add(row)
        await session.commit()
        await session.refresh(row)
    
    # Check if v2 support is available based on nebula_version
    nebula_ver = getattr(row, 'nebula_version', '1.9.7')
    v2_available = _is_v2_compatible(nebula_ver)
    
    return SettingsResponse(
        punchy_enabled=row.punchy_enabled,
        client_docker_image=row.client_docker_image,
        server_url=row.server_url,
        docker_compose_template=row.docker_compose_template,
        externally_managed_users=settings.externally_managed_users,
        cert_version=getattr(row, 'cert_version', 'v1'),
        nebula_version=nebula_ver,
        v2_support_available=v2_available
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("settings", "update"))):
    row = (await session.execute(select(GlobalSettings))).scalars().first()
    if not row:
        row = GlobalSettings()
        session.add(row)
    if body.punchy_enabled is not None:
        row.punchy_enabled = body.punchy_enabled
    if body.client_docker_image is not None:
        row.client_docker_image = body.client_docker_image
    if body.server_url is not None:
        row.server_url = body.server_url
    if body.docker_compose_template is not None:
        # Validate YAML by replacing placeholders with dummy values
        try:
            # Replace common placeholders with dummy values for validation
            validation_template = body.docker_compose_template
            validation_template = validation_template.replace(
                "{{CLIENT_NAME}}", "test-client")
            validation_template = validation_template.replace(
                "{{CLIENT_TOKEN}}", "dummy-token")
            validation_template = validation_template.replace(
                "{{SERVER_URL}}", "http://localhost:8080")
            validation_template = validation_template.replace(
                "{{CLIENT_DOCKER_IMAGE}}", "test-image:latest")
            validation_template = validation_template.replace(
                "{{POLL_INTERVAL_HOURS}}", "24")

            yaml.safe_load(validation_template)
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=400, detail=f"Invalid YAML: {str(e)}"
            ) from e
        row.docker_compose_template = body.docker_compose_template
    
    # Update nebula_version if provided
    if body.nebula_version is not None:
        row.nebula_version = body.nebula_version
    
    # Update cert_version if provided, with validation
    if body.cert_version is not None:
        # Validate that v2/hybrid requires compatible Nebula version on server
        if body.cert_version in ['v2', 'hybrid']:
            current_nebula_version = body.nebula_version if body.nebula_version is not None else getattr(row, 'nebula_version', '1.9.7')
            if not _is_v2_compatible(current_nebula_version):
                raise HTTPException(
                    status_code=400,
                    detail=f"Certificate version '{body.cert_version}' requires Nebula 1.10.0+ or nightly build on server. Current server version: {current_nebula_version}"
                )
        
        # Additional check: if switching to pure v2 (not hybrid), verify all clients are compatible
        if body.cert_version == 'v2':
            # Query all clients with their nebula_version
            from ..models.db import Client
            incompatible_clients = []
            result = await session.execute(select(Client))
            clients = result.scalars().all()
            
            for client in clients:
                client_nebula_ver = getattr(client, 'nebula_version', None)
                if client_nebula_ver and not _is_v2_compatible(client_nebula_ver):
                    incompatible_clients.append(f"{client.name} (v{client_nebula_ver})")
            
            if incompatible_clients:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot switch to pure v2 certificates. The following clients are not compatible with v2 (require Nebula 1.10.0+): {', '.join(incompatible_clients)}. Use 'hybrid' mode to support mixed client versions."
                )
        
        row.cert_version = body.cert_version
    
    await session.commit()
    await session.refresh(row)
    
    # Compute v2 support availability
    nebula_ver = getattr(row, 'nebula_version', '1.9.7')
    v2_available = _is_v2_compatible(nebula_ver)
    
    return SettingsResponse(
        punchy_enabled=row.punchy_enabled,
        client_docker_image=row.client_docker_image,
        server_url=row.server_url,
        docker_compose_template=row.docker_compose_template,
        externally_managed_users=settings.externally_managed_users,
        cert_version=getattr(row, 'cert_version', 'v1'),
        nebula_version=nebula_ver,
        v2_support_available=v2_available
    )


# ============ Docker Compose Template Settings ============
@router.get("/settings/docker-compose-template", response_model=DockerComposeTemplateResponse)
async def get_docker_compose_template(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("settings", "docker_compose"))
):
    """Retrieve the current docker-compose template (admin-only)."""
    row = (await session.execute(select(GlobalSettings))).scalars().first()
    if not row:
        # Create defaults if missing
        row = GlobalSettings()
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return DockerComposeTemplateResponse(template=row.docker_compose_template)


@router.put("/settings/docker-compose-template", response_model=DockerComposeTemplateResponse)
async def update_docker_compose_template(
    body: DockerComposeTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("settings", "docker_compose"))
):
    """Update the docker-compose template with validation (admin-only)."""
    # Validate YAML by replacing placeholders with dummy values
    try:
        # Replace common placeholders with dummy values for validation
        validation_template = body.template
        validation_template = validation_template.replace(
            "{{CLIENT_NAME}}", "test-client")
        validation_template = validation_template.replace(
            "{{CLIENT_TOKEN}}", "dummy-token")
        validation_template = validation_template.replace(
            "{{SERVER_URL}}", "http://localhost:8080")
        validation_template = validation_template.replace(
            "{{CLIENT_DOCKER_IMAGE}}", "test-image:latest")
        validation_template = validation_template.replace(
            "{{POLL_INTERVAL_HOURS}}", "24")

        yaml.safe_load(validation_template)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}") from e

    row = (await session.execute(select(GlobalSettings))).scalars().first()
    if not row:
        row = GlobalSettings()
        session.add(row)

    row.docker_compose_template = body.template
    await session.commit()
    await session.refresh(row)

    return DockerComposeTemplateResponse(template=row.docker_compose_template)


@router.get("/settings/placeholders", response_model=PlaceholdersResponse)
async def get_placeholders(user: User = Depends(require_permission("settings", "read"))):
    """List available placeholders with descriptions (admin-only)."""
    placeholders = [
        PlaceholderInfo(
            name="{{CLIENT_NAME}}",
            description="Client hostname/identifier",
            example="my-client"
        ),
        PlaceholderInfo(
            name="{{CLIENT_TOKEN}}",
            description="Authentication token for API access",
            example="abc123..."
        ),
        PlaceholderInfo(
            name="{{SERVER_URL}}",
            description="Full API endpoint URL",
            example="https://nebula.example.com"
        ),
        PlaceholderInfo(
            name="{{CLIENT_DOCKER_IMAGE}}",
            description="Docker image reference",
            example="ghcr.io/kumpeapps/managed-nebula/client:latest"
        ),
        PlaceholderInfo(
            name="{{POLL_INTERVAL_HOURS}}",
            description="Config polling frequency in hours",
            example="24"
        ),
    ]
    return PlaceholdersResponse(placeholders=placeholders)


# ============ Version Cache Management ============

@router.get("/settings/version-cache", response_model=VersionCacheResponse)
async def get_version_cache_status(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Get version cache status (last check time, cached versions).
    """
    from datetime import datetime
    
    # Get last checked timestamp
    cache_check_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "version_cache_last_checked")
    )
    cache_check_row = cache_check_result.scalar_one_or_none()
    
    last_checked = None
    cache_age_hours = None
    if cache_check_row:
        try:
            last_checked = datetime.fromisoformat(cache_check_row.value)
            cache_age_hours = (datetime.utcnow() - last_checked).total_seconds() / 3600
        except Exception:
            pass
    
    # Get cached versions
    latest_client_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "latest_client_version")
    )
    latest_client_row = latest_client_result.scalar_one_or_none()
    
    latest_nebula_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "latest_nebula_version")
    )
    latest_nebula_row = latest_nebula_result.scalar_one_or_none()
    
    return VersionCacheResponse(
        last_checked=last_checked,
        latest_client_version=latest_client_row.value if latest_client_row else None,
        latest_nebula_version=latest_nebula_row.value if latest_nebula_row else None,
        cache_age_hours=cache_age_hours
    )


@router.post("/settings/version-cache/refresh")
async def refresh_version_cache_endpoint(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("settings", "update"))
):
    """
    Manually refresh version cache by querying GitHub API.
    Requires settings update permission.
    """
    from ..services.advisory_checker import refresh_version_cache
    
    # Get GitHub token from system settings
    github_token = None
    try:
        github_token_setting = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "github_api_token")
        )
        token_row = github_token_setting.scalar_one_or_none()
        if token_row:
            github_token = token_row.value
    except Exception:
        pass
    
    result = await refresh_version_cache(session, github_token)
    
    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error", "Failed to refresh cache"))
    
    return result


# ============ Nebula Version Management ============

@router.get("/nebula/versions", response_model=NebulaVersionsResponse)
async def get_nebula_versions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """
    Get available Nebula versions from GitHub releases.
    
    Returns the current configured version and list of available versions
    from the slackhq/nebula GitHub repository.
    """
    from ..services.nebula_version_manager import NebulaVersionService
    
    # Get current version from settings
    row = (await session.execute(select(GlobalSettings))).scalars().first()
    current_version = getattr(row, 'nebula_version', '1.9.7') if row else '1.9.7'
    
    # Fetch available versions from GitHub
    version_service = NebulaVersionService(github_token=settings.github_token)
    available_versions = await version_service.fetch_available_versions(include_prereleases=True)
    
    # Convert to response format
    version_responses = [
        NebulaVersionInfoResponse(
            version=v.version,
            release_date=v.release_date,
            is_stable=v.is_stable,
            supports_v2=v.supports_v2,
            download_url_linux_amd64=v.download_url_linux_amd64,
            download_url_linux_arm64=v.download_url_linux_arm64,
            download_url_darwin_amd64=v.download_url_darwin_amd64,
            download_url_darwin_arm64=v.download_url_darwin_arm64,
            download_url_windows_amd64=v.download_url_windows_amd64,
            checksum=v.checksum
        )
        for v in available_versions
    ]
    
    # Find latest stable version
    latest_stable = next(
        (v.version for v in available_versions if v.is_stable),
        current_version  # Fallback to current if no stable found
    )
    
    return NebulaVersionsResponse(
        current_version=current_version,
        available_versions=version_responses,
        latest_stable=latest_stable,
        versions=version_responses  # Alias for frontend
    )


@router.post("/client/config")
async def get_client_config(body: ClientConfigRequest, session: AsyncSession = Depends(get_session)):
    # Validate token
    q = await session.execute(select(ClientToken).where(ClientToken.token == body.token, ClientToken.is_active == True))
    token = q.scalar_one_or_none()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Avoid lazy load on async session; fetch client explicitly with groups and firewall rulesets eager-loaded
    from sqlalchemy.orm import selectinload
    from ..models.client import FirewallRuleset
    cq = await session.execute(
        select(Client)
        .options(
            selectinload(Client.groups),
            selectinload(Client.firewall_rulesets).selectinload(
                FirewallRuleset.rules).selectinload(FirewallRule.groups)
        )
        .where(Client.id == token.client_id)
    )
    client = cq.scalar_one_or_none()
    # Resolve primary IP assignment (or first if no primary marked)
    q2 = await session.execute(
        select(IPAssignment)
        .where(IPAssignment.client_id == client.id)
        .order_by(IPAssignment.is_primary.desc(), IPAssignment.id)
    )
    ip_assignment = q2.scalars().first()
    if not ip_assignment:
        raise HTTPException(
            status_code=409, detail="Client has no IP assignment")

    # Load settings and fetch all CAs that should be in config
    settings = (await session.execute(select(GlobalSettings))).scalars().first()
    now_ts = datetime.utcnow()
    all_cas = (
        await session.execute(
            select(CACertificate).where(
                CACertificate.include_in_config == True,
                CACertificate.not_after > now_ts,
            )
        )
    ).scalars().all()
    if not all_cas:
        raise HTTPException(status_code=503, detail="CA not configured")
    
    # CRITICAL: V2 CAs are NOT backwards compatible with v1 clients (< Nebula 1.10.0)
    # Filter CA bundle based on client Nebula version
    client_nebula_version = getattr(client, 'nebula_version', None)
    supports_v2 = False
    if client_nebula_version:
        try:
            version_str = client_nebula_version.lstrip('v')
            parts = version_str.split('.')
            if len(parts) >= 2:
                major = int(parts[0])
                minor = int(parts[1])
                supports_v2 = (major > 1) or (major == 1 and minor >= 10)
        except (ValueError, AttributeError):
            supports_v2 = False
    
    # Filter CAs: v1 clients get only v1 CAs, v2 clients get all CAs
    if supports_v2:
        cas = all_cas
    else:
        # V1 clients cannot parse v2 CA certificates - exclude them
        cas = [ca for ca in all_cas if ca.cert_version != 'v2']
        if not cas:
            raise HTTPException(
                status_code=503,
                detail=f"No v1 CA available for client with Nebula {client_nebula_version or 'unknown'}. "
                       f"V2 CAs require Nebula 1.10.0+. Please create a v1 CA or upgrade client."
            )

    # Determine IP/CIDR prefix for certificate and tun.ip
    from ..models import IPPool
    import ipaddress
    if ip_assignment.pool_id:
        pool = (await session.execute(select(IPPool).where(IPPool.id == ip_assignment.pool_id))).scalars().first()
        cidr = pool.cidr if pool else (
            settings.default_cidr_pool if settings else "10.100.0.0/16")
    else:
        cidr = settings.default_cidr_pool if settings else "10.100.0.0/16"
    try:
        prefix = ipaddress.ip_network(cidr, strict=False).prefixlen
    except Exception:
        # Invalid CIDR format; fallback to /24
        prefix = 24
    client_ip_cidr = f"{ip_assignment.ip_address}/{prefix}"

    # If client is blocked, deny issuance and config
    if getattr(client, 'is_blocked', False):
        raise HTTPException(status_code=403, detail="Client is blocked")

    # Determine cert version based on client capabilities and global setting
    cert_version = getattr(settings, 'cert_version', 'v1')
    client_ip_version = getattr(client, 'ip_version', 'ipv4_only')
    client_nebula_version = getattr(client, 'nebula_version', None)
    
    # Log for debugging certificate version decisions
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Certificate request for client '{client.name}' - Nebula version: {client_nebula_version}, IP version: {client_ip_version}, Global cert version: {cert_version}")
    
    # Check if client's Nebula version supports v2 certs (1.10.0+)
    # Unknown version = old client (<=1.3.4) that doesn't report version
    supports_v2 = False
    if client_nebula_version:
        try:
            # Parse version string (e.g., "1.10.0", "v1.10.0")
            version_str = client_nebula_version.lstrip('v')
            parts = version_str.split('.')
            if len(parts) >= 2:
                major = int(parts[0])
                minor = int(parts[1])
                # Nebula 1.10.0+ supports v2 certs
                supports_v2 = (major > 1) or (major == 1 and minor >= 10)
        except (ValueError, AttributeError):
            # If we can't parse version, it's too old - treat as not supporting v2
            supports_v2 = False
    # else: client_nebula_version is None/empty = unknown/old client (<=1.3.4)
    
    # Client IP versions that require v2 features (multiple IPs or dual stack)
    requires_v2_features = client_ip_version in ['multi_ipv4', 'multi_ipv6', 'multi_both', 'dual_stack', 'ipv6_only']
    
    # CRITICAL: Clients with Nebula < 1.10.0 or unknown version can ONLY receive v1 certificates
    # Unknown/None version means old client (<=1.3.4) that doesn't support version reporting
    if not supports_v2:
        # Downgrade any v2/hybrid to v1 for incompatible/old clients
        if cert_version in ['v2', 'hybrid']:
            logger.info(f"Client '{client.name}' does not support v2 (version: {client_nebula_version}), downgrading from {cert_version} to v1")
            cert_version = 'v1'
        
        # If client requires v2 features but doesn't support them, error
        if requires_v2_features:
            raise HTTPException(
                status_code=400,
                detail=f"Client IP configuration '{client_ip_version}' requires v2 certificates (Nebula 1.10.0+). "
                       f"Current client Nebula version: {client_nebula_version or 'unknown (<=1.3.4)'}. "
                       f"Please upgrade client to Nebula 1.10.0+ or change IP version to 'ipv4_only'."
            )
    
    # If client requires v2 features (multiple IPs, IPv6, etc), force v2
    if requires_v2_features:
        cert_version = 'v2'
    
    logger.info(f"Final cert version for client '{client.name}': {cert_version} (supports_v2: {supports_v2})")
    
    # Hybrid mode: For single IPv4 clients with v2 support (>=1.10.0), issue both v1+v2
    # Hybrid automatically degrades to v1 for old/incompatible clients (handled above)
    # When client version changes from <1.10.0 to >=1.10.0, cert_version mismatch triggers reissuance
    
    # For v2 certs with multiple IPs, gather all IPs for the client
    # Note: hybrid certs use single IP only (enforced in CertManager)
    all_ips = []
    if cert_version == 'v2':
        # Get all IP assignments for this client (ordered by primary first)
        all_ip_rows = (await session.execute(
            select(IPAssignment)
            .where(IPAssignment.client_id == client.id)
            .order_by(IPAssignment.is_primary.desc(), IPAssignment.id)
        )).scalars().all()
        all_ips = [row.ip_address for row in all_ip_rows]
    
    # Generate or rotate client certificate using provided public key
    cert_mgr = CertManager(session)
    try:
        client_cert_pem, not_before, not_after = await cert_mgr.issue_or_rotate_client_cert(
            client=client,
            public_key_str=body.public_key,
            client_ip=ip_assignment.ip_address,
            cidr_prefix=prefix,
            cert_version=cert_version,
            all_ips=all_ips if all_ips else None,
        )
    except RuntimeError as e:
        # Convert cert generation errors (e.g., invalid public key) to 400 Bad Request
        error_msg = str(e)
        if "parsing in-pub" in error_msg or "did not contain a valid PEM" in error_msg:
            raise HTTPException(status_code=400, detail="Invalid public_key: must be a valid PEM-encoded Nebula X25519 public key")
        # Re-raise other RuntimeErrors as-is
        raise

    # Build lighthouse maps: static_host_map {nebula_ip: ["public_ip:port"]} and hosts list of nebula IPs
    # Only include lighthouses from the same IP pool as the client
    lighthouses = (
        await session.execute(select(Client).where(Client.is_lighthouse == True))
    ).scalars().all()
    static_map: dict[str, list[str]] = {}
    lh_hosts: list[str] = []
    for lh in lighthouses:
        lh_ip_row = (await session.execute(
            select(IPAssignment)
            .where(IPAssignment.client_id == lh.id)
            .order_by(IPAssignment.is_primary.desc(), IPAssignment.id)
        )).scalars().first()
        if not lh_ip_row:
            continue
        if not lh.public_ip:
            continue

        # Only include lighthouse if it's in the same pool as the client (or both have no pool)
        if lh_ip_row.pool_id != ip_assignment.pool_id:
            continue

        lh_hosts.append(lh_ip_row.ip_address)
        static_map[lh_ip_row.ip_address] = [
            f"{lh.public_ip}:{settings.lighthouse_port if settings else 4242}"]
    
    # If current client is a lighthouse, exclude itself from static_host_map
    # Lighthouses should not have their own IP in the static map
    if client.is_lighthouse and ip_assignment.ip_address in static_map:
        del static_map[ip_assignment.ip_address]

    # Build inline CA bundle (concatenated PEMs)
    ca_bundle = "".join([(c.pem_cert.decode().rstrip() + "\n") for c in cas])

    # Collect revoked fingerprints to distribute (skip expired to reduce bloat)
    now = datetime.utcnow()
    revoked_rows = (
        await session.execute(
            select(ClientCertificate.fingerprint).where(
                ClientCertificate.revoked == True,
                ClientCertificate.not_after > now,
                ClientCertificate.fingerprint.isnot(None)
            )
        )
    ).scalars().all()
    revoked_fps = [fp for fp in revoked_rows if fp]

    # Determine OS-specific paths based on os_type from request or client record
    os_type = body.os_type or client.os_type or "docker"
    import logging
    logger = logging.getLogger(__name__)
    print(f"[DEBUG] Client {client.name} requesting config - request.os_type: {body.os_type}, stored.os_type: {client.os_type}, final: {os_type}")
    logger.info(f"Client {client.name} requesting config with os_type: {os_type} (request: {body.os_type}, stored: {client.os_type})")
    
    if os_type == "windows":
        key_path = "C:/ProgramData/Nebula/host.key"
        ca_path = "C:/ProgramData/Nebula/ca.crt"
        cert_path = "C:/ProgramData/Nebula/host.crt"
    elif os_type == "macos":
        # macOS: Paths match where nebula-helper.sh installs files
        # Helper script copies keys to /var/lib/nebula/ and certs to /etc/nebula/
        key_path = "/var/lib/nebula/host.key"
        ca_path = "/etc/nebula/ca.crt"
        cert_path = "/etc/nebula/host.crt"
    else:  # docker or any other
        key_path = "/var/lib/nebula/host.key"
        ca_path = "/etc/nebula/ca.crt"
        cert_path = "/etc/nebula/host.crt"
    
    print(f"[DEBUG] Generated paths for os_type={os_type}: key={key_path}")
    logger.info(f"Generated config paths for {os_type}: key={key_path}, ca={ca_path}, cert={cert_path}")
    
    # Build config YAML; embed CA bundle inline to support multiple CAs
    config_yaml = build_nebula_config(
        client=client,
        client_ip_cidr=client_ip_cidr,
        settings=settings,
        static_host_map=static_map,
        lighthouse_host_ips=lh_hosts,
        revoked_fingerprints=revoked_fps,
        key_path=key_path,
        ca_path=ca_path,
        cert_path=cert_path,
        inline_ca_pem=ca_bundle,
        inline_cert_pem=client_cert_pem,
        os_type=os_type,
    )

    # Update last config download timestamp, version info, and os_type
    try:
        client.last_config_download_at = datetime.utcnow()
        if body.client_version:
            client.client_version = body.client_version
        if body.nebula_version:
            client.nebula_version = body.nebula_version
        if body.os_type:
            client.os_type = body.os_type
        if body.client_version or body.nebula_version or body.os_type:
            client.last_version_report_at = datetime.utcnow()
        await session.commit()
    except Exception:
        # Timestamp update is non-critical; log and continue
        pass

    return {
        "config": config_yaml,
        "client_cert_pem": client_cert_pem,
        "ca_chain_pems": [c.pem_cert.decode() for c in cas],
        "cert_not_before": not_before.isoformat(),
        "cert_not_after": not_after.isoformat(),
        "lighthouse": client.is_lighthouse,
        "key_path": key_path,
    }


# ============ Clients REST API ============

@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """List all clients visible to the user (admin sees all, others see owned/shared)."""
    from sqlalchemy.orm import selectinload

    query = select(Client).options(
        selectinload(Client.groups),
        selectinload(Client.firewall_rulesets)
    )

    # Non-admins only see clients they own or have permissions for
    is_admin = await user.has_permission(session, "users", "delete")
    if not is_admin:
        # Get client IDs user has access to (owned or shared)
        perm_result = await session.execute(
            select(ClientPermission.client_id).where(
                ClientPermission.user_id == user.id,
                ClientPermission.can_view == True
            )
        )
        permitted_ids = [row[0] for row in perm_result.all()]

        # Filter to owned or permitted clients
        query = query.where(
            (Client.owner_user_id == user.id) | (Client.id.in_(permitted_ids))
        )

    result = await session.execute(query)
    clients = result.scalars().all()

    # Build responses using helper
    response = []
    for client in clients:
        response.append(await build_client_response(client, session, user, include_token=is_admin))

    return response


@router.post("/clients", response_model=ClientResponse)
async def create_client(
    body: ClientCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("clients", "create"))
):
    """Create a new client with token and IP assignment (admin-only)."""
    from sqlalchemy.orm import selectinload
    from ..models.client import FirewallRuleset

    # Validate groups
    if body.group_ids:
        groups_result = await session.execute(
            select(Group).where(Group.id.in_(body.group_ids))
        )
        groups = groups_result.scalars().all()
        if len(groups) != len(body.group_ids):
            raise HTTPException(
                status_code=400, detail="One or more group IDs not found")
    else:
        groups = []

    # Validate firewall rulesets
    if body.firewall_ruleset_ids:
        rulesets_result = await session.execute(
            select(FirewallRuleset).where(
                FirewallRuleset.id.in_(body.firewall_ruleset_ids))
        )
        rulesets = rulesets_result.scalars().all()
        if len(rulesets) != len(body.firewall_ruleset_ids):
            raise HTTPException(
                status_code=400, detail="One or more firewall ruleset IDs not found")
    else:
        rulesets = []

    # Create client
    client = Client(
        name=body.name,
        is_lighthouse=body.is_lighthouse,
        public_ip=body.public_ip,
        is_blocked=body.is_blocked,
        owner_user_id=user.id,
        config_last_changed_at=datetime.utcnow(),
        groups=groups,
        firewall_rulesets=rulesets
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)

    # Generate token with current prefix from settings
    prefix = await get_token_prefix(session)
    token_value = generate_client_token(prefix)
    token = ClientToken(client_id=client.id, token=token_value, is_active=True, owner_user_id=user.id)
    session.add(token)

    # Handle IP allocation
    pool_id = body.pool_id
    if not pool_id:
        # Use default pool or first available pool
        settings = (await session.execute(select(GlobalSettings))).scalars().first()
        default_cidr = settings.default_cidr_pool if settings else "10.100.0.0/16"
        await ensure_default_pool(session, default_cidr)
        pool_result = await session.execute(select(IPPool).order_by(IPPool.id))
        pool = pool_result.scalars().first()
        if not pool:
            raise HTTPException(status_code=503, detail="No IP pool available")
        pool_id = pool.id
    else:
        # Load the specified pool
        pool_result = await session.execute(select(IPPool).where(IPPool.id == pool_id))
        pool = pool_result.scalars().first()
        if not pool:
            raise HTTPException(status_code=404, detail="IP pool not found")

    # Determine IP address
    if body.ip_address:
        # Manual IP assignment - validate it's available and in pool/group range
        import ipaddress
        allocated_ip = body.ip_address
        network = ipaddress.ip_network(pool.cidr)
        try:
            ip_obj = ipaddress.ip_address(allocated_ip)
            if ip_obj not in network:
                raise HTTPException(
                    status_code=400, detail="IP address not in pool CIDR")
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid IP address format")

        # Check if IP already assigned
        existing = await session.execute(
            select(IPAssignment).where(IPAssignment.ip_address == allocated_ip)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail="IP address already assigned")

        # If IP group specified, validate IP is in range
        if body.ip_group_id:
            group_result = await session.execute(
                select(IPGroup).where(IPGroup.id ==
                                      body.ip_group_id, IPGroup.pool_id == pool_id)
            )
            group = group_result.scalar_one_or_none()
            if not group:
                raise HTTPException(
                    status_code=404, detail="IP group not found or doesn't belong to selected pool")

            start_ip = ipaddress.ip_address(group.start_ip)
            end_ip = ipaddress.ip_address(group.end_ip)
            if not (start_ip <= ip_obj <= end_ip):
                raise HTTPException(
                    status_code=400, detail="IP address not in selected IP group range")
    else:
        # Auto-allocate IP
        try:
            allocated_ip = await allocate_ip_from_pool(session, pool)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))

    ip_assignment = IPAssignment(
        client_id=client.id,
        pool_id=pool_id,
        ip_address=allocated_ip,
        ip_group_id=body.ip_group_id if body.ip_group_id else None
    )
    session.add(ip_assignment)
    await session.commit()
    await session.refresh(client)

    # Reload with relationships
    result = await session.execute(
        select(Client)
        .options(selectinload(Client.groups), selectinload(Client.firewall_rulesets))
        .where(Client.id == client.id)
    )
    client = result.scalar_one()

    # Use the helper to build response with token
    return await build_client_response(client, session, user, include_token=True)


@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Get a single client by ID with access control check."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(Client)
        .options(selectinload(Client.groups), selectinload(Client.firewall_rulesets))
        .where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Access control: admins see all, others only see owned/shared
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = client.owner_user_id == user.id

    if not is_admin and not is_owner:
        # Check if user has view permission
        perm_result = await session.execute(
            select(ClientPermission).where(
                ClientPermission.client_id == client_id,
                ClientPermission.user_id == user.id,
                ClientPermission.can_view == True
            )
        )
        perm = perm_result.scalar_one_or_none()
        if not perm:
            raise HTTPException(status_code=403, detail="Access denied")

    return await build_client_response(client, session, user, include_token=(is_admin or is_owner))


@router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    body: ClientUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Update client fields and memberships."""
    from sqlalchemy.orm import selectinload

    from ..models.client import FirewallRuleset
    result = await session.execute(
        select(Client)
        .options(selectinload(Client.groups), selectinload(Client.firewall_rulesets))
        .where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Access control: admins can update all, others only owned or with can_update permission
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = client.owner_user_id == user.id

    if not is_admin and not is_owner:
        # Check if user has update permission
        perm_result = await session.execute(
            select(ClientPermission).where(
                ClientPermission.client_id == client_id,
                ClientPermission.user_id == user.id,
                ClientPermission.can_update == True
            )
        )
        perm = perm_result.scalar_one_or_none()
        if not perm:
            raise HTTPException(status_code=403, detail="Access denied")

    config_changed = False

    # Update basic fields
    if body.name is not None and body.name != client.name:
        client.name = body.name

    if body.is_lighthouse is not None and body.is_lighthouse != client.is_lighthouse:
        client.is_lighthouse = body.is_lighthouse
        config_changed = True

    if body.public_ip is not None and body.public_ip != client.public_ip:
        client.public_ip = body.public_ip
        config_changed = True

    if body.is_blocked is not None:
        client.is_blocked = body.is_blocked

    if body.os_type is not None and body.os_type != client.os_type:
        client.os_type = body.os_type

    if body.ip_version is not None and body.ip_version != client.ip_version:
        client.ip_version = body.ip_version
        config_changed = True

    # Update group memberships
    if body.group_ids is not None:
        # Fetch requested groups
        groups_result = await session.execute(
            select(Group).where(Group.id.in_(body.group_ids))
        )
        new_groups = groups_result.scalars().all()

        if len(new_groups) != len(body.group_ids):
            raise HTTPException(
                status_code=400, detail="One or more group IDs not found")

        if set(g.id for g in client.groups) != set(g.id for g in new_groups):
            client.groups = new_groups
            config_changed = True

    # Update firewall ruleset associations
    if body.firewall_ruleset_ids is not None:
        rulesets_result = await session.execute(
            select(FirewallRuleset).where(
                FirewallRuleset.id.in_(body.firewall_ruleset_ids))
        )
        new_rulesets = rulesets_result.scalars().all()

        if len(new_rulesets) != len(body.firewall_ruleset_ids):
            raise HTTPException(
                status_code=400, detail="One or more firewall ruleset IDs not found")

        if set(r.id for r in client.firewall_rulesets) != set(r.id for r in new_rulesets):
            client.firewall_rulesets = new_rulesets
            config_changed = True

    # Update IP assignment
    if body.ip_address is not None or body.pool_id is not None or body.ip_group_id is not None:
        # Get existing IP assignment
        ip_result = await session.execute(
            select(IPAssignment).where(IPAssignment.client_id == client_id)
        )
        ip_assignment = ip_result.scalar_one_or_none()

        if not ip_assignment:
            raise HTTPException(
                status_code=404, detail="Client has no IP assignment")

        # Update IP address if provided
        if body.ip_address is not None and body.ip_address != ip_assignment.ip_address:
            # Validate new IP is not already in use
            existing_ip = await session.execute(
                select(IPAssignment).where(
                    IPAssignment.ip_address == body.ip_address,
                    IPAssignment.id != ip_assignment.id
                )
            )
            if existing_ip.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, detail=f"IP address {body.ip_address} is already assigned")

            ip_assignment.ip_address = body.ip_address
            config_changed = True

        # Update pool_id if provided
        if body.pool_id is not None and body.pool_id != ip_assignment.pool_id:
            # Validate pool exists
            pool_check = await session.execute(
                select(IPPool).where(IPPool.id == body.pool_id)
            )
            if not pool_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=404, detail=f"IP pool {body.pool_id} not found")

            ip_assignment.pool_id = body.pool_id
            config_changed = True

        # Update ip_group_id if provided (allow setting to None to remove from group)
        if body.ip_group_id is not None and body.ip_group_id != ip_assignment.ip_group_id:
            from ..models.client import IPGroup
            group_check = await session.execute(
                select(IPGroup).where(IPGroup.id == body.ip_group_id)
            )
            if not group_check.scalar_one_or_none():
                raise HTTPException(
                    status_code=404, detail=f"IP group {body.ip_group_id} not found")

            ip_assignment.ip_group_id = body.ip_group_id
            config_changed = True

    # Mark config changed timestamp if needed
    if config_changed:
        client.config_last_changed_at = datetime.utcnow()

    await session.commit()
    await session.refresh(client)

    # Reload with relationships
    result = await session.execute(
        select(Client)
        .options(selectinload(Client.groups), selectinload(Client.firewall_rulesets))
        .where(Client.id == client_id)
    )
    client = result.scalar_one()

    return await build_client_response(client, session, user, include_token=(is_admin or is_owner))


@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("clients", "delete"))
):
    """Delete a client and all associated records.
    
    Deletes the client and cascades to:
    - ClientCertificate records
    - ClientToken records
    - IPAssignment records
    - Association table entries (groups, firewall rulesets)
    """
    try:
        # Eager load relationships to avoid lazy-load issues in async
        stmt = (
            select(Client)
            .where(Client.id == client_id)
            .options(
                selectinload(Client.groups),
                selectinload(Client.firewall_rulesets),
            )
        )
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail=f"Client with id {client_id} not found")

        # Log deletion for audit trail
        logger.info(
            f"Deleting client {client_id} (name: {client.name}) by user {user.email} (id: {user.id})"
        )

        # Manual cleanup only for tables lacking DB-level CASCADE
        await session.execute(delete(ClientCertificate).where(ClientCertificate.client_id == client_id))
        await session.execute(delete(ClientToken).where(ClientToken.client_id == client_id))
        await session.execute(delete(IPAssignment).where(IPAssignment.client_id == client_id))
        await session.execute(delete(ClientPermission).where(ClientPermission.client_id == client_id))
        # Null out logs referencing this client (SET NULL semantics)
        await session.execute(
            GitHubSecretScanningLog.__table__.update()
            .where(GitHubSecretScanningLog.client_id == client_id)
            .values(client_id=None)
        )

        # Let ORM handle association tables (client_groups, client_firewall_rulesets)
        # to avoid double-deletion rowcount mismatches

        # Finally delete the client itself; ORM will flush association deletions first
        await session.delete(client)
        await session.commit()

        logger.info(f"Successfully deleted client {client_id}")
        return {"status": "deleted", "id": client_id, "message": f"Client {client_id} deleted successfully"}

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except IntegrityError as e:
        # Handle any remaining FK constraint violations
        logger.error(f"Integrity error deleting client {client_id}: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete client due to database constraints. Please ensure all related records are removed first."
        )
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error deleting client {client_id}: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete client: {str(e)}"
        )


# ============ Client Alternate IPs ============

@router.post("/clients/{client_id}/alternate-ips", response_model=IPAssignmentResponse, status_code=201)
async def add_alternate_ip(
    client_id: int,
    body: AlternateIPAdd,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("clients", "update"))
):
    """Add an alternate IP address to a client (for multi-IP configurations)."""
    from ipaddress import ip_address as validate_ip
    
    # Verify client exists
    client_result = await session.execute(select(Client).where(Client.id == client_id))
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Validate IP address format
    try:
        ip_obj = validate_ip(body.ip_address)
        detected_version = "ipv6" if ip_obj.version == 6 else "ipv4"
        if body.ip_version != detected_version:
            raise HTTPException(
                status_code=400,
                detail=f"IP version mismatch: provided '{body.ip_version}' but detected '{detected_version}'"
            )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    
    # Check if IP is already assigned
    existing_result = await session.execute(
        select(IPAssignment).where(IPAssignment.ip_address == body.ip_address)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="IP address already assigned")
    
    # Validate pool and group if provided
    if body.pool_id:
        pool_result = await session.execute(select(IPPool).where(IPPool.id == body.pool_id))
        pool = pool_result.scalar_one_or_none()
        if not pool:
            raise HTTPException(status_code=404, detail="IP Pool not found")
        
        # Verify IP is within pool CIDR
        from ipaddress import ip_network
        pool_network = ip_network(pool.cidr)
        if ip_obj not in pool_network:
            raise HTTPException(
                status_code=400,
                detail=f"IP {body.ip_address} is not within pool CIDR {pool.cidr}"
            )
    
    if body.ip_group_id:
        group_result = await session.execute(select(IPGroup).where(IPGroup.id == body.ip_group_id))
        group = group_result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail="IP Group not found")
        
        # Verify IP is within group range
        from ipaddress import ip_address as parse_ip
        start_ip = parse_ip(group.start_ip)
        end_ip = parse_ip(group.end_ip)
        if not (start_ip <= ip_obj <= end_ip):
            raise HTTPException(
                status_code=400,
                detail=f"IP {body.ip_address} is not within group range {group.start_ip} - {group.end_ip}"
            )
    
    # Create the alternate IP assignment (not primary)
    ip_assignment = IPAssignment(
        client_id=client_id,
        ip_address=body.ip_address,
        ip_version=body.ip_version,
        is_primary=False,
        pool_id=body.pool_id,
        ip_group_id=body.ip_group_id
    )
    session.add(ip_assignment)
    
    # Mark config as changed to trigger certificate regeneration
    client.config_last_changed_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(ip_assignment)
    
    logger.info(f"Added alternate IP {body.ip_address} to client {client_id} by user {user.email}")
    
    return IPAssignmentResponse(
        id=ip_assignment.id,
        ip_address=ip_assignment.ip_address,
        ip_version=ip_assignment.ip_version,
        is_primary=ip_assignment.is_primary,
        pool_id=ip_assignment.pool_id,
        ip_group_id=ip_assignment.ip_group_id
    )


@router.delete("/clients/{client_id}/alternate-ips/{ip_assignment_id}", status_code=200)
async def delete_alternate_ip(
    client_id: int,
    ip_assignment_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("clients", "update"))
):
    """Delete an alternate IP address from a client."""
    # Verify client exists
    client_result = await session.execute(select(Client).where(Client.id == client_id))
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Get the IP assignment
    ip_result = await session.execute(
        select(IPAssignment).where(
            IPAssignment.id == ip_assignment_id,
            IPAssignment.client_id == client_id
        )
    )
    ip_assignment = ip_result.scalar_one_or_none()
    if not ip_assignment:
        raise HTTPException(status_code=404, detail="IP assignment not found")
    
    # Prevent deletion of primary IP
    if ip_assignment.is_primary:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete primary IP. Change the IP configuration to reassign the primary IP first."
        )
    
    ip_address = ip_assignment.ip_address
    await session.delete(ip_assignment)
    
    # Mark config as changed to trigger certificate regeneration
    client.config_last_changed_at = datetime.utcnow()
    
    await session.commit()
    
    logger.info(f"Deleted alternate IP {ip_address} from client {client_id} by user {user.email}")
    
    return {"status": "deleted", "id": ip_assignment_id, "ip_address": ip_address}


# ============ Client Ownership & Permissions ============

@router.put("/clients/{client_id}/owner", response_model=ClientResponse)
async def update_client_owner(
    client_id: int,
    body: ClientOwnerUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("clients", "update"))
):
    """Reassign client owner (admin-only)."""
    from sqlalchemy.orm import selectinload

    # Get client
    result = await session.execute(
        select(Client)
        .options(selectinload(Client.groups), selectinload(Client.firewall_rulesets))
        .where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Verify new owner exists
    owner_result = await session.execute(
        select(User).where(User.id == body.owner_user_id)
    )
    new_owner = owner_result.scalar_one_or_none()
    if not new_owner:
        raise HTTPException(status_code=404, detail="New owner user not found")

    # Update owner
    client.owner_user_id = body.owner_user_id
    await session.commit()
    await session.refresh(client)

    return await build_client_response(client, session, user, include_token=True)


@router.get("/clients/{client_id}/permissions", response_model=List[ClientPermissionResponse])
async def list_client_permissions(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """List all permissions for a client (owner/admin only)."""
    # Get client
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check access
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = client.owner_user_id == user.id
    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only owner or admin can view permissions")

    # Get permissions
    perm_result = await session.execute(
        select(ClientPermission).where(ClientPermission.client_id == client_id)
    )
    perms = perm_result.scalars().all()

    # Build response with user info
    response = []
    for perm in perms:
        user_result = await session.execute(select(User).where(User.id == perm.user_id))
        perm_user = user_result.scalar_one_or_none()
        if perm_user:
            response.append(ClientPermissionResponse(
                id=perm.id,
                user=UserRef(id=perm_user.id, email=perm_user.email),
                can_view=perm.can_view,
                can_update=perm.can_update,
                can_download_config=perm.can_download_config,
                can_view_token=perm.can_view_token,
                can_download_docker_config=perm.can_download_docker_config
            ))

    return response


@router.post("/clients/{client_id}/permissions", response_model=ClientPermissionResponse)
async def grant_client_permission(
    client_id: int,
    body: ClientPermissionGrant,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Grant permission to a user for a client (owner/admin only)."""
    # Get client
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check access
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = client.owner_user_id == user.id
    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only owner or admin can grant permissions")

    # Verify target user exists
    target_result = await session.execute(select(User).where(User.id == body.user_id))
    target_user = target_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Check if permission already exists
    existing_result = await session.execute(
        select(ClientPermission).where(
            ClientPermission.client_id == client_id,
            ClientPermission.user_id == body.user_id
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Update existing permission
        existing.can_view = body.can_view
        existing.can_update = body.can_update
        existing.can_download_config = body.can_download_config
        existing.can_view_token = body.can_view_token
        existing.can_download_docker_config = body.can_download_docker_config
        perm = existing
    else:
        # Create new permission
        perm = ClientPermission(
            client_id=client_id,
            user_id=body.user_id,
            can_view=body.can_view,
            can_update=body.can_update,
            can_download_config=body.can_download_config,
            can_view_token=body.can_view_token,
            can_download_docker_config=body.can_download_docker_config
        )
        session.add(perm)

    await session.commit()
    await session.refresh(perm)

    return ClientPermissionResponse(
        id=perm.id,
        user=UserRef(id=target_user.id, email=target_user.email),
        can_view=perm.can_view,
        can_update=perm.can_update,
        can_download_config=perm.can_download_config,
        can_view_token=perm.can_view_token,
        can_download_docker_config=perm.can_download_docker_config
    )


@router.delete("/clients/{client_id}/permissions/{permission_id}")
async def revoke_client_permission(
    client_id: int,
    permission_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Revoke a permission from a client (owner/admin only)."""
    # Get client
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check access
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = client.owner_user_id == user.id
    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only owner or admin can revoke permissions")

    # Get permission
    perm_result = await session.execute(
        select(ClientPermission).where(
            ClientPermission.id == permission_id,
            ClientPermission.client_id == client_id
        )
    )
    perm = perm_result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    await session.delete(perm)
    await session.commit()

    return {"status": "revoked", "permission_id": permission_id}


# ============ Client Certificate Management ============

@router.get("/clients/{client_id}/certificates")
async def list_client_certificates(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("clients", "read"))
):
    """List all certificates for a client (admin-only)."""
    from ..models.schemas import ClientCertificateResponse

    # Verify client exists
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Fetch certificates
    certs_result = await session.execute(
        select(ClientCertificate)
        .where(ClientCertificate.client_id == client_id)
        .order_by(ClientCertificate.created_at.desc())
    )
    certs = certs_result.scalars().all()

    return [ClientCertificateResponse.model_validate(cert) for cert in certs]


@router.post("/clients/{client_id}/certificates/reissue")
async def reissue_client_certificate(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("clients", "update"))
):
    """Manually reissue a client certificate (admin-only)."""
    from sqlalchemy.orm import selectinload
    from ..models.client import FirewallRuleset

    # Fetch client with relationships
    result = await session.execute(
        select(Client)
        .options(selectinload(Client.groups), selectinload(Client.firewall_rulesets))
        .where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Get IP assignment
    ip_result = await session.execute(
        select(IPAssignment).where(IPAssignment.client_id == client_id)
    )
    ip_assignment = ip_result.scalar_one_or_none()
    if not ip_assignment:
        raise HTTPException(
            status_code=409, detail="Client has no IP assignment")

    # Get active CA
    now_ts = datetime.utcnow()
    ca_result = await session.execute(
        select(CACertificate).where(
            CACertificate.is_active == True,
            CACertificate.can_sign == True,
            CACertificate.not_after > now_ts
        )
    )
    active_ca = ca_result.scalar_one_or_none()
    if not active_ca:
        raise HTTPException(status_code=503, detail="No active CA available")

    # Determine CIDR from pool
    cidr = "10.100.0.0/16"  # default
    if ip_assignment.pool_id:
        pool_result = await session.execute(
            select(IPPool).where(IPPool.id == ip_assignment.pool_id)
        )
        pool = pool_result.scalar_one_or_none()
        if pool:
            cidr = pool.cidr
    
    import ipaddress
    try:
        prefix = ipaddress.ip_network(cidr, strict=False).prefixlen
    except Exception:
        prefix = 24

    # Determine cert version: use v2/hybrid features if client requires multiple IPs or is compatible
    from ..core.config import settings
    cert_version = getattr(settings, 'cert_version', 'v1')
    client_ip_version = getattr(client, 'ip_version', 'ipv4_only')
    client_nebula_version = getattr(client, 'nebula_version', None)
    
    requires_v2_features = client_ip_version in ['multi_ipv4', 'multi_ipv6', 'multi_both', 'dual_stack', 'ipv6_only']
    
    # Check if client supports v2 (Nebula 1.10.0+)
    supports_v2 = False
    if client_nebula_version:
        try:
            version_str = client_nebula_version.lstrip('v')
            parts = version_str.split('.')
            if len(parts) >= 2:
                major = int(parts[0])
                minor = int(parts[1])
                supports_v2 = (major > 1) or (major == 1 and minor >= 10)
        except (ValueError, AttributeError):
            supports_v2 = False
    
    if requires_v2_features and cert_version == 'v1':
        cert_version = 'v2'
    # Keep hybrid for compatible clients when global is hybrid
    # Otherwise use global setting (v1, v2, or hybrid)
    
    # For v2 or hybrid certs, gather all IPs
    all_ips = []
    if cert_version in ['v2', 'hybrid']:
        all_ip_rows = (await session.execute(
            select(IPAssignment)
            .where(IPAssignment.client_id == client.id)
            .order_by(IPAssignment.is_primary.desc(), IPAssignment.id)
        )).scalars().all()
        all_ips = [row.ip_address for row in all_ip_rows]

    # Issue new certificate
    cert_manager = CertManager(session)
    # Generate keypair for reissue (or use existing public key if available)
    # For simplicity, we'll generate a new keypair
    import subprocess
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = os.path.join(tmpdir, "host.key")
        pub_path = os.path.join(tmpdir, "host.pub")

        # Generate keypair
        subprocess.run(
            ["nebula-cert", "keygen", "-out-key", key_path, "-out-pub", pub_path],
            check=True
        )

        with open(pub_path, "r") as f:
            public_key_pem = f.read()

        # Issue certificate using correct signature
        cert_pem, not_before, not_after = await cert_manager.issue_or_rotate_client_cert(
            client=client,
            public_key_str=public_key_pem,
            client_ip=ip_assignment.ip_address,
            cidr_prefix=prefix,
            cert_version=cert_version,
            all_ips=all_ips if all_ips else None
        )

    await session.commit()

    return {
        "status": "reissued",
        "message": "Certificate reissued successfully. Client must download new config."
    }


@router.post("/clients/{client_id}/certificates/{cert_id}/revoke")
async def revoke_client_certificate(
    client_id: int,
    cert_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("clients", "update"))
):
    """Revoke a client certificate (admin-only)."""
    # Fetch certificate
    result = await session.execute(
        select(ClientCertificate).where(
            ClientCertificate.id == cert_id,
            ClientCertificate.client_id == client_id
        )
    )
    cert = result.scalar_one_or_none()

    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    if cert.revoked:
        raise HTTPException(
            status_code=400, detail="Certificate already revoked")

    # Mark as revoked
    cert.revoked = True
    cert.revoked_at = datetime.utcnow()
    await session.commit()

    return {
        "status": "revoked",
        "certificate_id": cert_id,
        "revoked_at": cert.revoked_at
    }


@router.get("/clients/{client_id}/config")
async def download_client_config(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Download client config YAML and certificates. Requires admin, owner, or can_download_config permission."""
    from sqlalchemy.orm import selectinload
    from ..models.client import FirewallRuleset
    from ..models.schemas import ClientConfigDownloadResponse
    import ipaddress

    # Fetch client with relationships
    result = await session.execute(
        select(Client)
        .options(
            selectinload(Client.groups),
            selectinload(Client.firewall_rulesets).selectinload(
                FirewallRuleset.rules).selectinload(FirewallRule.groups)
        )
        .where(Client.id == client_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Access control: admins, owners, or users with can_download_config permission
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = client.owner_user_id == user.id

    if not is_admin and not is_owner:
        # Check if user has download permission
        perm_result = await session.execute(
            select(ClientPermission).where(
                ClientPermission.client_id == client_id,
                ClientPermission.user_id == user.id,
                ClientPermission.can_download_config == True
            )
        )
        perm = perm_result.scalar_one_or_none()
        if not perm:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get IP assignment
    ip_result = await session.execute(
        select(IPAssignment).where(IPAssignment.client_id == client_id)
    )
    ip_assignment = ip_result.scalar_one_or_none()
    if not ip_assignment:
        raise HTTPException(
            status_code=409, detail="Client has no IP assignment")

    # Load settings and active CA(s)
    settings = (await session.execute(select(GlobalSettings))).scalars().first()
    now_ts = datetime.utcnow()
    cas = (
        await session.execute(
            select(CACertificate).where(
                CACertificate.include_in_config == True,
                CACertificate.not_after > now_ts,
            )
        )
    ).scalars().all()
    if not cas:
        raise HTTPException(status_code=503, detail="CA not configured")

    # Determine IP/CIDR prefix for config
    if ip_assignment.pool_id:
        pool = (await session.execute(select(IPPool).where(IPPool.id == ip_assignment.pool_id))).scalars().first()
        cidr = pool.cidr if pool else (
            settings.default_cidr_pool if settings else "10.100.0.0/16")
    else:
        cidr = settings.default_cidr_pool if settings else "10.100.0.0/16"

    try:
        prefix = ipaddress.ip_network(cidr, strict=False).prefixlen
    except Exception:
        prefix = 24

    client_ip_cidr = f"{ip_assignment.ip_address}/{prefix}"

    # Get latest non-revoked certificate
    cert_result = await session.execute(
        select(ClientCertificate)
        .where(
            ClientCertificate.client_id == client_id,
            ClientCertificate.revoked == False
        )
        .order_by(ClientCertificate.created_at.desc())
    )
    cert = cert_result.scalars().first()
    if not cert:
        raise HTTPException(
            status_code=409, detail="No valid certificate found for client")

    # Build lighthouse maps: static_host_map {nebula_ip: ["public_ip:port"]} and hosts list of nebula IPs
    # Only include lighthouses from the same IP pool as the client
    lighthouses = (
        await session.execute(select(Client).where(Client.is_lighthouse == True))
    ).scalars().all()
    static_map: dict[str, list[str]] = {}
    lh_hosts: list[str] = []
    for lh in lighthouses:
        ip_row = (await session.execute(
            select(IPAssignment)
            .where(IPAssignment.client_id == lh.id)
            .order_by(IPAssignment.is_primary.desc(), IPAssignment.id)
        )).scalars().first()
        if not ip_row:
            continue
        if not lh.public_ip:
            continue
        
        # Only include lighthouse if it's in the same pool as the client (or both have no pool)
        if ip_row.pool_id != ip_assignment.pool_id:
            continue
        
        lh_hosts.append(ip_row.ip_address)
        static_map[ip_row.ip_address] = [
            f"{lh.public_ip}:{settings.lighthouse_port if settings else 4242}"]
    
    # If current client is a lighthouse, exclude itself from static_host_map
    # Lighthouses should not have their own IP in the static map
    if client.is_lighthouse and ip_assignment.ip_address in static_map:
        del static_map[ip_assignment.ip_address]

    # Build inline CA bundle (concatenated PEMs)
    ca_bundle = "".join([(c.pem_cert.decode().rstrip() + "\n") for c in cas])

    # Collect revoked fingerprints to distribute
    now = datetime.utcnow()
    revoked_rows = (
        await session.execute(
            select(ClientCertificate.fingerprint).where(
                ClientCertificate.revoked == True,
                ClientCertificate.not_after > now,
                ClientCertificate.fingerprint.isnot(None)
            )
        )
    ).scalars().all()
    revoked_fps = [fp for fp in revoked_rows if fp]

    # Decode cert PEM
    cert_pem = cert.pem_cert.decode(
        'utf-8') if isinstance(cert.pem_cert, bytes) else cert.pem_cert

    # Build config YAML with full lighthouse/revocation info
    config_yaml = build_nebula_config(
        client=client,
        client_ip_cidr=client_ip_cidr,
        settings=settings,
        static_host_map=static_map,
        lighthouse_host_ips=lh_hosts,
        revoked_fingerprints=revoked_fps,
        key_path="/var/lib/nebula/host.key",
        ca_path="/etc/nebula/ca.crt",
        cert_path="/etc/nebula/host.crt",
        inline_ca_pem=ca_bundle,
        inline_cert_pem=cert_pem,
    )

    return ClientConfigDownloadResponse(
        config_yaml=config_yaml,
        client_cert_pem=cert_pem,
        ca_chain_pems=[c.pem_cert.decode() for c in cas]
    )


@router.get("/clients/{client_id}/docker-compose")
async def download_client_docker_compose(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Download docker-compose.yml for client with pre-filled token. Requires admin, owner, or can_download_docker_config permission."""
    from fastapi.responses import Response

    # Fetch client
    result = await session.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Access control: admins, owners, or users with can_download_docker_config permission
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = client.owner_user_id == user.id

    if not is_admin and not is_owner:
        # Check if user has docker config download permission
        perm_result = await session.execute(
            select(ClientPermission).where(
                ClientPermission.client_id == client_id,
                ClientPermission.user_id == user.id,
                ClientPermission.can_download_docker_config == True
            )
        )
        perm = perm_result.scalar_one_or_none()
        if not perm:
            raise HTTPException(status_code=403, detail="Access denied")

    # Get client token
    token_result = await session.execute(
        select(ClientToken).where(ClientToken.client_id ==
                                  client_id, ClientToken.is_active == True)
    )
    token = token_result.scalar_one_or_none()
    if not token:
        raise HTTPException(
            status_code=409, detail="Client has no active token")

    # Get settings for template and values
    settings = (await session.execute(select(GlobalSettings))).scalars().first()
    if not settings:
        settings = GlobalSettings()
        session.add(settings)
        await session.commit()

    # Get template, fallback to default if None
    from ..models.settings import DEFAULT_DOCKER_COMPOSE_TEMPLATE
    template = settings.docker_compose_template
    if not template:
        template = DEFAULT_DOCKER_COMPOSE_TEMPLATE
        # Update the settings record to have the template for future use
        settings.docker_compose_template = template
        await session.commit()

    # Replace placeholders
    compose_content = template.replace("{{CLIENT_NAME}}", client.name)
    compose_content = compose_content.replace("{{CLIENT_TOKEN}}", token.token)
    compose_content = compose_content.replace(
        "{{SERVER_URL}}", settings.server_url)
    compose_content = compose_content.replace(
        "{{CLIENT_DOCKER_IMAGE}}", settings.client_docker_image)
    compose_content = compose_content.replace("{{POLL_INTERVAL_HOURS}}", "24")

    # Return as downloadable file
    return Response(
        content=compose_content,
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f"attachment; filename={client.name}-docker-compose.yml"
        }
    )


# ============ Groups REST API ============

@router.get("/groups", response_model=List[GroupResponse])
async def list_groups(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Group).options(selectinload(
            Group.clients), selectinload(Group.owner))
    )
    groups = result.scalars().all()

    response_groups = []
    for g in groups:
        # Determine parent and subgroup status
        parent_name = None
        is_subgroup = False
        if ':' in g.name:
            is_subgroup = True
            parent_name = ':'.join(g.name.split(':')[:-1])

        owner_ref = None
        if g.owner:
            owner_ref = UserRef(id=g.owner.id, email=g.owner.email)

        response_groups.append(GroupResponse(
            id=g.id,
            name=g.name,
            client_count=len(g.clients),
            owner=owner_ref,
            created_at=g.created_at,
            parent_name=parent_name,
            is_subgroup=is_subgroup
        ))

    return response_groups


@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Group).options(selectinload(Group.clients),
                              selectinload(Group.owner)).where(Group.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Determine parent and subgroup status
    parent_name = None
    is_subgroup = False
    if ':' in group.name:
        is_subgroup = True
        parent_name = ':'.join(group.name.split(':')[:-1])

    owner_ref = None
    if group.owner:
        owner_ref = UserRef(id=group.owner.id, email=group.owner.email)

    return GroupResponse(
        id=group.id,
        name=group.name,
        client_count=len(group.clients),
        owner=owner_ref,
        created_at=group.created_at,
        parent_name=parent_name,
        is_subgroup=is_subgroup
    )


@router.post("/groups", response_model=GroupResponse)
async def create_group(body: GroupCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    # Ensure unique name
    existing = await session.execute(select(Group).where(Group.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Group name already exists")

    # Check if this is a subgroup (contains colon)
    is_subgroup = ':' in body.name
    parent_name = None

    if is_subgroup:
        parent_name = ':'.join(body.name.split(':')[:-1])
        # Verify parent exists
        parent_result = await session.execute(select(Group).where(Group.name == parent_name))
        parent_group = parent_result.scalar_one_or_none()
        if not parent_group:
            raise HTTPException(
                status_code=400, detail=f"Parent group '{parent_name}' does not exist")

        # Check if user has permission to create subgroups of parent (unless admin)
        is_admin = await user.has_permission(session, "users", "delete")
        is_parent_owner = parent_group.owner_user_id == user.id

        if not is_admin and not is_parent_owner:
            # Check if user has can_create_subgroup permission via GroupPermission
            from ..models.permissions import GroupPermission
            perm_result = await session.execute(
                select(GroupPermission).where(
                    GroupPermission.group_id == parent_group.id,
                    GroupPermission.user_id == user.id,
                    GroupPermission.can_create_subgroup == True
                )
            )
            if not perm_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=403, detail="You don't have permission to create subgroups of this parent")

    # Create group with current user as owner
    group = Group(name=body.name, owner_user_id=user.id,
                  created_at=datetime.utcnow())
    session.add(group)
    await session.commit()
    await session.refresh(group)

    owner_ref = UserRef(id=user.id, email=user.email)
    return GroupResponse(
        id=group.id,
        name=group.name,
        client_count=0,
        owner=owner_ref,
        created_at=group.created_at,
        parent_name=parent_name,
        is_subgroup=is_subgroup
    )


@router.put("/groups/{group_id}", response_model=GroupResponse)
async def update_group(group_id: int, body: GroupUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Group).options(selectinload(Group.owner),
                              selectinload(Group.clients)).where(Group.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check permissions (admin or owner)
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = group.owner_user_id == user.id

    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only group owner or admin can update group")

    # Check duplicate name (other group)
    name_check = await session.execute(select(Group).where(Group.name == body.name, Group.id != group_id))
    if name_check.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Another group with that name exists")

    group.name = body.name
    await session.commit()
    await session.refresh(group)

    # Determine parent and subgroup status
    parent_name = None
    is_subgroup = False
    if ':' in group.name:
        is_subgroup = True
        parent_name = ':'.join(group.name.split(':')[:-1])

    owner_ref = None
    if group.owner:
        owner_ref = UserRef(id=group.owner.id, email=group.owner.email)

    return GroupResponse(
        id=group.id,
        name=group.name,
        client_count=len(group.clients),
        owner=owner_ref,
        created_at=group.created_at,
        parent_name=parent_name,
        is_subgroup=is_subgroup
    )


@router.delete("/groups/{group_id}")
async def delete_group(group_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    # Find group
    group_result = await session.execute(select(Group).where(Group.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check permissions (admin or owner)
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = group.owner_user_id == user.id

    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only group owner or admin can delete group")

    # Check if any clients use this group
    clients_using = await session.execute(select(Client).join(client_groups).where(client_groups.c.group_id == group_id))
    if clients_using.scalars().first():
        raise HTTPException(
            status_code=409, detail="Group still in use by one or more clients")

    # Check if this group has subgroups (any group with name starting with "groupname:")
    subgroups_check = await session.execute(
        select(Group).where(Group.name.like(f"{group.name}:%"))
    )
    if subgroups_check.scalars().first():
        raise HTTPException(
            status_code=409, detail="Cannot delete group with subgroups. Delete subgroups first.")

    await session.delete(group)
    await session.commit()
    return {"status": "deleted", "id": group_id}

# ============ Group Permissions REST API ============


@router.get("/groups/{group_id}/permissions", response_model=List[GroupPermissionResponse])
async def list_group_permissions(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """List all permissions for a group (owner or admin only)"""
    from ..models.permissions import GroupPermission
    from sqlalchemy.orm import selectinload

    # Get group with owner
    group_result = await session.execute(
        select(Group).options(selectinload(
            Group.owner)).where(Group.id == group_id)
    )
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check permissions (admin or owner)
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = group.owner_user_id == user.id

    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only group owner or admin can view permissions")

    # Get all permissions
    perms_result = await session.execute(
        select(GroupPermission).options(
            selectinload(GroupPermission.user),
            selectinload(GroupPermission.user_group)
        ).where(GroupPermission.group_id == group_id)
    )
    permissions = perms_result.scalars().all()

    response = []
    for perm in permissions:
        user_ref = None
        user_group_ref = None

        if perm.user:
            user_ref = UserRef(id=perm.user.id, email=perm.user.email)
        if perm.user_group:
            user_group_ref = UserGroupRef(
                id=perm.user_group.id, name=perm.user_group.name)

        response.append(GroupPermissionResponse(
            id=perm.id,
            group_id=perm.group_id,
            user=user_ref,
            user_group=user_group_ref,
            can_add_to_client=perm.can_add_to_client,
            can_remove_from_client=perm.can_remove_from_client,
            can_create_subgroup=perm.can_create_subgroup
        ))

    return response


@router.post("/groups/{group_id}/permissions", response_model=GroupPermissionResponse)
async def grant_group_permission(
    group_id: int,
    body: GroupPermissionGrant,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Grant permission on a group (owner or admin only)"""
    from ..models.permissions import GroupPermission, UserGroup
    from sqlalchemy.orm import selectinload

    # Get group with owner
    group_result = await session.execute(
        select(Group).options(selectinload(
            Group.owner)).where(Group.id == group_id)
    )
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check permissions (admin or owner)
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = group.owner_user_id == user.id

    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only group owner or admin can grant permissions")

    # Validate: must have either user_id or user_group_id, not both or neither
    if (body.user_id is None and body.user_group_id is None) or \
       (body.user_id is not None and body.user_group_id is not None):
        raise HTTPException(
            status_code=400, detail="Must specify either user_id or user_group_id, not both or neither")

    # Verify user or user_group exists
    if body.user_id:
        target_user_result = await session.execute(select(User).where(User.id == body.user_id))
        target_user = target_user_result.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=404, detail="Target user not found")

    if body.user_group_id:
        target_ug_result = await session.execute(select(UserGroup).where(UserGroup.id == body.user_group_id))
        target_ug = target_ug_result.scalar_one_or_none()
        if not target_ug:
            raise HTTPException(
                status_code=404, detail="Target user group not found")

    # Check for existing permission (upsert)
    existing_perm_query = select(GroupPermission).where(
        GroupPermission.group_id == group_id)
    if body.user_id:
        existing_perm_query = existing_perm_query.where(
            GroupPermission.user_id == body.user_id)
    else:
        existing_perm_query = existing_perm_query.where(
            GroupPermission.user_group_id == body.user_group_id)

    existing_perm_result = await session.execute(existing_perm_query)
    existing_perm = existing_perm_result.scalar_one_or_none()

    if existing_perm:
        # Update
        existing_perm.can_add_to_client = body.can_add_to_client
        existing_perm.can_remove_from_client = body.can_remove_from_client
        existing_perm.can_create_subgroup = body.can_create_subgroup
        await session.commit()
        await session.refresh(existing_perm, ['user', 'user_group'])
        perm = existing_perm
    else:
        # Create new
        perm = GroupPermission(
            group_id=group_id,
            user_id=body.user_id,
            user_group_id=body.user_group_id,
            can_add_to_client=body.can_add_to_client,
            can_remove_from_client=body.can_remove_from_client,
            can_create_subgroup=body.can_create_subgroup
        )
        session.add(perm)
        await session.commit()
        await session.refresh(perm, ['user', 'user_group'])

    # Build response
    user_ref = None
    user_group_ref = None

    if perm.user:
        user_ref = UserRef(id=perm.user.id, email=perm.user.email)
    if perm.user_group:
        user_group_ref = UserGroupRef(
            id=perm.user_group.id, name=perm.user_group.name)

    return GroupPermissionResponse(
        id=perm.id,
        group_id=perm.group_id,
        user=user_ref,
        user_group=user_group_ref,
        can_add_to_client=perm.can_add_to_client,
        can_remove_from_client=perm.can_remove_from_client,
        can_create_subgroup=perm.can_create_subgroup
    )


@router.delete("/groups/{group_id}/permissions/{permission_id}")
async def revoke_group_permission(
    group_id: int,
    permission_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Revoke a permission from a group (owner or admin only)"""
    from ..models.permissions import GroupPermission
    from sqlalchemy.orm import selectinload

    # Get group with owner
    group_result = await session.execute(
        select(Group).options(selectinload(
            Group.owner)).where(Group.id == group_id)
    )
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Check permissions (admin or owner)
    is_admin = await user.has_permission(session, "users", "delete")
    is_owner = group.owner_user_id == user.id

    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403, detail="Only group owner or admin can revoke permissions")

    # Get permission
    perm_result = await session.execute(
        select(GroupPermission).where(
            GroupPermission.id == permission_id,
            GroupPermission.group_id == group_id
        )
    )
    perm = perm_result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")

    await session.delete(perm)
    await session.commit()

    return {"status": "revoked", "id": permission_id}

# ============ Firewall Rulesets REST API ============


@router.get("/firewall-rulesets", response_model=List[FirewallRulesetResponse], response_model_exclude_none=True)
async def list_firewall_rulesets(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    from sqlalchemy.orm import selectinload
    from ..models.client import FirewallRuleset
    result = await session.execute(
        select(FirewallRuleset).options(
            selectinload(FirewallRuleset.rules).selectinload(
                FirewallRule.groups),
            selectinload(FirewallRuleset.clients)
        )
    )
    rulesets = result.scalars().all()

    responses = []
    for rs in rulesets:
        rule_responses = [
            FirewallRuleResponse(
                id=r.id,
                direction=r.direction,
                port=r.port,
                proto=r.proto,
                host=r.host,
                cidr=r.cidr,
                local_cidr=r.local_cidr,
                ca_name=r.ca_name,
                ca_sha=r.ca_sha,
                groups=[GroupRef(id=g.id, name=g.name) for g in r.groups] if r.groups else None
            )
            for r in rs.rules
        ]
        responses.append(FirewallRulesetResponse(
            id=rs.id,
            name=rs.name,
            description=rs.description,
            rules=rule_responses,
            client_count=len(rs.clients)
        ))
    return responses


@router.get("/firewall-rulesets/{ruleset_id}", response_model=FirewallRulesetResponse, response_model_exclude_none=True)
async def get_firewall_ruleset(ruleset_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    from sqlalchemy.orm import selectinload
    from ..models.client import FirewallRuleset
    result = await session.execute(
        select(FirewallRuleset).options(
            selectinload(FirewallRuleset.rules).selectinload(
                FirewallRule.groups),
            selectinload(FirewallRuleset.clients)
        ).where(FirewallRuleset.id == ruleset_id)
    )
    rs = result.scalar_one_or_none()
    if not rs:
        raise HTTPException(
            status_code=404, detail="Firewall ruleset not found")

    rule_responses = [
        FirewallRuleResponse(
            id=r.id,
            direction=r.direction,
            port=r.port,
            proto=r.proto,
            host=r.host,
            cidr=r.cidr,
            local_cidr=r.local_cidr,
            ca_name=r.ca_name,
            ca_sha=r.ca_sha,
            groups=[GroupRef(id=g.id, name=g.name) for g in r.groups] if r.groups else None
        )
        for r in rs.rules
    ]
    return FirewallRulesetResponse(
        id=rs.id,
        name=rs.name,
        description=rs.description,
        rules=rule_responses,
        client_count=len(rs.clients)
    )


@router.post("/firewall-rulesets", response_model=FirewallRulesetResponse, response_model_exclude_none=True)
async def create_firewall_ruleset(body: FirewallRulesetCreate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("firewall_rules", "create"))):
    from ..models.client import FirewallRuleset
    # Check duplicate name
    existing = await session.execute(select(FirewallRuleset).where(FirewallRuleset.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Firewall ruleset name already exists")

    # Validate and create rules
    rules_to_add = []
    for rule_data in body.rules:
        # Validate direction
        if rule_data.direction not in ("inbound", "outbound"):
            raise HTTPException(
                status_code=400, detail=f"Invalid direction: {rule_data.direction}")
        # Validate proto
        if rule_data.proto not in ("any", "tcp", "udp", "icmp"):
            raise HTTPException(
                status_code=400, detail=f"Invalid proto: {rule_data.proto}")
        # Validate at least one targeting field
        has_target = (
            rule_data.host or
            rule_data.cidr or
            rule_data.local_cidr or
            rule_data.ca_name or
            rule_data.ca_sha or
            (rule_data.group_ids and len(rule_data.group_ids) > 0)
        )
        if not has_target:
            raise HTTPException(
                status_code=400,
                detail="Each rule must specify at least one of: host, cidr, local_cidr, ca_name, ca_sha, or groups"
            )

        rule = FirewallRule(
            direction=rule_data.direction,
            port=rule_data.port,
            proto=rule_data.proto,
            host=rule_data.host,
            cidr=rule_data.cidr,
            local_cidr=rule_data.local_cidr,
            ca_name=rule_data.ca_name,
            ca_sha=rule_data.ca_sha,
        )

        # Assign groups if provided
        if rule_data.group_ids:
            groups_result = await session.execute(select(Group).where(Group.id.in_(rule_data.group_ids)))
            groups = groups_result.scalars().all()
            if len(groups) != len(rule_data.group_ids):
                raise HTTPException(
                    status_code=400, detail="One or more group IDs not found")
            rule.groups = groups
        else:
            # Explicitly set empty list to avoid async lazy-load on access
            rule.groups = []

        session.add(rule)
        rules_to_add.append(rule)

    # Create ruleset
    ruleset = FirewallRuleset(
        name=body.name,
        description=body.description,
        rules=rules_to_add
    )
    session.add(ruleset)
    await session.commit()
    await session.refresh(ruleset)

    # Build response without triggering async lazy-loads; use the in-memory rules we created
    rule_responses = [
        FirewallRuleResponse(
            id=r.id,
            direction=r.direction,
            port=r.port,
            proto=r.proto,
            host=r.host,
            cidr=r.cidr,
            local_cidr=r.local_cidr,
            ca_name=r.ca_name,
            ca_sha=r.ca_sha,
            groups=[GroupRef(id=g.id, name=g.name) for g in r.groups] if r.groups else None
        )
        for r in rules_to_add
    ]
    return FirewallRulesetResponse(
        id=ruleset.id,
        name=ruleset.name,
        description=ruleset.description,
        rules=rule_responses,
        client_count=0
    )


@router.put("/firewall-rulesets/{ruleset_id}", response_model=FirewallRulesetResponse, response_model_exclude_none=True)
async def update_firewall_ruleset(ruleset_id: int, body: FirewallRulesetUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("firewall_rules", "update"))):
    from sqlalchemy.orm import selectinload
    from ..models.client import FirewallRuleset
    result = await session.execute(
        select(FirewallRuleset).options(
            selectinload(FirewallRuleset.rules).selectinload(
                FirewallRule.groups),
            selectinload(FirewallRuleset.clients)
        ).where(FirewallRuleset.id == ruleset_id)
    )
    ruleset = result.scalar_one_or_none()
    if not ruleset:
        raise HTTPException(
            status_code=404, detail="Firewall ruleset not found")

    # Update name if provided
    if body.name is not None:
        # Check duplicate name
        name_check = await session.execute(
            select(FirewallRuleset).where(FirewallRuleset.name ==
                                          body.name, FirewallRuleset.id != ruleset_id)
        )
        if name_check.scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail="Another firewall ruleset with that name exists")
        ruleset.name = body.name

    if body.description is not None:
        ruleset.description = body.description

    # Replace rules if provided
    if body.rules is not None:
        # Delete old rules
        for old_rule in ruleset.rules:
            await session.delete(old_rule)

        # Create new rules
        new_rules = []
        for rule_data in body.rules:
            if rule_data.direction not in ("inbound", "outbound"):
                raise HTTPException(
                    status_code=400, detail=f"Invalid direction: {rule_data.direction}")
            if rule_data.proto not in ("any", "tcp", "udp", "icmp"):
                raise HTTPException(
                    status_code=400, detail=f"Invalid proto: {rule_data.proto}")
            # Validate at least one targeting field
            has_target = (
                rule_data.host or
                rule_data.cidr or
                rule_data.local_cidr or
                rule_data.ca_name or
                rule_data.ca_sha or
                (rule_data.group_ids and len(rule_data.group_ids) > 0)
            )
            if not has_target:
                raise HTTPException(
                    status_code=400,
                    detail="Each rule must specify at least one of: host, cidr, local_cidr, ca_name, ca_sha, or groups"
                )

            rule = FirewallRule(
                direction=rule_data.direction,
                port=rule_data.port,
                proto=rule_data.proto,
                host=rule_data.host,
                cidr=rule_data.cidr,
                local_cidr=rule_data.local_cidr,
                ca_name=rule_data.ca_name,
                ca_sha=rule_data.ca_sha,
            )

            if rule_data.group_ids:
                groups_result = await session.execute(select(Group).where(Group.id.in_(rule_data.group_ids)))
                groups = groups_result.scalars().all()
                if len(groups) != len(rule_data.group_ids):
                    raise HTTPException(
                        status_code=400, detail="One or more group IDs not found")
                rule.groups = groups
            else:
                # Explicitly set empty list to avoid async lazy-load on access
                rule.groups = []

            session.add(rule)
            new_rules.append(rule)

        ruleset.rules = new_rules

    await session.commit()
    await session.refresh(ruleset)

    # Build response
    rule_responses = [
        FirewallRuleResponse(
            id=r.id,
            direction=r.direction,
            port=r.port,
            proto=r.proto,
            host=r.host,
            cidr=r.cidr,
            local_cidr=r.local_cidr,
            ca_name=r.ca_name,
            ca_sha=r.ca_sha,
            groups=[GroupRef(id=g.id, name=g.name) for g in r.groups] if r.groups else None
        )
        for r in ruleset.rules
    ]
    return FirewallRulesetResponse(
        id=ruleset.id,
        name=ruleset.name,
        description=ruleset.description,
        rules=rule_responses,
        client_count=len(ruleset.clients)
    )


@router.delete("/firewall-rulesets/{ruleset_id}")
async def delete_firewall_ruleset(ruleset_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("firewall_rules", "delete"))):
    from ..models.client import FirewallRuleset, client_firewall_rulesets
    result = await session.execute(select(FirewallRuleset).where(FirewallRuleset.id == ruleset_id))
    ruleset = result.scalar_one_or_none()
    if not ruleset:
        raise HTTPException(
            status_code=404, detail="Firewall ruleset not found")

    # Check if any clients use this ruleset
    clients_using = await session.execute(
        select(Client).join(client_firewall_rulesets).where(
            client_firewall_rulesets.c.firewall_ruleset_id == ruleset_id)
    )
    if clients_using.scalars().first():
        raise HTTPException(
            status_code=409, detail="Firewall ruleset still in use by one or more clients")

    await session.delete(ruleset)
    await session.commit()
    return {"status": "deleted", "id": ruleset_id}

# ============ IP Pools REST API ============


def _validate_cidr(cidr: str):
    try:
        ipaddress.ip_network(cidr, strict=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CIDR: {e}")


@router.get("/ip-pools", response_model=List[IPPoolResponse])
async def list_ip_pools(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    pools_result = await session.execute(select(IPPool))
    pools = pools_result.scalars().all()
    responses: List[IPPoolResponse] = []
    for pool in pools:
        count_result = await session.execute(select(IPAssignment).where(IPAssignment.pool_id == pool.id))
        allocated = len(count_result.scalars().all())
        responses.append(IPPoolResponse(id=pool.id, cidr=pool.cidr,
                         description=pool.description, allocated_count=allocated))
    return responses


@router.get("/ip-pools/{pool_id}", response_model=IPPoolResponse)
async def get_ip_pool(pool_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    pool_result = await session.execute(select(IPPool).where(IPPool.id == pool_id))
    pool = pool_result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="IP pool not found")
    count_result = await session.execute(select(IPAssignment).where(IPAssignment.pool_id == pool.id))
    allocated = len(count_result.scalars().all())
    return IPPoolResponse(id=pool.id, cidr=pool.cidr, description=pool.description, allocated_count=allocated)


@router.post("/ip-pools", response_model=IPPoolResponse)
async def create_ip_pool_new(body: IPPoolCreate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_pools", "create"))):
    _validate_cidr(body.cidr)
    # Check duplicate CIDR
    existing = await session.execute(select(IPPool).where(IPPool.cidr == body.cidr))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="IP pool CIDR already exists")
    pool = IPPool(cidr=body.cidr, description=body.description)
    session.add(pool)
    await session.commit()
    await session.refresh(pool)
    return IPPoolResponse(id=pool.id, cidr=pool.cidr, description=pool.description, allocated_count=0)


@router.put("/ip-pools/{pool_id}", response_model=IPPoolResponse)
async def update_ip_pool(pool_id: int, body: IPPoolUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_pools", "update"))):
    pool_result = await session.execute(select(IPPool).where(IPPool.id == pool_id))
    pool = pool_result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="IP pool not found")
    # If cidr change requested, validate and ensure no allocations exist
    if body.cidr is not None and body.cidr != pool.cidr:
        _validate_cidr(body.cidr)
        allocs = await session.execute(select(IPAssignment).where(IPAssignment.pool_id == pool.id))
        if allocs.scalars().first():
            raise HTTPException(
                status_code=409, detail="Cannot change CIDR of a pool with allocated IPs")
        # Check duplicate CIDR
        other = await session.execute(select(IPPool).where(IPPool.cidr == body.cidr, IPPool.id != pool.id))
        if other.scalar_one_or_none():
            raise HTTPException(
                status_code=409, detail="Another pool with this CIDR already exists")
        pool.cidr = body.cidr
    if body.description is not None:
        pool.description = body.description
    await session.commit()
    await session.refresh(pool)
    count_result = await session.execute(select(IPAssignment).where(IPAssignment.pool_id == pool.id))
    allocated = len(count_result.scalars().all())
    return IPPoolResponse(id=pool.id, cidr=pool.cidr, description=pool.description, allocated_count=allocated)


@router.delete("/ip-pools/{pool_id}")
async def delete_ip_pool(pool_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_pools", "delete"))):
    pool_result = await session.execute(select(IPPool).where(IPPool.id == pool_id))
    pool = pool_result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="IP pool not found")
    # Check for allocations
    allocs = await session.execute(select(IPAssignment).where(IPAssignment.pool_id == pool.id))
    if allocs.scalars().first():
        raise HTTPException(
            status_code=409, detail="IP pool has allocated IPs and cannot be deleted")
    await session.delete(pool)
    await session.commit()
    return {"status": "deleted", "id": pool_id}


@router.get("/ip-pools/{pool_id}/clients", response_model=List[ClientResponse])
async def get_pool_clients(pool_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_pools", "read"))):
    """Get all clients using a specific IP pool."""
    # Verify pool exists
    pool_result = await session.execute(select(IPPool).where(IPPool.id == pool_id))
    pool = pool_result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="IP pool not found")

    # Get clients with IP assignments from this pool
    result = await session.execute(
        select(Client)
        .join(IPAssignment, Client.id == IPAssignment.client_id)
        .where(IPAssignment.pool_id == pool_id)
        .options(selectinload(Client.groups), selectinload(Client.firewall_rulesets))
    )
    clients = result.scalars().unique().all()

    # Build responses using helper
    is_admin = await user.has_permission(session, "users", "delete")
    responses = []
    for client in clients:
        responses.append(await build_client_response(client, session, user, include_token=is_admin))

    return responses


@router.get("/ip-pools/{pool_id}/available-ips", response_model=List[AvailableIPResponse])
async def get_available_ips(
    pool_id: int,
    ip_group_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("ip_pools", "read"))
):
    """Get available IP addresses in a pool, optionally filtered by IP group."""
    import ipaddress

    # Verify pool exists
    pool_result = await session.execute(select(IPPool).where(IPPool.id == pool_id))
    pool = pool_result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="IP pool not found")

    network = ipaddress.ip_network(pool.cidr)

    # Get assigned IPs in this pool
    assigned_result = await session.execute(
        select(IPAssignment.ip_address).where(IPAssignment.pool_id == pool_id)
    )
    assigned_ips = {row[0] for row in assigned_result.all()}

    # If IP group specified, filter by group range
    if ip_group_id:
        group_result = await session.execute(
            select(IPGroup).where(IPGroup.id ==
                                  ip_group_id, IPGroup.pool_id == pool_id)
        )
        group = group_result.scalar_one_or_none()
        if not group:
            raise HTTPException(
                status_code=404, detail="IP group not found or doesn't belong to this pool")

        start_ip = ipaddress.ip_address(group.start_ip)
        end_ip = ipaddress.ip_address(group.end_ip)

        available = []
        for ip in network.hosts():
            if start_ip <= ip <= end_ip and str(ip) not in assigned_ips:
                available.append(AvailableIPResponse(ip_address=str(ip)))
                if len(available) >= 100:  # Limit to 100 IPs
                    break
    else:
        # Return all available IPs in the pool (limited to 100)
        available = []
        for ip in network.hosts():
            if str(ip) not in assigned_ips:
                available.append(AvailableIPResponse(ip_address=str(ip)))
                if len(available) >= 100:
                    break

    return available


# ============ IP Groups ============

@router.get("/ip-groups", response_model=List[IPGroupResponse])
async def list_ip_groups(pool_id: Optional[int] = None, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_groups", "read"))):
    """List all IP groups, optionally filtered by pool."""
    query = select(IPGroup)
    if pool_id:
        query = query.where(IPGroup.pool_id == pool_id)
    result = await session.execute(query)
    groups = result.scalars().all()

    responses = []
    for group in groups:
        # Count clients using this IP group
        count_result = await session.execute(
            select(IPAssignment).where(IPAssignment.ip_group_id == group.id)
        )
        client_count = len(count_result.scalars().all())
        responses.append(IPGroupResponse(
            id=group.id,
            pool_id=group.pool_id,
            name=group.name,
            start_ip=group.start_ip,
            end_ip=group.end_ip,
            client_count=client_count
        ))
    return responses


@router.get("/ip-groups/{group_id}", response_model=IPGroupResponse)
async def get_ip_group(group_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_groups", "read"))):
    result = await session.execute(select(IPGroup).where(IPGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="IP group not found")

    # Count clients
    count_result = await session.execute(
        select(IPAssignment).where(IPAssignment.ip_group_id == group.id)
    )
    client_count = len(count_result.scalars().all())

    return IPGroupResponse(
        id=group.id,
        pool_id=group.pool_id,
        name=group.name,
        start_ip=group.start_ip,
        end_ip=group.end_ip,
        client_count=client_count
    )


@router.post("/ip-groups", response_model=IPGroupResponse)
async def create_ip_group(body: IPGroupCreate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_groups", "create"))):
    import ipaddress

    # Verify pool exists
    pool_result = await session.execute(select(IPPool).where(IPPool.id == body.pool_id))
    pool = pool_result.scalar_one_or_none()
    if not pool:
        raise HTTPException(status_code=404, detail="IP pool not found")

    # Validate IP addresses are within pool CIDR
    try:
        network = ipaddress.ip_network(pool.cidr)
        start_ip = ipaddress.ip_address(body.start_ip)
        end_ip = ipaddress.ip_address(body.end_ip)

        if start_ip not in network or end_ip not in network:
            raise HTTPException(
                status_code=400, detail="IP range must be within pool CIDR")
        if start_ip > end_ip:
            raise HTTPException(
                status_code=400, detail="start_ip must be less than or equal to end_ip")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid IP address: {e}")

    group = IPGroup(
        pool_id=body.pool_id,
        name=body.name,
        start_ip=body.start_ip,
        end_ip=body.end_ip
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)

    return IPGroupResponse(
        id=group.id,
        pool_id=group.pool_id,
        name=group.name,
        start_ip=group.start_ip,
        end_ip=group.end_ip,
        client_count=0
    )


@router.put("/ip-groups/{group_id}", response_model=IPGroupResponse)
async def update_ip_group(group_id: int, body: IPGroupUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_groups", "update"))):
    import ipaddress

    result = await session.execute(select(IPGroup).where(IPGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="IP group not found")

    # Get pool for validation
    pool_result = await session.execute(select(IPPool).where(IPPool.id == group.pool_id))
    pool = pool_result.scalar_one_or_none()
    network = ipaddress.ip_network(pool.cidr)

    # Update fields
    if body.name is not None:
        group.name = body.name

    start_ip_str = body.start_ip if body.start_ip is not None else group.start_ip
    end_ip_str = body.end_ip if body.end_ip is not None else group.end_ip

    # Validate new range
    try:
        start_ip = ipaddress.ip_address(start_ip_str)
        end_ip = ipaddress.ip_address(end_ip_str)

        if start_ip not in network or end_ip not in network:
            raise HTTPException(
                status_code=400, detail="IP range must be within pool CIDR")
        if start_ip > end_ip:
            raise HTTPException(
                status_code=400, detail="start_ip must be less than or equal to end_ip")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid IP address: {e}")

    if body.start_ip is not None:
        group.start_ip = body.start_ip
    if body.end_ip is not None:
        group.end_ip = body.end_ip

    await session.commit()
    await session.refresh(group)

    # Count clients
    count_result = await session.execute(
        select(IPAssignment).where(IPAssignment.ip_group_id == group.id)
    )
    client_count = len(count_result.scalars().all())

    return IPGroupResponse(
        id=group.id,
        pool_id=group.pool_id,
        name=group.name,
        start_ip=group.start_ip,
        end_ip=group.end_ip,
        client_count=client_count
    )


@router.delete("/ip-groups/{group_id}")
async def delete_ip_group(group_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_groups", "delete"))):
    result = await session.execute(select(IPGroup).where(IPGroup.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="IP group not found")

    # Check for assignments
    assignments = await session.execute(
        select(IPAssignment).where(IPAssignment.ip_group_id == group.id)
    )
    if assignments.scalars().first():
        raise HTTPException(
            status_code=409, detail="IP group has assigned IPs and cannot be deleted")

    await session.delete(group)
    await session.commit()
    return {"status": "deleted", "id": group_id}


@router.get("/ip-groups/{group_id}/clients", response_model=List[ClientResponse])
async def get_group_clients(group_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ip_groups", "read"))):
    """Get all clients using a specific IP group."""
    # Verify group exists
    group_result = await session.execute(select(IPGroup).where(IPGroup.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="IP group not found")

    # Get clients with IP assignments from this group
    result = await session.execute(
        select(Client)
        .join(IPAssignment, Client.id == IPAssignment.client_id)
        .where(IPAssignment.ip_group_id == group_id)
        .options(selectinload(Client.groups), selectinload(Client.firewall_rulesets))
    )
    clients = result.scalars().unique().all()

    # Build responses using helper
    is_admin = await user.has_permission(session, "users", "delete")
    responses = []
    for client in clients:
        responses.append(await build_client_response(client, session, user, include_token=is_admin))

    return responses


# ============ CA Management REST API ============

def _classify_ca_status(ca: CACertificate) -> str:
    now = datetime.utcnow()
    if now > ca.not_after:
        return "expired"
    elif ca.is_previous:
        return "previous"
    elif ca.is_active:
        return "current"
    else:
        return "inactive"


@router.get("/ca", response_model=List[CAResponse])
async def list_cas(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    result = await session.execute(select(CACertificate))
    cas = result.scalars().all()
    return [
        CAResponse(
            id=ca.id,
            name=ca.name,
            not_before=ca.not_before,
            not_after=ca.not_after,
            is_active=ca.is_active,
            is_previous=ca.is_previous,
            can_sign=ca.can_sign,
            include_in_config=ca.include_in_config,
            created_at=ca.created_at,
            status=_classify_ca_status(ca),
            cert_version=getattr(ca, 'cert_version', 'v1'),  # Default to v1 for existing CAs
            nebula_version=getattr(ca, 'nebula_version', None)  # May be None for existing CAs
        )
        for ca in cas
    ]


@router.post("/ca/create", response_model=CAResponse)
async def create_ca(body: CACreate, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ca", "create"))):
    # Use CertManager to create CA
    cert_manager = CertManager(session)
    ca_name = body.name
    cert_version = body.cert_version or "v1"
    
    # Validate cert_version
    if cert_version not in ["v1", "v2"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cert_version '{cert_version}'. Must be 'v1' or 'v2'."
        )
    
    # Check if v2 requires Nebula 1.10.0+
    if cert_version == "v2":
        settings_row = (await session.execute(select(GlobalSettings))).scalars().first()
        nebula_ver = getattr(settings_row, 'nebula_version', '1.9.7') if settings_row else '1.9.7'
        if not _is_v2_compatible(nebula_ver):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create v2 CA. Server Nebula version {nebula_ver} does not support v2 certificates. Requires Nebula 1.10.0+ or nightly build."
            )

    try:
        ca = await cert_manager.create_new_ca(ca_name, cert_version=cert_version)
        await session.commit()
        await session.refresh(ca)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create CA: {e}")

    return CAResponse(
        id=ca.id,
        name=ca.name,
        not_before=ca.not_before,
        not_after=ca.not_after,
        is_active=ca.is_active,
        is_previous=ca.is_previous,
        can_sign=ca.can_sign,
        include_in_config=ca.include_in_config,
        created_at=ca.created_at,
        status=_classify_ca_status(ca),
        cert_version=getattr(ca, 'cert_version', 'v1'),
        nebula_version=getattr(ca, 'nebula_version', None)
    )


@router.post("/ca/import", response_model=CAResponse)
async def import_ca(body: CAImport, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ca", "create"))):
    """
    Import a CA certificate (with or without private key), extracting real validity dates from the PEM.
    """
    cert_manager = CertManager(session)
    if body.pem_key:
        ca = await cert_manager.import_existing_ca(body.name, body.pem_cert, body.pem_key)
    else:
        ca = await cert_manager.import_public_ca(body.name, body.pem_cert)
    await session.refresh(ca)
    return CAResponse(
        id=ca.id,
        name=ca.name,
        not_before=ca.not_before,
        not_after=ca.not_after,
        is_active=ca.is_active,
        is_previous=ca.is_previous,
        can_sign=ca.can_sign,
        include_in_config=ca.include_in_config,
        created_at=ca.created_at,
        status=_classify_ca_status(ca),
        cert_version=getattr(ca, 'cert_version', 'v1'),
        nebula_version=getattr(ca, 'nebula_version', None)
    )


@router.post("/ca/{ca_id}/set-signing", response_model=CAResponse)
async def set_signing_ca(ca_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ca", "update"))):
    """Set a CA as the active signing CA. Current active CAs will be marked as previous."""
    result = await session.execute(select(CACertificate).where(CACertificate.id == ca_id))
    ca = result.scalar_one_or_none()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")
    
    if not ca.can_sign:
        raise HTTPException(status_code=400, detail="This CA cannot be used for signing (no private key)")
    
    # Mark all current active signing CAs as previous
    active_cas = (await session.execute(
        select(CACertificate).where(CACertificate.is_active == True, CACertificate.can_sign == True)
    )).scalars().all()
    
    for active_ca in active_cas:
        if active_ca.id != ca_id:
            active_ca.is_active = False
            active_ca.is_previous = True
            active_ca.include_in_config = True
    
    # Set this CA as active
    ca.is_active = True
    ca.is_previous = False
    ca.include_in_config = True
    
    await session.commit()
    await session.refresh(ca)
    
    return CAResponse(
        id=ca.id,
        name=ca.name,
        not_before=ca.not_before,
        not_after=ca.not_after,
        is_active=ca.is_active,
        is_previous=ca.is_previous,
        can_sign=ca.can_sign,
        include_in_config=ca.include_in_config,
        created_at=ca.created_at,
        status=_classify_ca_status(ca),
        cert_version=getattr(ca, 'cert_version', 'v1'),
        nebula_version=getattr(ca, 'nebula_version', None)
    )

@router.delete("/ca/{ca_id}")
async def delete_ca(ca_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("ca", "delete"))):
    result = await session.execute(select(CACertificate).where(CACertificate.id == ca_id))
    ca = result.scalar_one_or_none()
    if not ca:
        raise HTTPException(status_code=404, detail="CA not found")

    # Prevent deletion of active CA
    if ca.is_active:
        raise HTTPException(status_code=409, detail="Cannot delete active CA. Please deactivate it first by setting another CA as the signing CA.")

    await session.delete(ca)
    await session.commit()
    return {"status": "deleted", "id": ca_id}


# ============ Users REST API ============

@router.get("/users", response_model=List[UserResponse])
async def list_users(session: AsyncSession = Depends(get_session), user: User = Depends(require_permission("users", "read"))):
    from sqlalchemy.orm import selectinload
    from ..models.permissions import UserGroup, UserGroupMembership
    result = await session.execute(select(User))
    users = result.scalars().all()
    responses: List[UserResponse] = []
    for u in users:
        memberships = await session.execute(
            select(UserGroup)
            .join(UserGroupMembership, UserGroupMembership.user_group_id == UserGroup.id)
            .where(UserGroupMembership.user_id == u.id)
        )
        groups = memberships.scalars().all()
        responses.append(UserResponse(
            id=u.id,
            email=u.email,
            is_active=u.is_active,
            groups=[UserGroupRef(id=g.id, name=g.name) for g in groups],
            created_at=u.created_at
        ))
    return responses


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, session: AsyncSession = Depends(get_session), admin: User = Depends(require_permission("users", "read"))):
    from sqlalchemy.orm import selectinload
    from ..models.permissions import UserGroup, UserGroupMembership
    result = await session.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    memberships = await session.execute(
        select(UserGroup)
        .join(UserGroupMembership, UserGroupMembership.user_group_id == UserGroup.id)
        .where(UserGroupMembership.user_id == u.id)
    )
    groups = memberships.scalars().all()
    return UserResponse(
        id=u.id,
        email=u.email,
        is_active=u.is_active,
        groups=[UserGroupRef(id=g.id, name=g.name) for g in groups],
        created_at=u.created_at
    )


@router.post("/users", response_model=UserResponse)
async def create_user(body: UserCreate, session: AsyncSession = Depends(get_session), admin: User = Depends(require_permission("users", "create"))):
    # Respect external user management setting
    if settings.externally_managed_users:
        raise HTTPException(status_code=403, detail="Users are managed externally; local creation is disabled")
    from ..core.auth import hash_password
    from ..models.permissions import UserGroup, UserGroupMembership
    from sqlalchemy.orm import selectinload

    # Check duplicate email
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    # Hash password
    hashed = hash_password(body.password)

    new_user = User(
        email=body.email,
        hashed_password=hashed,
        is_active=body.is_active
    )
    session.add(new_user)
    await session.flush()

    # Handle user group memberships
    group_ids = body.user_group_ids or []
    if not group_ids:
        # Ensure default 'Users' group exists; assign by default
        users_group = (await session.execute(select(UserGroup).where(UserGroup.name == "Users"))).scalars().first()
        if not users_group:
            users_group = UserGroup(name="Users", description="Default users group", is_admin=False)
            session.add(users_group)
            await session.flush()
        group_ids = [users_group.id]

    # Validate and add memberships
    valid_groups = (await session.execute(select(UserGroup).where(UserGroup.id.in_(group_ids)))).scalars().all()
    for g in valid_groups:
        session.add(UserGroupMembership(user_id=new_user.id, user_group_id=g.id))

    await session.commit()
    await session.refresh(new_user)

    # Load groups for response
    memberships = await session.execute(
        select(UserGroup)
        .join(UserGroupMembership, UserGroupMembership.user_group_id == UserGroup.id)
        .where(UserGroupMembership.user_id == new_user.id)
    )
    groups = memberships.scalars().all()

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        is_active=new_user.is_active,
        groups=[UserGroupRef(id=g.id, name=g.name) for g in groups],
        created_at=new_user.created_at
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, body: UserUpdate, session: AsyncSession = Depends(get_session), admin: User = Depends(require_permission("users", "update"))):
    # Respect external user management setting
    if settings.externally_managed_users:
        raise HTTPException(status_code=403, detail="Users are managed externally; local editing is disabled")
    from ..core.auth import hash_password
    from sqlalchemy.orm import selectinload
    from ..models.permissions import UserGroup, UserGroupMembership

    result = await session.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    if body.email is not None and body.email != u.email:
        # Check duplicate
        dup = await session.execute(select(User).where(User.email == body.email, User.id != user_id))
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already exists")
        u.email = body.email

    if body.password is not None:
        u.hashed_password = hash_password(body.password)

    if body.is_active is not None:
        u.is_active = body.is_active

    # Update group memberships if provided
    if body.user_group_ids is not None:
        # Remove existing memberships not in new set; add missing ones
        current_memberships = (await session.execute(
            select(UserGroupMembership).where(UserGroupMembership.user_id == u.id)
        )).scalars().all()
        current_ids = {m.user_group_id for m in current_memberships}
        new_ids = set(body.user_group_ids)

        # Prevent removing last administrator membership
        # If removing from Administrators would leave zero, block
        admins_group = (await session.execute(select(UserGroup).where(UserGroup.name == "Administrators"))).scalars().first()
        if admins_group and admins_group.id in current_ids and admins_group.id not in new_ids:
            # Count admins
            admin_count = (await session.execute(
                select(func.count(UserGroupMembership.id)).where(UserGroupMembership.user_group_id == admins_group.id)
            )).scalar()
            if admin_count <= 1:
                raise HTTPException(status_code=409, detail="Cannot remove the last administrator. Add another admin first.")

        # Delete memberships not in new_ids
        for m in current_memberships:
            if m.user_group_id not in new_ids:
                await session.delete(m)
        # Add memberships for ids not currently present
        if new_ids:
            valid_groups = (await session.execute(select(UserGroup).where(UserGroup.id.in_(list(new_ids))))).scalars().all()
            valid_ids = {g.id for g in valid_groups}
            for gid in valid_ids:
                if gid not in current_ids:
                    session.add(UserGroupMembership(user_id=u.id, user_group_id=gid))

    await session.commit()
    await session.refresh(u)

    # Load groups for response
    memberships = await session.execute(
        select(UserGroup)
        .join(UserGroupMembership, UserGroupMembership.user_group_id == UserGroup.id)
        .where(UserGroupMembership.user_id == u.id)
    )
    groups = memberships.scalars().all()

    return UserResponse(
        id=u.id,
        email=u.email,
        is_active=u.is_active,
        groups=[UserGroupRef(id=g.id, name=g.name) for g in groups],
        created_at=u.created_at
    )


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session), admin: User = Depends(require_permission("users", "delete"))):
    # Respect external user management setting
    if settings.externally_managed_users:
        raise HTTPException(status_code=403, detail="Users are managed externally; local deletion is disabled")
    from ..models.permissions import UserGroup, UserGroupMembership

    result = await session.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if u.id == admin.id:
        raise HTTPException(
            status_code=409, detail="Cannot delete your own account")

    # Check if this is the last admin
    admins_group_result = await session.execute(
        select(UserGroup).where(UserGroup.name == "Administrators")
    )
    admins_group = admins_group_result.scalar_one_or_none()

    if admins_group:
        # Check if user is in admins group
        user_in_admins = await session.execute(
            select(UserGroupMembership).where(
                UserGroupMembership.user_id == user_id,
                UserGroupMembership.user_group_id == admins_group.id
            )
        )
        if user_in_admins.scalar_one_or_none():
            # Count total admins
            admin_count = await session.execute(
                select(func.count(UserGroupMembership.id)).where(
                    UserGroupMembership.user_group_id == admins_group.id
                )
            )
            if admin_count.scalar() <= 1:
                raise HTTPException(
                    status_code=409,
                    detail="Cannot delete the last administrator. Add another admin first."
                )

    await session.delete(u)
    await session.commit()
    return {"status": "deleted", "id": user_id}


# ============ Permissions REST API ============

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("user_groups", "read"))
):
    """List all available permissions in the system (requires users:read permission)."""
    from ..models.permissions import Permission

    result = await session.execute(select(Permission).order_by(Permission.resource, Permission.action))
    permissions = result.scalars().all()

    return [
        PermissionResponse(
            id=p.id,
            resource=p.resource,
            action=p.action,
            description=p.description
        )
        for p in permissions
    ]


# ============ User Groups REST API ============

@router.get("/user-groups", response_model=List[UserGroupResponse])
async def list_user_groups(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("user_groups", "read"))
):
    """List all user groups with member and permission counts (requires users:read permission)."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(UserGroup).options(
            selectinload(UserGroup.owner),
            selectinload(UserGroup.permissions)
        )
    )
    groups = result.scalars().all()

    # Get member counts for each group
    responses = []
    for group in groups:
        member_count_result = await session.execute(
            select(func.count(UserGroupMembership.id)).where(
                UserGroupMembership.user_group_id == group.id
            )
        )
        member_count = member_count_result.scalar()

        responses.append(UserGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            is_admin=group.is_admin,
            owner=UserRef(id=group.owner.id,
                          email=group.owner.email) if group.owner else None,
            created_at=group.created_at,
            updated_at=group.updated_at,
            member_count=member_count,
            permission_count=len(group.permissions) if group.permissions else 0
        ))

    return responses


@router.get("/user-groups/{group_id}", response_model=UserGroupResponse)
async def get_user_group(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("user_groups", "read"))
):
    """Get user group details with members and permissions (requires users:read permission)."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(UserGroup)
        .options(selectinload(UserGroup.owner), selectinload(UserGroup.permissions))
        .where(UserGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # Get member count
    member_count_result = await session.execute(
        select(func.count(UserGroupMembership.id)).where(
            UserGroupMembership.user_group_id == group.id
        )
    )
    member_count = member_count_result.scalar()

    return UserGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        is_admin=group.is_admin,
        owner=UserRef(id=group.owner.id,
                      email=group.owner.email) if group.owner else None,
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=member_count,
        permission_count=len(group.permissions) if group.permissions else 0
    )


@router.post("/user-groups", response_model=UserGroupResponse)
async def create_user_group(
    body: UserGroupCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("user_groups", "create"))
):
    """Create a new user group (requires users:create permission)."""
    # Check for duplicate name
    existing = await session.execute(select(UserGroup).where(UserGroup.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="User group with this name already exists")

    # Create group
    group = UserGroup(
        name=body.name,
        description=body.description,
        is_admin=body.is_admin,
        owner_user_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    session.add(group)
    await session.commit()
    await session.refresh(group)

    return UserGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        is_admin=group.is_admin,
        owner=UserRef(id=user.id, email=user.email),
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=0,
        permission_count=0
    )


@router.put("/user-groups/{group_id}", response_model=UserGroupResponse)
async def update_user_group(
    group_id: int,
    body: UserGroupUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("user_groups", "update"))
):
    """Update user group (requires users:update permission)."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(UserGroup)
        .options(selectinload(UserGroup.owner), selectinload(UserGroup.permissions))
        .where(UserGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # Prevent changing is_admin on Administrators group
    if group.name == "Administrators" and body.is_admin is not None and not body.is_admin:
        raise HTTPException(
            status_code=409,
            detail="Cannot remove admin status from Administrators group"
        )

    # Update fields
    if body.name is not None:
        # Check for duplicate name
        if body.name != group.name:
            existing = await session.execute(select(UserGroup).where(UserGroup.name == body.name))
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, detail="User group with this name already exists")
        group.name = body.name

    if body.description is not None:
        group.description = body.description

    if body.is_admin is not None and group.name != "Administrators":
        group.is_admin = body.is_admin

    group.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(group)

    # Get member count
    member_count_result = await session.execute(
        select(func.count(UserGroupMembership.id)).where(
            UserGroupMembership.user_group_id == group.id
        )
    )
    member_count = member_count_result.scalar()

    return UserGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        is_admin=group.is_admin,
        owner=UserRef(id=group.owner.id,
                      email=group.owner.email) if group.owner else None,
        created_at=group.created_at,
        updated_at=group.updated_at,
        member_count=member_count,
        permission_count=len(group.permissions) if group.permissions else 0
    )


@router.delete("/user-groups/{group_id}")
async def delete_user_group(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("user_groups", "delete"))
):
    """Delete user group (requires users:delete permission). Cannot delete Administrators group."""
    result = await session.execute(select(UserGroup).where(UserGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # Prevent deletion of Administrators group
    if group.name == "Administrators":
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the Administrators group"
        )

    await session.delete(group)
    await session.commit()

    return {"status": "deleted", "id": group_id}


# ============ User Group Membership REST API ============

@router.get("/user-groups/{group_id}/members", response_model=List[UserResponse])
async def list_group_members(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("user_groups", "manage_members"))
):
    """List all members of a user group (requires users:read permission)."""
    from sqlalchemy.orm import selectinload

    # Verify group exists
    group_result = await session.execute(select(UserGroup).where(UserGroup.id == group_id))
    if not group_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User group not found")

    # Get members
    result = await session.execute(
        select(User)
        .join(UserGroupMembership, UserGroupMembership.user_id == User.id)
        .where(UserGroupMembership.user_group_id == group_id)
    )
    members = result.scalars().all()

    responses: List[UserResponse] = []
    for u in members:
        # Load all groups for each user
        memberships = await session.execute(
            select(UserGroup)
            .join(UserGroupMembership, UserGroupMembership.user_group_id == UserGroup.id)
            .where(UserGroupMembership.user_id == u.id)
        )
        groups = memberships.scalars().all()
        responses.append(UserResponse(
            id=u.id,
            email=u.email,
            is_active=u.is_active,
            groups=[UserGroupRef(id=g.id, name=g.name) for g in groups],
            created_at=u.created_at
        ))

    return responses


@router.post("/user-groups/{group_id}/members")
async def add_group_member(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(
        require_permission("user_groups", "manage_members"))
):
    """Add user to group (requires users:update permission)."""
    # Verify group exists
    group_result = await session.execute(select(UserGroup).where(UserGroup.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # Verify user exists
    user_result = await session.execute(select(User).where(User.id == user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already a member
    existing = await session.execute(
        select(UserGroupMembership).where(
            UserGroupMembership.user_id == user_id,
            UserGroupMembership.user_group_id == group_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="User is already a member of this group")

    # Add membership
    membership = UserGroupMembership(
        user_id=user_id,
        user_group_id=group_id,
        added_at=datetime.utcnow()
    )
    session.add(membership)
    await session.commit()

    return {"status": "added", "user_id": user_id, "group_id": group_id}


@router.delete("/user-groups/{group_id}/members/{user_id}")
async def remove_group_member(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(
        require_permission("user_groups", "manage_members"))
):
    """Remove user from group (requires users:update permission). Cannot remove last admin."""
    # Verify group exists
    group_result = await session.execute(select(UserGroup).where(UserGroup.id == group_id))
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # Find membership
    membership_result = await session.execute(
        select(UserGroupMembership).where(
            UserGroupMembership.user_id == user_id,
            UserGroupMembership.user_group_id == group_id
        )
    )
    membership = membership_result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=404, detail="User is not a member of this group")

    # Prevent removing last admin from Administrators group
    if group.name == "Administrators":
        admin_count = await session.execute(
            select(func.count(UserGroupMembership.id)).where(
                UserGroupMembership.user_group_id == group_id
            )
        )
        if admin_count.scalar() <= 1:
            raise HTTPException(
                status_code=409,
                detail="Cannot remove the last administrator. Add another admin first."
            )

    await session.delete(membership)
    await session.commit()

    return {"status": "removed", "user_id": user_id, "group_id": group_id}


# ============ User Group Permissions REST API ============

@router.get("/user-groups/{group_id}/permissions", response_model=List[PermissionResponse])
async def list_group_permissions(
    group_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(
        "user_groups", "manage_permissions"))
):
    """List permissions granted to a user group (requires users:read permission)."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(UserGroup)
        .options(selectinload(UserGroup.permissions))
        .where(UserGroup.id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # If group is admin, return all permissions
    if group.is_admin:
        all_perms_result = await session.execute(select(Permission))
        all_perms = all_perms_result.scalars().all()
        return [
            PermissionResponse(
                id=p.id,
                resource=p.resource,
                action=p.action,
                description=p.description
            )
            for p in all_perms
        ]

    return [
        PermissionResponse(
            id=p.id,
            resource=p.resource,
            action=p.action,
            description=p.description
        )
        for p in group.permissions
    ]


@router.post("/user-groups/{group_id}/permissions")
async def grant_group_permission(
    group_id: int,
    body: PermissionGrantRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(
        "user_groups", "manage_permissions"))
):
    """Grant permission to group (requires users:update permission)."""
    from sqlalchemy.orm import selectinload

    # Verify group exists
    result = await session.execute(
        select(UserGroup)
        .options(selectinload(UserGroup.permissions))
        .where(UserGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # If group is admin, permissions are automatic (no need to grant)
    if group.is_admin:
        return {"status": "ignored", "message": "Admin groups automatically have all permissions"}

    # Find permission
    permission = None
    if body.permission_id:
        perm_result = await session.execute(
            select(Permission).where(Permission.id == body.permission_id)
        )
        permission = perm_result.scalar_one_or_none()
    elif body.resource and body.action:
        perm_result = await session.execute(
            select(Permission).where(
                Permission.resource == body.resource,
                Permission.action == body.action
            )
        )
        permission = perm_result.scalar_one_or_none()
    else:
        raise HTTPException(
            status_code=400,
            detail="Either permission_id or both resource and action must be provided"
        )

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    # Check if already granted
    if permission in group.permissions:
        raise HTTPException(
            status_code=409, detail="Permission already granted to this group")

    # Grant permission
    group.permissions.append(permission)
    group.updated_at = datetime.utcnow()
    await session.commit()

    return {"status": "granted", "permission_id": permission.id, "group_id": group_id}


@router.delete("/user-groups/{group_id}/permissions/{permission_id}")
async def revoke_group_permission(
    group_id: int,
    permission_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission(
        "user_groups", "manage_permissions"))
):
    """Revoke permission from group (requires users:update permission)."""
    from sqlalchemy.orm import selectinload

    # Verify group exists
    result = await session.execute(
        select(UserGroup)
        .options(selectinload(UserGroup.permissions))
        .where(UserGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="User group not found")

    # If group is admin, cannot revoke permissions (they have all)
    if group.is_admin:
        return {"status": "ignored", "message": "Cannot revoke permissions from admin groups"}

    # Find permission
    perm_result = await session.execute(
        select(Permission).where(Permission.id == permission_id)
    )
    permission = perm_result.scalar_one_or_none()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    # Check if permission is granted
    if permission not in group.permissions:
        raise HTTPException(
            status_code=404, detail="Permission not granted to this group")

    # Revoke permission
    group.permissions.remove(permission)
    group.updated_at = datetime.utcnow()
    await session.commit()

    return {"status": "revoked", "permission_id": permission_id, "group_id": group_id}


# ============ Token Re-issuance Endpoints ============

@router.post(
    "/clients/{client_id}/token/reissue",
    response_model=ClientTokenReissueResponse
)
async def reissue_client_token_auto(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Re-issue a client token with new value (auto-detects active token).
    
    This endpoint automatically finds the active token for the client,
    deactivates it, and generates a new one.
    Requires admin permissions or ownership of the client.
    """
    # Check admin permission or ownership
    is_admin = await user.has_permission(session, "users", "delete")
    
    # Verify client exists
    client_result = await session.execute(
        select(Client).where(Client.id == client_id)
    )
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Check ownership if not admin
    if not is_admin and client.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Admin permission or ownership required")
    
    # Find active token for this client
    token_result = await session.execute(
        select(ClientToken).where(
            ClientToken.client_id == client_id,
            ClientToken.is_active == True
        )
    )
    old_token = token_result.scalar_one_or_none()
    if not old_token:
        raise HTTPException(status_code=404, detail="No active token found for this client")
    
    # Deactivate old token
    old_token.is_active = False
    
    # Generate new token with current prefix
    prefix = await get_token_prefix(session)
    new_token_value = generate_client_token(prefix)
    
    # Create new token
    new_token = ClientToken(
        client_id=client_id,
        token=new_token_value,
        is_active=True,
        owner_user_id=user.id
    )
    session.add(new_token)
    await session.commit()
    await session.refresh(new_token)
    
    # Log the action
    logger.info(f"Token re-issued for client {client_id} by user {user.id}")
    
    # Return response with full token (only time it's shown)
    return ClientTokenReissueResponse(
        id=new_token.id,
        token=new_token.token,
        client_id=new_token.client_id,
        created_at=new_token.created_at,
        old_token_id=old_token.id
    )


@router.post(
    "/clients/{client_id}/tokens/{token_id}/reissue",
    response_model=ClientTokenReissueResponse
)
async def reissue_client_token(
    client_id: int,
    token_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Re-issue a client token with new value.
    
    This endpoint deactivates the old token and generates a new one.
    Requires admin permissions.
    """
    # Check admin permission
    is_admin = await user.has_permission(session, "users", "delete")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    # Verify client exists
    client_result = await session.execute(
        select(Client).where(Client.id == client_id)
    )
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Verify token exists and belongs to client
    token_result = await session.execute(
        select(ClientToken).where(
            ClientToken.id == token_id,
            ClientToken.client_id == client_id
        )
    )
    old_token = token_result.scalar_one_or_none()
    if not old_token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Deactivate old token
    old_token.is_active = False
    
    # Generate new token with current prefix
    prefix = await get_token_prefix(session)
    new_token_value = generate_client_token(prefix)
    
    # Create new token
    new_token = ClientToken(
        client_id=client_id,
        token=new_token_value,
        is_active=True,
        owner_user_id=user.id
    )
    session.add(new_token)
    await session.commit()
    await session.refresh(new_token)
    
    # Log the action
    logger.info(f"Token re-issued for client {client_id} by user {user.id}")
    
    # Return response with full token (only time it's shown)
    return ClientTokenReissueResponse(
        id=new_token.id,
        token=new_token.token,
        client_id=new_token.client_id,
        created_at=new_token.created_at,
        old_token_id=old_token.id
    )


# ============ System Settings Endpoints ============

@router.get(
    "/settings/token-prefix",
    response_model=SystemSettingResponse
)
async def get_token_prefix_setting(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Get current token prefix setting.
    
    Requires admin permissions.
    """
    # Check admin permission
    is_admin = await user.has_permission(session, "users", "delete")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    result = await session.execute(
        select(SystemSettings)
        .options(selectinload(SystemSettings.updated_by))
        .where(SystemSettings.key == "token_prefix")
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        # Return default if not found
        return SystemSettingResponse(
            key="token_prefix",
            value="mnebula_",
            updated_at=datetime.utcnow(),
            updated_by=None
        )
    
    return SystemSettingResponse(
        key=setting.key,
        value=setting.value,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by.email if setting.updated_by else None
    )


@router.put(
    "/settings/token-prefix",
    response_model=SystemSettingResponse
)
async def update_token_prefix_setting(
    data: TokenPrefixUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Update token prefix setting.
    
    This only affects new tokens. Existing tokens remain valid.
    Requires admin permissions.
    """
    # Check admin permission
    is_admin = await user.has_permission(session, "users", "delete")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    # Get or create setting
    result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "token_prefix")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = data.prefix
        setting.updated_at = datetime.utcnow()
        setting.updated_by_user_id = user.id
    else:
        setting = SystemSettings(
            key="token_prefix",
            value=data.prefix,
            updated_at=datetime.utcnow(),
            updated_by_user_id=user.id
        )
        session.add(setting)
    
    await session.commit()
    await session.refresh(setting)
    
    # Reload with relationship
    result = await session.execute(
        select(SystemSettings)
        .options(selectinload(SystemSettings.updated_by))
        .where(SystemSettings.id == setting.id)
    )
    setting = result.scalar_one()
    
    logger.info(f"Token prefix updated to '{data.prefix}' by user {user.id}")
    
    return SystemSettingResponse(
        key=setting.key,
        value=setting.value,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by.email if setting.updated_by else None
    )


@router.get(
    "/settings/github-webhook-secret",
    response_model=SystemSettingResponse
)
async def get_github_webhook_secret_setting(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Get GitHub webhook secret setting (masked).
    
    Requires admin permissions.
    """
    # Check admin permission
    is_admin = await user.has_permission(session, "users", "delete")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    result = await session.execute(
        select(SystemSettings)
        .options(selectinload(SystemSettings.updated_by))
        .where(SystemSettings.key == "github_webhook_secret")
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        return SystemSettingResponse(
            key="github_webhook_secret",
            value="",
            updated_at=datetime.utcnow(),
            updated_by=None
        )
    
    # Mask the secret value (show only first 4 chars)
    masked_value = ""
    if setting.value and len(setting.value) > 0:
        masked_value = setting.value[:4] + "*" * (len(setting.value) - 4)
    
    return SystemSettingResponse(
        key=setting.key,
        value=masked_value,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by.email if setting.updated_by else None
    )


@router.put(
    "/settings/github-webhook-secret",
    response_model=SystemSettingResponse
)
async def update_github_webhook_secret_setting(
    data: GitHubWebhookSecretUpdate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user)
):
    """Update GitHub webhook secret setting.
    
    Requires admin permissions.
    """
    # Check admin permission
    is_admin = await user.has_permission(session, "users", "delete")
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    # Get or create setting
    result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "github_webhook_secret")
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = data.secret
        setting.updated_at = datetime.utcnow()
        setting.updated_by_user_id = user.id
    else:
        setting = SystemSettings(
            key="github_webhook_secret",
            value=data.secret,
            updated_at=datetime.utcnow(),
            updated_by_user_id=user.id
        )
        session.add(setting)
    
    await session.commit()
    await session.refresh(setting)
    
    # Reload with relationship
    result = await session.execute(
        select(SystemSettings)
        .options(selectinload(SystemSettings.updated_by))
        .where(SystemSettings.id == setting.id)
    )
    setting = result.scalar_one()
    
    logger.info(f"GitHub webhook secret updated by user {user.id}")
    
    # Return masked value
    masked_value = setting.value[:4] + "*" * (len(setting.value) - 4) if setting.value else ""
    
    return SystemSettingResponse(
        key=setting.key,
        value=masked_value,
        updated_at=setting.updated_at,
        updated_by=setting.updated_by.email if setting.updated_by else None
    )


# ============ GitHub Secret Scanning Endpoints ============
# Note: /.well-known/secret-scanning.json is in public.py (no /api/v1 prefix)

@router.post(
    "/github/secret-scanning/verify",
    response_model=List[GitHubSecretVerificationResponse]
)
async def github_secret_scanning_verify(
    request: Request,
    tokens: List[GitHubSecretVerificationRequest],
    session: AsyncSession = Depends(get_session)
):
    """Verify tokens for GitHub Secret Scanning.
    
    This endpoint verifies if tokens are valid and returns details.
    Requires GitHub webhook signature verification.
    """
    # Get webhook secret from settings
    secret_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "github_webhook_secret")
    )
    secret_setting = secret_result.scalar_one_or_none()
    
    # Verify GitHub signature if secret is configured
    if secret_setting and secret_setting.value:
        # Get signature header
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        
        # Read body bytes
        body = await request.body()
        
        # Verify signature
        if not verify_github_signature(body, signature_header, secret_setting.value):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process each token
    responses = []
    for token_request in tokens:
        # Look up token in database
        token_result = await session.execute(
            select(ClientToken)
            .options(selectinload(ClientToken.client))
            .where(ClientToken.token == token_request.token)
        )
        token = token_result.scalar_one_or_none()
        
        if token:
            # Token found - return details
            client = token.client
            responses.append(
                GitHubSecretVerificationResponse(
                    token=token_request.token,
                    type=token_request.type,
                    label=client.name if client else "unknown",
                    url=f"{request.base_url}clients/{client.id}" if client else None,
                    is_active=token.is_active
                )
            )
            
            # Log verification
            log_entry = GitHubSecretScanningLog(
                action="verify",
                token_preview=get_token_preview(token_request.token),
                github_url=token_request.url,
                is_active=token.is_active,
                client_id=token.client_id
            )
            session.add(log_entry)
        # If token not found, don't add to responses (don't leak info)
    
    await session.commit()
    
    return responses


@router.post(
    "/github/secret-scanning/revoke",
    response_model=GitHubSecretRevocationResponse
)
async def github_secret_scanning_revoke(
    request: Request,
    tokens: List[GitHubSecretRevocationRequest],
    session: AsyncSession = Depends(get_session)
):
    """Revoke tokens reported by GitHub Secret Scanning.
    
    This endpoint automatically deactivates tokens found in public repositories.
    Requires GitHub webhook signature verification.
    """
    # Get webhook secret from settings
    secret_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "github_webhook_secret")
    )
    secret_setting = secret_result.scalar_one_or_none()
    
    # Verify GitHub signature if secret is configured
    if secret_setting and secret_setting.value:
        # Get signature header
        signature_header = request.headers.get("X-Hub-Signature-256", "")
        
        # Read body bytes
        body = await request.body()
        
        # Verify signature
        if not verify_github_signature(body, signature_header, secret_setting.value):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process each token
    revoked_count = 0
    for token_request in tokens:
        # Look up token in database
        token_result = await session.execute(
            select(ClientToken).where(ClientToken.token == token_request.token)
        )
        token = token_result.scalar_one_or_none()
        
        if token and token.is_active:
            # Deactivate token
            token.is_active = False
            revoked_count += 1
            
            logger.warning(
                f"Token revoked by GitHub Secret Scanning: "
                f"client_id={token.client_id}, "
                f"github_url={token_request.url}"
            )
        
        # Log revocation attempt (even if token not found)
        log_entry = GitHubSecretScanningLog(
            action="revoke",
            token_preview=get_token_preview(token_request.token),
            github_url=token_request.url,
            is_active=token.is_active if token else False,
            client_id=token.client_id if token else None
        )
        session.add(log_entry)
    
    await session.commit()
    
    return GitHubSecretRevocationResponse(
        message="Tokens processed",
        revoked_count=revoked_count
    )
