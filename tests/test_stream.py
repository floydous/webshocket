import asyncio

import pytest
import pytest_asyncio

import webshocket
from webshocket.enum import RPCErrorCode
from webshocket.rpc import rpc_method

HOST, PORT = "127.0.0.1", 5000

class StreamRPCHandler(webshocket.WebSocketHandler):
    @rpc_method(alias_name="count_to")
    async def count_to(self, connection: webshocket.ClientConnection, target: int, delay: float = 0.05):
        """Standard generator yielding numbers."""
        for i in range(1, target + 1):
            yield i
            await asyncio.sleep(delay)

    @rpc_method(alias_name="fail_midway")
    async def fail_midway(self, connection: webshocket.ClientConnection):
        """Generator that yields twice then intentionally raises an exception."""
        yield "one"
        yield "two"
        raise ValueError("Intentional crash in async generator")

    @rpc_method(alias_name="standard_rpc")
    async def standard_rpc(self, connection: webshocket.ClientConnection):
        """A normal, non-streaming RPC."""
        return "Not a stream"


@pytest_asyncio.fixture
async def server():
    server = webshocket.WebSocketServer(HOST, PORT, clientHandler=StreamRPCHandler)
    await server.start()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_successful_stream(server):
    """Test that a stream behaves correctly and yields all components."""
    async with webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as client:
        results = []
        async for packet in client.stream_rpc("count_to", 5):
            results.append(packet.response)

        assert results == [1, 2, 3, 4, 5]


@pytest.mark.asyncio
async def test_stream_fails_midway(server):
    """Test that mid-stream server crashes are gracefully sent to client as stream ends containing errors."""
    async with webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as client:
        results = []
        error_received = None

        async for packet in client.stream_rpc("fail_midway"):
            if packet.error is not None:
                error_received = packet.error
                results.append(packet.response)
            else:
                results.append(packet.response)

        assert results[:2] == ["one", "two"]
        assert len(results) == 3
        assert "Stream aborted: Intentional crash in async generator" in results[2]
        assert error_received == RPCErrorCode.INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_concurrent_rpcs(server):
    """Verify that multiple data streams alongside standard RPC execute completely concurrently."""
    async with webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as client:

        async def fetch_stream():
            return [p.response async for p in client.stream_rpc("count_to", 3, delay=0.1)]

        async def fetch_standard():
            await asyncio.sleep(0.15) # Wait to be midway into the stream fetching
            resp = await client.send_rpc("standard_rpc")
            return resp.response

        stream_results, standard_result = await asyncio.gather(
            fetch_stream(),
            fetch_standard(),
        )

        assert stream_results == [1, 2, 3]
        assert standard_result == "Not a stream"


@pytest.mark.asyncio
async def test_client_breaks_stream(server):
    """Verify that a client looping can prematurely break out safely preserving the stream buffer."""
    async with webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as client:
        results = []
        async for packet in client.stream_rpc("count_to", 100):
            results.append(packet.response)
            if packet.response == 3:
                break

        assert results == [1, 2, 3]

        # Test connection is still completely usable
        resp = await client.send_rpc("standard_rpc")
        assert resp.response == "Not a stream"
