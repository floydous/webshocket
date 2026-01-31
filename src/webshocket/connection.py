from webshocket.packets import _json_decoder
from webshocket.packets import _json_encoder
import asyncio
import logging
import msgspec

from uuid import uuid4
from picows import WSCloseCode, WSMsgType, WSTransport
from typing import Any, Iterable, Union, Optional, TYPE_CHECKING, TypeVar, Generic

from .packets import Packet, RPCResponse, serialize, deserialize
from .enum import PacketSource, ConnectionState, ClientType
from .handler import DefaultWebSocketHandler
from .exceptions import ConnectionClosedError, ReceiveTimeoutError

if TYPE_CHECKING:
    from .handler import WebSocketHandler


_MISSING = object()  # Marker for missing attributes
TState = TypeVar("TState")


class ClientConnection(Generic[TState]):
    """Represents a single client connection to the WebSocket server.

    This class wraps the underlying `picows.WSTransport` and provides convenient access structure
    to session-specific state, channel management, and communication methods.
    It supports dynamic attribute access which maps to an internal session state dictionary.

    Attributes:
        client_type (ClientType): The type of client (e.g., FRAMEWORK, GENERIC).
        connection_state (ConnectionState): The current state of the connection (CONNECTED, CLOSED, etc.).
        session_state (dict): A dictionary holding arbitrary user-defined state for this connection.
        uid (UUID): A unique identifier for this connection instance.
        logger (Logger): A logger instance for this connection.
        remote_address (tuple[str, int]): The (host, port) of the connected client.
        subscribed_channel (set[str]): A set of channel names this client is subscribed to.
    """

    __slots__ = (
        "_remote_address",
        "_payload_queue",
        "_packet_queue",
        "_protocol",
        "_handler",
        "client_type",
        "connection_state",
        "session_state",
        "uid",
        "logger",
    )

    def __init__(
        self,
        websocket_protocol: WSTransport,
        handler: "WebSocketHandler",
        client_type: ClientType,
        packet_qsize: int = 128,
    ) -> None:
        """Initializes a new ClientConnection instance.

        This constructor is intended for internal use by the `WebSocketHandler`
        and should not be called directly.

        Args:
            websocket_protocol (WSTransport): The underlying picows transport object.
            handler (WebSocketHandler): The handler instance managing this connection.
            client_type (ClientType): The classification of the connected client.
            packet_qsize (int): The maximum size of the packet queue. Defaults to 128.
        """

        object.__setattr__(self, "_payload_queue", asyncio.Queue[bytes](maxsize=1024))
        object.__setattr__(self, "_packet_queue", asyncio.Queue[Packet](maxsize=packet_qsize))
        object.__setattr__(self, "_protocol", websocket_protocol)
        object.__setattr__(self, "_handler", handler)

        object.__setattr__(self, "client_type", client_type)
        object.__setattr__(self, "connection_state", ConnectionState.CONNECTED)
        object.__setattr__(self, "session_state", dict())
        object.__setattr__(self, "uid", uuid4())
        object.__setattr__(self, "logger", logging.getLogger("webshocket.connection"))

        if TYPE_CHECKING:
            self._protocol: WSTransport

    @property
    def remote_address(self) -> tuple[str, int]:
        """A property that gets the remote address of the connection."""
        try:
            return self._remote_address
        except AttributeError:
            remote_address: tuple[str, int] = self._protocol.underlying_transport.get_extra_info("peername")

            object.__setattr__(self, "_remote_address", remote_address)
            return self._remote_address

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

    def send(self, data: Union[Any, Packet], chunk_size: int = 1024 * 64) -> None:
        """Sends data over the connection.

        This is method ensures all data is sent in a structured Packet format.

        - If given a Pydantic `Packet` object, it serializes and sends it.
        - If given a raw `str` or `bytes`, it automatically wraps it in a
          default `Packet` before serializing and sending.
        """

        packet: Packet = data

        if not isinstance(data, Packet):
            packet = Packet(
                data=data,
                source=PacketSource.CUSTOM,
                channel=None,
            )

        if self.client_type is ClientType.FRAMEWORK:
            response = serialize(packet)
        else:
            response = _json_encoder.encode(packet)

        if len(response) <= chunk_size:
            self._protocol.send(WSMsgType.BINARY, response)
            return

        # ---------------------------------------------------------

        payload = memoryview(response)
        payload_length = len(payload)
        offset = chunk_size

        self._protocol.send(WSMsgType.BINARY, payload[:chunk_size], fin=False)

        while offset + chunk_size < payload_length:
            self._protocol.send(
                WSMsgType.CONTINUATION,
                payload[offset : offset + chunk_size],
                fin=False,
            )

            offset += chunk_size

        self._protocol.send(
            WSMsgType.CONTINUATION,
            payload[offset:],
            fin=True,
        )

    def _send_rpc_response(self, rpc_response: "RPCResponse") -> None:
        """
        Sends an RPC response back to the client.

        Args:
            rpc_response (RPCResponse): The RPC response object to send.
        """

        packet = Packet(
            source=PacketSource.RPC,
            rpc=rpc_response,
        )

        self.send(packet)

    async def recv(self, timeout: Optional[float] = 30.0) -> Packet:
        """Receives the next message and parses it into a validated Packet object.

        This method receives the incoming data from the client and parse it into
        a validated Packet object, if the data is raw, meaning it's coming outside
        of the client module, the data will be wrapped with the source of Packet
        set to CUSTOM.

        Args:
            timeout: Max seconds to wait for a message. Defaults to 30.

        Raises:
            ConnectionError: If the client is not connected.
            TimeoutError: If no message is received within the timeout period.
            MessageError: If the received data fails to parse as a valid Packet.

        Returns:
            A validated Packet object.
        """

        # if self.on_receive_callback:
        #     raise TypeError("Cannot use manual recv() when an on_receive callback is active.")
        packet: Packet

        if not self._protocol or self.connection_state is ConnectionState.DISCONNECTED:
            raise ConnectionClosedError("Cannot receive data: client is not connected.")

        try:
            if isinstance(self._handler, DefaultWebSocketHandler):
                packet = await self._packet_queue.get()
                return packet

            raw_data = await asyncio.wait_for(self._payload_queue.get(), timeout=timeout)

            try:
                if self.client_type is ClientType.FRAMEWORK:
                    packet = deserialize(raw_data)
                else:
                    packet = _json_decoder.decode(raw_data)

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

    def close(self, code: WSCloseCode = WSCloseCode.OK, reason: bytes = b"") -> None:
        """Closes the connection."""

        object.__setattr__(self, "connection_state", ConnectionState.CLOSED)
        self._protocol.send_close(code, reason)
        self._protocol.disconnect()

    async def __aiter__(self):
        while self.connection_state != ConnectionState.CLOSED:
            payload = await self._payload_queue.get()

            if payload is None:
                break

            yield payload

        raise ConnectionClosedError

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
