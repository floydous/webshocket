import pytest
import pytest_asyncio
import asyncio
import json
import uuid
import webshocket
from webshocket import Packet


class StateTestHandler(webshocket.WebSocketHandler):
    async def on_receive(self, connection: webshocket.ClientConnection, packet: Packet):
        try:
            command_data = json.loads(packet.data)
            command = command_data.get("command")

            if command == "set_state":
                key = command_data["key"]
                value = command_data["value"]
                setattr(connection, key, value)
                connection.send(f"OK: Set {key} to {value}")

            elif command == "get_state":
                key = command_data["key"]
                value = getattr(connection, key, "NOT_FOUND")
                connection.send(f"VALUE: {value}")

        except (
            json.JSONDecodeError,
            KeyError,
        ):
            connection.send("ERROR: Invalid command format")


@pytest_asyncio.fixture
async def state_server():
    (host, port) = ("127.0.0.1", 8778)
    server = webshocket.WebSocketServer(host, port, clientHandler=StateTestHandler)
    await server.start()

    yield (
        server,
        f"ws://{host}:{port}",
    )
    await server.close()


@pytest.mark.asyncio
async def test_session_state_set_and_get(
    state_server,
):
    """
    Test Case 1: Verifies that state can be set and retrieved on a
    single connection using both attribute and dictionary access.
    """
    (
        server,
        uri,
    ) = state_server

    async with webshocket.WebSocketClient(uri) as client:
        client.send(json.dumps({"command": "set_state", "key": "username", "value": "alice"}))
        response = await client.recv()
        assert response.data == "OK: Set username to alice"

        assert len(server.handler.clients) == 1
        alice_connection = list(server.handler.clients)[0]

        assert alice_connection.username == "alice"
        assert alice_connection.session_state["username"] == "alice"


@pytest.mark.asyncio
async def test_session_state_is_isolated_per_client(
    state_server,
):
    """
    Verifies that session_state is isolated between two clients,
    using a robust self-identification protocol.
    """
    (server, uri) = state_server

    client_a_id = str(uuid.uuid4())
    client_b_id = str(uuid.uuid4())

    async with webshocket.WebSocketClient(uri) as client_a, webshocket.WebSocketClient(uri) as client_b:
        client_a.send(json.dumps({"command": "set_state", "key": "user_id", "value": client_a_id}))
        await client_a.recv()

        client_b.send(json.dumps({"command": "set_state", "key": "user_id", "value": client_b_id}))
        await client_b.recv()

        conn_a = next(
            (c for c in server.clients if getattr(c, "user_id", None) == client_a_id),
            None,
        )
        conn_b = next(
            (c for c in server.clients if getattr(c, "user_id", None) == client_b_id),
            None,
        )

        assert conn_a is not None and conn_b is not None
        assert conn_a.user_id == client_a_id
        assert conn_b.user_id == client_b_id
        assert conn_a.user_id != conn_b.user_id


@pytest.mark.asyncio
async def test_session_state_is_cleared_on_disconnect(
    state_server,
):
    """
    Test Case 3: Verifies that a client's state is gone after it disconnects.
    """
    (
        server,
        uri,
    ) = state_server

    async with webshocket.WebSocketClient(uri) as client:
        client.send(
            json.dumps(
                {
                    "command": "set_state",
                    "key": "status",
                    "value": "active",
                }
            )
        )
        await client.recv()
        assert len(server.handler.clients) == 1

    await asyncio.sleep(0.1)

    assert len(server.handler.clients) == 0
