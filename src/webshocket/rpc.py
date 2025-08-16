import asyncio
import time

from functools import wraps
from typing import Callable, Any, Optional, TYPE_CHECKING
from collections import defaultdict

from .enum import TimeUnit

if TYPE_CHECKING:
    from .handler import WebSocketHandler
    from .connection import ClientConnection


def rpc_method(
    alias_name: Optional[str] = None, requires: Optional[Callable[["ClientConnection"], bool]] = None
) -> Callable[..., Any]:
    """
    Decorator to mark a method in a WebSocketHandler as an RPC-callable method.
    When a method is decorated with @rpc_method, it becomes callable by clients
    via RPC requests. The method must be an async function.

    The decorated method will be automatically registered with the handler's
    RPC dispatcher.

    Usage:
        class MyHandler(WebSocketHandler):
            @rpc_method(alias_name="my_rpc_function", requires=lambda connection: connection.is_admin)
            async def my_rpc(self, connection: ClientConnection, arg1: str, arg2: int):
                # ... implementation ...
                return True

    Args:
        alias_name (Optional[str]): An alias name for the RPC method.
        requires (Optional[Callable[[ClientConnection], bool]]): A function that returns
            True if the client connection is allowed to call the method, False otherwise.

    Returns:
        Callable: The wrapped function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"RPC method '{func.__name__}' must be an async function.")

        @wraps(func)
        async def wrapper(self: "WebSocketHandler", *args: Any, **kwargs: Any) -> Any:
            return await func(self, *args, **kwargs)

        setattr(wrapper, "_rpc_alias_name", (alias_name or func.__name__))
        setattr(wrapper, "_restricted", requires)
        setattr(wrapper, "_is_rpc_method", True)
        return wrapper

    return decorator


def rate_limit(
    limit: int,
    unit: TimeUnit,
    *,
    key: Callable[["ClientConnection"], Any] = lambda connection: getattr(connection, "uid"),
) -> Callable[..., Any]:
    """
    Decorator to mark a method in a WebSocketHandler as a rate-limited method.
    This decorator is used to limit the number of times a method can be called
    within a certain period of time.

    Usage:
        class MyHandler(WebSocketHandler):
            @rate_limit(limit=5, unit="MINUTE", key=lambda connection: connection.client_id)
            async def on_receive(self, connection: ClientConnection):
                ...

    Args:
        limit (int): The maximum number of times the method can be called within the specified time unit.
        unit (TimeUnit): The time unit for the rate limit.
        key (Callable[[ClientConnection]]): A function that takes a ClientConnection object as input and returns
                                           a unique key for the rate limit.

    Returns:
        Callable: The wrapped function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"RPC method '{func.__name__}' must be an async function.")

        @wraps(func)
        async def wrapper(self: "WebSocketHandler", *args: Any, **kwargs: Any) -> Any:
            return await func(self, *args, **kwargs)

        setattr(wrapper, "_rate_limit", (limit, unit, key))
        setattr(
            wrapper,
            "_list_client",
            defaultdict(
                lambda: {
                    "count": 0,
                    "last_called": time.time(),
                }
            ),
        )
        return wrapper

    return decorator
