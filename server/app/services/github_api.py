"""GitHub API integration for version and security advisory checks."""
import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ReleaseInfo:
    """Information about a GitHub release."""
    version: str
    tag_name: str
    published_at: datetime
    prerelease: bool
    url: str
    body: Optional[str] = None


@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    data: Any
    expires_at: datetime


class GitHubAPIClient:
    """Client for GitHub API with caching and rate limit handling."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client.
        
        Args:
            token: Optional GitHub API token for higher rate limits
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def _get_from_cache(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry and entry.expires_at > datetime.utcnow():
                logger.debug(f"Cache hit for {key}")
                return entry.data
            elif entry:
                logger.debug(f"Cache expired for {key}")
                del self._cache[key]
            return None
    
    async def _set_cache(self, key: str, data: Any, ttl_seconds: int):
        """Set data in cache with TTL."""
        async with self._lock:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            self._cache[key] = CacheEntry(data=data, expires_at=expires_at)
            logger.debug(f"Cached {key} until {expires_at}")
    
    async def get_latest_release(
        self,
        owner: str,
        repo: str,
        cache_ttl: int = 3600
    ) -> Optional[ReleaseInfo]:
        """
        Get latest release from GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            cache_ttl: Cache TTL in seconds (default 1 hour)
            
        Returns:
            ReleaseInfo object or None if not found
        """
        cache_key = f"release:{owner}/{repo}"
        
        # Check cache
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Fetch from GitHub
        url = f"{self.base_url}/repos/{owner}/{repo}/releases/latest"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._get_headers())
                
                if response.status_code == 404:
                    logger.warning(f"No releases found for {owner}/{repo}")
                    return None
                
                if response.status_code == 403:
                    logger.error(f"GitHub API rate limit exceeded for {owner}/{repo}")
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                # Parse release info
                version = data.get("tag_name", "").lstrip("v")
                published_at_str = data.get("published_at", "")
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                
                release_info = ReleaseInfo(
                    version=version,
                    tag_name=data.get("tag_name", ""),
                    published_at=published_at,
                    prerelease=data.get("prerelease", False),
                    url=data.get("html_url", ""),
                    body=data.get("body")
                )
                
                # Cache result
                await self._set_cache(cache_key, release_info, cache_ttl)
                
                return release_info
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch latest release for {owner}/{repo}: {e}")
            return None
    
    async def get_all_releases(
        self,
        owner: str,
        repo: str,
        per_page: int = 30,
        cache_ttl: int = 3600
    ) -> List[ReleaseInfo]:
        """
        Get all releases from GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            per_page: Number of releases per page
            cache_ttl: Cache TTL in seconds (default 1 hour)
            
        Returns:
            List of ReleaseInfo objects
        """
        cache_key = f"releases:{owner}/{repo}"
        
        # Check cache
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Fetch from GitHub
        url = f"{self.base_url}/repos/{owner}/{repo}/releases"
        params = {"per_page": per_page}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._get_headers(), params=params)
                
                if response.status_code == 404:
                    logger.warning(f"No releases found for {owner}/{repo}")
                    return []
                
                if response.status_code == 403:
                    logger.error(f"GitHub API rate limit exceeded for {owner}/{repo}")
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                # Parse releases
                releases = []
                for item in data:
                    version = item.get("tag_name", "").lstrip("v")
                    published_at_str = item.get("published_at", "")
                    published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
                    
                    releases.append(ReleaseInfo(
                        version=version,
                        tag_name=item.get("tag_name", ""),
                        published_at=published_at,
                        prerelease=item.get("prerelease", False),
                        url=item.get("html_url", ""),
                        body=item.get("body")
                    ))
                
                # Cache result
                await self._set_cache(cache_key, releases, cache_ttl)
                
                return releases
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch releases for {owner}/{repo}: {e}")
            return []
    
    async def get_security_advisories(
        self,
        owner: str,
        repo: str,
        cache_ttl: int = 21600
    ) -> List[Dict[str, Any]]:
        """
        Get security advisories from GitHub repository.
        
        Note: This endpoint requires authentication and may not be available
        for all repositories. Returns empty list if unavailable.
        
        Args:
            owner: Repository owner
            repo: Repository name
            cache_ttl: Cache TTL in seconds (default 6 hours)
            
        Returns:
            List of advisory dictionaries
        """
        cache_key = f"advisories:{owner}/{repo}"
        
        # Check cache
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Fetch from GitHub
        # Note: Using the GraphQL API or REST endpoint for security advisories
        # The REST endpoint is: GET /repos/{owner}/{repo}/security-advisories
        url = f"{self.base_url}/repos/{owner}/{repo}/security-advisories"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._get_headers())
                
                # Advisories endpoint may not be available without proper permissions
                if response.status_code in [404, 403]:
                    logger.info(f"Security advisories not accessible for {owner}/{repo}")
                    # Cache empty result to avoid repeated failed requests
                    await self._set_cache(cache_key, [], cache_ttl)
                    return []
                
                response.raise_for_status()
                advisories = response.json()
                
                # Cache result
                await self._set_cache(cache_key, advisories, cache_ttl)
                
                return advisories
                
        except httpx.HTTPError as e:
            logger.warning(f"Failed to fetch advisories for {owner}/{repo}: {e}")
            # Cache empty result
            await self._set_cache(cache_key, [], cache_ttl)
            return []
    
    async def check_rate_limit(self) -> Dict[str, Any]:
        """
        Check current GitHub API rate limit status.
        
        Returns:
            Dictionary with rate limit information
        """
        url = f"{self.base_url}/rate_limit"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to check rate limit: {e}")
            return {}
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        logger.info("GitHub API cache cleared")


# Global client instance
_github_client: Optional[GitHubAPIClient] = None


def get_github_client(token: Optional[str] = None) -> GitHubAPIClient:
    """
    Get global GitHub API client instance.
    
    Args:
        token: Optional GitHub API token
        
    Returns:
        GitHubAPIClient instance
    """
    global _github_client
    if _github_client is None:
        _github_client = GitHubAPIClient(token=token)
    elif token and _github_client.token != token:
        # Token changed, recreate client
        _github_client = GitHubAPIClient(token=token)
    return _github_client
