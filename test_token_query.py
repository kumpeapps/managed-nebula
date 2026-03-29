#!/usr/bin/env python3
"""Test client token authentication query."""
import sys
sys.path.append('/app')

import asyncio
from sqlalchemy import select
from app.models import ClientToken
from app.db import get_session


async def test_query():
    """Test the exact query used in the client/config endpoint."""
    try:
        async for session in get_session():
            # Get all tokens
            result = await session.execute(select(ClientToken))
            all_tokens = result.scalars().all()
            print(f"Total tokens in database: {len(all_tokens)}")
            
            # Get active tokens
            result = await session.execute(
                select(ClientToken).where(ClientToken.is_active == True)
            )
            active_tokens = result.scalars().all()
            print(f"Active tokens: {len(active_tokens)}")
            
            # Show all tokens with details
            result = await session.execute(select(ClientToken))
            tokens = result.scalars().all()
            print("\nAll tokens:")
            for token in tokens:
                print(f"  ID: {token.id}, Client ID: {token.client_id}, Active: {token.is_active}, Token: {token.token[:20] if token.token else 'None'}...")
            
            # Try one example query like the endpoint does
            if active_tokens:
                test_token = active_tokens[0].token
                print(f"\nTesting query with token: {test_token[:20]}...")
                q = await session.execute(
                    select(ClientToken).where(
                        ClientToken.token == test_token,
                        ClientToken.is_active == True
                    )
                )
                result_token = q.scalar_one_or_none()
                if result_token:
                    print(f"✓ Query successful - Found token for client {result_token.client_id}")
                else:
                    print("✗ Query returned None (should have found token!)")
            
            break
            
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_query())
