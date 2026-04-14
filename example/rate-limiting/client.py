"""
Feature 3: Decorator-Based Rate Limiting (Client)
===================================================
Demonstrates the client-side experience when hitting rate limits.
"""

import asyncio
import webshocket
from webshocket.enum import RPCErrorCode


async def main():
    async with webshocket.WebSocketClient("ws://localhost:5000") as client:
        # 1. Call limited_action 5 times (limit is 3 per 10s)
        print("--- Testing limited_action (3 per 10s) ---")
        for i in range(5):
            r = await client.send_rpc("limited_action", f"call-{i + 1}", raise_on_rate_limit=False)
            if r.rpc.error == RPCErrorCode.RATE_LIMIT_EXCEEDED:
                print(f"  Call {i + 1}: RATE LIMITED")
            else:
                print(f"  Call {i + 1}: {r.data}")

        # 2. Call strict_action (limit=2, then disconnects)
        print("\n--- Testing strict_action (2 per 10s, auto-disconnect) ---")
        for i in range(3):
            try:
                r = await client.send_rpc("strict_action", raise_on_rate_limit=False)
                if r.rpc.error == RPCErrorCode.RATE_LIMIT_EXCEEDED:
                    print(f"  Call {i + 1}: RATE LIMITED (connection may be closed)")
                else:
                    print(f"  Call {i + 1}: {r.data}")
            except Exception as e:
                print(f"  Call {i + 1}: Disconnected - {e}")
                break


if __name__ == "__main__":
    asyncio.run(main())
