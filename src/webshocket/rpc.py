import inspect
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, cast

from .typing import RateLimitConfig, RPCDecorator
from .utils import parse_duration

if TYPE_CHECKING:
    from .handler import WebSocketHandler


def rpc_method(alias_name: str | None = None, requires: Any | None = None) -> RPCDecorator:
    """
    Decorator to mark a function as an RPC method in a WebSocketHandler.

    Usage:
        class MyHandler(WebSocketHandler):
            @rpc_method()
            async def my_method(self, connection: ClientConnection, data: Any):
                ...

            @rpc_method(alias_name="custom-name")
            async def another_method(self, connection: ClientConnection):
                ...

            @webshocket.rpc_method(requires=webshocket.IsEqual("admin", True))
            async def admin_only(self, connection: webshocket.ClientConnection):
                ...

    Args:
        alias_name (str | None): Optional alias to expose the method under a different name.
        requires (Any | None): Optional permission or requirement for the method.

    Returns:
        RPCDecorator: The decorator function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if not params:
            raise TypeError(
                f"'{func.__name__}' must accept at least one parameter for the client connection."
            )

        is_method = params[0].name == "self"
        min_required = 2 if is_method else 1

        if len(params) < min_required:
            expected = "('self', connection_obj, ...)" if is_method else "(connection_obj, ...)"
            raise TypeError(f"'{func.__name__}' must accept at least {min_required} parameters: {expected}")

        is_asyncgenfunction = inspect.isasyncgenfunction(func)
        if not (inspect.iscoroutinefunction(func) or is_asyncgenfunction):
            raise TypeError(f"RPC method '{func.__name__}' must be an async function.")

        if is_asyncgenfunction:

            @wraps(func)
            async def async_gen_wrapper(*args: Any, **kwargs: Any) -> Any:
                async for chunk in func(*args, **kwargs):
                    yield chunk

            wrapper = async_gen_wrapper
        else:

            @wraps(func)
            async def regular_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await func(*args, **kwargs)

            wrapper = regular_wrapper

        wrapper.__dict__["_rpc_alias_name"] = alias_name or func.__name__
        wrapper.__dict__["_is_stream"] = is_asyncgenfunction
        wrapper.__dict__["_restricted"] = requires
        wrapper.__dict__["_is_rpc_method"] = True

        return wrapper

    return cast(RPCDecorator, decorator)


def rate_limit(
    *,
    limit: int,
    period: str = "1s",
    disconnect_on_limit_exceeded: bool = False,
) -> Callable[..., Any]:
    """
    Decorator to mark a method in a WebSocketHandler as a rate-limited method.
    This decorator is used to limit the number of times a method can be called
    within a certain period of time.

    Usage:
        class MyHandler(WebSocketHandler):
            @rate_limit(limit=5, period="1m") # 5 calls per minute
            async def on_receive(self, connection: ClientConnection):
                ...

    Args:
        limit (int): The maximum number of times the method can be called within the specified time unit.
        period (str): The time unit for the rate limit.
        disconnect_on_limit_exceeded (bool): Whether to disconnect the client when the rate limit is exceeded.

    Returns:
        Callable: The wrapped function.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not (inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func)):
            raise TypeError(f"RPC method '{func.__name__}' must be an async function.")

        if inspect.isasyncgenfunction(func):

            @wraps(func)
            async def wrapper(self: "WebSocketHandler", *args: Any, **kwargs: Any) -> Any:
                async for chunk in func(self, *args, **kwargs):
                    yield chunk
        else:

            @wraps(func)
            async def wrapper(self: "WebSocketHandler", *args: Any, **kwargs: Any) -> Any:
                return await func(self, *args, **kwargs)

        wrapper.__dict__["_rate_limit"] = RateLimitConfig(
            limit=limit,
            period=parse_duration(period),
            disconnect_on_limit_exceeded=disconnect_on_limit_exceeded,
        )

        return wrapper

    return decorator
