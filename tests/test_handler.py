import picows
import webshocket
import pytest
import asyncio


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
            _response_normal = await client_normal.recv(timeout=0.2)

    finally:
        await server.close()


@pytest.mark.asyncio
async def test_wildcard_subscriptions() -> None:
    """Verify that wildcard subscriptions (* and ?) receive matching messages."""

    server = webshocket.WebSocketServer(HOST, PORT)

    @webshocket.rpc_method()
    async def sub(connection: webshocket.ClientConnection, channel: str):
        connection.subscribe(channel)

    @webshocket.rpc_method()
    async def unsub(connection: webshocket.ClientConnection, channel: str):
        connection.unsubscribe(channel)

    server.register_rpc_method(sub)
    server.register_rpc_method(unsub)

    await server.start()

    try:
        client_a = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        await client_a.send_rpc("sub", channel="news.*")

        client_b = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        await client_b.send_rpc("sub", channel="news.tech")

        client_c = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        await client_c.send_rpc("sub", channel="news.sport.?")

        # 1. Publish to "news.tech" -> Should go to A (wildcard) and B (exact)
        server.publish("news.tech", "Tech News")

        assert (await client_a.recv()).data == "Tech News"
        assert (await client_b.recv()).data == "Tech News"

        with pytest.raises(ReceiveTimeoutError):
            await client_c.recv(timeout=0.1)

        # 2. Publish to "news.sport.1" -> Should go to A (news.*) and C (news.sport.?)
        server.publish("news.sport.1", "Sport News")

        assert (await client_a.recv()).data == "Sport News"
        assert (await client_c.recv()).data == "Sport News"

        with pytest.raises(ReceiveTimeoutError):
            await client_b.recv(timeout=0.1)

        # 3. Verify Character Set [abc]
        client_d = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        await client_d.send_rpc("sub", channel="news.market.[ABC]")
        await asyncio.sleep(0.1)

        server.publish("news.market.A", "Market A")
        assert (await client_d.recv()).data == "Market A"

        server.publish("news.market.D", "Market D")
        with pytest.raises(ReceiveTimeoutError):
            await client_d.recv(timeout=0.1)

        await client_d.close()

        # 4. Verify Cleanup
        await client_a.send_rpc("unsub", channel="news.*")
        await asyncio.sleep(0.1)

        # Consume any buffered messages (A received Market A/D earlier)
        while True:
            try:
                await client_a.recv(timeout=0.1)
            except ReceiveTimeoutError:
                break

        server.publish("news.tech", "More Tech")
        assert (await client_b.recv()).data == "More Tech"

        with pytest.raises(ReceiveTimeoutError):
            await client_a.recv(timeout=0.1)

        assert "news.*" not in server.handler.patterns
        assert "news.*" not in server.handler._compiled_patterns

    finally:
        await client_a.close()
        await client_b.close()
        await client_c.close()
        await server.close()
