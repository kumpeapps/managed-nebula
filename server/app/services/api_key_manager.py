"""Service for managing user API keys."""
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext

from ..models.api_key import UserAPIKey
from ..models.user import User
from ..models.client import Group, IPPool


# Use the same password hashing context as auth.py for consistency
pwd_context = CryptContext(
    schemes=["bcrypt_sha256"],
    deprecated="auto",
)


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key with prefix and hash.
    
    Returns:
        tuple: (full_key, key_prefix, key_hash)
            - full_key: The complete API key to be shown to user once
            - key_prefix: First 8 characters for display/identification
            - key_hash: Hashed version for secure storage
    """
    # Generate 32-byte random key and encode as hex
    key = secrets.token_hex(32)  # 64 character hex string
    
    # Add a prefix for identification
    full_key = f"mnapi_{key}"
    
    # Store first 8 chars for preview
    key_prefix = full_key[:12]  # "mnapi_" + first 6 chars
    
    # Hash the key for storage
    key_hash = pwd_context.hash(full_key)
    
    return full_key, key_prefix, key_hash


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash.
    
    Args:
        plain_key: The plain text API key
        hashed_key: The hashed API key from database
        
    Returns:
        bool: True if the key matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_key, hashed_key)
    except Exception:
        return False


async def create_api_key(
    session: AsyncSession,
    user_id: int,
    name: str,
    scopes: Optional[List[str]] = None,
    expires_in_days: Optional[int] = None,
    allowed_group_ids: Optional[List[int]] = None,
    allowed_ip_pool_ids: Optional[List[int]] = None,
    restrict_to_created_clients: bool = False,
    parent_key_id: Optional[int] = None
) -> tuple[UserAPIKey, str]:
    """Create a new API key for a user.
    
    Args:
        session: Database session
        user_id: ID of the user creating the key
        name: Descriptive name for the API key
        scopes: List of permission scopes (legacy, for future use)
        expires_in_days: Number of days until expiration (None = no expiration)
        allowed_group_ids: List of group IDs this key can access (None = all)
        allowed_ip_pool_ids: List of IP pool IDs this key can access (None = all)
        restrict_to_created_clients: If True, key can only access clients it created
        parent_key_id: ID of parent key if this is a regeneration
        
    Returns:
        tuple: (api_key_model, full_key)
            - api_key_model: The created UserAPIKey database object
            - full_key: The plaintext API key (show only once)
    """
    full_key, key_prefix, key_hash = generate_api_key()
    
    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    # Convert scopes list to JSON string for storage
    scopes_json = json.dumps(scopes) if scopes else None
    
    api_key = UserAPIKey(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes_json,
        is_active=True,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        usage_count=0,
        restrict_to_created_clients=restrict_to_created_clients,
        parent_key_id=parent_key_id
    )
    
    session.add(api_key)
    await session.flush()  # Flush to get the ID before adding relationships
    
    # Add group restrictions
    if allowed_group_ids:
        groups = await session.execute(
            select(Group).where(Group.id.in_(allowed_group_ids))
        )
        api_key.allowed_groups = list(groups.scalars().all())
    
    # Add IP pool restrictions
    if allowed_ip_pool_ids:
        pools = await session.execute(
            select(IPPool).where(IPPool.id.in_(allowed_ip_pool_ids))
        )
        api_key.allowed_ip_pools = list(pools.scalars().all())
    
    await session.commit()
    await session.refresh(api_key)
    
    return api_key, full_key


async def get_user_api_keys(
    session: AsyncSession,
    user_id: int,
    include_inactive: bool = False
) -> List[UserAPIKey]:
    """Get all API keys for a user.
    
    Args:
        session: Database session
        user_id: ID of the user
        include_inactive: Whether to include inactive/revoked keys
        
    Returns:
        List of UserAPIKey objects
    """
    query = select(UserAPIKey).where(UserAPIKey.user_id == user_id)
    
    if not include_inactive:
        query = query.where(UserAPIKey.is_active == True)
    
    # Load relationships for scope information
    query = query.options(
        selectinload(UserAPIKey.allowed_groups),
        selectinload(UserAPIKey.allowed_ip_pools)
    )
    
    result = await session.execute(query.order_by(UserAPIKey.created_at.desc()))
    return list(result.scalars().all())


async def get_api_key_by_id(
    session: AsyncSession,
    key_id: int,
    user_id: Optional[int] = None
) -> Optional[UserAPIKey]:
    """Get an API key by ID.
    
    Args:
        session: Database session
        key_id: ID of the API key
        user_id: Optional user ID to filter by (for non-admin access)
        
    Returns:
        UserAPIKey object or None if not found
    """
    query = select(UserAPIKey).where(UserAPIKey.id == key_id)
    
    if user_id is not None:
        query = query.where(UserAPIKey.user_id == user_id)
    
    # Load relationships for scope information
    query = query.options(
        selectinload(UserAPIKey.allowed_groups),
        selectinload(UserAPIKey.allowed_ip_pools)
    )
    
    result = await session.execute(query)
    return result.scalars().first()


async def revoke_api_key(
    session: AsyncSession,
    key_id: int,
    user_id: Optional[int] = None
) -> bool:
    """Revoke (deactivate) an API key.
    
    Args:
        session: Database session
        key_id: ID of the API key to revoke
        user_id: Optional user ID to filter by (for non-admin access)
        
    Returns:
        bool: True if key was revoked, False if not found
    """
    api_key = await get_api_key_by_id(session, key_id, user_id)
    
    if not api_key:
        return False
    
    api_key.is_active = False
    await session.commit()
    
    return True


async def regenerate_api_key(
    session: AsyncSession,
    key_id: int,
    user_id: Optional[int] = None,
    new_name: Optional[str] = None
) -> Optional[tuple[UserAPIKey, str]]:
    """Regenerate an API key while maintaining its permissions.
    
    Creates a new key with the same scope restrictions as the original key,
    then deactivates the original key. The new key will have a reference to
    the original key via parent_key_id.
    
    Args:
        session: Database session
        key_id: ID of the API key to regenerate
        user_id: Optional user ID to filter by (for non-admin access)
        new_name: Optional new name (defaults to original name with "(Regenerated)")
        
    Returns:
        tuple: (new_api_key, full_key) or None if original key not found
    """
    # Get the original key with all scope information
    original_key = await get_api_key_by_id(session, key_id, user_id)
    
    if not original_key:
        return None
    
    # Determine new name
    if new_name is None:
        new_name = f"{original_key.name} (Regenerated)"
    
    # Calculate expires_in_days from original key's expiration
    expires_in_days = None
    if original_key.expires_at:
        remaining = original_key.expires_at - datetime.utcnow()
        if remaining.total_seconds() > 0:
            expires_in_days = int(remaining.total_seconds() / 86400)
    
    # Extract scope restrictions from original key
    allowed_group_ids = [g.id for g in original_key.allowed_groups] if original_key.allowed_groups else None
    allowed_ip_pool_ids = [p.id for p in original_key.allowed_ip_pools] if original_key.allowed_ip_pools else None
    
    # Create new key with same permissions
    new_key, full_key = await create_api_key(
        session=session,
        user_id=original_key.user_id,
        name=new_name,
        scopes=None,  # Scopes field is legacy, not used
        expires_in_days=expires_in_days,
        allowed_group_ids=allowed_group_ids,
        allowed_ip_pool_ids=allowed_ip_pool_ids,
        restrict_to_created_clients=original_key.restrict_to_created_clients,
        parent_key_id=original_key.id
    )
    
    # Deactivate original key
    original_key.is_active = False
    await session.commit()
    
    return new_key, full_key


async def update_api_key(
    session: AsyncSession,
    key_id: int,
    user_id: Optional[int] = None,
    name: Optional[str] = None,
    is_active: Optional[bool] = None,
    allowed_group_ids: Optional[List[int]] = None,
    allowed_ip_pool_ids: Optional[List[int]] = None,
    restrict_to_created_clients: Optional[bool] = None
) -> Optional[UserAPIKey]:
    """Update an API key's metadata and scope restrictions.
    
    Args:
        session: Database session
        key_id: ID of the API key
        user_id: Optional user ID to filter by (for non-admin access)
        name: New name for the key
        is_active: New active status
        allowed_group_ids: New list of allowed group IDs (None = no change, [] = clear restrictions)
        allowed_ip_pool_ids: New list of allowed IP pool IDs (None = no change, [] = clear restrictions)
        restrict_to_created_clients: New restriction setting
        
    Returns:
        Updated UserAPIKey object or None if not found
    """
    api_key = await get_api_key_by_id(session, key_id, user_id)
    
    if not api_key:
        return None
    
    if name is not None:
        api_key.name = name
    
    if is_active is not None:
        api_key.is_active = is_active
    
    if restrict_to_created_clients is not None:
        api_key.restrict_to_created_clients = restrict_to_created_clients
    
    # Update group restrictions
    if allowed_group_ids is not None:
        if allowed_group_ids:
            groups = await session.execute(
                select(Group).where(Group.id.in_(allowed_group_ids))
            )
            api_key.allowed_groups = list(groups.scalars().all())
        else:
            api_key.allowed_groups = []
    
    # Update IP pool restrictions
    if allowed_ip_pool_ids is not None:
        if allowed_ip_pool_ids:
            pools = await session.execute(
                select(IPPool).where(IPPool.id.in_(allowed_ip_pool_ids))
            )
            api_key.allowed_ip_pools = list(pools.scalars().all())
        else:
            api_key.allowed_ip_pools = []
    
    await session.commit()
    await session.refresh(api_key)
    
    return api_key


async def authenticate_with_api_key(
    session: AsyncSession,
    api_key: str
) -> Optional[User]:
    """Authenticate a user using an API key.
    
    Args:
        session: Database session
        api_key: The plaintext API key from the request
        
    Returns:
        User object if authentication successful, None otherwise
    """
    # Get all active API keys (we need to check each hash)
    result = await session.execute(
        select(UserAPIKey).where(UserAPIKey.is_active == True)
    )
    all_keys = result.scalars().all()
    
    # Try to match the provided key with any stored hash
    matched_key = None
    for key in all_keys:
        if verify_api_key(api_key, key.key_hash):
            matched_key = key
            break
    
    if not matched_key:
        return None
    
    # Check if key is expired
    if matched_key.expires_at and matched_key.expires_at < datetime.utcnow():
        return None
    
    # Update usage tracking
    matched_key.last_used_at = datetime.utcnow()
    matched_key.usage_count += 1
    await session.commit()
    
    # Get the user
    user_result = await session.execute(
        select(User).where(User.id == matched_key.user_id)
    )
    user = user_result.scalars().first()
    
    if not user or not user.is_active:
        return None
    
    return user


async def get_api_key_count(session: AsyncSession, user_id: int) -> int:
    """Get count of active API keys for a user.
    
    Args:
        session: Database session
        user_id: ID of the user
        
    Returns:
        Count of active API keys
    """
    result = await session.execute(
        select(func.count(UserAPIKey.id))
        .where(UserAPIKey.user_id == user_id)
        .where(UserAPIKey.is_active == True)
    )
    return result.scalar() or 0
