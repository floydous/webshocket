import pytest
import asyncio

import webshocket
from webshocket.rpc import rpc_method, rate_limit
from webshocket.enum import PacketSource
from webshocket.packets import RPCResponse


class _TestRpcHandler(webshocket.WebSocketHandler):
    async def on_connect(self, connection: webshocket.ClientConnection):
        pass

    async def on_disconnect(self, connection: webshocket.ClientConnection):
        pass

    async def on_receive(
        self, connection: webshocket.ClientConnection, packet: webshocket.Packet
    ):
        if packet.source != PacketSource.RPC and packet.data is not None:
            await connection.send(packet.data)
        else:
            pass

    @rpc_method(alias_name="sum")
    @rate_limit(limit=1, unit=webshocket.TimeUnit.MINUTES)
    async def add_num(self, connection: webshocket.ClientConnection, data):
        return data

    @rpc_method()
    async def delayed_response(
        self, connection: webshocket.ClientConnection, delay: float
    ):
        await asyncio.sleep(delay)
        return "Delayed response"


@pytest.mark.asyncio
async def test_rate_limit():
    server = webshocket.WebSocketServer(
        "localhost", 5000, clientHandler=_TestRpcHandler
    )
    await server.start()

    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send_rpc("sum", a := b"babt")
        response_packet = await client.recv()
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.result == a
        assert response_packet.rpc.content_type == webshocket.enum.DataType.BINARY

    await server.close()


@pytest.mark.asyncio
async def test_rpc_timeout():
    server = webshocket.WebSocketServer(
        "localhost", 5000, clientHandler=_TestRpcHandler
    )
    await server.start()

    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        with pytest.raises(asyncio.TimeoutError):
            await client.send_rpc("delayed_response", delay=2)
            await client.recv(timeout=1)

    await server.close()


@pytest.mark.asyncio
async def test_send_bytes_data():
    server = webshocket.WebSocketServer(
        "localhost", 5000, clientHandler=_TestRpcHandler
    )
    await server.start()

    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        test_bytes = b"hello world bytes"
        await client.send(test_bytes)
        response_packet = await client.recv()

        assert response_packet.data == test_bytes
        assert response_packet.content_type == webshocket.enum.DataType.BINARY

    await server.close()
