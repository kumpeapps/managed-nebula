#!/usr/bin/env python3
"""Quick script to check client tokens in the database."""
import asyncio
from sqlalchemy import select, text
from server.app.db import get_session
from server.app.models import ClientToken

async def check_tokens():
    async for session in get_session():
        # Count all tokens
        result = await session.execute(select(text("COUNT(*) as total")).select_from(ClientToken))
        total = result.scalar()
        print(f"Total client tokens: {total}")
        
        # Count active tokens
        result = await session.execute(
            select(text("COUNT(*) as active")).select_from(ClientToken).where(ClientToken.is_active == True)
        )
        active = result.scalar()
        print(f"Active client tokens: {active}")
        
        # Show sample tokens (first 5)
        result = await session.execute(
            select(ClientToken).limit(5)
        )
        tokens = result.scalars().all()
        print(f"\nSample tokens:")
        for token in tokens:
            print(f"  ID: {token.id}, Client ID: {token.client_id}, Active: {token.is_active}, Token: {token.token[:20]}...")
        
        break

if __name__ == "__main__":
    asyncio.run(check_tokens())
