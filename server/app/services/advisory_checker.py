"""Security advisory checking service."""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .github_api import get_github_client
from .version_parser import compare_versions

logger = logging.getLogger(__name__)


class Severity(str, Enum):
    """Security advisory severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class SecurityAdvisory:
    """Security advisory information."""
    id: str
    severity: Severity
    summary: str
    affected_versions: str
    patched_version: Optional[str]
    published_at: str
    url: str
    cve_id: Optional[str] = None


class AdvisoryChecker:
    """Service for checking security advisories against client versions."""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize advisory checker.
        
        Args:
            github_token: Optional GitHub API token
        """
        self.github_client = get_github_client(token=github_token)
    
    async def get_advisories_for_repo(
        self,
        owner: str,
        repo: str
    ) -> List[SecurityAdvisory]:
        """
        Get all security advisories for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of SecurityAdvisory objects
        """
        raw_advisories = await self.github_client.get_security_advisories(owner, repo)
        
        advisories = []
        for advisory in raw_advisories:
            try:
                severity_str = advisory.get("severity", "unknown").lower()
                severity = Severity(severity_str) if severity_str in [s.value for s in Severity] else Severity.UNKNOWN
                
                # Extract affected and patched versions
                vulnerabilities = advisory.get("vulnerabilities", [])
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
                
                advisories.append(SecurityAdvisory(
                    id=advisory.get("ghsa_id", advisory.get("id", "unknown")),
                    severity=severity,
                    summary=advisory.get("summary", "No summary available"),
                    affected_versions=affected_versions,
                    patched_version=patched_version,
                    published_at=advisory.get("published_at", ""),
                    url=advisory.get("html_url", ""),
                    cve_id=advisory.get("cve_id")
                ))
            except Exception as e:
                logger.warning(f"Failed to parse advisory: {e}")
                continue
        
        return advisories
    
    def is_version_affected(
        self,
        version: str,
        affected_range: str
    ) -> bool:
        """
        Check if a version is affected by an advisory.
        
        Args:
            version: Version to check
            affected_range: Affected version range (e.g., "< 1.2.0", ">= 1.0.0, < 1.2.0")
            
        Returns:
            True if version is affected
        """
        if not version or not affected_range or affected_range == "unknown":
            return False
        
        # Parse the affected range
        # Common formats:
        # "< 1.2.0"
        # ">= 1.0.0, < 1.2.0"
        # "<= 1.1.9"
        
        # Split by comma for multiple conditions
        conditions = [c.strip() for c in affected_range.split(",")]
        
        for condition in conditions:
            if not self._check_version_condition(version, condition):
                return False
        
        return True
    
    def _check_version_condition(self, version: str, condition: str) -> bool:
        """Check if version satisfies a single condition."""
        condition = condition.strip()
        
        # Extract operator and version
        if condition.startswith(">="):
            op = ">="
            check_version = condition[2:].strip()
        elif condition.startswith("<="):
            op = "<="
            check_version = condition[2:].strip()
        elif condition.startswith(">"):
            op = ">"
            check_version = condition[1:].strip()
        elif condition.startswith("<"):
            op = "<"
            check_version = condition[1:].strip()
        elif condition.startswith("="):
            op = "="
            check_version = condition[1:].strip()
        else:
            # No operator, assume exact match
            op = "="
            check_version = condition
        
        # Compare versions
        comparison = compare_versions(version, check_version)
        if comparison is None:
            return False
        
        if op == "<":
            return comparison < 0
        elif op == "<=":
            return comparison <= 0
        elif op == ">":
            return comparison > 0
        elif op == ">=":
            return comparison >= 0
        elif op == "=":
            return comparison == 0
        
        return False
    
    async def check_version_vulnerabilities(
        self,
        version: str,
        owner: str,
        repo: str
    ) -> List[SecurityAdvisory]:
        """
        Check if a version has known vulnerabilities.
        
        Args:
            version: Version to check
            owner: Repository owner
            repo: Repository name
            
        Returns:
            List of applicable SecurityAdvisory objects
        """
        if not version:
            return []
        
        advisories = await self.get_advisories_for_repo(owner, repo)
        
        # Filter advisories that affect this version
        applicable = []
        for advisory in advisories:
            if self.is_version_affected(version, advisory.affected_versions):
                applicable.append(advisory)
        
        return applicable
    
    def get_highest_severity(self, advisories: List[SecurityAdvisory]) -> Severity:
        """
        Get the highest severity from a list of advisories.
        
        Args:
            advisories: List of advisories
            
        Returns:
            Highest severity level
        """
        if not advisories:
            return Severity.UNKNOWN
        
        severity_order = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
            Severity.UNKNOWN: 0
        }
        
        highest = Severity.UNKNOWN
        highest_value = 0
        
        for advisory in advisories:
            value = severity_order.get(advisory.severity, 0)
            if value > highest_value:
                highest = advisory.severity
                highest_value = value
        
        return highest


# Repository configurations
MANAGED_NEBULA_REPO = ("kumpeapps", "managed-nebula")
NEBULA_REPO = ("slackhq", "nebula")


async def check_client_version_status(
    client_version: Optional[str],
    nebula_version: Optional[str],
    github_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check version status for both client and Nebula versions.
    
    Args:
        client_version: managed-nebula client version
        nebula_version: Nebula binary version
        github_token: Optional GitHub API token
        
    Returns:
        Dictionary with version status information
    """
    checker = AdvisoryChecker(github_token=github_token)
    github_client = get_github_client(token=github_token)
    
    # Get latest releases
    latest_client_release = await github_client.get_latest_release(*MANAGED_NEBULA_REPO)
    latest_nebula_release = await github_client.get_latest_release(*NEBULA_REPO)
    
    # Get advisories
    client_advisories = []
    nebula_advisories = []
    
    if client_version:
        client_advisories = await checker.check_version_vulnerabilities(
            client_version, *MANAGED_NEBULA_REPO
        )
    
    if nebula_version:
        nebula_advisories = await checker.check_version_vulnerabilities(
            nebula_version, *NEBULA_REPO
        )
    
    # Determine status
    client_status = _determine_status(
        client_version,
        latest_client_release.version if latest_client_release else None,
        client_advisories
    )
    
    nebula_status = _determine_status(
        nebula_version,
        latest_nebula_release.version if latest_nebula_release else None,
        nebula_advisories
    )
    
    # Calculate days behind
    days_behind = None
    if latest_client_release and latest_client_release.published_at:
        from datetime import datetime
        days_behind = (datetime.utcnow() - latest_client_release.published_at.replace(tzinfo=None)).days
    
    return {
        "client_version_status": client_status,
        "nebula_version_status": nebula_status,
        "client_advisories": [_advisory_to_dict(a) for a in client_advisories],
        "nebula_advisories": [_advisory_to_dict(a) for a in nebula_advisories],
        "latest_client_version": latest_client_release.version if latest_client_release else None,
        "latest_nebula_version": latest_nebula_release.version if latest_nebula_release else None,
        "current_client_version": client_version,
        "current_nebula_version": nebula_version,
        "days_behind": days_behind
    }


def _determine_status(
    current_version: Optional[str],
    latest_version: Optional[str],
    advisories: List[SecurityAdvisory]
) -> str:
    """Determine version status."""
    if not current_version:
        return "unknown"
    
    if advisories:
        return "vulnerable"
    
    if not latest_version:
        return "unknown"
    
    comparison = compare_versions(current_version, latest_version)
    if comparison is None:
        return "unknown"
    elif comparison < 0:
        return "outdated"
    else:
        return "current"


def _advisory_to_dict(advisory: SecurityAdvisory) -> Dict[str, Any]:
    """Convert SecurityAdvisory to dictionary."""
    return {
        "id": advisory.id,
        "severity": advisory.severity.value,
        "summary": advisory.summary,
        "affected_versions": advisory.affected_versions,
        "patched_version": advisory.patched_version,
        "published_at": advisory.published_at,
        "url": advisory.url,
        "cve_id": advisory.cve_id
    }


async def check_client_version_status_cached(
    session,
    client_version: Optional[str],
    nebula_version: Optional[str]
) -> Optional[Dict[str, Any]]:
    """
    Check version status using cached data from SystemSettings.
    Only performs fresh GitHub API calls if cache is stale (>24 hours).
    
    Args:
        session: Database session
        client_version: managed-nebula client version
        nebula_version: Nebula binary version
        
    Returns:
        Dictionary with version status or None if no cached data available
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from ..models import SystemSettings
    
    # Check cache age
    cache_check_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "version_cache_last_checked")
    )
    cache_check_row = cache_check_result.scalar_one_or_none()
    
    # If no cache exists, initialize it automatically
    if not cache_check_row:
        logger.info("Version cache not found, initializing automatically")
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
        
        # Initialize cache
        await refresh_version_cache(session, github_token)
        
        # Re-query cache after initialization
        cache_check_result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "version_cache_last_checked")
        )
        cache_check_row = cache_check_result.scalar_one_or_none()
    
    # Check if cache is stale (>24 hours)
    if cache_check_row:
        try:
            last_checked = datetime.fromisoformat(cache_check_row.value)
            cache_age = datetime.utcnow() - last_checked
            if cache_age > timedelta(hours=24):
                logger.info(f"Version cache is stale ({cache_age.total_seconds()/3600:.1f} hours old), auto-refreshing")
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
                
                # Auto-refresh cache
                await refresh_version_cache(session, github_token)
        except Exception as e:
            logger.warning(f"Failed to parse cache timestamp: {e}")
            return None
    
    # Get cached versions
    latest_client_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "latest_client_version")
    )
    latest_client_row = latest_client_result.scalar_one_or_none()
    latest_client_version = latest_client_row.value if latest_client_row else None
    
    latest_nebula_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "latest_nebula_version")
    )
    latest_nebula_row = latest_nebula_result.scalar_one_or_none()
    latest_nebula_version = latest_nebula_row.value if latest_nebula_row else None
    
    # Get cached advisories
    import json
    
    client_advisories_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "cached_client_advisories")
    )
    client_advisories_row = client_advisories_result.scalar_one_or_none()
    all_client_advisories = []
    if client_advisories_row and client_advisories_row.value:
        try:
            all_client_advisories = json.loads(client_advisories_row.value)
        except Exception as e:
            logger.warning(f"Failed to parse cached client advisories: {e}")
    
    nebula_advisories_result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "cached_nebula_advisories")
    )
    nebula_advisories_row = nebula_advisories_result.scalar_one_or_none()
    all_nebula_advisories = []
    if nebula_advisories_row and nebula_advisories_row.value:
        try:
            all_nebula_advisories = json.loads(nebula_advisories_row.value)
        except Exception as e:
            logger.warning(f"Failed to parse cached nebula advisories: {e}")
    
    # Filter advisories that affect the current versions
    checker = AdvisoryChecker()
    
    applicable_client_advisories = []
    if client_version and all_client_advisories:
        for adv_dict in all_client_advisories:
            if checker.is_version_affected(client_version, adv_dict.get("affected_versions", "")):
                applicable_client_advisories.append(adv_dict)
    
    applicable_nebula_advisories = []
    if nebula_version and all_nebula_advisories:
        for adv_dict in all_nebula_advisories:
            if checker.is_version_affected(nebula_version, adv_dict.get("affected_versions", "")):
                applicable_nebula_advisories.append(adv_dict)
    
    # Also check managed-nebula advisories for Nebula-related CVEs
    # Some managed-nebula advisories reference upstream Nebula vulnerabilities
    if nebula_version and all_client_advisories:
        for adv_dict in all_client_advisories:
            summary = adv_dict.get("summary", "").lower()
            # Check if this is a Nebula-related advisory (contains [Nebula] or mentions nebula in summary)
            if "[nebula]" in summary or "nebula" in summary:
                # Try to extract Nebula version info from the summary/description
                # Common patterns: "Affects Nebula v1.9.x", "Nebula versions < 1.9.4", etc.
                # For now, use a heuristic: if it mentions nebula and has a CVE, check common vulnerable versions
                cve_id = adv_dict.get("cve_id")
                if cve_id:
                    # CVE-2025-62820: Source IP Spoofing Defect
                    # Affects Nebula <= 1.9.7
                    if cve_id == "CVE-2025-62820":
                        # This CVE affects all Nebula versions <= 1.9.7
                        if checker.is_version_affected(nebula_version, "<= 1.9.7"):
                            # Create a Nebula-specific advisory entry
                            nebula_adv = {
                                "id": adv_dict["id"],
                                "severity": adv_dict["severity"],
                                "summary": adv_dict["summary"],
                                "affected_versions": "<= 1.9.7",  # Nebula version range
                                "patched_version": ">= 1.9.8",
                                "published_at": adv_dict["published_at"],
                                "url": adv_dict["url"],
                                "cve_id": cve_id
                            }
                            applicable_nebula_advisories.append(nebula_adv)
    
    # Determine status using cached data
    # Convert advisory dicts to SecurityAdvisory objects for _determine_status
    client_advisory_objs = [SecurityAdvisory(
        id=a.get("id", "unknown"),
        severity=Severity(a.get("severity", "unknown")) if a.get("severity") in [s.value for s in Severity] else Severity.UNKNOWN,
        summary=a.get("summary", ""),
        affected_versions=a.get("affected_versions", ""),
        patched_version=a.get("patched_version"),
        published_at=a.get("published_at", ""),
        url=a.get("url", ""),
        cve_id=a.get("cve_id")
    ) for a in applicable_client_advisories]
    
    nebula_advisory_objs = [SecurityAdvisory(
        id=a.get("id", "unknown"),
        severity=Severity(a.get("severity", "unknown")) if a.get("severity") in [s.value for s in Severity] else Severity.UNKNOWN,
        summary=a.get("summary", ""),
        affected_versions=a.get("affected_versions", ""),
        patched_version=a.get("patched_version"),
        published_at=a.get("published_at", ""),
        url=a.get("url", ""),
        cve_id=a.get("cve_id")
    ) for a in applicable_nebula_advisories]
    
    client_status = _determine_status(client_version, latest_client_version, client_advisory_objs)
    nebula_status = _determine_status(nebula_version, latest_nebula_version, nebula_advisory_objs)
    
    return {
        "client_version_status": client_status,
        "nebula_version_status": nebula_status,
        "client_advisories": applicable_client_advisories,
        "nebula_advisories": applicable_nebula_advisories,
        "latest_client_version": latest_client_version,
        "latest_nebula_version": latest_nebula_version,
        "current_client_version": client_version,
        "current_nebula_version": nebula_version,
        "days_behind": None
    }


async def refresh_version_cache(session, github_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Refresh version cache by calling GitHub API.
    Should be called manually from settings page or by scheduled task.
    
    Args:
        session: Database session
        github_token: Optional GitHub API token
        
    Returns:
        Dictionary with cache refresh status
    """
    from datetime import datetime
    from sqlalchemy import select
    from ..models import SystemSettings
    import json
    
    try:
        github_client = get_github_client(token=github_token)
        checker = AdvisoryChecker(github_token=github_token)
        
        # Get latest releases
        latest_client_release = await github_client.get_latest_release(*MANAGED_NEBULA_REPO)
        latest_nebula_release = await github_client.get_latest_release(*NEBULA_REPO)
        
        # Get all advisories for both repos
        client_advisories = await checker.get_advisories_for_repo(*MANAGED_NEBULA_REPO)
        nebula_advisories = await checker.get_advisories_for_repo(*NEBULA_REPO)
        
        # Update cache
        now = datetime.utcnow()
        
        # Update or create cache timestamp
        timestamp_result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "version_cache_last_checked")
        )
        timestamp_row = timestamp_result.scalar_one_or_none()
        if timestamp_row:
            timestamp_row.value = now.isoformat()
        else:
            session.add(SystemSettings(key="version_cache_last_checked", value=now.isoformat()))
        
        # Update or create latest client version
        if latest_client_release:
            client_result = await session.execute(
                select(SystemSettings).where(SystemSettings.key == "latest_client_version")
            )
            client_row = client_result.scalar_one_or_none()
            if client_row:
                client_row.value = latest_client_release.version
            else:
                session.add(SystemSettings(key="latest_client_version", value=latest_client_release.version))
        
        # Update or create latest nebula version
        if latest_nebula_release:
            nebula_result = await session.execute(
                select(SystemSettings).where(SystemSettings.key == "latest_nebula_version")
            )
            nebula_row = nebula_result.scalar_one_or_none()
            if nebula_row:
                nebula_row.value = latest_nebula_release.version
            else:
                session.add(SystemSettings(key="latest_nebula_version", value=latest_nebula_release.version))
        
        # Cache client advisories as JSON
        client_advisories_json = json.dumps([_advisory_to_dict(a) for a in client_advisories])
        client_adv_result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "cached_client_advisories")
        )
        client_adv_row = client_adv_result.scalar_one_or_none()
        if client_adv_row:
            client_adv_row.value = client_advisories_json
        else:
            session.add(SystemSettings(key="cached_client_advisories", value=client_advisories_json))
        
        # Cache nebula advisories as JSON
        nebula_advisories_json = json.dumps([_advisory_to_dict(a) for a in nebula_advisories])
        nebula_adv_result = await session.execute(
            select(SystemSettings).where(SystemSettings.key == "cached_nebula_advisories")
        )
        nebula_adv_row = nebula_adv_result.scalar_one_or_none()
        if nebula_adv_row:
            nebula_adv_row.value = nebula_advisories_json
        else:
            session.add(SystemSettings(key="cached_nebula_advisories", value=nebula_advisories_json))
        
        await session.commit()
        
        return {
            "success": True,
            "last_checked": now.isoformat(),
            "latest_client_version": latest_client_release.version if latest_client_release else None,
            "latest_nebula_version": latest_nebula_release.version if latest_nebula_release else None,
            "client_advisories_count": len(client_advisories),
            "nebula_advisories_count": len(nebula_advisories)
        }
    except Exception as e:
        logger.error(f"Failed to refresh version cache: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Internal error occurred while refreshing version cache."
        }
