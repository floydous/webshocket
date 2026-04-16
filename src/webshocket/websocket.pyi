import asyncio
import ssl
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable
from typing import (
    Any,
    Generic,
    Self,
    TypeVar,
)

from picows import WSTransport

from ._internal import picows_server
from .connection import ClientConnection
from .enum import ConnectionState, ServerState
from .handler import WebSocketHandler
from .packets import Packet, RPCResponse
from .typing import RPC_Function, RPC_Predicate, Serializable

H = TypeVar("H", bound=WebSocketHandler)

class server(Generic[H]):
    """Represents a WebSocket server that handles incoming connections and messages.

    This class provides functionality to start, manage, and close a WebSocket server,
    integrating with a custom WebSocketHandler for application-specific logic.
    It supports both secure (WSS) and unsecure (WS) connections.
    """

    state: ServerState
    handler: H
    host: str
    port: int
    ssl_context: ssl.SSLContext | None
    max_connection: int | None

    _packet_queue: asyncio.Queue[Packet]

    def __init__(
        self,
        host: str,
        port: int,
        *,
        clientHandler: type[H] = ...,
        ssl_context: ssl.SSLContext | None = None,
        max_connection: int | None = None,
        packet_qsize: int = 512,
        rpc_task_limit: int = 1024,
    ) -> None: ...
    def register_rpc_method(self, func: RPC_Function, alias_name: str | None = None) -> None: ...
    def subscribe(self, client: ClientConnection, channel: str | Iterable[str]) -> None: ...
    def unsubscribe(self, client: ClientConnection, channel: str | Iterable[str]) -> None: ...
    def broadcast(
        self,
        data: Serializable,
        exclude: tuple[ClientConnection, ...] | None = None,
        predicate: RPC_Predicate | None = None,
    ) -> None: ...
    def publish(
        self,
        channel: str | Iterable[str],
        data: Serializable,
        exclude: tuple[ClientConnection, ...] | None = None,
        predicate: RPC_Predicate | None = None,
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
    on_receive_callback: Callable[[Packet], Awaitable[None]] | None
    ssl_context: ssl.SSLContext | None
    uri: str

    def __init__(
        self,
        uri: str,
        on_receive: Callable[[Packet], Awaitable[None]] | None = None,
        *,
        ssl_context: ssl.SSLContext | None = None,
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
    async def send_rpc(
        self,
        method_name: str,
        /,
        *args,
        raise_on_rate_limit: bool = False,
        **kwargs,
    ) -> RPCResponse: ...
    def stream_rpc(
        self,
        method_name: str,
        /,
        *args,
        raise_on_rate_limit: bool = True,
        **kwargs,
    ) -> AsyncGenerator[RPCResponse]: ...
    def send(self, data: Serializable) -> None: ...
    async def recv(self, timeout: float | None = 30) -> Packet: ...
    async def close(self) -> None: ...
    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
