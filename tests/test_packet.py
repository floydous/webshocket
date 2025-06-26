import webshocket
import pytest


HOST, PORT = ("127.0.0.1", 5000)


@pytest.mark.asyncio
async def test_simple_packet() -> None:
    payload = "This is Custom Packet"

    try:
        server = webshocket.WebSocketServer(HOST, PORT)
        await server.start()

        custom_packet = webshocket.Packet(
            data=payload,
            source=webshocket.PacketSource.CUSTOM,
            channel=None,
        )

        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()
        await client.send(custom_packet)

        connected_client = await server.accept()
        received_response = await connected_client.recv()

        assert received_response.data == payload
        assert received_response.source == webshocket.PacketSource.CUSTOM

    finally:
        await client.close()
        await server.close()


@pytest.mark.asyncio
async def test_packet_source() -> None:
    payload = "Sport News!"
    payload2 = "Global Announcement!"

    try:
        server = webshocket.WebSocketServer(HOST, PORT)
        await server.start()

        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()

        connected_client = await server.accept()
        connected_client.subscribe("sport")

        assert "sport" in connected_client.subscribed_channel

        await server.publish("sport", payload)
        received_packet = await client.recv()

        assert received_packet.data == payload
        assert received_packet.source == webshocket.PacketSource.CHANNEL

        await server.broadcast(payload2)
        received_packet = await client.recv()

        assert received_packet.data == payload2
        assert received_packet.source == webshocket.PacketSource.BROADCAST

    finally:
        await client.close()
        await server.close()
