##########
Quickstart
##########

This guide walks you through building a working server and client in under 5 minutes.

Creating a Server
=================

All server logic lives in a handler class that inherits from ``WebSocketHandler``.

.. code-block:: python

   import asyncio
   import webshocket

   class MyHandler(webshocket.WebSocketHandler):
       async def on_connect(self, connection: webshocket.ClientConnection):
           await super().on_connect(connection)
           print(f"Client connected: {connection.uid}")

       @webshocket.rpc_method()
       async def greet(self, connection: webshocket.ClientConnection, name: str):
           return f"Hello, {name}!"

   async def main():
       server = webshocket.WebSocketServer("localhost", 5000, clientHandler=MyHandler)
       async with server:
           await server.serve_forever()

   asyncio.run(main())

Connecting a Client
===================

The client connects and calls server methods directly.

.. code-block:: python

   import asyncio
   import webshocket

   async def main():
       async with webshocket.WebSocketClient("ws://localhost:5000") as client:
           result = await client.send_rpc("greet", "World")
           print(result.data)  # "Hello, World!"

   asyncio.run(main())

That's it. The server exposes ``greet`` as an RPC endpoint, and the client calls it by name.

What's Next
===========

The :doc:`features` page covers everything else: streaming RPC, session state, pub/sub channels, rate limiting, access control, auto-retry, and secure connections.
