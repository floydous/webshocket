import websockets

from typing import Optional, Iterable, Union, Any, Callable, Awaitable, Self
from .handler import WebSocketHandler, DefaultWebSocketHandler
from .typing import CertificatePaths
from .connection import ClientConnection
from .packets import Packet
from .enum import ConnectionState, ServerState

class server:
    """
    Represents a WebSocket server that handles incoming connections and messages.

    This class provides functionality to start, manage, and close a WebSocket server,
    integrating with a custom WebSocketHandler for application-specific logic.
    It supports both secure (WSS) and unsecure (WS) connections.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        clientHandler: type[WebSocketHandler] = DefaultWebSocketHandler,
        certificate: Optional[CertificatePaths] = None,
    ) -> None: ...
    state: ServerState
    def subscribe(
        self, client: "ClientConnection", channel: str | Iterable
    ) -> None: ...
    def unsubscribe(
        self, client: "ClientConnection", channel: str | Iterable
    ) -> None: ...
    async def broadcast(
        self,
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection"]] = None,
    ) -> None: ...
    async def publish(
        self,
        channel: str,
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection"]] = None,
    ) -> None: ...
    async def _handler(
        self, websocket_protocol: websockets.ServerConnection
    ) -> None: ...
    async def accept(self) -> ClientConnection: ...
    async def start(self, *args, **kwargs) -> None: ...
    async def serve_forever(self, *args, **kwargs) -> None: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
    def __getattr__(self, name: str) -> Any: ...
    @property
    def clients(self) -> set[ClientConnection]: ...
    @property
    def channels(self) -> dict[str, set[ClientConnection]]: ...
    @property
    def _reversed_channel(self) -> dict["ClientConnection", set[str]]: ...

class client:
    def __init__(
        self,
        uri: str,
        on_receive: Optional[Callable[[Packet], Awaitable[None]]] = None,
        *,
        ca_cert_path: Optional[str] = None,
    ) -> None: ...
    state: ConnectionState = ConnectionState.DISCONNECTED
    on_receive_callback: Callable[[Packet], Awaitable[None]]
    cert: str
    uri: str

    async def _handler(self) -> None: ...
    async def _connect_once(self, **kwargs) -> None: ...
    async def connect(
        self,
        retry: bool = False,
        max_retry_attempt: int = 3,
        retry_interval: int = 2,
        **kwargs,
    ) -> None: ...
    async def send_rpc(self, method_name: str, *args, **kwargs) -> Self: ...
    async def send(self, data: Union[str | bytes, Packet]) -> None: ...
    async def recv(self, timeout: int | None = 30) -> Packet: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
