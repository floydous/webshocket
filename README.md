[![docs](https://readthedocs.org/projects/web-shocket/badge/?style=flat)](https://web-shocket.readthedocs.io/)
[![Build Status](https://github.com/floydous/webshocket/actions/workflows/tests.yml/badge.svg)](https://github.com/floydous/webshocket/actions/workflows/tests.yml)
[![PyPI Downloads](https://pepy.tech/badge/webshocket)](https://pepy.tech/project/webshocket)
[![PyPI version](https://img.shields.io/pypi/v/webshocket)](https://pypi.org/project/webshocket/)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://opensource.org/license/mit)
[![Code style: ruff](https://img.shields.io/badge/code_style-ruff-dafd5e)](https://github.com/astral-sh/ruff)

> [!WARNING]
> Webshocket is still unfinished and is not ready for proper-project use. It is advised to not expect any stability from this project until it reaches a stable release

# Webshocket

Webshocket is a lightweight Python framework designed to handle the complexity of WebSocket-based RPC applications. It provides a high-level API for remote procedure calls, per-client session management, and efficient message broadcasting.

# Why Webshocket?

Exposing local TCP projects to the internet effectively often requires expensive paid tunnels or unstable free alternatives. Webshocket solves this by running over standard WebSockets, making it natively compatible with robust, free HTTP tunnel services like Cloudflare Argo and LocalTunnel.

It combines the simplicity of raw sockets with a rich feature set for easier development:

- **Free Tunneling:** Works out-of-the-box with any HTTP/WebSocket tunnel.
- **Developer Experience:** Includes a complete RPC system, session state management, rate limiting, and pub/sub channels—no complex middleware or global state required.

## Comparison with Other WebSocket Libraries

| Feature          | Webshocket                 | websockets      | socket.io           | FastAPI WS      |
| ---------------- | -------------------------- | --------------- | ------------------- | --------------- |
| RPC Layer        | ✅ Built-in                | ❌ Manual       | ⚠ Client-driven     | ❌ Manual       |
| Session State    | ✅ Connection attrs        | ❌ Manual       | ✅ Rooms            | ❌ Manual       |
| Predicates/Auth  | ✅ Built-in                | ❌ Manual       | ⚠ Library-dependent | ❌ Manual       |
| Pub/Sub Channels | ✅ Built-in                | ❌ Manual       | ✅ Rooms            | ❌ Manual       |
| Rate Limiting    | ✅ Decorator-based         | ❌ Manual       | ❌ Manual           | ⚠ Middleware    |
| Auto-Retry       | ✅ Built-in (exp. backoff) | ❌ Manual       | ✅ Built-in         | ❌ Manual       |
| HTTP Tunnels     | ✅ Designed for            | ✅ Compatible   | ⚠ HTTP fallback     | ✅ Compatible   |
| Cross-Language   | ✅ Binary + JSON           | ⚠ Protocol only | ✅ Client libs      | ⚠ Protocol only |
| Performance Core | picows (Cython)            | Pure Python     | JS-heavy            | ASGI stack      |

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

### 3. Decorator-Based Rate Limiting

Protect your RPC methods from abuse with a simple decorator. Supports human-readable periods and optional auto-disconnect.

```python
class MyHandler(webshocket.WebSocketHandler):
    @webshocket.rate_limit(limit=5, period="1m")  # 5 calls per minute
    @webshocket.rpc_method()
    async def expensive_operation(self, connection: webshocket.ClientConnection, query: str):
        return await run_ai_model(query)

    @webshocket.rate_limit(limit=100, period="10s", disconnect_on_limit_exceeded=True)
    @webshocket.rpc_method()
    async def chat_message(self, connection: webshocket.ClientConnection, msg: str):
        return await process_message(msg)
```

### 4. Pub/Sub Channels with Smart Filtering

Subscribe clients to channels, then publish messages with optional predicates to filter recipients.

```python
class GameHandler(webshocket.WebSocketHandler):
    @webshocket.rpc_method()
    async def join_game(self, connection: webshocket.ClientConnection, room: str):
        connection.subscribe(room)
        connection.team = "red"

    @webshocket.rpc_method()
    async def send_team_update(self, connection: webshocket.ClientConnection, room: str, data):
        # Only publish to players on the "red" team in this room
        self.publish(room, data, predicate=webshocket.IsEqual("team", "red"))

        # Or broadcast to ALL connected clients who are admins
        self.broadcast("Server announcement", predicate=webshocket.Is("is_admin"))
```

### 5. Auto-Retry with Exponential Backoff

The client handles reconnection automatically — no manual retry loops needed.

```python
async def main():
    client = webshocket.WebSocketClient("ws://your-tunnel.url")
    await client.connect(retry=True, max_retry_attempt=5, retry_interval=2)

    result = await client.send_rpc("add", 10, 20)
    print(result.data)  # 30
```

### 6. Integrated Tunnelling & Deployment

Designed to run perfectly behind free HTTP tunnels, making it the easiest way to expose a local AI or IoT project to the world.

```python
async def main():
    server = webshocket.WebSocketServer("0.0.0.0", 5000, clientHandler=MyHandler)
    async with server:
        await server.serve_forever()
```

### 7. Cross-Language Compatibility

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
