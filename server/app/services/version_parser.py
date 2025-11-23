"""Version parsing and comparison utilities using semantic versioning."""
from typing import Optional, Tuple
import re
from packaging.version import Version, InvalidVersion


def parse_version(version_string: Optional[str]) -> Optional[Version]:
    """
    Parse a version string into a Version object.
    
    Handles formats like:
    - "v1.9.7" -> Version("1.9.7")
    - "1.9.7" -> Version("1.9.7")
    - "1.9" -> Version("1.9")
    - "v1.9.7-beta" -> Version("1.9.7b0")
    
    Args:
        version_string: Version string to parse
        
    Returns:
        Version object if parsing succeeds, None otherwise
    """
    if not version_string:
        return None
    
    # Remove leading 'v' or 'V'
    clean_version = version_string.strip()
    if clean_version.lower().startswith('v'):
        clean_version = clean_version[1:]
    
    try:
        return Version(clean_version)
    except InvalidVersion:
        # Try to extract just the numeric version
        match = re.match(r'^(\d+\.\d+(?:\.\d+)?)', clean_version)
        if match:
            try:
                return Version(match.group(1))
            except InvalidVersion:
                pass
    
    return None


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.
    
    Args:
        version1: First version string
        version2: Second version string
        
    Returns:
        -1 if version1 < version2
        0 if version1 == version2
        1 if version1 > version2
        None if comparison fails
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)
    
    if v1 is None or v2 is None:
        return None
    
    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0


def is_version_current(current: str, latest: str) -> bool:
    """
    Check if current version is up to date with latest.
    
    Args:
        current: Current version string
        latest: Latest version string
        
    Returns:
        True if current >= latest, False otherwise
    """
    result = compare_versions(current, latest)
    return result is not None and result >= 0


def extract_version_components(version_string: str) -> Optional[Tuple[int, int, int]]:
    """
    Extract major, minor, and patch components from version string.
    
    Args:
        version_string: Version string to parse
        
    Returns:
        Tuple of (major, minor, patch) or None if parsing fails
    """
    version = parse_version(version_string)
    if version is None:
        return None
    
    # Use packaging.version's parsed components
    major = version.major
    minor = version.minor
    micro = version.micro
    
    return (major, minor, micro)


def is_prerelease(version_string: str) -> bool:
    """
    Check if a version string represents a pre-release.
    
    Args:
        version_string: Version string to check
        
    Returns:
        True if version is a pre-release (alpha, beta, rc, etc.)
    """
    version = parse_version(version_string)
    if version is None:
        return False
    
    return version.is_prerelease


def normalize_version(version_string: str) -> Optional[str]:
    """
    Normalize a version string to a standard format.
    
    Args:
        version_string: Version string to normalize
        
    Returns:
        Normalized version string (e.g., "1.9.7") or None
    """
    version = parse_version(version_string)
    if version is None:
        return None
    
    return str(version.base_version)
