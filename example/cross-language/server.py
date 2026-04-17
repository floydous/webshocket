"""Feature 7: Cross-Language Compatibility (Server)
==================================================
Demonstrates:
  - A standard Webshocket server that accepts both framework and generic clients
  - The same RPC method can be called from Python, JavaScript, or any language

Run:  python server.py
Then: Open client.html in a browser, or run the Python client
"""

import asyncio

import webshocket
from webshocket import ClientConnection
from webshocket.rpc import rpc_method


class CrossLanguageHandler(webshocket.WebSocketHandler):
    @rpc_method()
    async def add(self, connection: ClientConnection, a: int, b: int):
        return a + b

    @rpc_method()
    async def greet(self, connection: ClientConnection, name: str):
        return f"Hello, {name}!"

    async def on_receive(self, connection: ClientConnection, packet):
        # Generic (non-framework) clients can also send raw messages
        connection.send(f"Echo: {packet.data}")


async def main():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=CrossLanguageHandler)

    async with server:
        print("[Server] Running on ws://localhost:5000")
        print("[Server] Accepts Python, JavaScript, and any WebSocket client")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
