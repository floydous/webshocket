"""Feature 6: Integrated Tunnelling & Deployment
================================================
Demonstrates:
  - Running a Webshocket server on 0.0.0.0 for external access
  - Using async context manager for clean lifecycle management
  - serve_forever() for production-style deployment

This server is designed to sit behind a free HTTP tunnel like:
  - Cloudflare Argo Tunnel: cloudflared tunnel --url http://localhost:5000
  - LocalTunnel:            lt --port 5000

Run:  python server.py
"""

import asyncio

import webshocket
from webshocket import ClientConnection
from webshocket.rpc import rpc_method


class DeployHandler(webshocket.WebSocketHandler):
    async def on_connect(self, connection: ClientConnection):
        print(f"[Server] Client connected: {connection.remote_address}")

    async def on_disconnect(self, connection: ClientConnection):
        print(f"[Server] Client disconnected: {connection.remote_address}")

    @rpc_method()
    async def ping(self, connection: ClientConnection):
        return "pong"

    @rpc_method()
    async def server_info(self, connection: ClientConnection):
        return {
            "version": webshocket.__version__,
            "clients": len(self.clients),
        }


async def main():
    # Bind to 0.0.0.0 to accept connections from tunnels
    server = webshocket.WebSocketServer("0.0.0.0", 5000, clientHandler=DeployHandler)

    async with server:
        print(f"[Server] Webshocket v{webshocket.__version__} running on ws://0.0.0.0:5000")
        print("[Server] Ready for tunnel connections (Cloudflare Argo, LocalTunnel, etc.)")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
