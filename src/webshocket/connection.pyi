from collections.abc import AsyncIterator, Iterable
from typing import Any, Generic, TypeVar
from uuid import UUID

from picows import WSCloseCode, WSTransport

from .enum import ClientType, ConnectionState
from .handler import SessionState, WebSocketHandler
from .packets import Packet, RPCResponse
from .typing import Serializable
from .constant import DEFAULT_CHUNK_SIZE

_TState = TypeVar("_TState", bound=SessionState)

class ClientConnection(Generic[_TState]):
    __slots__ = (
        "_handler",
        "_packet_queue",
        "_payload_queue",
        "_protocol",
        "_remote_address",
        "_subscribed_channels",
        "client_type",
        "connection_state",
        "logger",
        "max_subscribed_channels",
        "session_state",
        "uid",
    )

    _protocol: WSTransport
    client_type: ClientType
    session_state: _TState
    connection_state: ConnectionState
    max_subscribed_channels: int
    uid: UUID
    logger: Any

    def __init__(
        self,
        websocket_protocol: WSTransport,
        handler: WebSocketHandler,
        client_type: ClientType = ...,
        packet_qsize: int = 128,
        max_subscribed_channels: int = 5,
    ) -> None: ...
    @property
    def subscribed_channel(self) -> set[str]: ...
    def send(self, data: Serializable, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None: ...
    def _send_rpc_response(self, rpc_response: RPCResponse) -> None: ...
    async def recv(self, timeout: float | None = 30.0) -> Packet: ...
    def subscribe(self, channel: str | Iterable[str]) -> None: ...
    def unsubscribe(self, channel: str | Iterable[str]) -> None: ...
    def close(self, code: WSCloseCode = ..., reason: bytes = b"") -> None: ...
    def __aiter__(self) -> AsyncIterator[bytes]: ...
    def __setattr__(self, name: str, value: Any) -> None: ...
    def __getattr__(self, name: str) -> Any: ...
    def __delattr__(self, name: str) -> None: ...
    def __setitem__(self, name: str, value: Any) -> None: ...
    def __getitem__(self, name: str) -> Any: ...
    def __delitem__(self, name: str) -> None: ...
    def __hash__(self) -> int: ...
    def __eq__(self, other: object) -> bool: ...
