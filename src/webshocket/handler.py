import asyncio
import collections
import inspect

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Optional, Set, Dict, Iterable, Union, TypeVar, Generic, cast

from .packets import Packet, PacketSource
from .typing import RPC_Function, RPCMethod, SessionState
from .exceptions import PacketError

if TYPE_CHECKING:
    from .connection import ClientConnection


TState = TypeVar("TState", bound=SessionState)


class WebSocketHandler(Generic[TState]):
    """Defines the interface for handling server-side WebSocket logic."""

    def __init__(self) -> None:
        self.clients: Set["ClientConnection"] = set()
        self.channels: Dict[str, Set["ClientConnection"]] = collections.defaultdict(set)
        self._rpc_methods: Dict[str, RPCMethod] = dict()

        for name, func in inspect.getmembers(self, predicate=callable):
            rpc_alias_name = getattr(func, "_rpc_alias_name", name)

            if not (callable(func) and getattr(func, "_is_rpc_method", False)):
                continue

            # self._rpc_methods[rpc_alias_name] = cast(RPC_Function, func)
            self._rpc_methods[rpc_alias_name] = RPCMethod(
                func=cast(RPC_Function, func),
                rate_limit=getattr(func, "_rate_limit", None),
                restricted=getattr(func, "_restricted", None),
            )

    def register_rpc_method(self, func: RPC_Function, alias_name: Optional[str] = None) -> None:
        """Registers an RPC method with the handler."""

        if not getattr(func, "_is_rpc_method", False):
            raise ValueError("Function is a non-RPC method.")

        rpc_alias_name = alias_name or getattr(func, "_rpc_alias_name", None) or func.__name__

        if rpc_alias_name:
            self._rpc_methods[rpc_alias_name] = RPCMethod(
                func=func,
                rate_limit=getattr(func, "_rate_limit", None),
                restricted=getattr(func, "_restricted", None),
            )

    async def on_connect(self, connection: "ClientConnection[TState]"):
        """(Optional) Called when a new client connects."""
        pass

    async def on_disconnect(self, connection: "ClientConnection[TState]"):
        """(Optional) Called when a client disconnects."""
        pass

    async def on_receive(self, connection: "ClientConnection[TState]", packet: Packet):
        """(Optional) Called when a client sends a packet."""
        pass

    async def broadcast(
        self,
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection", ...]] = None,
        **kwargs,
    ) -> None:
        """Broadcasts a message to all connected clients, with optional exclusions.

        Args:
            data (Union[str, bytes, Packet]): The message data to broadcast.
            exclude (Optional[tuple["ClientConnection"]]): A tuple of client connections
                                                           to exclude from the broadcast. Defaults to None.
        """

        if not self.clients:
            return

        exclude_set = set(exclude if exclude is not None else tuple())

        if not isinstance(data, Packet):
            data = Packet(data=data, source=PacketSource.BROADCAST, **kwargs)

        if data.source != PacketSource.BROADCAST:
            raise PacketError("Cannot broadcast non-broadcast packet.")

        tasks: list[Awaitable[None]] = [client.send(data) for client in self.clients if client not in exclude_set]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def publish(
        self,
        channel: str | Iterable[str],
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection", ...]] = None,
    ) -> None:
        """Publishes a message to all clients subscribed to a specific channel.

        Args:
            channel (str): The name of the channel to publish the message to.
            data (str | bytes | Packet): The message data to publish.
            exclude (Optional[tuple["ClientConnection"]]): A tuple of client connections
                                                           to exclude from the publication. Defaults to None.

        Returns:
            int: The number of clients the message was sent to.
        """
        exclude_set = set(exclude if exclude is not None else tuple())
        channels = {channel} if isinstance(channel, str) else set(channel)

        if isinstance(data, Packet) and data.source != PacketSource.CHANNEL:
            raise PacketError("Cannot publish non-channel packet.")

        for channel in channels:
            packet = Packet(data=data, source=PacketSource.CHANNEL, channel=channel) if not isinstance(data, Packet) else data
            tasks: list[Awaitable[None]] = [client.send(packet) for client in self.channels[channel] if client not in exclude_set]

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def subscribe(self, client: "ClientConnection", channel: str | Iterable) -> None:
        """Subscribes a client to one or more channels.

        Args:
            client (ClientConnection): The client connection to subscribe.
            channel (str | Iterable): The channel name(s) to subscribe the client to.
        """
        channel = {channel} if isinstance(channel, str) else set(channel)

        for channel_name in channel:
            self.channels[channel_name].add(client)

    def unsubscribe(self, client: "ClientConnection", channel: str | Iterable[str]) -> None:
        """Unsubscribes a client from one or more channels.

        Args:
            client (ClientConnection): The client connection to unsubscribe.
            channel (str | Iterable[str]): The channel name(s) to unsubscribe the client from.
        """
        channel = {channel} if isinstance(channel, str) else set(channel)

        for channel_name in channel:
            self.channels[channel_name].discard(client)

            if not self.channels[channel_name]:
                del self.channels[channel_name]


class DefaultWebSocketHandler(WebSocketHandler):
    """A minimal, built-in handler that performs no actions on events.

    This is used as the default by the webshocket.server if no custom
    handler is provided by the user.
    """
