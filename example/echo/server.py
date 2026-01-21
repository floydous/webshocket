import asyncio
import webshocket
from webshocket import ClientConnection, Packet


class ClientHandler(webshocket.WebSocketHandler):
    async def on_receive(self, connection: ClientConnection, packet: Packet):
        await connection.send("Echo: " + packet.data)

    @webshocket.rpc_method()
    async def echo(self, connection: ClientConnection, message: str):
        return "Echo: " + message


async def main():
    server = webshocket.WebSocketServer("0.0.0.0", 5000, clientHandler=ClientHandler)

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
