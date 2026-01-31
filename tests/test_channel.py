import webshocket
import pytest
import asyncio
import os

(HOST, PORT) = ("127.0.0.1", 5000)

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


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

        server.publish(
            "sports",
            "Sports News!",
        )
        received_response = await client_one.recv()
        assert received_response.data == "Sports News!"
        assert received_response.source == webshocket.PacketSource.CHANNEL

        server.publish(
            "news",
            "News Report!",
        )
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

    clients = [webshocket.WebSocketClient(f"ws://{HOST}:{PORT}") for _ in range(number_of_clients)]

    try:
        connect_tasks = [client.connect() for client in clients]
        await asyncio.gather(*connect_tasks)

        await asyncio.sleep(0.5)
        assert len(server.handler.clients) == number_of_clients

        server.broadcast("Global Announcement!")

        receive_tasks = [client.recv() for client in clients]
        received_packets = await asyncio.gather(*receive_tasks)

        assert len(received_packets) == number_of_clients

        for packet in received_packets:
            assert packet.data == "Global Announcement!"
            assert packet.source == webshocket.PacketSource.BROADCAST

    finally:
        close_tasks = [client.close() for client in clients]
        await asyncio.gather(
            *close_tasks,
            return_exceptions=True,
        )
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

        server.publish(
            "news",
            "This is News update!",
        )

        with pytest.raises(TimeoutError):
            await asyncio.wait_for(
                client.recv(),
                timeout=1,
            )

    finally:
        await client.close()
        await server.close()


@pytest.mark.asyncio
async def test_multiple_publish() -> None:
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()

    try:
        client_sport = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client_sport.connect()

        client_news = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client_news.connect()

        connected_client1 = await server.accept()
        connected_client1.subscribe("sports")
        connected_client2 = await server.accept()
        connected_client2.subscribe("news")

        server.publish({"sports", "news"}, "This is Global update!")

        received_packet = await client_sport.recv()
        assert received_packet.data == "This is Global update!"

        received_packet = await client_news.recv()
        assert received_packet.data == "This is Global update!"

    finally:
        await client_sport.close()
        await client_news.close()
        await server.close()


@pytest.mark.asyncio
async def test_channel_auto_delete() -> None:
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()

    try:
        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()

        connected_client = await server.accept()
        connected_client.subscribe("sports")

        assert len(server.channels) == 1

        connected_client.unsubscribe("sports")

        assert len(server.channels) == 0

    finally:
        await client.close()
        await server.close()


@pytest.mark.asyncio
async def test_remove_on_disconnect() -> None:
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()

    try:
        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect()

        connected_client = await server.accept()
        connected_client.subscribe("sports")

        assert len(server.channels) == 1

        await client.close()
        await asyncio.sleep(0.2)

        assert len(server.channels) == 0

    finally:
        await server.close()
