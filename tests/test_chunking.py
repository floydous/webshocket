import pytest
import pytest_asyncio
import webshocket
import asyncio
import random
import string

HOST, PORT = "127.0.0.1", 5002


@pytest_asyncio.fixture
async def server():
    server = webshocket.WebSocketServer(HOST, PORT, packet_qsize=1024)
    await server.start()
    yield server
    await server.close()


@pytest_asyncio.fixture
async def client(server):
    client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}", max_packet_qsize=1024)
    await client.connect()
    yield client
    await client.close()


async def wait_for_client_connection(server, timeout=2.0):
    """Polls until a client is connected to the server."""
    for _ in range(int(timeout * 20)):
        if len(server.clients) > 0:
            return list(server.clients)[0]
        await asyncio.sleep(0.05)
    raise TimeoutError("Client did not connect to server")


@pytest.mark.asyncio
async def test_chunking_exact_64kb(server, client):
    """Test sending exactly 64KB data (chunk size limit)."""
    payload_size = 64 * 1024
    data = "a" * payload_size

    client.send(data)
    server_conn = await wait_for_client_connection(server)

    packet = await asyncio.wait_for(server_conn._packet_queue.get(), timeout=5.0)
    assert packet.data == data


@pytest.mark.asyncio
async def test_chunking_larger_than_64kb(server, client):
    """Test sending 64KB + 10 bytes."""
    payload_size = (64 * 1024) + 10
    data = "b" * payload_size

    client.send(data)
    server_conn = await wait_for_client_connection(server)

    packet = await asyncio.wait_for(server_conn._packet_queue.get(), timeout=5.0)
    assert packet.data == data


@pytest.mark.asyncio
async def test_chunking_large_1mb(server, client):
    """Test sending 1MB payload."""
    payload_size = 1024 * 1024
    data = "".join(random.choices(string.ascii_letters, k=payload_size))

    client.send(data)

    server_conn = await wait_for_client_connection(server)

    packet = await asyncio.wait_for(server_conn._packet_queue.get(), timeout=10.0)
    assert packet.data == data
