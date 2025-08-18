import pytest
import asyncio
import webshocket
import webshocket.exceptions


HOST, PORT = "127.0.0.1", 5000


@pytest.mark.asyncio
async def test_client_no_retry_on_disconnect():
    server = webshocket.WebSocketServer(HOST, PORT)
    await server.start()

    try:
        client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")
        await client.connect(retry=False)
        assert client.state == webshocket.ConnectionState.CONNECTED

        await server.close()
        await asyncio.sleep(0.5)

        assert client.state == webshocket.ConnectionState.DISCONNECTED

        with pytest.raises(
            webshocket.exceptions.WebSocketError,
            match="Cannot send data: client is not connected.",
        ):
            await client.send("test")

    finally:
        await client.close()
        await server.close()


@pytest.mark.asyncio
async def test_client_retry_failure_max_attempts():
    client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")

    try:
        with pytest.raises(
            webshocket.exceptions.ConnectionFailedError,
            match="All connection attempts failed after multiple retries.",
        ):
            await client.connect(
                retry=True,
                max_retry_attempt=2,
                retry_interval=1,
            )

        assert client.state == webshocket.ConnectionState.CLOSED

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_client_retry_interval_and_attempts():
    server = webshocket.WebSocketServer(HOST, PORT)
    client = webshocket.WebSocketClient(f"ws://{HOST}:{PORT}")

    async def start_server_later():
        await asyncio.sleep(3)
        await server.start()

    server_start_task = asyncio.create_task(start_server_later())

    try:
        start_time = asyncio.get_event_loop().time()
        await client.connect(
            retry=True,
            max_retry_attempt=3,
            retry_interval=1,
        )
        end_time = asyncio.get_event_loop().time()

        assert client.state == webshocket.ConnectionState.CONNECTED

        # Verify that at least some delay occurred due to retry attempts
        # The exact time will vary due to random backoff, so check for a minimum
        assert (end_time - start_time) > 0.5

    finally:
        server_start_task.cancel()
        await server.close()
        await client.close()
