import asyncio
import collections

from collections.abc import Awaitable
from typing import (
    TYPE_CHECKING,
    Optional,
    Set,
    Dict,
    Iterable,
    Union,
    Callable,
    Any,
)

from .packets import Packet, PacketSource

if TYPE_CHECKING:
    from .connection import ClientConnection


class WebSocketHandler:
    """Defines the interface for handling server-side WebSocket logic."""

    def __init__(self) -> None:
        self.clients: Set["ClientConnection"] = set()
        self.channels: Dict[str, Set["ClientConnection"]] = collections.defaultdict(set)
        self.reversed_channels: Dict["ClientConnection", Set[str]] = (
            collections.defaultdict(set)
        )
        self._rpc_methods: Dict[str, Callable[..., Any]] = dict()

        for name in dir(self):
            method = getattr(self, name)

            if not (callable(method) and getattr(method, "_is_rpc_method", False)):
                continue

            self._rpc_methods[getattr(method, "_rpc_alias_name", name)] = method

    async def on_connect(self, websocket: "ClientConnection"):
        """(Optional) Called when a new client connects."""
        pass

    async def on_disconnect(self, websocket: "ClientConnection"):
        """(Optional) Called when a client disconnects."""
        pass

    async def on_receive(self, connection: "ClientConnection", packet: Packet):
        pass

    async def broadcast(
        self,
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection"]] = None,
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
            data = Packet(
                data=data,
                source=PacketSource.BROADCAST,
            )

        tasks: list[Awaitable[None]] = [
            client.send(data) for client in self.clients if client not in exclude_set
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def publish(
        self,
        channel: str,
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection"]] = None,
    ) -> int:
        """Publishes a message to all clients subscribed to a specific channel.

        Args:
            channel (str): The name of the channel to publish the message to.
            data (str | bytes | Packet): The message data to publish.
            exclude (Optional[tuple["ClientConnection"]]): A tuple of client connections
                                                           to exclude from the publication. Defaults to None.

        Returns:
            int: The number of clients the message was sent to.
        """
        if self.channels[channel]:
            exclude_set = set(exclude if exclude is not None else tuple())

            if not isinstance(data, Packet):
                data = Packet(
                    data=data,
                    source=PacketSource.CHANNEL,
                    channel=channel,
                )

            tasks: list[Awaitable[None]] = [
                client.send(data)
                for client in self.channels[channel]
                if client not in exclude_set
            ]

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                return len(tasks)

        return 0

    def subscribe(self, client: "ClientConnection", channel: str | Iterable) -> None:
        """Subscribes a client to one or more channels.

        Args:
            client (ClientConnection): The client connection to subscribe.
            channel (str | Iterable): The channel name(s) to subscribe the client to.
        """
        channel = {channel} if isinstance(channel, str) else set(channel)

        for channel_name in channel:
            self.channels[channel_name].add(client)

        self.reversed_channels[client].update(channel)

    def unsubscribe(
        self, client: "ClientConnection", channel: str | Iterable[str]
    ) -> None:
        """Unsubscribes a client from one or more channels.

        Args:
            client (ClientConnection): The client connection to unsubscribe.
            channel (str | Iterable[str]): The channel name(s) to unsubscribe the client from.
        """
        channel = {channel} if isinstance(channel, str) else set(channel)

        self.reversed_channels[client] -= channel

        if not self.reversed_channels[client]:
            del self.reversed_channels[client]

        for channel_name in channel:
            self.channels[channel_name].discard(client)

            if not self.channels[channel_name]:
                del self.channels[channel_name]


class DefaultWebSocketHandler(WebSocketHandler):
    """A minimal, built-in handler that performs no actions on events.

    This is used as the default by the webshocket.server if no custom
    handler is provided by the user.
    """
