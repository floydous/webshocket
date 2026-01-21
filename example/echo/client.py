import webshocket
import asyncio


async def main():
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        await client.send("Hello")

        response = await client.recv()
        print("Received: " + response.data)

        # ------------------------------------------

        response = await client.send_rpc("echo", "Hello")
        print("RPC Response: " + response.data)


if __name__ == "__main__":
    asyncio.run(main())
