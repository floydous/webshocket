import webshocket
import websockets
import pytest
import pytest_asyncio

HOST, PORT = "127.0.0.1", 5000


@pytest_asyncio.fixture
async def server():
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()
    yield server
    await server.close()


@pytest_asyncio.fixture
async def client(server):
    client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
    await client.connect()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_simple_packet(server, client) -> None:
    payload = "This is Custom Packet"

    custom_packet = webshocket.Packet(
        data=payload,
        source=webshocket.PacketSource.CUSTOM,
        channel=None,
    )

    client.send(custom_packet)

    connected_client = await server.accept()
    received_response = await connected_client.recv()

    assert received_response.data == payload
    assert received_response.source == webshocket.PacketSource.CUSTOM


@pytest.mark.asyncio
async def test_packet_source(server, client) -> None:
    payload = "Sport News!"
    payload2 = "Global Announcement!"

    connected_client = await server.accept()
    connected_client.subscribe("sport")

    assert "sport" in connected_client.subscribed_channel

    server.publish(
        "sport",
        payload,
    )
    received_packet = await client.recv()

    assert received_packet.data == payload
    assert received_packet.source == webshocket.PacketSource.CHANNEL

    server.broadcast(payload2)
    received_packet = await client.recv()

    assert received_packet.data == payload2
    assert received_packet.source == webshocket.PacketSource.BROADCAST


@pytest.mark.asyncio
async def test_send_other_datatype(server, client):
    connected_client = await server.accept()
    connected_client.send({"hello": "world"})

    received_packet = await client.recv()
    assert received_packet.data == {"hello": "world"}


@pytest.mark.asyncio
async def test_send_unserializeable_data(server, client):
    data_to_send = [
        lambda: "Function type",
        webshocket.ClientConnection,
    ]

    for item in data_to_send:
        with pytest.raises(TypeError):
            client.send(item)


@pytest.mark.asyncio
async def test_unknown_packet(server):
    client = await websockets.connect(f"ws://{HOST}:{PORT}")

    try:
        connected_client = await server.accept()
        await client.send("Raw String.")

        received_packet = await connected_client.recv()

        assert received_packet.data == b"Raw String."
        assert received_packet.source == webshocket.PacketSource.UNKNOWN

    finally:
        await client.close()


# ---------------------------------------------------------------------------
# websocket.py:108 — _to_packet with non-bytes for FRAMEWORK
# ---------------------------------------------------------------------------


def test_to_packet_non_bytes_framework():
    """_to_packet with a string for FRAMEWORK falls through to UNKNOWN source."""
    from webshocket.websocket import server as WebSocketServerClass
    from webshocket.enum import ClientType

    pkt = WebSocketServerClass._to_packet("not-bytes-data", ClientType.FRAMEWORK)
    assert pkt.source == webshocket.PacketSource.UNKNOWN
