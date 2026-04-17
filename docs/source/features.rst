########
Features
########

This page covers every feature in Webshocket with short, working examples.

============================
Remote Procedure Call (RPC)
============================

Expose server methods to clients using the ``@rpc_method`` decorator. The client calls them by name with ``send_rpc()``.

Defining RPC Methods
--------------------

.. code-block:: python

   class MathHandler(webshocket.WebSocketHandler):
       @webshocket.rpc_method()
       async def add(self, connection: webshocket.ClientConnection, a: int, b: int):
           return a + b

       @webshocket.rpc_method(alias_name="multiply")
       async def mul(self, connection: webshocket.ClientConnection, a: int, b: int):
           return a * b

The ``alias_name`` parameter lets you expose a method under a different name. The client calls ``"multiply"`` but the server runs ``mul()``.

Calling RPC from the Client
----------------------------

.. code-block:: python

   async with webshocket.WebSocketClient("ws://localhost:5000") as client:
       result = await client.send_rpc("add", 10, 20)
       print(result.data)  # 30

       result = await client.send_rpc("multiply", 3, 7)
       print(result.data)  # 21

=============
Streaming RPC
=============

Server methods that ``yield`` values become streaming endpoints. The client iterates over chunks as they arrive — perfect for AI token streaming, live feeds, or progressive results.

Server Side
-----------

Use a regular ``yield`` inside an ``@rpc_method``. Webshocket detects the async generator automatically.

.. code-block:: python

   class StreamHandler(webshocket.WebSocketHandler):
       @webshocket.rpc_method()
       async def count_to(self, connection: webshocket.ClientConnection, n: int):
           for i in range(1, n + 1):
               yield i
               await asyncio.sleep(0.1)

Client Side
-----------

Use ``stream_rpc()`` instead of ``send_rpc()``. It returns an async iterator.

.. code-block:: python

   async with webshocket.WebSocketClient("ws://localhost:5000") as client:
       async for packet in client.stream_rpc("count_to", 5):
           print(packet.data)  # 1, 2, 3, 4, 5

=============
Session State
=============

Every ``ClientConnection`` is a stateful object. You can assign and read attributes directly — no external store needed.

.. code-block:: python

   class AuthHandler(webshocket.WebSocketHandler):
       @webshocket.rpc_method()
       async def login(self, connection: webshocket.ClientConnection, username: str):
           connection.username = username
           connection.is_admin = False
           return f"Logged in as {username}"

       @webshocket.rpc_method()
       async def whoami(self, connection: webshocket.ClientConnection):
           return connection.username  # Persists for the session lifetime

State is automatically cleaned up when the client disconnects. You can also use dict-style access:

.. code-block:: python

   connection["username"] = "alice"
   print(connection["username"])  # "alice"

==========================
Pub/Sub Channels
==========================

Webshocket has built-in channels for one-to-many messaging.

Subscribing and Publishing
--------------------------

.. code-block:: python

   class ChatHandler(webshocket.WebSocketHandler):
       @webshocket.rpc_method()
       async def join(self, connection: webshocket.ClientConnection, room: str):
           connection.subscribe(room)
           return f"Joined {room}"

       @webshocket.rpc_method()
       async def send_message(self, connection: webshocket.ClientConnection, room: str, msg: str):
           self.publish(room, {"user": connection.username, "msg": msg}, exclude=(connection,))

The ``exclude`` parameter prevents the sender from receiving their own message.

Wildcard Subscriptions
----------------------

Channels support glob patterns (``*``, ``?``, ``[]``). Subscribe to a pattern, and you'll receive messages published to any matching channel.

.. code-block:: python

   # Client subscribes to a pattern
   connection.subscribe("news.*")

   # Later, publishing to "news.tech" or "news.sports" will reach this client
   self.publish("news.tech", {"headline": "New CPU released"})
   self.publish("news.sports", {"headline": "Team wins championship"})

Broadcasting
------------

``broadcast()`` sends a message to **all** connected clients, regardless of channel subscriptions.

.. code-block:: python

   self.broadcast("Server is shutting down in 5 minutes")

You can filter recipients with ``exclude`` and ``predicate``:

.. code-block:: python

   # Only send to admins
   self.broadcast("Admin notice", predicate=webshocket.Is("is_admin"))

=============
Rate Limiting
=============

Protect RPC methods from abuse with the ``@rate_limit`` decorator. It supports human-readable time periods.

.. code-block:: python

   class ApiHandler(webshocket.WebSocketHandler):
       @webshocket.rate_limit(limit=5, period="1m")  # 5 calls per minute
       @webshocket.rpc_method()
       async def expensive_query(self, connection: webshocket.ClientConnection, q: str):
           return await run_query(q)

       @webshocket.rate_limit(limit=100, period="10s", disconnect_on_limit_exceeded=True)
       @webshocket.rpc_method()
       async def chat(self, connection: webshocket.ClientConnection, msg: str):
           return await process(msg)

Supported period formats: ``"30s"`` (seconds), ``"5m"`` (minutes), ``"1h"`` (hours).

When a client exceeds the limit, they receive an ``RPC_RATE_LIMITED`` error. If ``disconnect_on_limit_exceeded=True``, the connection is closed immediately.

==============
Access Control
==============

Use predicates to restrict who can call an RPC method. Predicates check attributes on the ``ClientConnection`` object.

Built-in Predicates
-------------------

.. list-table::
   :header-rows: 1

   * - Predicate
     - Meaning
   * - ``Is("attr")``
     - ``connection.attr`` is truthy
   * - ``Has("attr")``
     - ``connection`` has the attribute
   * - ``IsEqual("attr", value)``
     - ``connection.attr == value``
   * - ``Any(p1, p2)``
     - At least one predicate passes
   * - ``All(p1, p2)``
     - All predicates pass

Example
-------

.. code-block:: python

   class SecureHandler(webshocket.WebSocketHandler):
       @webshocket.rpc_method(requires=webshocket.Is("is_admin"))
       async def admin_action(self, connection: webshocket.ClientConnection):
           return "Secret data"

       @webshocket.rpc_method(requires=webshocket.All(
           webshocket.Has("username"),
           webshocket.IsEqual("role", "editor"),
       ))
       async def edit(self, connection: webshocket.ClientConnection, doc_id: str):
           return f"Editing {doc_id}"

If the predicate fails, the client receives an ``RPC_ACCESS_DENIED`` error.

You can also use predicates with ``broadcast()`` and ``publish()`` to filter recipients:

.. code-block:: python

   self.publish("alerts", data, predicate=webshocket.IsEqual("region", "us-east"))

==========
Auto-Retry
==========

The client can automatically reconnect on disconnection with exponential backoff.

.. code-block:: python

   client = webshocket.WebSocketClient("ws://your-server.com")
   await client.connect(
       retry=True,
       max_retry_attempt=5,
       retry_interval=2,  # seconds between retries
   )

The client will attempt to reconnect up to 5 times, with increasing delays between attempts. Once reconnected, you can continue calling ``send_rpc()`` as normal.

=====================
Secure Connections
=====================

Enable SSL/TLS with a standard Python ``SSLContext``.

Server
------

.. code-block:: python

   import ssl

   ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
   ssl_ctx.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

   server = webshocket.WebSocketServer(
       "0.0.0.0", 5000,
       clientHandler=MyHandler,
       ssl_context=ssl_ctx,
   )

Client
------

.. code-block:: python

   import ssl

   ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
   ssl_ctx.load_verify_locations("cert.pem")

   async with webshocket.WebSocketClient("wss://localhost:5000", ssl_context=ssl_ctx) as client:
       result = await client.send_rpc("greet", "Secure World")

===========================
Cross-Language Clients
===========================

Framework clients (Python) use fast binary msgpack. But the server also accepts plain JSON from any WebSocket client — JavaScript, Java, C#, etc.

JavaScript Example
-------------------

.. code-block:: javascript

   const socket = new WebSocket("ws://your-server.com");

   socket.onopen = () => {
       socket.send(JSON.stringify({
           rpc: {
               type: "request",
               method: "add",
               args: [10, 20],
               kwargs: {},
           },
           source: 5,
       }));
   };

   socket.onmessage = async (event) => {
       const packet = JSON.parse(await event.data.text());
       console.log("Result:", packet.rpc.response);  // 30
   };

No special client library needed. Any language that can open a WebSocket and send JSON can talk to your server.
