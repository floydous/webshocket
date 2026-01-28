from typing import Any as TAny, TYPE_CHECKING
from .typing import RPC_Predicate

if TYPE_CHECKING:
    from .connection import ClientConnection

_MISSING = object()


class Has:
    """Checks if the connection has a specific state attribute."""

    __slots__ = ("key",)

    def __init__(self, key: str) -> None:
        self.key = key

    def __call__(self, connection: "ClientConnection") -> bool:
        # Check session_state (user/handler state)
        return connection.session_state.get(self.key, _MISSING) is not _MISSING

    def __repr__(self) -> str:
        return f"Has('{self.key}')"


class Is:
    """Checks if the connection has a specific state attribute that is truthy."""

    __slots__ = ("key",)

    def __init__(self, key: str) -> None:
        self.key = key

    def __call__(self, connection: "ClientConnection") -> bool:
        return bool(connection.session_state.get(self.key))

    def __repr__(self) -> str:
        return f"Is('{self.key}')"


class IsEqual:
    """Checks if the connection has a specific state attribute with a matching value."""

    __slots__ = ("key", "value")

    def __init__(self, key: str, value: TAny) -> None:
        self.key = key
        self.value = value

    def __call__(self, connection: "ClientConnection") -> bool:
        return connection.session_state.get(self.key, _MISSING) == self.value

    def __repr__(self) -> str:
        return f"IsEqual('{self.key}', {self.value!r})"


class Any:
    """Logical OR: Returns True if ANY of the provided predicates are True."""

    __slots__ = ("predicates",)

    def __init__(self, *predicates: RPC_Predicate) -> None:
        self.predicates = predicates

    def __call__(self, connection: "ClientConnection") -> bool:
        return any(predicate(connection) for predicate in self.predicates)

    def __repr__(self) -> str:
        return f"Any({', '.join(repr(p) for p in self.predicates)})"


class All:
    """Logical AND: Returns True if ALL of the provided predicates are True."""

    __slots__ = ("predicates",)

    def __init__(self, *predicates: RPC_Predicate) -> None:
        self.predicates = predicates

    def __call__(self, connection: "ClientConnection") -> bool:
        return all(predicate(connection) for predicate in self.predicates)

    def __repr__(self) -> str:
        return f"All({', '.join(repr(p) for p in self.predicates)})"
