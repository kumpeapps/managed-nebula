#!/usr/bin/env python3
"""Test authentication with all active tokens to find which ones fail."""
import sys
import os
sys.path.insert(0, "/app")
os.chdir("/app")

import asyncio
import httpx
from sqlalchemy import select
from app.db import get_session
from app.models import ClientToken, Client

async def test_all_tokens():
    """Test authentication with every active token."""
    async for session in get_session():
        result = await session.execute(
            select(ClientToken, Client)
            .join(Client, ClientToken.client_id == Client.id)
            .where(ClientToken.is_active == True)
            .order_by(Client.name)
        )
        
        url = "http://localhost:8080/api/v1/client/config"
        
        print("Testing authentication with all active tokens...\n")
        
        success_count = 0
        fail_count = 0
        
        async with httpx.AsyncClient(timeout=10) as http_client:
            for token_obj, client in result.all():
                payload = {
                    "token": token_obj.token,
                    "public_key": "test-public-key-12345"
                }
                
                try:
                    response = await http_client.post(url, json=payload)
                    
                    if response.status_code == 200:
                        print(f"✅ {client.name:25} - 200 OK")
                        success_count += 1
                    elif response.status_code == 401:
                        print(f"❌ {client.name:25} - 401 UNAUTHORIZED (active token rejected!)")
                        fail_count += 1
                    elif response.status_code == 409:
                        print(f"⚠️  {client.name:25} - 409 No IP assignment")
                        success_count += 1  # Auth worked, just missing IP
                    else:
                        print(f"⚠️  {client.name:25} - {response.status_code} {response.text[:50]}")
                        
                except Exception as e:
                    print(f"❌ {client.name:25} - ERROR: {str(e)[:50]}")
                    fail_count += 1
        
        print(f"\nResults: {success_count} succeeded, {fail_count} failed")
        
        if fail_count > 0:
            print("\n🚨 AUTHENTICATION BROKEN: Active tokens are being rejected!")
        else:
            print("\n✅ All active tokens authenticate successfully")
        
        break

if __name__ == "__main__":
    asyncio.run(test_all_tokens())
