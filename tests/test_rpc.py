import pytest_asyncio
import pytest

import webshocket
from webshocket.rpc import rpc_method
from webshocket.exceptions import RPCError
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
        if packet.source != PacketSource.RPC:
            await connection.send(f"Non-RPC Echo: {packet.data}")
        else:
            pass

    @rpc_method()
    async def echo(self, connection: webshocket.ClientConnection, data: str):
        return data

    @rpc_method(alias_name="add")
    async def add_numbers(
        self, connection: webshocket.ClientConnection, a: int, b: int
    ):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise RPCError("Inputs must be numbers.")
        return a + b

    @rpc_method()
    async def raise_rpc_error(
        self, connection: webshocket.ClientConnection, message: str
    ):
        raise RPCError(message)

    @rpc_method()
    async def raise_generic_error(self, connection: webshocket.ClientConnection):
        raise ValueError("This is a generic value error.")

    async def non_rpc_method(self, connection: webshocket.ClientConnection):
        return "This should not be called via RPC"


@pytest_asyncio.fixture
async def rpc_server():
    server = webshocket.WebSocketServer(
        "localhost", 5000, clientHandler=_TestRpcHandler
    )
    await server.start()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_rpc_echo_method(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send_rpc("echo", "Hello RPC World")
        response_packet = await client.recv()

        assert response_packet.source == PacketSource.RPC
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.result == "Hello RPC World"
        assert response_packet.data == "Hello RPC World"
        assert response_packet.rpc.error is None


@pytest.mark.asyncio
async def test_rpc_add_numbers(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send_rpc("add_numbers", 10, 20)
        response_packet = await client.recv()

        assert response_packet.source == PacketSource.RPC
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.result is None
        assert "not found" in response_packet.rpc.error
        assert "not found" in response_packet.data


@pytest.mark.asyncio
async def test_rpc_method_alias(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send_rpc("add", 5, 7)  # Using the alias
        response_packet = await client.recv()

        assert response_packet.source == PacketSource.RPC
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.error is None
        assert response_packet.rpc.result == 12
        assert response_packet.data == 12


@pytest.mark.asyncio
async def test_rpc_method_not_found(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send_rpc("non_existent_method", "test")
        response_packet = await client.recv()

        assert response_packet.source == PacketSource.RPC
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.result is None
        assert "not found" in response_packet.rpc.error
        assert "not found" in response_packet.data


@pytest.mark.asyncio
async def test_rpc_method_not_exposed(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        # Attempt to call a method that exists but is not decorated with @rpc_method
        await client.send_rpc("non_rpc_method", "test")
        response_packet = await client.recv()

        assert response_packet.source == PacketSource.RPC
        assert response_packet.rpc.result is None
        assert "not found" in response_packet.rpc.error
        assert "not found" in response_packet.data


@pytest.mark.asyncio
async def test_rpc_method_raises_rpc_error(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        error_msg = "This is a custom RPC error."
        await client.send_rpc("raise_rpc_error", error_msg)
        response_packet = await client.recv()

        assert response_packet.source == PacketSource.RPC
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.result is None
        assert response_packet.rpc.error == error_msg
        assert response_packet.data == error_msg


@pytest.mark.asyncio
async def test_rpc_method_raises_generic_exception(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send_rpc("raise_generic_error")
        response_packet = await client.recv()

        assert response_packet.source == PacketSource.RPC
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.result is None
        assert (
            "Server error (ValueError): This is a generic value error."
            in response_packet.rpc.error
        )
        assert (
            "Server error (ValueError): This is a generic value error."
            in response_packet.data
        )


@pytest.mark.asyncio
async def test_on_receive_handles_non_rpc_packet(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        test_message = "Hello, non-RPC world!"
        await client.send(test_message)
        response_packet = await client.recv()

        assert (
            response_packet.source == PacketSource.CUSTOM
        )  # Or UNKNOWN, depending on client.send behavior
        assert response_packet.rpc is None
        assert response_packet.data == f"Non-RPC Echo: {test_message}"
