[![docs](https://readthedocs.org/projects/web-shocket/badge/?style=flat)](https://web-shocket.readthedocs.io/)
[![Build Status](https://github.com/floydous/webshocket/actions/workflows/tests.yml/badge.svg)](https://github.com/floydous/webshocket/actions/workflows/tests.yml)
[![PyPI Downloads](https://pepy.tech/badge/webshocket)](https://pepy.tech/project/webshocket)
[![PyPI version](https://img.shields.io/pypi/v/webshocket)](https://pypi.org/project/webshocket/)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://opensource.org/license/mit)
[![Code style: ruff](https://img.shields.io/badge/code_style-ruff-dafd5e)](https://github.com/astral-sh/ruff)

> [!WARNING]
> Webshocket is still unfinished and is not ready for proper-project use. It is advised to not expect any stability from this project until it reaches a stable release (>=v0.5.0)

# Webshocket

Webshocket is a lightweight Python framework designed to handle the complexity of WebSocket-based RPC applications. It provides a high-level API for remote procedure calls, per-client session management, and efficient message broadcasting.

# Why Webshocket?

- **Built for Tunnels**: Since Webshocket runs over WebSockets (HTTP), it works perfectly with free tunnel services like Cloudflare Tunnels (Argo) or Localtunnel. Avoid expensive TCP-only tunnels like ngrok.
- **Focus on Your Logic**: Perfect for AI and IoT projects. Just handle the packets and session state while we handle the network heartbeats and protocol validation.
- **Good Performance**: Handles **17,000+ RPC calls/sec** on a single connection with **50MB/s+** throughput.
- **Elegant State Management**: No more global dicts. Assign data directly to the `connection` object and it persists for the session.

# Unique Features at a Glance

Webshocket simplifies complex networking logic into simple, object-oriented patterns.

### 1. Powerful RPC with Access Control

Define server methods effortlessly and protect them with custom rules (predicates).

```python
class MyHandler(webshocket.WebSocketHandler):
    @webshocket.rpc_method(alias_name="add")
    async def add(self, _: webshocket.ClientConnection, a: int, b: int):
        return a + b

    # Unique: Use built-in predicates for clean access control
    @webshocket.rpc_method(requires=webshocket.Is("is_admin"))
    async def secret_function(self, conn: webshocket.ClientConnection):
        return "Sensitive Data"
```

### 2. Effortless Session State

No more look-up tables. Assign data directly to the client connection; Webshocket handles the persistence for you.

```python
    @webshocket.rpc_method()
    async def login(self, connection: webshocket.ClientConnection, user_id: str):
        # Direct attribute assignment persists for the session
        connection.user_id = user_id
        connection.is_admin = True

        # Subscribe to updates immediately
        connection.subscribe("broadcast-channel")
```

### 3. Integrated Tunnelling & Deployment

Designed to run perfectly behind free HTTP tunnels, making it the easiest way to expose a local AI or IoT project to the world.

```python
async def main():
    server = webshocket.WebSocketServer("0.0.0.0", 5000, clientHandler=MyHandler)
    async with server:
        await server.serve_forever()
```

### 4. Cross-Language Compatibility

Webshocket is designed to be language-agnostic. While the Python client is optimized with MessagePack, the server natively understands **standard JSON packets**. This means you can build a client in **JavaScript**, Java, or C# using nothing but the standard library.

```javascript
// Example: Standard Browser JavaScript Client
const socket = new WebSocket("ws://your-tunnel.url");

socket.onopen = () => {
	const rpcRequest = {
		rpc: {
			type: "request",
			method: "add",
			args: [10, 20],
			kwargs: {},
		},
		source: 5,
	};

	socket.send(JSON.stringify(rpcRequest));
};

socket.onmessage = async (event) => {
	const packet = JSON.parse(await event.data.text());
	console.log("Result:", packet.rpc.response); // 30
};
```

# Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request on our GitHub repository.

# License

This project is licensed under the MIT License - see the LICENSE file for details.
