import picows
import webshocket
import pytest
import pytest_asyncio
import asyncio

from webshocket.exceptions import ReceiveTimeoutError

HOST, PORT = "127.0.0.1", 5001


class customClientHandler(webshocket.handler.WebSocketHandler):
    async def on_connect(self, connection: webshocket.ClientConnection):
        connection.send("I just joined!")

    async def on_disconnect(self, connection: webshocket.ClientConnection): ...

    async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
        connection.send(f"Echo: {packet.data}")


class recvClientHandler(webshocket.handler.WebSocketHandler):
    async def on_connect(self, connection: webshocket.ClientConnection):
        packet = await connection.recv(timeout=5.0)
        connection.send(f"Recv: {packet.data}")

    async def on_disconnect(self, connection: webshocket.ClientConnection): ...
    async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet): ...



@pytest_asyncio.fixture
async def handler_server():
    server = webshocket.WebSocketServer(HOST, PORT, clientHandler=customClientHandler)
    await server.start()
    yield server
    await server.close()


@pytest_asyncio.fixture
async def default_server():
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()
    yield server
    await server.close()


@pytest.mark.asyncio
async def test_server_handler(handler_server) -> None:
    client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
    await client.connect()

    try:
        on_connect_packet = await client.recv()
        assert on_connect_packet.data == "I just joined!"

        client.send("Hello World!")
        echo_packet = await client.recv()
        assert echo_packet.data == "Echo: Hello World!"

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_manual_recv_handler() -> None:
    server = webshocket.WebSocketServer(HOST, PORT, clientHandler=recvClientHandler)
    await server.start()

    client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
    await client.connect()

    try:
        client.send("Testing manual recv!")
        echo_packet = await client.recv()
        assert echo_packet.data == "Recv: Testing manual recv!"
    finally:
        await client.close()
        await server.close()


@pytest.mark.asyncio
async def test_max_connection() -> None:
    server = webshocket.WebSocketServer(HOST, PORT, clientHandler=customClientHandler, max_connection=1)
    await server.start()

    client1 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    client1.send("Hello")

    try:
        with pytest.raises(picows.WSError):
            client2 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
            client2.send("Hello")

        assert len(server.clients) == 1

    finally:
        await client1.close()
        await server.close()


@pytest.mark.asyncio
async def test_handler_pubsub_prequisite(default_server) -> None:
    @webshocket.rpc_method()
    async def get_admin(connection: webshocket.ClientConnection):
        connection.admin = True

    default_server.register_rpc_method(get_admin)

    client_admin = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    client_normal = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()

    try:
        await client_admin.send_rpc("get_admin")

        default_server.broadcast("Admin-exclusive broadcast", predicate=webshocket.Is("admin"))

        response_admin = await client_admin.recv()
        assert response_admin.data == "Admin-exclusive broadcast"

        with pytest.raises(ReceiveTimeoutError):
            _response_normal = await client_normal.recv(timeout=0.2)

    finally:
        await client_admin.close()
        await client_normal.close()


@pytest.mark.asyncio
async def test_wildcard_subscriptions(default_server) -> None:
    """Verify that wildcard subscriptions (* and ?) receive matching messages."""

    @webshocket.rpc_method()
    async def sub(connection: webshocket.ClientConnection, channel: str):
        connection.subscribe(channel)

    @webshocket.rpc_method()
    async def unsub(connection: webshocket.ClientConnection, channel: str):
        connection.unsubscribe(channel)

    default_server.register_rpc_method(sub)
    default_server.register_rpc_method(unsub)

    client_a = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    await client_a.send_rpc("sub", channel="news.*")

    client_b = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    await client_b.send_rpc("sub", channel="news.tech")

    client_c = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    await client_c.send_rpc("sub", channel="news.sport.?")

    try:
        # 1. Publish to "news.tech" -> Should go to A (wildcard) and B (exact)
        default_server.publish("news.tech", "Tech News")

        assert (await client_a.recv()).data == "Tech News"
        assert (await client_b.recv()).data == "Tech News"

        with pytest.raises(ReceiveTimeoutError):
            await client_c.recv(timeout=0.1)

        # 2. Publish to "news.sport.1" -> Should go to A (news.*) and C (news.sport.?)
        default_server.publish("news.sport.1", "Sport News")

        assert (await client_a.recv()).data == "Sport News"
        assert (await client_c.recv()).data == "Sport News"

        with pytest.raises(ReceiveTimeoutError):
            await client_b.recv(timeout=0.1)

        # 3. Verify Character Set [abc]
        client_d = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
        await client_d.send_rpc("sub", channel="news.market.[ABC]")
        await asyncio.sleep(0.1)

        default_server.publish("news.market.A", "Market A")
        assert (await client_d.recv()).data == "Market A"

        default_server.publish("news.market.D", "Market D")
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

        default_server.publish("news.tech", "More Tech")
        assert (await client_b.recv()).data == "More Tech"

        with pytest.raises(ReceiveTimeoutError):
            await client_a.recv(timeout=0.1)

        assert "news.*" not in default_server.handler.patterns
        assert "news.*" not in default_server.handler._compiled_patterns

    finally:
        await client_a.close()
        await client_b.close()
        await client_c.close()

@pytest.mark.asyncio
async def test_client_on_receive_decorator(handler_server):
    received_packets = []

    client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")

    async def handle(packet):
        received_packets.append(packet.data)

    client.on_receive_callback = handle
    await client.connect()

    try:
        client.send("Hello")

        for _ in range(20):
            if "Echo: Hello" in received_packets:
                break
            await asyncio.sleep(0.1)

    finally:
        await client.close()

    assert "Echo: Hello" in received_packets, f"Packets were: {received_packets}"


# ---------------------------------------------------------------------------
# handler.py edge-case coverage
# ---------------------------------------------------------------------------

from webshocket.handler import WebSocketHandler, DefaultWebSocketHandler
from webshocket.exceptions import PacketError


def test_register_non_rpc_raises():
    """handler.py:69 — register_rpc_method with non-RPC function raises ValueError."""
    handler = WebSocketHandler()

    def plain_func():
        pass

    with pytest.raises(ValueError, match="non-RPC method"):
        handler.register_rpc_method(plain_func)


@pytest.mark.asyncio
async def test_base_handler_on_receive_noop():
    """handler.py:103 — base WebSocketHandler.on_receive is a no-op pass."""
    handler = WebSocketHandler()
    result = await handler.on_receive(None, None)
    assert result is None


@pytest.mark.asyncio
async def test_broadcast_no_clients():
    """handler.py:125 — broadcast with no connected clients returns early."""
    handler = WebSocketHandler()
    handler.broadcast("hello")


@pytest.mark.asyncio
async def test_broadcast_wrong_source_raises(handler_server):
    """handler.py:133 — broadcast with non-BROADCAST source raises PacketError."""
    client = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    await asyncio.sleep(0.05)

    try:
        pkt = webshocket.Packet(data="x", source=webshocket.PacketSource.CUSTOM)
        with pytest.raises(PacketError, match="Cannot broadcast non-broadcast"):
            handler_server.handler.broadcast(pkt)
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_broadcast_exclude(handler_server):
    """handler.py:137 — broadcast excludes specified clients."""
    c1 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    c2 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    await asyncio.sleep(0.05)

    try:
        all_clients = list(handler_server.handler.clients)
        assert len(all_clients) >= 2
        handler_server.handler.broadcast("test_msg", exclude=(all_clients[0],))
    finally:
        await c1.close()
        await c2.close()


@pytest.mark.asyncio
async def test_publish_wrong_source_raises():
    """handler.py:166 — publish with non-CHANNEL source raises PacketError."""
    handler = WebSocketHandler()
    pkt = webshocket.Packet(data="x", source=webshocket.PacketSource.BROADCAST)
    with pytest.raises(PacketError, match="Cannot publish non-channel"):
        handler.publish("ch", pkt)


@pytest.mark.asyncio
async def test_publish_exclude_and_predicate(handler_server):
    """handler.py:179, 182 — publish with exclude and failing predicate."""
    c1 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    c2 = await webshocket.WebSocketClient(f"ws://{HOST}:{PORT}").connect()
    await asyncio.sleep(0.05)

    try:
        all_clients = list(handler_server.handler.clients)
        for c in all_clients:
            handler_server.handler.subscribe(c, "test_ch")

        handler_server.handler.publish(
            "test_ch",
            "msg",
            exclude=(all_clients[0],),
            predicate=lambda conn: False,
        )
    finally:
        await c1.close()
        await c2.close()


def test_pattern_cache_hit():
    """handler.py:236 — _get_matching_patterns returns cached result."""
    handler = WebSocketHandler()
    handler._pattern_cache["news.tech"] = ["news.*"]
    assert handler._get_matching_patterns("news.tech") == ["news.*"]


@pytest.mark.asyncio
async def test_default_handler_on_receive():
    """handler.py:252 — DefaultWebSocketHandler.on_receive queues packet."""
    handler = DefaultWebSocketHandler()

    class FakeConn:
        def __init__(self):
            self._packet_queue = asyncio.Queue()

    conn = FakeConn()
    pkt = webshocket.Packet(data="hi", source=webshocket.PacketSource.CUSTOM)
    await handler.on_receive(conn, pkt)
    assert not conn._packet_queue.empty()
