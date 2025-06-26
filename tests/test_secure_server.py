import webshocket
import pytest
import ssl
import websockets

from webshocket.handler import WebSocketHandler

certifi: webshocket.CertificatePaths = {
    "cert_path": "tests/dummy_certificate/dummy_cert.pem",
    "key_path": "tests/dummy_certificate/dummy_key.pem",
}


class DummyHandler(WebSocketHandler):
    async def on_receive(self, websocket, packet):
        await websocket.send("Echo: " + str(packet.data))


@pytest.mark.asyncio
async def test_secure_server():
    try:
        server = webshocket.websocket.server(
            "127.0.0.1", 8080, clientHandler=DummyHandler, certificate=certifi
        )
        await server.start()

        client = webshocket.websocket.client(
            "wss://localhost:8080",
            ca_cert_path="tests/dummy_certificate/dummy_cert.pem",
        )

        await client.connect()
        await client.send("Hello World")

        response = await client.recv()
        assert response.data == "Echo: Hello World"
        assert response.source == webshocket.PacketSource.CUSTOM

    finally:
        await client.close()
        await server.close()


@pytest.mark.asyncio
async def test_unsecured_client():
    try:
        server = webshocket.websocket.server(
            "127.0.0.1", 8080, clientHandler=DummyHandler, certificate=certifi
        )
        await server.start()

        with pytest.raises(ssl.SSLCertVerificationError):
            client = webshocket.websocket.client("wss://localhost:8080")
            await client.connect()

        with pytest.raises(websockets.exceptions.InvalidMessage):
            client = webshocket.websocket.client("ws://localhost:8080")
            await client.connect()

    finally:
        await client.close()
        await server.close()
