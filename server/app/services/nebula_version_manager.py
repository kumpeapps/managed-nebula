"""Nebula version management service for fetching and managing Nebula binaries."""
import logging
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


@dataclass
class NebulaVersionInfo:
    """Information about a Nebula release version."""
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


class NebulaVersionService:
    """Service for managing Nebula version information and binaries."""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the Nebula version service.
        
        Args:
            github_token: Optional GitHub API token for higher rate limits
        """
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.repo_owner = "slackhq"
        self.repo_name = "nebula"
        
    def _get_headers(self) -> dict:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers
    
    def is_version_compatible_with_v2(self, version: str) -> bool:
        """
        Check if a Nebula version supports v2 certificates.
        
        Args:
            version: Version string (e.g., "1.9.7", "1.10.0", "nightly-2025-12-04")
            
        Returns:
            True if version >= 1.10.0 or is a nightly build
        """
        if version.startswith('nightly'):
            return True
        
        try:
            # Parse version string (e.g., "1.10.0" -> [1, 10, 0])
            # Remove 'v' prefix if present
            clean_version = version.lstrip('v')
            parts = clean_version.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            
            # v2 support added in 1.10.0
            if major > 1:
                return True
            if major == 1 and minor >= 10:
                return True
            return False
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse Nebula version: {version}")
            return False
    
    async def fetch_available_versions(self, include_prereleases: bool = False) -> List[NebulaVersionInfo]:
        """
        Fetch available Nebula versions from GitHub releases.
        
        Args:
            include_prereleases: Whether to include pre-release versions (alpha, beta, rc)
            
        Returns:
            List of NebulaVersionInfo objects, sorted by release date (newest first)
        """
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/releases"
        params = {"per_page": 30}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._get_headers(), params=params)
                
                if response.status_code == 404:
                    logger.warning(f"No releases found for {self.repo_owner}/{self.repo_name}")
                    return []
                
                if response.status_code == 403:
                    logger.error(f"GitHub API rate limit exceeded for {self.repo_owner}/{self.repo_name}")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                versions = []
                for release in data:
                    # Skip pre-releases if not requested
                    if release.get("prerelease", False) and not include_prereleases:
                        continue
                    
                    # Skip drafts
                    if release.get("draft", False):
                        continue
                    
                    tag_name = release.get("tag_name", "")
                    version = tag_name.lstrip('v')
                    
                    # Parse published date
                    published_at_str = release.get("published_at", "")
                    published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                    
                    # Determine if stable (not prerelease, no alpha/beta/rc in name)
                    is_stable = not release.get("prerelease", False)
                    if any(x in version.lower() for x in ['alpha', 'beta', 'rc', 'nightly']):
                        is_stable = False
                    
                    # Check v2 support
                    supports_v2 = self.is_version_compatible_with_v2(version)
                    
                    # Extract download URLs from assets
                    assets = release.get("assets", [])
                    download_urls = self._extract_download_urls(tag_name, assets)
                    
                    versions.append(NebulaVersionInfo(
                        version=version,
                        release_date=published_at,
                        is_stable=is_stable,
                        supports_v2=supports_v2,
                        **download_urls
                    ))
                
                # Sort by release date, newest first
                versions.sort(key=lambda v: v.release_date, reverse=True)
                return versions
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch Nebula releases: {e}")
            return []
    
    def _extract_download_urls(self, tag_name: str, assets: List[dict]) -> dict:
        """
        Extract download URLs for different platforms from release assets.
        
        Args:
            tag_name: Release tag name (e.g., "v1.10.0")
            assets: List of release assets from GitHub API
            
        Returns:
            Dictionary with platform-specific download URLs
        """
        urls = {}
        
        # Map asset filenames to platform keys
        platform_map = {
            'linux-amd64.tar.gz': 'download_url_linux_amd64',
            'linux-arm64.tar.gz': 'download_url_linux_arm64',
            'darwin-amd64.tar.gz': 'download_url_darwin_amd64',
            'darwin-arm64.tar.gz': 'download_url_darwin_arm64',
            'windows-amd64.zip': 'download_url_windows_amd64',
        }
        
        for asset in assets:
            name = asset.get("name", "")
            browser_download_url = asset.get("browser_download_url")
            
            for pattern, key in platform_map.items():
                if pattern in name and browser_download_url:
                    urls[key] = browser_download_url
                    break
        
        return urls
    
    async def get_latest_stable_version(self) -> Optional[NebulaVersionInfo]:
        """
        Get the latest stable Nebula version.
        
        Returns:
            NebulaVersionInfo for the latest stable release, or None if not found
        """
        versions = await self.fetch_available_versions(include_prereleases=False)
        stable_versions = [v for v in versions if v.is_stable]
        return stable_versions[0] if stable_versions else None
