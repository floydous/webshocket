import asyncio
import logging
import ssl
from collections.abc import Awaitable, Callable
from functools import partial
from typing import TYPE_CHECKING

from picows import WSCloseCode, WSFrame, WSListener, WSMsgType, WSTransport, ws_connect

from ..constant import DEFAULT_CHUNK_SIZE, DEFAULT_WEBSHOCKET_SUBPROTOCOL
from ..exceptions import ConnectionClosedError, ConnectionFailedError
from ..packets import Packet

ON_RECEIVE_TYPE = Callable[[Packet], Awaitable[None]]


_logger = logging.getLogger("webshocket.client")


class ClientListener(WSListener):
    __slots__ = ("_clientInstance", "_frag_buffer")

    def __init__(self, clientInstance: "client") -> None:
        self._clientInstance = clientInstance
        self._frag_buffer: list[bytes] = []

    def on_ws_connected(self, transport: WSTransport) -> None:
        self._clientInstance._protocol = transport

    def on_ws_disconnected(self, transport: WSTransport) -> None:
        self._clientInstance._frame_queue.put_nowait(None)

    def _enqueue(self, payload: bytes) -> None:
        try:
            self._clientInstance._frame_queue.put_nowait(payload)
        except asyncio.QueueFull:
            _logger.warning("Client frame queue full — dropping frame. Consider increasing frame_qsize or consuming faster.")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame) -> None:
        if frame.msg_type == WSMsgType.CLOSE:
            close_code = frame.get_close_code()
            close_msg = frame.get_close_message()

            transport.send_close(close_code, close_msg)
            transport.disconnect()
            return

        if frame.msg_type != WSMsgType.CONTINUATION and frame.fin == 1:
            self._enqueue(frame.get_payload_as_bytes())
            return

        self._frag_buffer.append(frame.get_payload_as_bytes())

        if frame.fin == 1:
            self._enqueue(b"".join(self._frag_buffer))
            self._frag_buffer.clear()


class client:
    __slots__ = (
        "_frame_queue",
        "_listener_instance",
        "_protocol",
        "cert",
        "ssl_context",
        "uri",
    )

    def __init__(
        self,
        uri: str,
        *,
        ca_cert_path: str | None = None,
        ssl_context: ssl.SSLContext | None = None,
        frame_qsize: int = 8192,
    ):
        self._protocol: WSTransport | None = None
        self._listener_instance: ClientListener | None = None
        self._frame_queue = asyncio.Queue(maxsize=frame_qsize)

        self.ssl_context = ssl_context
        self.cert = ca_cert_path
        self.uri = uri

    async def connect(self, *args, **kwargs) -> None:
        extra_headers = {"Sec-WebSocket-Protocol": DEFAULT_WEBSHOCKET_SUBPROTOCOL}

        if "extra_headers" in kwargs:
            extra_headers.update(kwargs["extra_headers"])
            del kwargs["extra_headers"]

        self._protocol, listener_instance = await ws_connect(
            *args,
            ws_listener_factory=partial(ClientListener, self),
            extra_headers=extra_headers,
            ssl_context=self.ssl_context,
            url=self.uri,
            enable_auto_ping=True,
            **kwargs,
        )

        if TYPE_CHECKING:
            assert isinstance(listener_instance, ClientListener)

        self._listener_instance = listener_instance

    def send(self, data: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        if not self._protocol:
            raise ConnectionFailedError("Client is not connected to the server.")

        if len(data) <= chunk_size:
            self._protocol.send(WSMsgType.BINARY, data)
            return

        payload = memoryview(data)
        payload_length = len(payload)
        offset = chunk_size

        self._protocol.send(WSMsgType.BINARY, payload[:chunk_size], fin=False)

        while offset + chunk_size < payload_length:
            self._protocol.send(
                WSMsgType.CONTINUATION,
                payload[offset : offset + chunk_size],
                fin=False,
            )

            offset += chunk_size

        if offset < payload_length:
            self._protocol.send(
                WSMsgType.CONTINUATION,
                payload[offset:],
                fin=True,
            )

    async def close(self) -> bool:
        if self._protocol:
            await self._frame_queue.put(None)

            self._protocol.send_close(WSCloseCode.OK, b"Client is closing the connection.")
            self._protocol.disconnect()
            self._protocol = None
            return True

        return False

    async def __aiter__(self):
        while True:
            payload = await self._frame_queue.get()

            if payload is None:
                break

            yield payload

        raise ConnectionClosedError
