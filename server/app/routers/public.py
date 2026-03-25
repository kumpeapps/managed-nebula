"""Public endpoints (no authentication required)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
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
    # Get current token prefix for client tokens
    prefix = await get_token_prefix(session)
    
    # Generate pattern regex for client tokens
    client_token_pattern = get_github_pattern_regex(prefix)
    
    # Return pattern metadata for both client tokens and API keys
    patterns = [
        GitHubSecretScanningPattern(
            type="managed_nebula_client_token",
            pattern=client_token_pattern,
            description="Managed Nebula Client Token"
        ),
        GitHubSecretScanningPattern(
            type="managed_nebula_api_key",
            pattern="mnapi_[a-f0-9]{64}",
            description="Managed Nebula API Key"
        )
    ]
    
    return [p.model_dump() for p in patterns]
