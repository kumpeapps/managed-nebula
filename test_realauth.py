#!/usr/bin/env python3
"""Test client authentication with a real token from the database."""
import sys
import os
sys.path.insert(0, "/app")
os.chdir("/app")

import asyncio
import httpx
from sqlalchemy import select
from app.db import get_session
from app.models import ClientToken, Client

async def test_real_auth():
    """Get a real token and test authentication."""
    async for session in get_session():
        # Get first active token
        result = await session.execute(
            select(ClientToken, Client)
            .join(Client, ClientToken.client_id == Client.id)
            .where(ClientToken.is_active == True)
            .limit(1)
        )
        row = result.first()
        
        if not row:
            print("❌ No active tokens found in database")
            return
        
        token, client = row
        print(f"✓ Found client: {client.name} (ID: {client.id})")
        print(f"  Token: {token.token[:12]}...{token.token[-8:]}")
        
        # Test authentication
        url = "http://localhost:8080/api/v1/client/config"
        payload = {
            "token": token.token,
            "public_key": "test-public-key"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as http_client:
                response = await http_client.post(url, json=payload)
                
                if response.status_code == 200:
                    print(f"\n✅ Authentication SUCCESSFUL (200 OK)")
                    config = response.json()
                    print(f"   Config received: {len(config.get('config', ''))} bytes")
                elif response.status_code == 401:
                    print(f"\n❌ Authentication FAILED (401 Unauthorized)")
                    print(f"   Response: {response.text}")
                else:
                    print(f"\n⚠  Unexpected status: {response.status_code}")
                    print(f"   Response: {response.text}")
                    
        except Exception as e:
            print(f"\n❌ Request failed: {e}")
        
        break

if __name__ == "__main__":
    asyncio.run(test_real_auth())
