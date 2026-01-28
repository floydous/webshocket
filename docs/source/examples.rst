########
Examples
########

===============================================
Creating Your First WebSocket Server & Client
===============================================

The core of the library is the object-oriented ``server`` and ``client`` classes, which use ``asyncio`` and ``async with`` for robust, modern network programming.

A minimal application involves two parts: a server that runs continuously, and a client that connects to it.

1. A Simple Echo Server (`echo_server.py`)
-------------------------------------------------

All server-side logic is defined in a class that inherits from ``webshocket.WebSocketHandler``. The server automatically handles creating ``ClientConnection`` objects and passing them to your handler's methods.

.. code-block:: python
   :linenos:

   import asyncio
   import webshocket

   class EchoHandler(webshocket.WebSocketHandler):
       """A simple handler that echoes back any message it receives."""
       async def on_connect(self, connection: webshocket.ClientConnection):
           # The base on_connect method handles adding the client to state.
           await super().on_connect(connection)
           print(f"New client connected: {connection.remote_address}")
           await connection.send("Welcome to the echo server!")

       async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
           response_data = f"Echo: {packet.data}"
           print(f"Received '{packet.data}', sending '{response_data}'")
           await connection.send(response_data)

   async def main():
       # Initialize the server with a host, port, and your handler class.
       server = webshocket.WebSocketServer(
           "localhost", 8765,
           clientHandler=EchoHandler,
           # Enable automatic heartbeat to detect dead connections
           ping_interval=20.0
       )

       print("Starting echo server on ws://localhost:8765")
       # `async with` ensures the server is started and cleanly shut down.
       async with server:
           await server.serve_forever()

   if __name__ == "__main__":
       asyncio.run(main())


2. A Simple Client (`echo_client.py`)
-------------------------------------------

The client also uses ``async with`` for safe, automatic connection management.

.. code-block:: python
   :linenos:

   import asyncio
   import webshocket

   async def main():
       uri = "ws://localhost:8765"

       try:
           async with webshocket.WebSocketClient(uri) as client:
               print("Connected to server.")

               # The recv() method automatically parses incoming messages into Packets
               welcome_packet = await client.recv()
               print(f"Server says: '{welcome_packet.data}'")

               # The smart send() method automatically wraps raw strings
               await client.send("Hello from Denpasar!")
               echo_packet = await client.recv()
               print(f"Server echoed: '{echo_packet.data}'")

       except ConnectionRefusedError:
           print("Connection failed. Is the server running?")

   if __name__ == "__main__":
       asyncio.run(main())


=================
Advanced Features
=================

Beyond basic connections, **webshocket** provides a framework for building sophisticated real-time applications.


Secure Connections (WSS/TLS)
------------------------------

Enabling encryption is simple. Create a standard Python ``ssl.SSLContext`` and pass it to the server or client.

1. Generate a Test Certificate

.. code-block:: bash

   openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 36500 -subj "/CN=localhost"

**2. Start a Secure Server**

.. code-block:: python
   :emphasize-lines: 9-13

   # ... imports ...
   import ssl

   # Create a standard SSL Context
   ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
   ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

   # Pass the context during server initialization
   server = webshocket.WebSocketServer(
       "localhost", 8765,
       clientHandler=EchoHandler,
       ssl_context=ssl_context
   )

   # Server will now be running on wss://localhost:8765

3. Connect a Secure Client

.. code-block:: python
   :emphasize-lines: 6,9-11

   # ... imports ...
   import ssl

   # Trust the self-signed certificate
   client_ssl = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
   client_ssl.load_verify_locations("cert.pem")

   client = webshocket.WebSocketClient(
       "wss://localhost:8765",
       ssl_context=client_ssl
   )

   # The rest of the client code is the same!

Broadcasting and Channels (Pub/Sub)
-------------------------------------

The ``WebSocketHandler`` provides built-in methods for multi-user communication. The ``broadcast()`` method sends a message to every connected client, while ``publish()`` sends only to clients subscribed to a specific channel.

.. code-block:: python

   class ChatHandler(webshocket.WebSocketHandler):
       async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
           # A client sends a command to join a room
           if packet.data.startswith("join"):
               room_name = packet.data.split(" ")[1]
               connection.subscribe(room_name)
               await connection.send(f"You joined room '{room_name}'")
               # Use the built-in publish method to notify the room
               await self.publish(room_name, f"A new user joined.", exclude=(connection,))

           # A client sends a normal message
           else:
               # Send the message only to channels the client is in
               for room in connection.subscribed_channel:
                   await self.publish(room, packet.data, exclude=(connection,))

Per-Connection State Management
---------------------------------

The ``ClientConnection`` object acts as a dynamic "state bag," allowing you to attach any information to a connection for its entire lifecycle. This is perfect for managing user authentication and other session data directly on the socket object.

.. code-block:: python
   :emphasize-lines: 6,10

   class AuthHandler(webshocket.WebSocketHandler):
       async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
           # Pretend the user is sending a login command
           if packet.data.startswith("login"):
               # Set state directly on the connection object like a dictionary or attribute
               connection.username = packet.data.split(" ")[1]
               connection.is_authenticated = True
               await connection.send("Login successful!")

           elif packet.data == "whoami":
               # Read the state back later
               if getattr(connection, 'is_authenticated', False):
                   await connection.send(f"You are logged in as {connection.username}")
               else:
                   await connection.send("You are not logged in.")

Remote Procedure Call (RPC)
----------------------------

RPC enables a client to call a function or method on a server as if that function were part of the client's own code. The client doesn't need to know the network details (like IP addresses, ports, or how data is serialized) to make the call. The RPC mechanism handles all the "plumbing" behind the scenes.

To expose a method on your `WebSocketHandler` as an RPC endpoint, use the `@rpc_method` decorator. The first argument of your RPC method must always be the `ClientConnection` object.

.. code-block:: python
   :linenos:

   import asyncio
   import webshocket
   from webshocket.rpc import rpc_method

   class RpcHandler(webshocket.WebSocketHandler):
       @rpc_method()
       async def echo(self, connection: webshocket.ClientConnection, message: str):
           return f"RPC Echo: {message}"

       @rpc_method(alias_name="sum_numbers")
       async def add(self, connection: webshocket.ClientConnection, a: int, b: int):
           return a + b

   async def main():
       server = webshocket.WebSocketServer("localhost", 5000, clientHandler=RpcHandler)
       await server.start()

       async with webshocket.WebSocketClient("ws://localhost:5000") as client:
           # Call 'echo' RPC method
           response = await client.send_rpc("echo", "Hello RPC!")
           print(f"Echo response: {response.data}")

           # Call 'add' RPC method using its alias 'sum_numbers'
           response = await client.send_rpc("sum_numbers", 10, 20)
           print(f"Sum response: {response.data}")

       await server.close()

   if __name__ == "__main__":
       asyncio.run(main())

This is the output of the code above:

.. code-block:: text
    :linenos:

    Client connected
    Echo response: RPC Echo: Hello RPC!
    Sum response: 30
    Client disconnected
