"""
API Key Authorization Service

Provides scope-based authorization for API keys with restricted permissions.
Checks if API keys have permission to access/modify specific resources based on:
- Allowed groups
- Allowed IP pools
- Created clients only restriction
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from ..models.api_key import UserAPIKey
from ..models.client import Client, Group, IPPool


async def get_api_key_with_scopes(
    session: AsyncSession,
    api_key_id: int
) -> Optional[UserAPIKey]:
    """Get API key with all scope relationships loaded."""
    result = await session.execute(
        select(UserAPIKey)
        .where(UserAPIKey.id == api_key_id)
        .options(
            selectinload(UserAPIKey.allowed_groups),
            selectinload(UserAPIKey.allowed_ip_pools)
        )
    )
    return result.scalar_one_or_none()


async def check_client_access(
    session: AsyncSession,
    api_key: UserAPIKey,
    client: Client,
    operation: str = "read"
) -> bool:
    """
    Check if API key has access to a client.
    
    Args:
        session: Database session
        api_key: The API key being used
        client: The client to check access for
        operation: "read", "update", or "delete"
    
    Returns:
        True if access is allowed, False otherwise
    """
    # If key has restrict_to_created_clients, only allow access to clients it created
    if api_key.restrict_to_created_clients:
        if client.created_by_api_key_id != api_key.id:
            return False
    
    # If key has group restrictions, check if client is in allowed groups
    if api_key.allowed_groups:
        # Load client groups if not already loaded
        if not client.groups:
            result = await session.execute(
                select(Client)
                .where(Client.id == client.id)
                .options(selectinload(Client.groups))
            )
            client = result.scalar_one()
        
        # Check if any client group is in allowed groups
        client_group_ids = {g.id for g in client.groups}
        allowed_group_ids = {g.id for g in api_key.allowed_groups}
        
        if not client_group_ids.intersection(allowed_group_ids):
            return False
    
    # If key has IP pool restrictions, check if client's IPs are in allowed pools
    if api_key.allowed_ip_pools:
        # Load client IP assignments if not already loaded
        if not client.ip_assignments:
            result = await session.execute(
                select(Client)
                .where(Client.id == client.id)
                .options(selectinload(Client.ip_assignments))
            )
            client = result.scalar_one()
        
        # Check if any client IP is in allowed pools
        client_pool_ids = {ip.pool_id for ip in client.ip_assignments if ip.pool_id}
        allowed_pool_ids = {p.id for p in api_key.allowed_ip_pools}
        
        if not client_pool_ids.intersection(allowed_pool_ids):
            return False
    
    return True


async def check_group_access(
    api_key: UserAPIKey,
    group: Group
) -> bool:
    """
    Check if API key has access to a group.
    
    Args:
        api_key: The API key being used
        group: The group to check access for
    
    Returns:
        True if access is allowed, False otherwise
    """
    # If key has no group restrictions, allow all groups
    if not api_key.allowed_groups:
        return True
    
    # Check if group is in allowed groups
    allowed_group_ids = {g.id for g in api_key.allowed_groups}
    return group.id in allowed_group_ids


async def check_ip_pool_access(
    api_key: UserAPIKey,
    ip_pool: IPPool
) -> bool:
    """
    Check if API key has access to an IP pool.
    
    Args:
        api_key: The API key being used
        ip_pool: The IP pool to check access for
    
    Returns:
        True if access is allowed, False otherwise
    """
    # If key has no IP pool restrictions, allow all pools
    if not api_key.allowed_ip_pools:
        return True
    
    # Check if pool is in allowed pools
    allowed_pool_ids = {p.id for p in api_key.allowed_ip_pools}
    return ip_pool.id in allowed_pool_ids


async def filter_clients_by_scope(
    session: AsyncSession,
    api_key: UserAPIKey,
    clients: List[Client]
) -> List[Client]:
    """
    Filter a list of clients based on API key scope restrictions.
    
    Args:
        session: Database session
        api_key: The API key being used
        clients: List of clients to filter
    
    Returns:
        Filtered list of clients the API key has access to
    """
    allowed_clients = []
    
    for client in clients:
        if await check_client_access(session, api_key, client, "read"):
            allowed_clients.append(client)
    
    return allowed_clients


async def require_client_access(
    session: AsyncSession,
    api_key: UserAPIKey,
    client: Client,
    operation: str = "read"
) -> None:
    """
    Require API key to have access to a client, raise HTTPException if not.
    
    Args:
        session: Database session
        api_key: The API key being used
        client: The client to check access for
        operation: "read", "update", or "delete"
    
    Raises:
        HTTPException: 403 if access is denied
    """
    if not await check_client_access(session, api_key, client, operation):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key does not have permission to {operation} this client"
        )


async def require_group_access(
    api_key: UserAPIKey,
    group: Group
) -> None:
    """
    Require API key to have access to a group, raise HTTPException if not.
    
    Args:
        api_key: The API key being used
        group: The group to check access for
    
    Raises:
        HTTPException: 403 if access is denied
    """
    if not await check_group_access(api_key, group):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to access this group"
        )


async def require_ip_pool_access(
    api_key: UserAPIKey,
    ip_pool: IPPool
) -> None:
    """
    Require API key to have access to an IP pool, raise HTTPException if not.
    
    Args:
        api_key: The API key being used
        ip_pool: The IP pool to check access for
    
    Raises:
        HTTPException: 403 if access is denied
    """
    if not await check_ip_pool_access(api_key, ip_pool):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key does not have permission to access this IP pool"
        )
