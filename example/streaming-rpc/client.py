"""
Feature 8: Streaming RPC (Client)
====================================
Iterates over streamed responses and demonstrates mid-stream abort.
"""

import asyncio
import webshocket


async def main():
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        # 1. Stream a full countdown
        print("--- Countdown Stream ---")
        async for packet in client.stream_rpc("countdown", 5):
            print(f"  {packet.data}")

        # 2. Stream words (simulated AI token output)
        print("\n--- Word Stream ---")
        async for packet in client.stream_rpc("generate_words", "The quick brown fox jumps"):
            print(packet.data, end="", flush=True)
        print()  # newline

        # 3. Abort a stream early by breaking out
        print("\n--- Aborted Stream (break after 2 chunks) ---")
        count = 0
        async for packet in client.stream_rpc("countdown", 10):
            print(f"  {packet.data}")
            count += 1
            if count >= 2:
                print("  [Client] Aborting stream!")
                break  # Server-side task is cancelled cleanly


if __name__ == "__main__":
    asyncio.run(main())
