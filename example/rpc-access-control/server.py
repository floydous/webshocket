"""
Feature 1: Powerful RPC with Access Control
============================================
Demonstrates:
  - Defining RPC methods with @rpc_method()
  - Alias names for RPC methods
  - Protecting methods with predicates (webshocket.Is)

Run:  python server.py
Then: python client.py
"""

import asyncio
import webshocket
from webshocket import ClientConnection


class MyHandler(webshocket.WebSocketHandler):
    @webshocket.rpc_method(alias_name="add")
    async def add_numbers(self, _: ClientConnection, a: int, b: int):
        """A simple RPC method that adds two numbers. Aliased as 'add'."""
        return a + b

    @webshocket.rpc_method()
    async def grant_admin(self, connection: ClientConnection):
        """Grants admin privileges to the calling client."""
        connection.is_admin = True
        return "You are now an admin."

    @webshocket.rpc_method(requires=webshocket.Is("is_admin"))
    async def secret_data(self, connection: ClientConnection):
        """Only accessible to clients where connection.is_admin is True."""
        return "Top-secret admin data!"


async def main():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=MyHandler)

    async with server:
        print("[Server] Running on ws://localhost:5000")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
