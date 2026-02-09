import asyncio
import ssl
from picows import WSTransport

from typing import Optional, Iterable, Union, Any, Callable, Awaitable, Self, TypeVar, Generic
from .handler import WebSocketHandler, DefaultWebSocketHandler
from .typing import RPC_Function, RPC_Predicate
from .connection import ClientConnection
from .packets import Packet, RPCResponse
from .enum import ConnectionState, ServerState
from ._internal import picows_server

H = TypeVar("H", bound=WebSocketHandler)

class server(Generic[H]):
    """
    Represents a WebSocket server that handles incoming connections and messages.

    This class provides functionality to start, manage, and close a WebSocket server,
    integrating with a custom WebSocketHandler for application-specific logic.
    It supports both secure (WSS) and unsecure (WS) connections.
    """

    state: ServerState
    handler: H
    host: str
    port: int
    ssl_context: Optional[ssl.SSLContext]
    max_connection: Optional[int]

    _packet_queue: asyncio.Queue[Packet]

    def __init__(
        self,
        host: str,
        port: int,
        *,
        clientHandler: type[H] = DefaultWebSocketHandler,
        ssl_context: Optional[ssl.SSLContext] = None,
        max_connection: Optional[int] = None,
        packet_qsize: int = 128,
    ) -> None: ...
    def register_rpc_method(self, func: "RPC_Function", alias_name: Optional[str] = None) -> None: ...
    def subscribe(self, client: "ClientConnection", channel: str | Iterable) -> None: ...
    def unsubscribe(self, client: "ClientConnection", channel: str | Iterable) -> None: ...
    def broadcast(
        self,
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection", ...]] = None,
        predicate: Optional[RPC_Predicate] = None,
    ) -> None: ...
    def publish(
        self,
        channel: str | Iterable[str],
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection", ...]] = None,
        predicate: Optional[RPC_Predicate] = None,
    ) -> None: ...
    async def _handler(self, transport: WSTransport, listener: picows_server.ServerClientListener) -> None: ...
    async def accept(self) -> ClientConnection: ...
    async def start(self, *args, **kwargs) -> Self: ...
    async def serve_forever(self, *args, **kwargs) -> None: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
    def __getattr__(self, name: str) -> Any: ...
    @property
    def clients(self) -> set[ClientConnection]: ...
    @property
    def channels(self) -> dict[str, set[ClientConnection]]: ...

class client:
    state: ConnectionState
    on_receive_callback: Optional[Callable[[Packet], Awaitable[None]]]
    ssl_context: Optional[ssl.SSLContext]
    uri: str

    def __init__(
        self,
        uri: str,
        on_receive: Optional[Callable[[Packet], Awaitable[None]]] = None,
        *,
        ssl_context: Optional[ssl.SSLContext] = None,
        max_packet_qsize: int = 128,
    ) -> None: ...
    async def _handler(self) -> None: ...
    async def _connect_once(self, **kwargs) -> None: ...
    async def connect(
        self,
        retry: bool = False,
        max_retry_attempt: int = 3,
        retry_interval: int = 2,
        **kwargs,
    ) -> Self: ...
    async def send_rpc(self, method_name: str, *args, raise_on_rate_limit: bool = False, **kwargs) -> Packet[RPCResponse]: ...
    def send(self, data: Union[Any, Packet]) -> None: ...
    async def recv(self, timeout: int | None = 30) -> Packet: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb): ...
