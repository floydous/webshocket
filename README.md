[![docs](https://readthedocs.org/projects/web-shocket/badge/?style=flat)](https://web-shocket.readthedocs.io/)
[![Build Status](https://github.com/floydous/webshocket/actions/workflows/tests.yml/badge.svg)](https://github.com/floydous/webshocket/actions/workflows/tests.yml)
[![PyPI Downloads](https://pepy.tech/badge/webshocket)](https://pepy.tech/project/webshocket)
[![PyPI version](https://img.shields.io/pypi/v/webshocket)](https://pypi.org/project/webshocket/)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://opensource.org/license/mit)
[![Code style: ruff](https://img.shields.io/badge/code_style-ruff-dafd5e)](https://github.com/astral-sh/ruff)

> [!WARNING]
> Webshocket is still unfinished and is not ready for proper-project use. It is advised to not expect any stability from this project until it reaches a stable release (>=v0.5.0)

# Webshocket

Webshocket is a Python library that handles the boilerplate of building WebSocket applications. It provides a high-level, object-oriented layer on top of the excellent websockets library, designed to let you focus on your application's features instead of its plumbing.

## Why Use Webshocket?

Building real-time applications involves more than just sending messages. You have to manage connection lifecycles, handle state for thousands of clients, and structure your code to be maintainable. Webshocket is designed to solve these problems for you.

- **A Cleaner API:** Instead of writing raw protocol handlers, you work with clean, powerful objects like WebSocketServer and ClientConnection

- **Effortless State Management:** Need to remember a user's name or authentication status? Just assign it directly: `connection.username = "alice"`. No more managing complicated external dictionaries to track client state.

- **Built-in Best Practices:** async with provides safe, automatic resource management for both servers and clients, while the handler pattern promotes a clean separation between network and application logic.

# Quick Start

Get a simple echo server running in seconds.

### 1. Server Code (`server.py`)

```python
import asyncio
import webshocket

# Define your application logic by inheriting from WebSocketHandler
class EchoHandler(webshocket.WebSocketHandler):
    async def on_connect(self, connection: webshocket.ClientConnection):
        print(f"New connection: {connection.remote_address}")
        # The smart send method automatically wraps raw strings into a Packet
        await connection.send("Welcome to the Echo Server!")

    async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
        # The server automatically parses data into a Packet object
        print(f"Received '{packet.data}' from {connection.remote_address}")
        await connection.send(f"Echo: {packet.data}")

# Start the server
async def main():
    server = webshocket.WebSocketServer("localhost", 8765, handler_class=EchoHandler)

    print("Starting server...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Client Code (client.py)

```python
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

            # Send a message and wait for the echo
            await client.send("Hello from Denpasar!")
            echo_packet = await client.recv()
            print(f"Server echoed: '{echo_packet.data}'")

    except ConnectionRefusedError:
        print("Connection failed. Is the server running?")

if __name__ == "__main__":
    asyncio.run(main())
```

# Advanced Features Made Simple

Webshocket is more than just a simple wrapper. It provides a framework for building sophisticated real-time applications.

- **Channels and Broadcasting:** Move beyond simple echo servers. The publish() and broadcast() methods provide a high-level API for building multi-user chat rooms and notification systems, handling the complexity of concurrent message delivery for you.

- **Secure and Resilient Connections:** Easily enable secure wss:// with TLS certificates. The included WebSocketClient can be configured to automatically survive network drops with a production-ready reconnection strategy.

- **Structured and Validated Data:** Enforce a strict data protocol by defining your message types with Pydantic. The library will automatically validate incoming packets, rejecting malformed or malicious data before your code ever sees it.

- **Remote Procedure Calls (RPC):** Call server-side functions directly from your client! Define methods on your `WebSocketHandler` with the `@rpc_method` decorator, and Webshocket handles the magic of remote execution, making client-server interactions feel like local function calls.

# Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request on our GitHub repository.

# License

This project is licensed under the MIT License - see the LICENSE file for details.
