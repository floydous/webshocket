import pytest
import asyncio

import webshocket
from webshocket.rpc import rpc_method, rate_limit
from webshocket.enum import PacketSource, RPCErrorCode
from webshocket.packets import RPCResponse
from webshocket.exceptions import ReceiveTimeoutError, RateLimitError


class _TestRpcHandler(webshocket.WebSocketHandler):
    async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
        if packet.source != PacketSource.RPC and packet.data is not None:
            connection.send(packet.data)
        else:
            pass

    @rpc_method(alias_name="sum")
    @rate_limit(limit=1, period="1m")  # 1 minute
    async def add_num(self, connection: webshocket.ClientConnection, data):
        return data

    @rpc_method()
    async def delayed_response(self, connection: webshocket.ClientConnection, delay: float):
        await asyncio.sleep(delay)
        return "Delayed response"


@pytest.mark.asyncio
async def test_rate_limit():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=_TestRpcHandler)
    await server.start()

    payload = b"Hello World"

    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        response_packet = await client.send_rpc("sum", payload)
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.response == payload

        with pytest.raises(RateLimitError):
            await client.send_rpc("sum", payload, raise_on_rate_limit=True)

        response_on_error = await client.send_rpc("sum", payload, raise_on_rate_limit=False)

        assert isinstance(response_on_error.rpc, RPCResponse)
        assert response_on_error.rpc.error == RPCErrorCode.RATE_LIMIT_EXCEEDED

    await server.close()


@pytest.mark.asyncio
async def test_rpc_timeout():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=_TestRpcHandler)
    await server.start()

    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        with pytest.raises(ReceiveTimeoutError):
            await client.send_rpc("delayed_response", delay=2)
            await client.recv(timeout=1)

    await server.close()


@pytest.mark.asyncio
async def test_send_bytes_data():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=_TestRpcHandler)
    await server.start()

    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        test_bytes = b"hello world bytes"
        client.send(test_bytes)
        response_packet = await client.recv()

        assert response_packet.data == test_bytes

    await server.close()
