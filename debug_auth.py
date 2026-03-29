#!/usr/bin/env python3
"""Debug 401 errors by checking recent client requests."""
import sys
import os
sys.path.insert(0, "/app")
os.chdir("/app")

import asyncio
from sqlalchemy import select, desc
from app.db import get_session
from app.models import ClientToken, Client

async def debug_auth():
    async for session in get_session():
        # Get all clients with their tokens
        result = await session.execute(
            select(Client, ClientToken)
            .join(ClientToken, ClientToken.client_id == Client.id)
            .where(ClientToken.is_active == True)
            .order_by(Client.name)
        )
        
        print("=== Active Clients and Tokens ===\n")
        for client, token in result.all():
            token_preview = f"{token.token[:12]}...{token.token[-8:]}"
            print(f"Client: {client.name} (ID: {client.id})")
            print(f"  Token: {token_preview}")
            print(f"  Active: {token.is_active}")
            print(f"  Last config download: {client.last_config_download_at}")
            print()
        
        # Check for inactive tokens
        result = await session.execute(
            select(ClientToken).where(ClientToken.is_active == False)
        )
        inactive = result.scalars().all()
        
        if inactive:
            print(f"\n=== Inactive Tokens ({len(inactive)}) ===\n")
            for token in inactive:
                result = await session.execute(
                    select(Client).where(Client.id == token.client_id)
                )
                client = result.scalar_one_or_none()
                if client:
                    print(f"  Client: {client.name} (ID: {client.id}) - INACTIVE TOKEN")
        
        break

if __name__ == "__main__":
    asyncio.run(debug_auth())
