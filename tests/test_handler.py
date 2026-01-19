import webshocket
import websockets
import pytest

HOST, PORT = "127.0.0.1", 5000


class customClientHandler(webshocket.handler.WebSocketHandler):
    async def on_connect(self, connection: webshocket.ClientConnection):
        await connection.send("I just joined!")

    async def on_disconnect(self, connection: webshocket.ClientConnection): ...

    async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
        await connection.send(f"Echo: {packet.data}")


@pytest.mark.asyncio
async def test_server_handler() -> None:
    server = webshocket.WebSocketServer(HOST, PORT, clientHandler=customClientHandler)
    await server.start()

    try:
        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()

        on_connect_packet = await client.recv()
        assert on_connect_packet.data == "I just joined!"

        await client.send("Hello World!")
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
    await client1.send("Hello")

    with pytest.raises(websockets.exceptions.ConnectionClosedError):
        client2 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        await client2.send("Hello")

    assert len(server.clients) == 1

    await server.close()
    await client1.close()
    await client2.close()
