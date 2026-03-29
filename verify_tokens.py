#!/usr/bin/env python3
"""Verify client token integrity after migration."""
import sys
import os
sys.path.insert(0, "/app")
os.chdir("/app")

import asyncio
from sqlalchemy import select, func
from app.db import get_session
from app.models import ClientToken, Client

async def verify_tokens():
    async for session in get_session():
        # Count clients and tokens
        client_count = await session.scalar(select(func.count()).select_from(Client))
        token_count = await session.scalar(select(func.count()).select_from(ClientToken))
        active_token_count = await session.scalar(
            select(func.count()).select_from(ClientToken).where(ClientToken.is_active == True)
        )
        
        print(f"Total clients: {client_count}")
        print(f"Total tokens: {token_count}")
        print(f"Active tokens: {active_token_count}")
        
        # Show clients without active tokens
        result = await session.execute(
            select(Client).outerjoin(ClientToken, (ClientToken.client_id == Client.id) & (ClientToken.is_active == True))
            .where(ClientToken.id == None)
        )
        clients_without_tokens = result.scalars().all()
        
        if clients_without_tokens:
            print(f"\n⚠️  Clients WITHOUT active tokens ({len(clients_without_tokens)}):")
            for client in clients_without_tokens:
                print(f"  - {client.name} (ID: {client.id})")
        else:
            print("\n✓ All clients have active tokens")
        
        break

if __name__ == "__main__":
    asyncio.run(verify_tokens())
