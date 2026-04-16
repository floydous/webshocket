from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, Protocol, TypeVar, overload

if TYPE_CHECKING:
    from .connection import ClientConnection

P = ParamSpec("P")
R = TypeVar("R")


class RPCDecorator(Protocol):
    @overload
    def __call__(
        self, func: Callable[Concatenate[Any, "ClientConnection", P], R]
    ) -> Callable[Concatenate[Any, "ClientConnection", P], R]: ...

    @overload
    def __call__(self, func: Callable[Concatenate["ClientConnection", P], R]) -> Callable[Concatenate["ClientConnection", P], R]: ...


class RPC_Function(Protocol):
    def __call__(self, connection: "ClientConnection", /, *args: Any, **kwargs: Any) -> Awaitable[Any]: ...
    @property
    def __name__(self) -> str: ...


class RPC_Predicate(Protocol):
    def __call__(self, connection: "ClientConnection") -> bool: ...


class SessionState(Protocol):
    """Defines the interface for session state."""


@dataclass(slots=True, frozen=True)
class RateLimitConfig:
    limit: int
    period: float
    disconnect_on_limit_exceeded: bool


@dataclass(slots=True, frozen=True)
class RPCMethod:
    func: Callable
    rate_limit: RateLimitConfig | None = None
    restricted: RPC_Predicate | None = None
    is_stream: bool = False

    def __repr__(self) -> str:
        return f"RPCMethod(func={self.func.__name__}, rate_limit={self.rate_limit}, restricted={self.restricted})"
