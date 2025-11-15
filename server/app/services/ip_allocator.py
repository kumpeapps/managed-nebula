from __future__ import annotations
import ipaddress
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models import IPPool, IPAssignment, IPGroup


async def ensure_default_pool(session: AsyncSession, cidr: str) -> IPPool:
    existing = (await session.execute(select(IPPool).where(IPPool.cidr == cidr))).scalars().first()
    if existing:
        return existing
    pool = IPPool(cidr=cidr, description="Default pool")
    session.add(pool)
    await session.flush()
    return pool


async def allocate_ip_from_pool(session: AsyncSession, pool: IPPool) -> str:
    """Allocate the next available host IP within the given pool's CIDR.

    Only considers assignments within the same pool.
    """
    network = ipaddress.ip_network(pool.cidr)
    assigned = (
        await session.execute(
            select(IPAssignment.ip_address).where(IPAssignment.pool_id == pool.id)
        )
    ).scalars().all()
    assigned_set = set(assigned)
    # Skip network and broadcast (hosts() iterator handles this)
    for ip in network.hosts():
        ip_str = str(ip)
        if ip_str not in assigned_set:
            return ip_str
    raise RuntimeError("No available IPs in pool")


async def list_available_ips(session: AsyncSession, pool: IPPool, ip_group: IPGroup | None = None, limit: int = 512) -> list[str]:
    """Return up to 'limit' available IPs in the pool or within ip_group range if provided."""
    network = ipaddress.ip_network(pool.cidr)
    assigned = (
        await session.execute(
            select(IPAssignment.ip_address).where(IPAssignment.pool_id == pool.id)
        )
    ).scalars().all()
    assigned_set = set(assigned)
    candidates = []
    if ip_group:
        try:
            start = ipaddress.ip_address(ip_group.start_ip)
            end = ipaddress.ip_address(ip_group.end_ip)
        except Exception:
            return []
        ip = start
        while ip <= end and len(candidates) < limit:
            if ip in network.hosts() and str(ip) not in assigned_set:
                candidates.append(str(ip))
            ip = ip + 1
        return candidates
    else:
        for ip in network.hosts():
            ip_str = str(ip)
            if ip_str not in assigned_set:
                candidates.append(ip_str)
                if len(candidates) >= limit:
                    break
        return candidates


async def allocate_ip_from_group(session: AsyncSession, pool: IPPool, ip_group: IPGroup) -> str:
    """Allocate next available IP within an IPGroup range in a pool."""
    avail = await list_available_ips(session, pool, ip_group, limit=1)
    if not avail:
        raise RuntimeError("No available IPs in selected IP group")
    return avail[0]
