import webshocket
import pytest

HOST, PORT = ("127.0.0.1", 5000)


class customClientHandler(webshocket.handler.WebSocketHandler):
    async def on_connect(self, websocket: webshocket.ClientConnection):
        await websocket.send("I just joined!")

    async def on_disconnect(self, websocket: webshocket.ClientConnection): ...

    async def on_receive(
        self, websocket: webshocket.ClientConnection, packet: webshocket.Packet
    ):
        await websocket.send(f"Echo: {packet.data}")


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
