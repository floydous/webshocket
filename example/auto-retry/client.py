"""
Feature 5: Auto-Retry with Exponential Backoff
=================================================
Demonstrates:
  - Client automatically retries when connection fails
  - Exponential backoff between attempts
  - Max retry attempts configuration

Usage:
  1. Run this client WITHOUT a server running - watch it retry
  2. Start a server within 10 seconds - watch it reconnect

  Server (in another terminal):
    python -c "import asyncio, webshocket; asyncio.run(webshocket.WebSocketServer('localhost', 5000).serve_forever())"
"""

import asyncio
import webshocket


async def main():
    client = webshocket.WebSocketClient("ws://localhost:5000")

    print("[Client] Connecting with retry enabled (max 5 attempts, 2s base interval)...")

    try:
        await client.connect(
            retry=True,
            max_retry_attempt=5,
            retry_interval=2,  # Base interval in seconds (doubles each retry)
        )
        print("[Client] Connected successfully!")

        client.send("Hello from auto-retry client!")
        print("[Client] Message sent.")
    except Exception as e:
        print(f"[Client] Failed to connect after retries: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
