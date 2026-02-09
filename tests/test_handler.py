import picows
import webshocket
import pytest

from webshocket.exceptions import ReceiveTimeoutError

HOST, PORT = "127.0.0.1", 5000


class customClientHandler(webshocket.handler.WebSocketHandler):
    async def on_connect(self, connection: webshocket.ClientConnection):
        connection.send("I just joined!")

    async def on_disconnect(self, connection: webshocket.ClientConnection): ...

    async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
        connection.send(f"Echo: {packet.data}")


@pytest.mark.asyncio
async def test_server_handler() -> None:
    server = webshocket.WebSocketServer(HOST, PORT, clientHandler=customClientHandler)
    await server.start()

    try:
        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()

        on_connect_packet = await client.recv()
        assert on_connect_packet.data == "I just joined!"

        client.send("Hello World!")
        echo_packet = await client.recv()
        assert echo_packet.data == "Echo: Hello World!"

    finally:
        await client.close()
        await server.close()


@pytest.mark.asyncio
async def test_max_connection() -> None:
    server = webshocket.WebSocketServer(HOST, PORT, clientHandler=customClientHandler, max_connection=1)
    await server.start()

    client1 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    client1.send("Hello")

    with pytest.raises(picows.picows.WSError):
        client2 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        client2.send("Hello")

    assert len(server.clients) == 1

    await server.close()
    await client1.close()


@pytest.mark.asyncio
async def test_handler_pubsub_prequisite() -> None:
    @webshocket.rpc_method()
    async def get_admin(connection: webshocket.ClientConnection):
        connection.admin = True

    try:
        server = webshocket.WebSocketServer(HOST, PORT, max_connection=2)
        server.register_rpc_method(get_admin)
        await server.start()

        client_admin = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        client_normal = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        await client_admin.send_rpc("get_admin")

        server.broadcast("Admin-exclusive broadcast", predicate=webshocket.Is("admin"))

        response_admin = await client_admin.recv()
        assert response_admin.data == "Admin-exclusive broadcast"

        with pytest.raises(ReceiveTimeoutError):
            _response_normal = await client_normal.recv(timeout=1)

    finally:
        await server.close()
