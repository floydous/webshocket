"""
Feature 8: Streaming RPC
==========================
Demonstrates:
  - Server-side async generator RPC methods that yield chunks
  - Client-side iteration over streamed responses
  - Mid-stream abort by breaking out of the loop

Run:  python server.py
Then: python client.py
"""

import asyncio
import webshocket
from webshocket import ClientConnection
from webshocket.rpc import rpc_method


class StreamHandler(webshocket.WebSocketHandler):
    @rpc_method()
    async def countdown(self, connection: ClientConnection, start: int):
        """Streams a countdown from 'start' down to 0, one number per second."""
        for i in range(start, -1, -1):
            yield f"T-{i}"
            await asyncio.sleep(0.5)

    @rpc_method()
    async def generate_words(self, connection: ClientConnection, sentence: str):
        """Simulates token-by-token streaming (like an AI model)."""
        words = sentence.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.3)


async def main():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=StreamHandler)

    async with server:
        print("[Server] Running on ws://localhost:5000")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
