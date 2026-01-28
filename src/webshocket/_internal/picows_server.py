import asyncio
import ssl

from webshocket import ConnectionState
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Self
from picows import (
    WSFrame,
    WSListener,
    WSMsgType,
    WSUpgradeRequest,
    WSTransport,
    WSUpgradeResponse,
    WSUpgradeResponseWithListener,
    ws_create_server,
)

from webshocket.enum import ClientType
from webshocket.typing import DEFAULT_WEBSHOCKET_SUBPROTOCOL
from webshocket.connection import ClientConnection

if TYPE_CHECKING:
    from webshocket import WebSocketServer

HandlerLike = Callable[[WSTransport, "ServerClientListener"], Coroutine[Any, Any, None]]


class ServerClientListener(WSListener):
    __slots__ = (
        "clientType",
        "handler",
        "_handler_task",
        "_connection",
        "_ready",
        "_pending_payload",
        "_frag_buffer",
    )

    def __init__(self, handler: HandlerLike, clientType: ClientType):
        self.clientType = clientType
        self.handler = handler

        self._handler_task: asyncio.Task | None = None
        self._connection: ClientConnection | None = None
        self._ready = asyncio.Event()

        self._pending_payload: asyncio.Queue[bytes] = asyncio.Queue(maxsize=64)
        self._frag_buffer: list[bytes] = []

    async def _on_ready(self):
        await self._ready.wait()

        while not self._pending_payload.empty():
            payload = await self._pending_payload.get()

            if self._connection:
                await self._connection._payload_queue.put(payload)

    def on_ws_connected(self, transport: WSTransport) -> None:
        self._handler_task = asyncio.create_task(
            self.handler(transport, self),
        )

    def on_ws_disconnected(self, transport: WSTransport) -> None:
        if self._connection is not None:
            self._connection.connection_state = ConnectionState.CLOSED
            self._connection._payload_queue.put_nowait(None)

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame) -> None:
        if frame.msg_type == WSMsgType.CLOSE:
            transport.send_close(frame.get_close_code(), frame.get_close_message())
            transport.disconnect()
            return

        if frame.msg_type != WSMsgType.CONTINUATION and frame.fin == 1:
            payload = frame.get_payload_as_bytes()

            if self._connection is None:
                self._pending_payload.put_nowait(payload)
                return

            self._connection._payload_queue.put_nowait(payload)
            return

        self._frag_buffer.append(frame.get_payload_as_bytes())

        if frame.fin == 1:
            payload = b"".join(self._frag_buffer)
            self._frag_buffer.clear()

            if self._connection is None:
                self._pending_payload.put_nowait(payload)
                return

            self._connection._payload_queue.put_nowait(payload)


class PicowsServer:
    __slots__ = (
        "host",
        "port",
        "ssl_context",
        "_handler",
        "_client_bucket",
        "_max_connection",
        "_picows_server",
    )

    def __init__(self, host: str, port: int, webshocket_server: "WebSocketServer", ssl_context: ssl.SSLContext | None = None):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context

        self._handler = webshocket_server._handler
        self._client_bucket = webshocket_server.clients
        self._max_connection = webshocket_server.max_connection

        self._picows_server: asyncio.base_events.Server | None = None

    def _listener_factory(self, request: WSUpgradeRequest) -> ServerClientListener | WSUpgradeResponseWithListener:
        if self._max_connection is not None and len(self._client_bucket) >= self._max_connection:
            return WSUpgradeResponseWithListener(
                WSUpgradeResponse.create_error_response(
                    status=503,
                    body=b"Server is full, try again later.",
                ),
                None,
            )

        if DEFAULT_WEBSHOCKET_SUBPROTOCOL in request.headers.get("Sec-WebSocket-Protocol", ""):
            return WSUpgradeResponseWithListener(
                WSUpgradeResponse.create_101_response(
                    extra_headers={"Sec-WebSocket-Protocol": DEFAULT_WEBSHOCKET_SUBPROTOCOL},
                ),
                ServerClientListener(self._handler, ClientType.FRAMEWORK),
            )

        return ServerClientListener(self._handler, ClientType.GENERIC)

    async def serve(self, **kwargs) -> Self:
        if self._picows_server is not None:
            raise RuntimeError("Server is already running")

        self._picows_server = await ws_create_server(
            ws_listener_factory=self._listener_factory,
            ssl=self.ssl_context,
            host=self.host,
            port=self.port,
            enable_auto_ping=True,
            **kwargs,
        )

        await self._picows_server.start_serving()
        return self
