import asyncio

import webshocket


async def main():
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        client.send("Hello")

        response = await client.recv()
        print("Received: " + response.data)

        # ------------------------------------------

        response_packet = await client.send_rpc("echo", "Hello")
        print("RPC Response: " + response_packet.response)


if __name__ == "__main__":
    asyncio.run(main())
