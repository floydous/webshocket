"""
Feature 4: Pub/Sub Channels with Wildcard Support
====================================================
Demonstrates:
  - Subscribing to exact channels and wildcard patterns
  - Publishing to channels with automatic pattern matching
  - Filtering with predicates (IsEqual)

Run:  python server.py
Then: python client.py
"""

import asyncio
import webshocket
from webshocket import ClientConnection
from webshocket.rpc import rpc_method


class PubSubHandler(webshocket.WebSocketHandler):
    @rpc_method()
    async def subscribe_channel(self, connection: ClientConnection, channel: str):
        """Subscribes the client to a channel (supports wildcards)."""
        connection.subscribe(channel)
        return f"Subscribed to '{channel}'"

    @rpc_method()
    async def set_team(self, connection: ClientConnection, team: str):
        """Sets the client's team for predicate filtering."""
        connection.team = team
        return f"Team set to '{team}'"

    async def publish_news(self, channel: str, message: str):
        """Publishes news to a channel."""
        self.publish(channel, {"channel": channel, "message": message})

    async def publish_team_update(self, channel: str, team: str, message: str):
        """Publishes only to clients on a specific team."""
        self.publish(
            channel,
            {"team": team, "message": message},
            predicate=webshocket.IsEqual("team", team),
        )


async def main():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=PubSubHandler)
    await server.start()

    print("[Server] Running on ws://localhost:5000")
    print("[Server] Waiting 3 seconds for clients to connect...\n")
    await asyncio.sleep(3)

    handler = server.handler

    # Publish to specific channels
    print("[Server] Publishing to 'news.tech'")
    await handler.publish_news("news.tech", "New Python release!")

    print("[Server] Publishing to 'news.sports'")
    await handler.publish_news("news.sports", "World Cup finals!")

    print("[Server] Publishing to 'news.finance.USD'")
    await handler.publish_news("news.finance.USD", "Dollar rising!")

    # Publish team-specific updates
    print("[Server] Publishing team update for 'red' team on 'game.lobby'")
    await handler.publish_team_update("game.lobby", "red", "Red team advance!")

    print("[Server] Publishing team update for 'blue' team on 'game.lobby'")
    await handler.publish_team_update("game.lobby", "blue", "Blue team scored!")

    await asyncio.sleep(1)
    await server.close()


if __name__ == "__main__":
    asyncio.run(main())
