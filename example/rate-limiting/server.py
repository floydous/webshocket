"""
Feature 3: Decorator-Based Rate Limiting
==========================================
Demonstrates:
  - @rate_limit with human-readable periods ("5s", "1m")
  - Client receives RATE_LIMIT_EXCEEDED error after exhausting the limit
  - disconnect_on_limit_exceeded auto-kicks abusive clients

Run:  python server.py
Then: python client.py
"""

import asyncio
import webshocket
from webshocket import ClientConnection
from webshocket.rpc import rpc_method, rate_limit


class RateLimitHandler(webshocket.WebSocketHandler):
    @rpc_method()
    @rate_limit(limit=3, period="10s")
    async def limited_action(self, connection: ClientConnection, message: str):
        """Allows only 3 calls per 10 seconds."""
        return f"OK: {message}"

    @rpc_method()
    @rate_limit(limit=2, period="10s", disconnect_on_limit_exceeded=True)
    async def strict_action(self, connection: ClientConnection):
        """Allows 2 calls per 10s, then disconnects the client."""
        return "Strict OK"


async def main():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=RateLimitHandler)

    async with server:
        print("[Server] Running on ws://localhost:5000")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
