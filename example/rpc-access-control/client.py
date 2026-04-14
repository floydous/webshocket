"""
Feature 1: Powerful RPC with Access Control (Client)
=====================================================
Calls the server's RPC methods and demonstrates access-denied flow.
"""

import asyncio
import webshocket


async def main():
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        # 1. Call the aliased 'add' method
        result = await client.send_rpc("add", 10, 20)
        print(f"add(10, 20) = {result.data}")  # 30

        # 2. Try to access the protected method BEFORE being admin
        denied = await client.send_rpc("secret_data")
        print(f"Before admin: {denied.data}")  # Access denied error

        # 3. Grant ourselves admin
        grant = await client.send_rpc("grant_admin")
        print(f"Grant admin: {grant.data}")

        # 4. Now access the protected method
        secret = await client.send_rpc("secret_data")
        print(f"After admin: {secret.data}")  # Top-secret admin data!


if __name__ == "__main__":
    asyncio.run(main())
