"""
Feature 4: Pub/Sub Channels with Wildcard Support (Client)
============================================================
Two clients subscribing to different patterns and teams.
"""

import asyncio
import webshocket
from webshocket.exceptions import ReceiveTimeoutError


async def client_all_news():
    """Client A: Subscribes to 'news.*' (all news via wildcard)."""
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send_rpc("subscribe_channel", "news.*")
        await client.send_rpc("set_team", "red")
        await client.send_rpc("subscribe_channel", "game.lobby")
        print("[Client A] Subscribed to 'news.*' and 'game.lobby' (team=red)")

        while True:
            try:
                pkt = await client.recv(timeout=5.0)
                print(f"  [Client A] Received: {pkt.data}")
            except ReceiveTimeoutError:
                break

    print("[Client A] Done")


async def client_tech_only():
    """Client B: Subscribes to 'news.tech' only (exact match)."""
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send_rpc("subscribe_channel", "news.tech")
        await client.send_rpc("set_team", "blue")
        await client.send_rpc("subscribe_channel", "game.lobby")
        print("[Client B] Subscribed to 'news.tech' and 'game.lobby' (team=blue)")

        while True:
            try:
                pkt = await client.recv(timeout=5.0)
                print(f"  [Client B] Received: {pkt.data}")
            except ReceiveTimeoutError:
                break

    print("[Client B] Done")


async def main():
    await asyncio.gather(client_all_news(), client_tech_only())


if __name__ == "__main__":
    asyncio.run(main())
