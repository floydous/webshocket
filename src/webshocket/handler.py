import fnmatch
import inspect
import re
from collections import defaultdict
from collections.abc import Iterable
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
    cast,
)

from .exceptions import PacketError
from .packets import Packet, PacketSource
from .typing import RPC_Function, RPC_Predicate, RPCMethod, SessionState, Serializable

if TYPE_CHECKING:
    from .connection import ClientConnection


TState = TypeVar("TState", bound=SessionState)


class WebSocketHandler(Generic[TState]):
    """Defines the interface for handling server-side WebSocket logic.

    This class serves as the base for implementing custom application logic.
    Subclasses should override the lifecycle methods (`on_connect`, `on_receive`, `on_disconnect`)
    to handle WebSocket events.

    Attributes:
        clients (Set[ClientConnection]): A set of all currently connected clients managed by this handler.
        channels (Dict[str, Set[ClientConnection]]): A dictionary mapping channel names to sets of subscribed clients.

    """

    __slots__ = ("_compiled_patterns", "_pattern_cache", "_rpc_methods", "channels", "clients", "patterns")

    def __init__(self) -> None:
        """Initializes the WebSocketHandler."""
        self.clients: set[ClientConnection] = set()
        self.channels: dict[str, set[ClientConnection]] = defaultdict(set)
        self.patterns: dict[str, set[ClientConnection]] = defaultdict(set)
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._pattern_cache: dict[str, list[str]] = {}

        self._rpc_methods: dict[str, RPCMethod] = {}

        for name, func in inspect.getmembers(self, predicate=callable):
            rpc_alias_name = getattr(func, "_rpc_alias_name", name)

            if not (callable(func) and getattr(func, "_is_rpc_method", False)):
                continue

            self._rpc_methods[rpc_alias_name] = RPCMethod(
                func=cast("RPC_Function", func),
                rate_limit=getattr(func, "_rate_limit", None),
                restricted=getattr(func, "_restricted", None),
                is_stream=getattr(func, "_is_stream", False),
            )

    def register_rpc_method(self, func: RPC_Function, alias_name: str | None = None) -> None:
        """Registers a function as an RPC method dynamically.

        Args:
            func (RPC_Function): The function to register. Must be marked with `@rpc_method`.
            alias_name (Optional[str]): An optional alias for the method name.
                                        If provided, the client will use this name to call the method.

        Raises:
            ValueError: If the function is not marked as an RPC method.

        """
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
        """Called when a new client connects (after handshake).

        Args:
            connection (ClientConnection[TState]): The connection object for the new client.

        """

    async def on_disconnect(self, connection: "ClientConnection[TState]"):
        """Called when a client disconnects.

        Args:
            connection (ClientConnection[TState]): The connection object for the disconnected client.

        """

    async def on_receive(self, connection: "ClientConnection[TState]", packet: Packet):
        """Called when a client sends a confirmed packet.

        Args:
            connection (ClientConnection[TState]): The connection object sending the packet.
            packet (Packet): The received data packet.

        """

    def broadcast(
        self,
        data: Serializable,
        exclude: tuple["ClientConnection", ...] | None = None,
        predicate: RPC_Predicate | None = None,
        **kwargs,
    ) -> None:
        """Broadcasts a message to all connected clients, with optional exclusions.

        Args:
            data (Serializable): The message data to broadcast.
            exclude (Optional[tuple[ClientConnection, ...]]): A tuple of client connections
                to exclude from the broadcast. Defaults to None.
            **kwargs: Additional arguments to pass to the Packet constructor.

        Raises:
            PacketError: If attempting to broadcast a packet with a source other than PacketSource.BROADCAST.

        """
        if not self.clients:
            return

        exclude_set = set(exclude) if exclude else set()

        if not isinstance(data, Packet):
            data = Packet(data=data, source=PacketSource.BROADCAST, **kwargs)

        if data.source != PacketSource.BROADCAST:
            raise PacketError("Cannot broadcast non-broadcast packet.")

        for client in self.clients:
            if client in exclude_set:
                continue

            if predicate and not predicate(client):
                continue

            client.send(data)

    def publish(
        self,
        channel: str | Iterable[str],
        data: Serializable,
        exclude: tuple["ClientConnection", ...] | None = None,
        predicate: RPC_Predicate | None = None,
    ) -> None:
        """Publishes a message to all clients subscribed to a specific channel.

        Args:
            channel (str | Iterable[str]): The name of the channel(s) to publish the message to.
            data (Serializable): The message data to publish.
            exclude (Optional[tuple[ClientConnection, ...]]): A tuple of client connections
                to exclude from the publication. Defaults to None.

        Raises:
            PacketError: If attempting to publish a packet with a source other than PacketSource.CHANNEL.

        """
        exclude_set = set(exclude if exclude is not None else ())
        channels = {channel} if isinstance(channel, str) else set(channel)

        if isinstance(data, Packet) and data.source is not PacketSource.CHANNEL:
            raise PacketError("Cannot publish non-channel packet.")

        for channel in channels:
            packet = Packet(data=data, source=PacketSource.CHANNEL, channel=channel) if not isinstance(data, Packet) else data

            recipients: set[ClientConnection] = set()
            recipients.update(self.channels.get(channel, ()))

            for pattern in self._get_matching_patterns(channel):
                recipients.update(self.patterns.get(pattern, ()))

            for client in recipients:
                if client in exclude_set:
                    continue

                if predicate and not predicate(client):
                    continue

                client.send(packet)

    def subscribe(self, client: "ClientConnection", channel: str | Iterable) -> None:
        """Subscribes a client to one or more channels.

        Args:
            client (ClientConnection): The client connection to subscribe.
            channel (str | Iterable): The channel name(s) to subscribe the client to.

        """
        channel = {channel} if isinstance(channel, str) else set(channel)

        for channel_name in channel:
            if any(char in channel_name for char in "*?[]"):
                if channel_name not in self._compiled_patterns:
                    re_compiled = re.compile(fnmatch.translate(channel_name))
                    self._compiled_patterns[channel_name] = re_compiled
                    self._pattern_cache.clear()

                self.patterns[channel_name].add(client)
            else:
                self.channels[channel_name].add(client)

            client._subscribed_channels.add(channel_name)

    def unsubscribe(self, client: "ClientConnection", channel: str | Iterable[str]) -> None:
        """Unsubscribes a client from one or more channels.

        Args:
            client (ClientConnection): The client connection to unsubscribe.
            channel (str | Iterable[str]): The channel name(s) to unsubscribe the client from.

        """
        channel = {channel} if isinstance(channel, str) else set(channel)

        for channel_name in channel:
            if channel_name in self.channels:
                self.channels[channel_name].discard(client)

                if not self.channels[channel_name]:
                    del self.channels[channel_name]

            elif channel_name in self.patterns:
                self.patterns[channel_name].discard(client)

                if not self.patterns[channel_name]:
                    del self.patterns[channel_name]
                    self._compiled_patterns.pop(channel_name, None)
                    self._pattern_cache.clear()

            client._subscribed_channels.discard(channel_name)

    def _get_matching_patterns(self, channel: str) -> list[str]:
        if channel in self._pattern_cache:
            return self._pattern_cache[channel]

        result = [p for p, regex in self._compiled_patterns.items() if regex.match(channel)]
        self._pattern_cache[channel] = result
        return result


class DefaultWebSocketHandler(WebSocketHandler):
    """A minimal, built-in handler that performs no actions on events.

    This is used as the default by the webshocket.server if no custom
    handler is provided by the user. It simply queues received packets
    for manual retrieval via `accept()`/`recv()`.
    """

    async def on_receive(self, connection: "ClientConnection[TState]", packet: Packet):
        await connection._packet_queue.put(packet)
