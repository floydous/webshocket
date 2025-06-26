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
       server = webshocket.server("localhost", 8765, handler_class=EchoHandler)

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
           async with webshocket.client(uri) as client:
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

Enabling encryption is a first-class feature. Simply generate a self-signed certificate and provide the paths when creating your server. The client can then be configured to trust it for local testing.

1. Generate a Test Certificate

.. code-block:: bash

   openssl req -x509 -newkey rsa:4096 -nodes -keyout key.pem -out cert.pem -days 36500 -subj "/CN=localhost"

**2. Start a Secure Server**

.. code-block:: python
   :emphasize-lines: 9,10

   # ... imports ...

   # Define the paths to your certificate files
   cert_info = {"cert": "cert.pem", "key": "key.pem"}

   # Pass the certificate info during server initialization
   server = webshocket.server(
       "localhost", 8765, EchoHandler,
       certificate=cert_info
   )

   # Server will now be running on wss://localhost:8765

3. Connect a Secure Client

.. code-block:: python
   :emphasize-lines: 6

   # ... imports ...

   # Tell the client to trust your self-signed certificate
   client = webshocket.client(
       "wss://localhost:8765",
       ca_cert_path="cert.pem"
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
               await self.publish(room_name, f"A new user joined.", exclude=connection)

           # A client sends a normal message
           else:
               # Send the message only to channels the client is in
               for room in connection.subscribed_channels:
                   await self.publish(room, packet.data, exclude=connection)

Per-Connection State Management
---------------------------------

The ``ClientConnection`` object acts as a dynamic "state bag," allowing you to attach any information to a connection for its entire lifecycle. This is perfect for managing user authentication and other session data.

.. code-block:: python
   :emphasize-lines: 6,10

   class AuthHandler(webshocket.WebSocketHandler):
       async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
           # Pretend the user is sending a login command
           if packet.data.startswith("login"):
               # Set state directly on the connection object
               connection.username = packet.data.split(" ")[1]
               connection.is_authenticated = True
               await connection.send("Login successful!")

           elif packet.data == "whoami":
               # Read the state back later
               if getattr(connection, 'is_authenticated', False):
                   await connection.send(f"You are logged in as {connection.username}")
               else:
                   await connection.send("You are not logged in.")
