import pytest
import webshocket

(HOST, PORT) = ("127.0.0.1", 5000)


@pytest.mark.asyncio
async def test_simple_server() -> None:
    async with webshocket.WebSocketServer(HOST, PORT) as server:
        assert server.state == webshocket.ServerState.SERVING

        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()
        client.send("Hello World")

        connected_client = await server.accept()
        received_packet = await connected_client.recv()

        assert received_packet.data == "Hello World"

    assert server.state == webshocket.ServerState.CLOSED


@pytest.mark.asyncio
async def test_simple_client() -> None:
    server = webshocket.WebSocketServer(
        HOST,
        PORT,
    )
    await server.start()

    async with webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") as client:
        await client.connect()

        assert client.state == webshocket.ConnectionState.CONNECTED

    assert client.state == webshocket.ConnectionState.CLOSED
    await server.close()
