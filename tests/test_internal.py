"""Tests for webshocket._internal — picows_server and picows_client edge cases."""

import pytest
import asyncio

import webshocket
from webshocket.enum import ClientType
from webshocket.exceptions import ConnectionFailedError
from picows import WSMsgType


# ---------------------------------------------------------------------------
# picows_server.py — lines 50-56, 78-79, 91-92
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_listener_pending_payload_and_ready():
    """ServerClientListener queues payloads before _connection is set, then flushes on _on_ready."""
    from webshocket._internal.picows_server import ServerClientListener

    async def noop_handler(t, l):
        pass

    listener = ServerClientListener(noop_handler, ClientType.FRAMEWORK)

    # Single-frame payload when _connection is None (lines 78-79)
    class SingleFrame:
        msg_type = WSMsgType.BINARY
        fin = 1

        def get_payload_as_bytes(self):
            return b"single"

    listener.on_ws_frame(None, SingleFrame())

    # Fragmented payload when _connection is None (lines 91-92)
    class FragStart:
        msg_type = WSMsgType.BINARY
        fin = 0

        def get_payload_as_bytes(self):
            return b"part1"

    class FragEnd:
        msg_type = WSMsgType.CONTINUATION
        fin = 1

        def get_payload_as_bytes(self):
            return b"part2"

    listener.on_ws_frame(None, FragStart())
    listener.on_ws_frame(None, FragEnd())

    assert listener._pending_payload.qsize() == 2

    # Simulate _on_ready flushing pending payloads (lines 50-56)
    flush_queue = asyncio.Queue()

    class FakeConnection:
        _payload_queue = flush_queue

    listener._connection = FakeConnection()
    listener._ready.set()
    await listener._on_ready()

    items = []
    while not flush_queue.empty():
        items.append(await flush_queue.get())

    assert items == [b"single", b"part1part2"]


# ---------------------------------------------------------------------------
# picows_server.py — line 141
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_picows_server_double_serve_raises():
    """PicowsServer.serve() raises RuntimeError when already running."""
    server = webshocket.WebSocketServer("localhost", 5030)
    await server.start()

    try:
        with pytest.raises(RuntimeError, match="already running"):
            await server._server.serve()
    finally:
        await server.close()


# ---------------------------------------------------------------------------
# picows_client.py — line 99
# ---------------------------------------------------------------------------


def test_client_send_before_connect_raises():
    """picows_client.client.send() before connect raises ConnectionFailedError."""
    from webshocket._internal.picows_client import client as PicowsClient

    c = PicowsClient("ws://localhost:9999")
    with pytest.raises(ConnectionFailedError, match="not connected"):
        c.send(b"hello")


# ---------------------------------------------------------------------------
# picows_client.py — lines 79-80
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_extra_headers():
    """picows_client.client.connect() merges extra_headers kwarg."""
    server = webshocket.WebSocketServer("localhost", 5031)
    await server.start()

    try:
        client = webshocket.WebSocketClient("ws://localhost:5031")
        await client.connect(extra_headers={"X-Custom": "test123"})
        await client.close()
    finally:
        await server.close()
