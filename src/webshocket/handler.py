import collections
import inspect

from typing import TYPE_CHECKING, Optional, Set, Dict, Iterable, Union, TypeVar, Generic, cast

from .packets import Packet, PacketSource
from .typing import RPC_Function, RPC_Predicate, RPCMethod, SessionState
from .exceptions import PacketError

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

    __slots__ = ("clients", "channels", "_rpc_methods")

    def __init__(self) -> None:
        """Initializes the WebSocketHandler."""
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
        pass

    async def on_disconnect(self, connection: "ClientConnection[TState]"):
        """Called when a client disconnects.

        Args:
            connection (ClientConnection[TState]): The connection object for the disconnected client.
        """
        pass

    async def on_receive(self, connection: "ClientConnection[TState]", packet: Packet):
        """Called when a client sends a confirmed packet.

        Args:
            connection (ClientConnection[TState]): The connection object sending the packet.
            packet (Packet): The received data packet.
        """
        pass

    def broadcast(
        self,
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection", ...]] = None,
        predicate: Optional[RPC_Predicate] = None,
        **kwargs,
    ) -> None:
        """Broadcasts a message to all connected clients, with optional exclusions.

        Args:
            data (Union[str, bytes, Packet]): The message data to broadcast.
            exclude (Optional[tuple[ClientConnection, ...]]): A tuple of client connections
                to exclude from the broadcast. Defaults to None.
            **kwargs: Additional arguments to pass to the Packet constructor.

        Raises:
            PacketError: If attempting to broadcast a packet with a source other than PacketSource.BROADCAST.
        """

        if not self.clients:
            return

        exclude_set = set(exclude if exclude is not None else tuple())

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
        data: Union[str | bytes, Packet],
        exclude: Optional[tuple["ClientConnection", ...]] = None,
        predicate: Optional[RPC_Predicate] = None,
    ) -> None:
        """Publishes a message to all clients subscribed to a specific channel.

        Args:
            channel (str | Iterable[str]): The name of the channel(s) to publish the message to.
            data (Union[str, bytes, Packet]): The message data to publish.
            exclude (Optional[tuple[ClientConnection, ...]]): A tuple of client connections
                to exclude from the publication. Defaults to None.

        Raises:
            PacketError: If attempting to publish a packet with a source other than PacketSource.CHANNEL.
        """
        exclude_set = set(exclude if exclude is not None else tuple())
        channels = {channel} if isinstance(channel, str) else set(channel)

        if isinstance(data, Packet) and data.source is not PacketSource.CHANNEL:
            raise PacketError("Cannot publish non-channel packet.")

        for channel in channels:
            packet = Packet(data=data, source=PacketSource.CHANNEL, channel=channel) if not isinstance(data, Packet) else data

            for client in self.channels[channel]:
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
    handler is provided by the user. It simply queues received packets
    for manual retrieval via `accept()`/`recv()`.
    """

    async def on_receive(self, connection: "ClientConnection[TState]", packet: Packet):
        await connection._packet_queue.put(packet)
