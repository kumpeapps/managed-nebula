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
