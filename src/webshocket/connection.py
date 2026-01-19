import asyncio
import logging
import msgspec

from uuid import uuid4
from websockets import ServerConnection
from typing import Any, Iterable, Union, Optional, cast, TYPE_CHECKING, TypeVar, Generic

from .packets import Packet, RPCResponse, serialize, deserialize
from .enum import PacketSource, ConnectionState
from .typing import DEFAULT_WEBSHOCKET_SUBPROTOCOL
from .handler import DefaultWebSocketHandler
from .exceptions import ConnectionClosedError, ReceiveTimeoutError

if TYPE_CHECKING:
    from .handler import WebSocketHandler


_MISSING = object()  # Marker for missing attributes
TState = TypeVar("TState")


class ClientConnection(Generic[TState]):
    """Represents a single client connection to the WebSocket server.

    This class wraps the underlying `websockets.ServerConnection` and provides
    convenient access to session-specific state and channel management.
    It allows setting and getting attributes dynamically, which are stored
    in an internal `session_state` dictionary.
    """

    __slots__ = (
        "_packet_queue",
        "_protocol",
        "_handler",
        "connection_state",
        "session_state",
        "uid",
        "logger",
    )

    def __init__(self, websocket_protocol: ServerConnection, handler: "WebSocketHandler", packet_qsize: int = 1) -> None:
        """
        Initializes a new ClientConnection instance.

        This constructor sets the internal attributes for the connection and should
        not be called directly by the user. It is called by the WebSocketHandler.

        Args:
            websocket_protocol (ServerConnection): The underlying WebSocket protocol object for the connection.
            handler (WebSocketHandler): The handler instance that manages this connection.
        """

        object.__setattr__(self, "_packet_queue", asyncio.Queue[Packet](maxsize=packet_qsize))
        object.__setattr__(self, "_protocol", websocket_protocol)
        object.__setattr__(self, "_handler", handler)

        object.__setattr__(self, "connection_state", ConnectionState.CONNECTED)
        object.__setattr__(self, "session_state", dict())
        object.__setattr__(self, "uid", uuid4())
        object.__setattr__(self, "logger", logging.getLogger("webshocket.connection"))

    @property
    def subscribed_channel(self) -> set[str]:
        """A property that gets the authoritative list of channels from the handler.

        Returns:
            A set of channel names that the client is subscribed to.
        """

        subscribed_channel = set()

        for channel_name, client_list in self._handler.channels.items():
            if self not in client_list:
                continue

            subscribed_channel.add(channel_name)

        return subscribed_channel

    async def send(self, data: Union[Any, Packet]) -> None:
        """Sends data over the connection.

        This is method ensures all data is sent in a structured Packet format.

        - If given a Pydantic `Packet` object, it serializes and sends it.
        - If given a raw `str` or `bytes`, it automatically wraps it in a
          default `Packet` before serializing and sending.
        """

        packet: Packet

        if isinstance(data, Packet):
            packet = data

        else:
            packet = Packet(
                data=data,
                source=PacketSource.CUSTOM,
                channel=None,
            )

        await self._protocol.send(serialize(packet))

    async def _send_rpc_response(self, rpc_response: "RPCResponse") -> None:
        """
        Sends an RPC response back to the client.

        Args:
            rpc_response (RPCResponse): The RPC response object to send.
        """

        packet = Packet(
            source=PacketSource.RPC,
            rpc=rpc_response,
        )

        await self._protocol.send(
            serialize(packet) if self._protocol.subprotocol == DEFAULT_WEBSHOCKET_SUBPROTOCOL else msgspec.json.encode(packet)
        )

    async def recv(self, timeout: Optional[float] = 30.0) -> Packet:
        """Receives the next message and parses it into a validated Packet object.

        This method receives the incoming data from the client and parse it into
        a validated Packet object, if the data is raw, meaning it's coming outside
        of the client module, the data will be wrapped with the source of Packet
        set to CUSTOM.

        Args:
            timeout: Max seconds to wait for a message. Defaults to 30.

        Raises:
            TypeError: If an on_receive_callback is active.
            ConnectionError: If the client is not connected.
            TimeoutError: If no message is received within the timeout period.
            MessageError: If the received data fails to parse as a valid Packet.

        Returns:
            A validated Packet object.
        """

        # if self.on_receive_callback:
        #     raise TypeError("Cannot use manual recv() when an on_receive callback is active.")
        packet: Packet

        if not self._protocol or self.connection_state == ConnectionState.DISCONNECTED:
            raise ConnectionClosedError("Cannot receive data: client is not connected.")

        try:
            if isinstance(self._handler, DefaultWebSocketHandler):
                packet = await self._packet_queue.get()
                return packet

            self._protocol: ServerConnection
            raw_data = await asyncio.wait_for(self._protocol.recv(), timeout=timeout)
            raw_data = cast(bytes, raw_data)

            try:
                if self._protocol.subprotocol == DEFAULT_WEBSHOCKET_SUBPROTOCOL:
                    packet = deserialize(raw_data, Packet)
                else:
                    # packet = Packet.model_validate_json(raw_data)
                    packet = msgspec.json.decode(raw_data, type=Packet)

            except (msgspec.ValidationError, msgspec.DecodeError, TypeError) as e:
                self.logger.debug("Failed to decode packet from %s: %s", self.remote_address, e)
                packet = Packet(
                    data=raw_data,
                    source=PacketSource.UNKNOWN,
                    channel=None,
                )

            return packet

        except asyncio.TimeoutError:
            raise ReceiveTimeoutError(f"Receive operation timed out after {timeout} seconds.") from None

    def subscribe(self, channel: Union[str, Iterable[str]]) -> None:
        """A shortcut method for this connection to join one or more channels.

        Args:
            channel: A string or iterable that contains lists of channel to join.
        """
        self._handler.subscribe(self, channel)

    def unsubscribe(self, channel: Union[str, Iterable[str]]) -> None:
        """A shortcut method for this connection to leave one or more channels.

        Args:
            channel: A string or iterable that contains lists of channel to leave."""
        self._handler.unsubscribe(self, channel)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Closes the connection."""

        await self._protocol.close(code=code, reason=reason)
        object.__setattr__(self, "connection_state", ConnectionState.CLOSED)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Called when setting an attribute. All assignments are redirected
        to the session_state dictionary.
        """
        session_state = object.__getattribute__(self, "session_state")
        session_state[name] = value

    def __getattr__(self, name: str) -> Any:
        """Called when reading `session_state` via `connection._example_data`

        Called when getting an attribute. The lookup order is:
            1. Check the session_state dictionary.
            2. Check the underlying websocket protocol object.
            3. Raise an AttributeError if not found anywhere.
        """
        session_state: dict = object.__getattribute__(self, "session_state")

        if (value := session_state.get(name, _MISSING)) is not _MISSING:
            return value

        if (value := getattr(self._protocol, name, _MISSING)) is not _MISSING:
            return value

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'") from None

    def __delattr__(self, name: str) -> None:
        """Called when deleting an attribute (e.g., `del connection.username`)."""

        if name in object.__getattribute__(self, "session_state"):
            del object.__getattribute__(self, "session_state")[name]
        else:
            super().__delattr__(name)

    def __setitem__(self, name: str, value: Any) -> None:
        """Allows setting state via `connection['key'] = value`."""
        self.__setattr__(name, value)

    def __delitem__(self, name: str) -> None:
        """Allows deleting state via `del connection['key']`."""
        self.__delattr__(name)

    # --- The missing piece ---
    def __getitem__(self, name: str) -> Any:
        """Allows reading state via `value = connection['key']`."""
        try:
            return self.__getattr__(name)
        except AttributeError:
            # Raise a KeyError for dictionary-style access, which is the expected behavior.
            raise KeyError(name) from None

    def __repr__(self) -> str:
        """Returns a string representation of the ClientConnection object."""
        return f"<{type(self).__name__}(uid={self.uid}, remote_address='{self.remote_address}', session_state={self.session_state})>"

    def __hash__(self):
        """Returns a hash value for the ClientConnection object."""
        return hash(self._protocol)

    def __eq__(self, other):
        """Returns True if the ClientConnection's underlying protocol object are equal."""
        return isinstance(other, ClientConnection) and self._protocol == other._protocol
