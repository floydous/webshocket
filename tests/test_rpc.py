import pytest_asyncio
import pytest

import webshocket
from webshocket.rpc import rpc_method, rate_limit
from webshocket.exceptions import RPCError
from webshocket.enum import PacketSource, RPCErrorCode
from webshocket.packets import (
    RPCResponse,
)


class _TestRpcHandler(webshocket.WebSocketHandler):
    async def on_receive(
        self,
        connection: webshocket.ClientConnection,
        packet: webshocket.Packet,
    ):
        if packet.source != PacketSource.RPC:
            connection.send(f"Non-RPC Echo: {packet.data}")
        else:
            pass

    @rpc_method(alias_name="echo")
    async def echo(self, connection: webshocket.ClientConnection, data: str):
        return data

    @rpc_method(alias_name="add")
    async def add_numbers(self, connection: webshocket.ClientConnection, a: int, b: int):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            raise RPCError("Inputs must be numbers.")

        return a + b

    @rpc_method()
    async def raise_rpc_error(self, connection: webshocket.ClientConnection, message: str):
        raise RPCError(message)

    @rpc_method()
    async def raise_generic_error(self, connection: webshocket.ClientConnection):
        raise ValueError("This is a generic value error.")

    @rpc_method()
    async def raise_invalid_params(self, connection: webshocket.ClientConnection, param1):
        pass

    @rpc_method()
    @rate_limit(limit=0, period="1m")
    async def raise_rate_limit_exceeded(self, connection: webshocket.ClientConnection):
        pass

    @rpc_method(requires=lambda connection: getattr(connection, "is_admin", False))
    async def test_requires(self, connection: webshocket.ClientConnection):
        return "This is secret data"

    @rpc_method()
    async def get_admin(self, connection: webshocket.ClientConnection):
        connection.is_admin = True

    async def non_rpc_method(self, connection: webshocket.ClientConnection):
        return "This should not be called via RPC"


@pytest_asyncio.fixture
async def rpc_server():
    server = webshocket.WebSocketServer("localhost", 5000, clientHandler=_TestRpcHandler)
    await server.start()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_rpc_echo_method(
    rpc_server,
):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        response_packet = await client.send_rpc(
            "echo",
            "Hello RPC World",
        )

        assert response_packet.source == PacketSource.RPC
        assert isinstance(
            response_packet.rpc,
            RPCResponse,
        )
        assert response_packet.rpc.response == "Hello RPC World"
        assert response_packet.data == "Hello RPC World"
        assert response_packet.rpc.error is None


@pytest.mark.asyncio
async def test_rpc_add_numbers(
    rpc_server,
):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        response_packet = await client.send_rpc("add_numbers", 10, 20)

        assert response_packet.source == PacketSource.RPC
        assert isinstance(response_packet.rpc, RPCResponse)
        assert response_packet.rpc.error == RPCErrorCode.METHOD_NOT_FOUND
        assert "not found" in response_packet.data


@pytest.mark.asyncio
async def test_rpc_method_alias(
    rpc_server,
):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        response_packet = await client.send_rpc("add", 5, 7)

        assert response_packet.source == PacketSource.RPC
        assert isinstance(
            response_packet.rpc,
            RPCResponse,
        )
        assert response_packet.rpc.error is None
        assert response_packet.rpc.response == 12
        assert response_packet.data == 12


@pytest.mark.asyncio
async def test_rpc_method_not_found(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        response_packet = await client.send_rpc(
            "non_existent_method",
            "test",
        )

        assert response_packet.source == PacketSource.RPC
        assert isinstance(
            response_packet.rpc,
            RPCResponse,
        )
        assert response_packet.rpc.error == RPCErrorCode.METHOD_NOT_FOUND
        assert "not found" in response_packet.data


@pytest.mark.asyncio
async def test_rpc_method_not_exposed(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        # Attempt to call a method that exists but is not decorated with @rpc_method
        response_packet = await client.send_rpc(
            "non_rpc_method",
            "test",
        )

        assert response_packet.source == PacketSource.RPC
        assert isinstance(
            response_packet.rpc,
            RPCResponse,
        )
        assert response_packet.rpc.error == RPCErrorCode.METHOD_NOT_FOUND
        assert "not found" in response_packet.data


@pytest.mark.asyncio
async def test_rpc_method_raises_rpc_error(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        error_msg = "This is a custom RPC error."
        response_packet = await client.send_rpc(
            "raise_rpc_error",
            error_msg,
        )

        assert response_packet.source == PacketSource.RPC
        assert isinstance(
            response_packet.rpc,
            RPCResponse,
        )
        # assert response_packet.rpc.response is None
        assert response_packet.rpc.error == RPCErrorCode.APPLICATION_ERROR
        assert response_packet.data == error_msg


@pytest.mark.asyncio
async def test_on_receive_handles_non_rpc_packet(rpc_server):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        test_message = "Hello, non-RPC world!"
        client.send(test_message)
        response_packet = await client.recv()

        assert response_packet.source == PacketSource.CUSTOM
        assert response_packet.rpc is None
        assert response_packet.data == f"Non-RPC Echo: {test_message}"


@pytest.mark.asyncio
async def test_rpc_error_code(
    rpc_server,
):
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        # ---------------------------------------------------------------------------------
        response = await client.send_rpc("non_rpc_method")

        assert isinstance(
            response.rpc,
            RPCResponse,
        )
        assert response.rpc.error == RPCErrorCode.METHOD_NOT_FOUND
        # ---------------------------------------------------------------------------------

        response = await client.send_rpc(
            "raise_rpc_error",
            "This is a custom RPC error.",
        )

        assert isinstance(
            response.rpc,
            RPCResponse,
        )
        assert response.rpc.error == RPCErrorCode.APPLICATION_ERROR
        assert response.rpc.response == "This is a custom RPC error."
        # ---------------------------------------------------------------------------------

        response = await client.send_rpc("raise_generic_error")

        assert isinstance(
            response.rpc,
            RPCResponse,
        )
        assert response.rpc.error == RPCErrorCode.INTERNAL_SERVER_ERROR
        assert "Server error (ValueError): This is a generic value error." in response.data

        # ---------------------------------------------------------------------------------

        # Expected 1 argument, given 2 instead
        response = await client.send_rpc(
            "raise_invalid_params",
            "test",
            "test2",
        )

        assert isinstance(
            response.rpc,
            RPCResponse,
        )
        assert response.rpc.error == RPCErrorCode.INVALID_PARAMS

        # Expected 1 argument, no argument given
        response = await client.send_rpc("raise_invalid_params")

        assert isinstance(
            response.rpc,
            RPCResponse,
        )
        assert response.rpc.error == RPCErrorCode.INVALID_PARAMS

        # ---------------------------------------------------------------------------------
        response = await client.send_rpc("raise_rate_limit_exceeded")

        assert isinstance(
            response.rpc,
            RPCResponse,
        )
        assert response.rpc.error == RPCErrorCode.RATE_LIMIT_EXCEEDED

        # ---------------------------------------------------------------------------------

        response = await client.send_rpc("test_requires")

        assert isinstance(
            response.rpc,
            RPCResponse,
        )

        assert response.rpc.error == RPCErrorCode.ACCESS_DENIED

        response = await client.send_rpc("get_admin")
        assert response.data is None

        response = await client.send_rpc("test_requires")
        assert response.data == "This is secret data"


@pytest.mark.asyncio
async def test_manual_rpc_add_w_handler(rpc_server: webshocket.WebSocketServer):
    @rpc_method(alias_name="say_my_name")
    async def say_my_name(_):
        return "Heisenberg"

    rpc_server.handler.register_rpc_method(say_my_name)

    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        response = await client.send_rpc("say_my_name")
        assert response.data == "Heisenberg"


@pytest.mark.asyncio
async def test_manual_rpc_add_wo_handler():
    rpc_server = webshocket.WebSocketServer("localhost", 5000)
    await rpc_server.start()

    @rpc_method(alias_name="say_my_name")
    async def say_my_name(_):
        return "Heisenberg"

    rpc_server.register_rpc_method(say_my_name)

    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        connected_client = await rpc_server.accept()
        response = await client.send_rpc("say_my_name")
        assert response.data == "Heisenberg"

        connected_client.send("Hello")
        response = await client.recv()
        assert response.data == "Hello"

        client.send("World")

        response = await connected_client.recv()
        assert response.data == "World"

    await rpc_server.close()


# if __name__ == "__main__":
#     import asyncio

#     asyncio.run(test_manual_rpc_add_wo_handler())
