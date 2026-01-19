from typing import Callable, Optional, TypedDict, Any, Awaitable, Protocol, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .connection import ClientConnection

DEFAULT_WEBSHOCKET_SUBPROTOCOL = "webshocket.v1"


class RPC_Function(Protocol):
    def __call__(self, connection: "ClientConnection", /, *args: Any, **kwargs: Any) -> Awaitable[Any]: ...
    @property
    def __name__(self) -> str: ...


class RPC_Predicate(Protocol):
    def __call__(self, connection: "ClientConnection") -> bool: ...


class SessionState(Protocol):
    """
    Defines the interface for session state.
    """

    pass


@dataclass(frozen=True)
class RateLimitConfig:
    limit: int
    period: float
    disconnect_on_limit_exceeded: bool


@dataclass(slots=True, frozen=True)
class RPCMethod:
    func: Callable
    rate_limit: Optional[RateLimitConfig] = None
    restricted: Optional[RPC_Predicate] = None

    def __repr__(self) -> str:
        return f"RPCMethod(func={self.func.__name__}, rate_limit={self.rate_limit}, restricted={self.restricted})"


class CertificatePaths(TypedDict):
    """A TypedDict defining the structure for SSL/TLS certificate paths.

    Attributes:
        cert_path (str): The file path to the SSL certificate.
        key_path (str): The file path to the SSL key.
    """

    cert_path: str
    key_path: str
