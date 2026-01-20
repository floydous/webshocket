[![docs](https://readthedocs.org/projects/web-shocket/badge/?style=flat)](https://web-shocket.readthedocs.io/)
[![Build Status](https://github.com/floydous/webshocket/actions/workflows/tests.yml/badge.svg)](https://github.com/floydous/webshocket/actions/workflows/tests.yml)
[![PyPI Downloads](https://pepy.tech/badge/webshocket)](https://pepy.tech/project/webshocket)
[![PyPI version](https://img.shields.io/pypi/v/webshocket)](https://pypi.org/project/webshocket/)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://opensource.org/license/mit)
[![Code style: ruff](https://img.shields.io/badge/code_style-ruff-dafd5e)](https://github.com/astral-sh/ruff)

> [!WARNING]
> Webshocket is still unfinished and is not ready for proper-project use. It is advised to not expect any stability from this project until it reaches a stable release (>=v0.5.0)

# Webshocket

Webshocket is a lightweight Python framework for building WebSocket RPC applications with per-client state and channel routing, built on the [WebSocket](https://github.com/python-websockets/websockets) library.

# Usage

### Calling RPC Methods
```python
class Handler(webshocket.WebSocketHandler):
    @webshocket.rpc_method(alias_name="add")
    async def add(self, _: webshocket.ClientConnection, a: int, b: int):
        return a + b


async def main():
    server = webshocket.WebSocketServer("127.0.0.1", 5000, clientHandler=Handler)
    await server.start()

    async with webshocket.WebSocketClient("ws://127.0.0.1:5000") as client:
        response_packet = await client.send_rpc("add", 1, 2)
```
```python
        print(response_packet.data)  # 3
```
```python
    await server.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Managing Client State
```python
class Handler(webshocket.WebSocketHandler):
    @webshocket.rpc_method()
    async def register(self, connection: webshocket.ClientConnection, favorite_color: str) -> None:
        connection.favorite_color = favorite_color

    @webshocket.rpc_method(alias_name="my-favorite-color")
    async def tell(self, connection: webshocket.ClientConnection) -> str:
        return connection.session_state["favorite_color"]


async def main():
    server = webshocket.WebSocketServer("127.0.0.1", 5000, clientHandler=Handler)
    await server.start()

    async with webshocket.WebSocketClient("ws://127.0.0.1:5000") as client:
        await client.send_rpc("register", "blue")

        response = await client.send_rpc("my-favorite-color")
```
```python
        print(response.data)  # blue
```
```python
    await server.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Working With Channels
```python
class Handler(webshocket.WebSocketHandler):
    @webshocket.rpc_method()  # Alias name automatically set to the method name if `alias_name` is not provided
    async def subscribe_to(self, connection: webshocket.ClientConnection, channel: str):
        connection.subscribe(channel)


async def main():
    server = webshocket.WebSocketServer("127.0.0.1", 5000, clientHandler=Handler)
    await server.start()

    SportsSubscriber = await webshocket.WebSocketClient("ws://127.0.0.1:5000").connect()
    NewsSubscriber = await webshocket.WebSocketClient("ws://127.0.0.1:5000").connect()

    try:
        await SportsSubscriber.send_rpc("subscribe_to", "sports")
        await NewsSubscriber.send_rpc("subscribe_to", "news")
        await asyncio.sleep(1)

        await server.publish("sports", "Sports News!")
        await server.publish("news", "News update!")
        await asyncio.sleep(1)

```
```python
        print((await SportsSubscriber.recv()).data)  # Sports News!
        print((await NewsSubscriber.recv()).data)  # News update!
```
```python
    finally:
        await SportsSubscriber.close()
        await NewsSubscriber.close()

    await server.close()


if __name__ == "__main__":
    asyncio.run(main())
```

# Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request on our GitHub repository.

# License

This project is licensed under the MIT License - see the LICENSE file for details.
