import webshocket
import pytest
import ssl
import websockets

from webshocket.handler import WebSocketHandler

cert_path = "tests/dummy_certificate/dummy_cert.pem"
cert_key = "tests/dummy_certificate/dummy_key.pem"

server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
server_ctx.load_cert_chain(cert_path, cert_key)

client_ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
client_ctx.load_verify_locations(cert_path)


class DummyHandler(WebSocketHandler):
    async def on_receive(self, connection: webshocket.ClientConnection, packet: webshocket.Packet):
        connection.send("Echo: " + str(packet.data))


@pytest.mark.asyncio
async def test_secure_server():
    try:
        server = webshocket.WebSocketServer("127.0.0.1", 8080, clientHandler=DummyHandler, ssl_context=server_ctx)
        await server.start()

        client = webshocket.WebSocketClient("wss://localhost:8080", ssl_context=client_ctx)
        await client.connect()
        client.send("Hello World")

        response = await client.recv()
        assert response.data == "Echo: Hello World"
        assert response.source == webshocket.PacketSource.CUSTOM

    finally:
        await client.close()
        await server.close()


@pytest.mark.asyncio
async def test_unsecured_client():
    try:
        server = webshocket.WebSocketServer("127.0.0.1", 8080, clientHandler=DummyHandler, ssl_context=server_ctx)
        await server.start()

        with pytest.raises(ssl.SSLCertVerificationError):
            client = webshocket.WebSocketClient("wss://localhost:8080")
            await client.connect()

    finally:
        await client.close()
        await server.close()
