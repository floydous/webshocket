import pytest

import webshocket

(HOST, PORT) = ("127.0.0.1", 5000)


@pytest.mark.asyncio
async def test_simple_server() -> None:
    async with webshocket.WebSocketServer(HOST, PORT) as server:
        assert server.state == webshocket.ServerState.SERVING

        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()
        client.send("Hello World")

        connected_client = await server.accept()
        received_packet = await connected_client.recv()

        assert received_packet.data == "Hello World"

    assert server.state == webshocket.ServerState.CLOSED


@pytest.mark.asyncio
async def test_simple_client() -> None:
    server = webshocket.WebSocketServer(
        HOST,
        PORT,
    )
    await server.start()

    async with webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as client:
        await client.connect()

        assert client.state == webshocket.ConnectionState.CONNECTED

    assert client.state == webshocket.ConnectionState.CLOSED
    await server.close()


# ---------------------------------------------------------------------------
# websocket.py edge cases — accept, serve_forever, getattr, client errors
# ---------------------------------------------------------------------------


class _DummyHandler(webshocket.WebSocketHandler):
    async def on_connect(self, connection):
        pass

    async def on_disconnect(self, connection):
        pass

    async def on_receive(self, connection, packet):
        pass


@pytest.mark.asyncio
async def test_accept_non_default_handler_raises():
    """websocket.py:391 — accept() with non-default handler raises TypeError."""
    server = webshocket.WebSocketServer(HOST, 5050, clientHandler=_DummyHandler)
    await server.start()

    try:
        with pytest.raises(TypeError, match="Cannot use manual accept"):
            await server.accept()
    finally:
        await server.close()


@pytest.mark.asyncio
async def test_accept_server_not_started_raises():
    """websocket.py:394 — accept() when server is None raises."""
    from webshocket.exceptions import WebSocketError

    server = webshocket.WebSocketServer(HOST, 5041)
    with pytest.raises(WebSocketError, match="server is not started"):
        await server.accept()


@pytest.mark.asyncio
async def test_serve_forever_starts_and_stops():
    """websocket.py:429-433 — serve_forever starts and can be cancelled."""
    import asyncio

    server = webshocket.WebSocketServer(HOST, 5042)

    async def cancel_after():
        await asyncio.sleep(0.2)
        await server.close()

    task = asyncio.create_task(server.serve_forever())
    cancel_task = asyncio.create_task(cancel_after())

    try:
        await asyncio.wait_for(task, timeout=2.0)
    except (TimeoutError, asyncio.CancelledError):
        pass

    await cancel_task


@pytest.mark.asyncio
async def test_server_getattr_fallthrough_raises():
    """websocket.py:462-463 — server __getattr__ falls through then raises."""
    server = webshocket.WebSocketServer(HOST, 5043)
    with pytest.raises(AttributeError, match="have no attribute"):
        _ = server.totally_nonexistent_attribute


@pytest.mark.asyncio
async def test_client_handler_not_connected_raises():
    """websocket.py:557 — _handler when client is None raises ConnectionClosedError."""
    from webshocket.exceptions import ConnectionClosedError

    client = webshocket.WebSocketClient("ws://localhost:9999")
    with pytest.raises(ConnectionClosedError):
        await client._handler()


@pytest.mark.asyncio
async def test_stream_rpc_not_connected_raises():
    """websocket.py:688 — stream_rpc when not connected raises WebSocketError."""
    from webshocket.exceptions import WebSocketError

    client = webshocket.WebSocketClient("ws://localhost:9999")
    with pytest.raises(WebSocketError, match="not connected"):
        async for _ in client.stream_rpc("test"):
            pass


@pytest.mark.asyncio
async def test_send_rpc_not_connected_raises():
    """websocket.py:738 — send_rpc when not connected raises WebSocketError."""
    from webshocket.exceptions import WebSocketError

    client = webshocket.WebSocketClient("ws://localhost:9999")
    with pytest.raises(WebSocketError, match="not connected"):
        await client.send_rpc("test")


@pytest.mark.asyncio
async def test_client_recv_not_connected_raises():
    """websocket.py:779 — recv when not connected raises WebSocketError."""
    from webshocket.exceptions import WebSocketError

    client = webshocket.WebSocketClient("ws://localhost:9999")
    with pytest.raises(WebSocketError, match="not connected"):
        await client.recv()


@pytest.mark.asyncio
async def test_client_send_not_connected_raises():
    """websocket.py — send when not connected raises WebSocketError."""
    from webshocket.exceptions import WebSocketError

    client = webshocket.WebSocketClient("ws://localhost:9999")
    with pytest.raises(WebSocketError, match="not connected"):
        client.send("test")
