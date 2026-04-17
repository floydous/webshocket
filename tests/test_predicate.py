import pytest
import pytest_asyncio

import webshocket
from webshocket.enum import RPCErrorCode
from webshocket.exceptions import ReceiveTimeoutError

HOST, PORT = "127.0.0.1", 5006


class PredicateHandler(webshocket.WebSocketHandler):
    @webshocket.rpc_method()
    async def set_flag(self, connection: webshocket.ClientConnection, key: str, value: object):
        connection.session_state[key] = value

    @webshocket.rpc_method(requires=webshocket.IsEqual("admin", True))
    async def admin_only(self, connection: webshocket.ClientConnection):
        return "allowed"

    @webshocket.rpc_method(requires=webshocket.Any(webshocket.Has("admin"), webshocket.Is("active")))
    async def any_allowed(self, connection: webshocket.ClientConnection):
        return "allowed"

    @webshocket.rpc_method(requires=webshocket.All(webshocket.Has("admin"), webshocket.Is("active")))
    async def all_allowed(self, connection: webshocket.ClientConnection):
        return "allowed"


@pytest_asyncio.fixture
async def server():
    server = webshocket.WebSocketServer(HOST, PORT, clientHandler=PredicateHandler)
    await server.start()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_predicates_gate_rpc_access(server):
    async with webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as client:
        denied = await client.send_rpc("admin_only")
        assert denied.error == RPCErrorCode.ACCESS_DENIED

        await client.send_rpc("set_flag", "admin", True)
        allowed = await client.send_rpc("admin_only")
        assert allowed.response == "allowed"

        any_allowed = await client.send_rpc("any_allowed")
        assert any_allowed.response == "allowed"

        all_denied = await client.send_rpc("all_allowed")
        assert all_denied.error == RPCErrorCode.ACCESS_DENIED

        await client.send_rpc("set_flag", "active", True)
        all_allowed = await client.send_rpc("all_allowed")
        assert all_allowed.response == "allowed"


@pytest.mark.asyncio
async def test_predicates_filter_broadcasts(server):
    async with (
        webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as privileged,
        webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as regular,
    ):
        await privileged.send_rpc("set_flag", "admin", True)
        await regular.send_rpc("set_flag", "active", True)

        server.broadcast("admin message", predicate=webshocket.Has("admin"))
        assert (await privileged.recv()).data == "admin message"

        with pytest.raises(ReceiveTimeoutError):
            await regular.recv(timeout=0.1)

        server.broadcast("active message", predicate=webshocket.Is("active"))
        assert (await regular.recv()).data == "active message"

        with pytest.raises(ReceiveTimeoutError):
            await privileged.recv(timeout=0.1)
