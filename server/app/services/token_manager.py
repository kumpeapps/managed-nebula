"""Token generation and management utilities."""
import secrets
import string
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


async def get_token_prefix(session: AsyncSession) -> str:
    """Get current token prefix from system settings.
    
    Args:
        session: Database session
        
    Returns:
        Token prefix string (default: 'mnebula_')
    """
    from ..models.system_settings import SystemSettings
    
    result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == "token_prefix")
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else "mnebula_"


def validate_token_prefix(prefix: str) -> bool:
    """Validate token prefix format.
    
    Args:
        prefix: Token prefix to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not prefix or not (3 <= len(prefix) <= 20):
        return False
    if not all(c.isalnum() or c == '_' for c in prefix):
        return False
    return True


def generate_client_token(prefix: str) -> str:
    """Generate a standardized client token with configurable prefix.
    
    The token format is: <prefix><32-random-alphanumeric-chars>
    Example: mnebula_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
    
    Args:
        prefix: Token prefix (e.g., 'mnebula_')
        
    Returns:
        Complete token string
        
    Raises:
        ValueError: If prefix format is invalid
    """
    if not validate_token_prefix(prefix):
        raise ValueError(
            "Prefix must be 3-20 characters and contain only alphanumeric characters and underscores"
        )
    
    # Generate 32 random lowercase alphanumeric characters
    alphabet = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    return f"{prefix}{random_part}"


def is_token_valid_format(token: str) -> bool:
    """Check if a token matches the expected format (with or without prefix).
    
    This supports backward compatibility with legacy tokens.
    
    Args:
        token: Token string to validate
        
    Returns:
        True if token format is valid
    """
    # Pattern 1: 3-20 char prefix (alphanumeric + underscore) + 32 lowercase alphanumeric chars
    # Minimum prefix: 3 chars total (e.g., "ab_"), maximum 20 chars (e.g., "very_long_prefix_")
    # Pattern 2: 32+ alphanumeric chars (legacy format)
    pattern1 = r'^[a-z0-9_]{3,20}[a-z0-9]{32}$'  # New format with prefix
    pattern2 = r'^[A-Za-z0-9_-]{32,}$'  # Legacy format
    return bool(re.match(pattern1, token) or re.match(pattern2, token))


def get_token_preview(token: str, preview_length: int = 12) -> str:
    """Get a preview of the token (first N characters) for logging.
    
    Args:
        token: Full token string
        preview_length: Number of characters to include in preview
        
    Returns:
        Token preview (e.g., 'mnebula_a1b2')
    """
    return token[:preview_length] if len(token) >= preview_length else token
