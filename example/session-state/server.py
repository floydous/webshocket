"""Feature 2: Effortless Session State
=====================================
Demonstrates:
  - Assigning attributes directly to ClientConnection
  - Session state persists across multiple RPC calls
  - State is isolated between clients

Run:  python server.py
Then: python client.py
"""

import asyncio

import webshocket
from webshocket import ClientConnection


class SessionHandler(webshocket.WebSocketHandler):
    @webshocket.rpc_method()
    async def login(self, connection: ClientConnection, username: str):
        """Assigns session state via direct attribute access."""
        connection.username = username
        connection.login_count = 0
        return f"Welcome, {username}!"

    @webshocket.rpc_method()
    async def increment_counter(self, connection: ClientConnection):
        """Demonstrates that state persists across calls."""
        connection.login_count += 1
        return f"{connection.username}: counter = {connection.login_count}"

    @webshocket.rpc_method()
    async def whoami(self, connection: ClientConnection):
        """Returns session state, showing it persists."""
        name = getattr(connection, "username", "Anonymous")
        count = getattr(connection, "login_count", 0)
        return f"You are '{name}' with counter={count}"


async def main():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=SessionHandler)

    async with server:
        print("[Server] Running on ws://localhost:5000")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
