"""
Feature 2: Effortless Session State (Client)
==============================================
Shows state persisting across multiple RPC calls on the same connection.
"""

import asyncio
import webshocket


async def main():
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        # Check identity before login
        r = await client.send_rpc("whoami")
        print(r.data)  # Anonymous

        # Login
        r = await client.send_rpc("login", "Alice")
        print(r.data)  # Welcome, Alice!

        # Increment counter multiple times - state persists
        for _ in range(3):
            r = await client.send_rpc("increment_counter")
            print(r.data)

        # Verify state
        r = await client.send_rpc("whoami")
        print(r.data)  # Alice with counter=3


if __name__ == "__main__":
    asyncio.run(main())
