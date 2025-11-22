"""Public endpoints (no authentication required)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ..db import get_session
from ..models.system_settings import SystemSettings
from ..models.schemas import GitHubSecretScanningPattern
from ..services.token_manager import get_token_prefix
from ..core.github_verification import get_github_pattern_regex


router = APIRouter(tags=["public"])


@router.get("/.well-known/secret-scanning.json")
async def github_secret_scanning_metadata(
    session: AsyncSession = Depends(get_session)
):
    """GitHub Secret Scanning Partner Program metadata endpoint.
    
    This is a public endpoint that GitHub uses to discover secret patterns.
    No authentication required.
    """
    # Get current token prefix
    prefix = await get_token_prefix(session)
    
    # Generate pattern regex
    pattern = get_github_pattern_regex(prefix)
    
    # Return pattern metadata
    patterns = [
        GitHubSecretScanningPattern(
            type="managed_nebula_client_token",
            pattern=pattern,
            description="Managed Nebula Client Token"
        )
    ]
    
    return [p.model_dump() for p in patterns]
