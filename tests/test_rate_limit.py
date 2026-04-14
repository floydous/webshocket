import pytest
import pytest_asyncio
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

    @rpc_method(alias_name="stream_sum")
    @rate_limit(limit=1, period="1m")
    async def stream_add_num(self, connection: webshocket.ClientConnection, data):
        yield data
        yield data

    @rpc_method()
    async def delayed_response(self, connection: webshocket.ClientConnection, delay: float):
        await asyncio.sleep(delay)
        return "Delayed response"


@pytest_asyncio.fixture
async def server():
    server = webshocket.WebSocketServer("localhost", 5003, clientHandler=_TestRpcHandler)
    await server.start()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_rate_limit(server):
    payload = b"Hello World"

    async with webshocket.WebSocketClient("ws://localhost:5003") as client:
        response_packet = await client.send_rpc("sum", payload)
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.response == payload

        with pytest.raises(RateLimitError):
            await client.send_rpc("sum", payload, raise_on_rate_limit=True)

        response_on_error = await client.send_rpc("sum", payload, raise_on_rate_limit=False)

        assert isinstance(response_on_error.rpc, RPCResponse)
        assert response_on_error.rpc.error == RPCErrorCode.RATE_LIMIT_EXCEEDED


@pytest.mark.asyncio
async def test_rpc_timeout(server):
    async with webshocket.WebSocketClient("ws://localhost:5003") as client:
        with pytest.raises(ReceiveTimeoutError):
            await client.send_rpc("delayed_response", delay=2)
            await client.recv(timeout=1)


@pytest.mark.asyncio
async def test_send_bytes_data(server):
    async with webshocket.WebSocketClient("ws://localhost:5003") as client:
        test_bytes = b"hello world bytes"
        client.send(test_bytes)
        response_packet = await client.recv()

        assert response_packet.data == test_bytes


@pytest.mark.asyncio
async def test_rate_limit_streaming(server):
    payload = b"Hello Stream"

    async with webshocket.WebSocketClient("ws://localhost:5003") as client:
        results = [packet.rpc.response async for packet in client.stream_rpc("stream_sum", payload)]
        assert results == [payload, payload]

        with pytest.raises(RateLimitError):
            async for packet in client.stream_rpc("stream_sum", payload, raise_on_rate_limit=True):
                pass


# ---------------------------------------------------------------------------
# websocket.py:274-275, 279 — rate limit period reset & disconnect on exceed
# ---------------------------------------------------------------------------


class _PeriodResetHandler(webshocket.WebSocketHandler):
    async def on_connect(self, connection):
        pass

    async def on_disconnect(self, connection):
        pass

    async def on_receive(self, connection, packet):
        pass

    @rpc_method()
    @rate_limit(limit=1, period="1s")
    async def quick_limit(self, connection, data):
        return data

    @rpc_method()
    @rate_limit(limit=1, period="1s", disconnect_on_limit_exceeded=True)
    async def disconnect_limit(self, connection, data):
        return data


@pytest.mark.asyncio
async def test_rate_limit_period_reset():
    """websocket.py:274-275 — rate limit counter resets after period elapses."""
    server = webshocket.WebSocketServer("localhost", 5004, clientHandler=_PeriodResetHandler)
    await server.start()

    try:
        async with webshocket.WebSocketClient("ws://localhost:5004") as client:
            r1 = await client.send_rpc("quick_limit", "a")
            assert r1.rpc.response == "a"

            r2 = await client.send_rpc("quick_limit", "b", raise_on_rate_limit=False)
            assert r2.rpc.error == RPCErrorCode.RATE_LIMIT_EXCEEDED

            await asyncio.sleep(1.2)

            r3 = await client.send_rpc("quick_limit", "c")
            assert r3.rpc.response == "c"
    finally:
        await server.close()


@pytest.mark.asyncio
async def test_rate_limit_disconnect_on_exceed():
    """websocket.py:279 — disconnect_on_limit_exceeded closes the connection."""
    from webshocket.exceptions import RPCTimeoutError

    server = webshocket.WebSocketServer("localhost", 5005, clientHandler=_PeriodResetHandler)
    await server.start()

    try:
        client = webshocket.WebSocketClient("ws://localhost:5005")
        await client.connect()

        await client.send_rpc("disconnect_limit", "first")

        # Server disconnects the client after sending the rate-limit response,
        # so the second RPC either gets the error packet or times out.
        try:
            r2 = await asyncio.wait_for(
                client.send_rpc("disconnect_limit", "second", raise_on_rate_limit=False),
                timeout=2.0,
            )
            assert r2.rpc.error == RPCErrorCode.RATE_LIMIT_EXCEEDED
        except (RPCTimeoutError, asyncio.TimeoutError):
            pass  # Connection was killed — expected behavior

        await client.close()
    finally:
        await server.close()
