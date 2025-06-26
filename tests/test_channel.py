import webshocket
import pytest
import asyncio

HOST, PORT = ("127.0.0.1", 5000)


@pytest.mark.asyncio
async def test_simple_subscription() -> None:
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()

    try:
        client_one = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client_one.connect()

        client_two = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client_two.connect()

        connected_client_one = await server.accept()
        connected_client_two = await server.accept()

        connected_client_one.subscribe("sports")
        connected_client_two.subscribe("news")

        assert "sports" in connected_client_one.subscribed_channel
        assert "news" in connected_client_two.subscribed_channel

        await server.publish("sports", "Sports News!")
        received_response = await client_one.recv()
        assert received_response.data == "Sports News!"
        assert received_response.source == webshocket.PacketSource.CHANNEL

        await server.publish("news", "News Report!")
        received_response = await client_two.recv()
        assert received_response.data == "News Report!"
        assert received_response.source == webshocket.PacketSource.CHANNEL

    finally:
        await client_one.close()
        await client_two.close()
        await server.close()


@pytest.mark.asyncio
async def test_broadcast():
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()

    number_of_clients = 5

    clients = [
        webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        for _ in range(number_of_clients)
    ]

    try:
        connect_tasks = [client.connect() for client in clients]
        await asyncio.gather(*connect_tasks)

        await asyncio.sleep(0.5)
        assert len(server.handler.clients) == number_of_clients

        await server.broadcast("Global Announcement!")

        receive_tasks = [client.recv() for client in clients]
        received_packets = await asyncio.gather(*receive_tasks)

        assert len(received_packets) == number_of_clients

        for packet in received_packets:
            assert packet.data == "Global Announcement!"
            assert packet.source == webshocket.PacketSource.BROADCAST

    finally:
        close_tasks = [client.close() for client in clients]
        await asyncio.gather(*close_tasks, return_exceptions=True)
        await server.close()


@pytest.mark.asyncio
async def test_receive_timeout() -> None:
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()

    try:
        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()

        connected_client = await server.accept()
        connected_client.subscribe("sports")

        await server.publish("news", "This is News update!")

        with pytest.raises(TimeoutError):
            await asyncio.wait_for(client.recv(), timeout=1)

    finally:
        await client.close()
        await server.close()
