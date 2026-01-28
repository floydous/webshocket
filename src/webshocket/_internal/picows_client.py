import asyncio
import ssl

from typing import Awaitable, Callable, Optional, TYPE_CHECKING
from picows import WSCloseCode, WSFrame, WSListener, WSMsgType, WSTransport, ws_connect
from functools import partial

from ..packets import Packet
from ..typing import DEFAULT_WEBSHOCKET_SUBPROTOCOL
from ..exceptions import ConnectionFailedError, ConnectionClosedError

ON_RECEIVE_TYPE = Callable[[Packet], Awaitable[None]]


class ClientListener(WSListener):
    __slots__ = ("_clientInstance", "_frag_buffer")

    def __init__(self, clientInstance: "client") -> None:
        self._clientInstance = clientInstance
        self._frag_buffer: list[bytes] = []

    def on_ws_connected(self, transport: WSTransport) -> None:
        self._clientInstance._protocol = transport

    def on_ws_disconnected(self, transport: WSTransport) -> None:
        self._clientInstance._frame_queue.put_nowait(None)

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame) -> None:
        if frame.msg_type == WSMsgType.CLOSE:
            close_code = frame.get_close_code()
            close_msg = frame.get_close_message()

            transport.send_close(close_code, close_msg)
            transport.disconnect()
            return

        if frame.msg_type != WSMsgType.CONTINUATION and frame.fin == 1:
            self._clientInstance._frame_queue.put_nowait(frame.get_payload_as_bytes())
            return

        self._frag_buffer.append(frame.get_payload_as_bytes())

        if frame.fin == 1:
            self._clientInstance._frame_queue.put_nowait(b"".join(self._frag_buffer))
            self._frag_buffer.clear()


class client:
    __slots__ = (
        "_protocol",
        "_listener_instance",
        "_frame_queue",
        "ssl_context",
        "cert",
        "uri",
    )

    def __init__(
        self,
        uri: str,
        *,
        ca_cert_path: Optional[str] = None,
        ssl_context: ssl.SSLContext | None = None,
        frame_qsize: int = 64,
    ):
        self._protocol: Optional[WSTransport] = None
        self._listener_instance: Optional[ClientListener] = None
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
            ws_listener_factory=partial(ClientListener, self),
            extra_headers=extra_headers,
            ssl_context=self.ssl_context,
            url=self.uri,
            enable_auto_ping=True,
            *args,
            **kwargs,
        )

        if TYPE_CHECKING:
            assert isinstance(listener_instance, ClientListener)

        self._listener_instance = listener_instance

    def send(self, data: bytes, chunk_size: int = 1024 * 64) -> None:
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

        return bool(self._protocol)

    async def __aiter__(self):
        while True:
            payload = await self._frame_queue.get()

            if payload is None:
                break

            yield payload

        raise ConnectionClosedError
