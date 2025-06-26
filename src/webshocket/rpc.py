from __future__ import annotations
import asyncio
from functools import wraps
from typing import Callable, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .handler import WebSocketHandler


def rpc_method(alias_name: Optional[str] = None) -> Callable[..., Any]:
    """
    Decorator to mark a method in a WebSocketHandler as an RPC-callable method.
    When a method is decorated with @rpc_method, it becomes callable by clients
    via RPC requests. The method must be an async function.

    The decorated method will be automatically registered with the handler's
    RPC dispatcher.

    Usage:
        class MyHandler(WebSocketHandler):
            @rpc_method
            async def my_rpc_function(self, connection: ClientConnection, arg1: str, arg2: int):
                # ... implementation ...
                return {"status": "success"}

    Args:
        func (Callable): The asynchronous method to be exposed as an RPC endpoint.

    Returns:
        Callable: The wrapped function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:

        if not asyncio.iscoroutinefunction(func):
            raise TypeError(f"RPC method '{func.__name__}' must be an async function.")

        @wraps(func)
        def wrapper(self: "WebSocketHandler", *args: Any, **kwargs: Any) -> Any:
            return func(self, *args, **kwargs)

        setattr(wrapper, "_is_rpc_method", True)
        setattr(wrapper, "_rpc_alias_name", (alias_name or func.__name__))
        return wrapper

    return decorator
