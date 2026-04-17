import asyncio
import logging
from collections.abc import AsyncGenerator, Iterable
from typing import TYPE_CHECKING, Any, Generic, TypeVar
from uuid import uuid4

import msgspec
from picows import WSCloseCode, WSMsgType, WSTransport

from webshocket.packets import _json_decoder, _json_encoder

from .constant import DEFAULT_CHUNK_SIZE, DEFAULT_ENCODE_BUFFER_SIZE
from .enum import ClientType, ConnectionState, PacketSource
from .exceptions import ConnectionClosedError, ReceiveTimeoutError
from .handler import DefaultWebSocketHandler
from .packets import Packet, RPCResponse, _encoder, deserialize
from .typing import Serializable

if TYPE_CHECKING:
    from .handler import WebSocketHandler


_MISSING = object()  # Marker for missing attributes
TState = TypeVar("TState")


class ClientConnection(Generic[TState]):
    """Represents a single client connection to the WebSocket server.

    This class wraps the underlying `picows.WSTransport` and provides convenient access structure
    to session-specific state, channel management, and communication methods.
    It supports dynamic attribute access which maps to an internal session state dictionary.

    .. code-block:: python

        async def on_receive(self, connection: ClientConnection, packet: Packet):
            # Access session state directly
            connection.username = "alice"

            # Subscribe to a channel
            connection.subscribe("chat-room")

            # Send data
            connection.send({"status": "ok"})

    Attributes:
        client_type (ClientType): The type of client (e.g., FRAMEWORK, GENERIC).
        connection_state (ConnectionState): The current state of the connection (CONNECTED, CLOSED, etc.).
        session_state (dict): A dictionary holding arbitrary user-defined state for this connection.
        max_subscribed_channels (int): The maximum number of channels this client can subscribe to.
        uid (UUID): A unique identifier for this connection instance.
        logger (Logger): A logger instance for this connection.
        remote_address (tuple[str, int]): The (host, port) of the connected client.
        subscribed_channel (set[str]): A set of channel names this client is subscribed to.

    """

    __slots__ = (
        "_active_stream",
        "_encode_buffer",
        "_handler",
        "_packet_queue",
        "_payload_queue",
        "_protocol",
        "_remote_address",
        "_subscribed_channels",
        "client_type",
        "connection_state",
        "logger",
        "max_subscribed_channels",
        "session_state",
        "uid",
    )

    def __init__(
        self,
        websocket_protocol: WSTransport,
        handler: "WebSocketHandler",
        client_type: ClientType,
        packet_qsize: int = 128,
        max_subscribed_channels: int = 5,
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
        object.__setattr__(self, "_subscribed_channels", set())
        object.__setattr__(self, "_payload_queue", asyncio.Queue[bytes](maxsize=1024))
        object.__setattr__(self, "_packet_queue", asyncio.Queue[Packet](maxsize=packet_qsize))
        object.__setattr__(self, "_active_stream", {})
        object.__setattr__(self, "_encode_buffer", bytearray(DEFAULT_ENCODE_BUFFER_SIZE))
        object.__setattr__(self, "_protocol", websocket_protocol)
        object.__setattr__(self, "_handler", handler)

        object.__setattr__(self, "client_type", client_type)
        object.__setattr__(self, "connection_state", ConnectionState.CONNECTED)
        object.__setattr__(self, "session_state", {})
        object.__setattr__(self, "uid", uuid4())
        object.__setattr__(self, "logger", logging.getLogger("webshocket.connection"))
        object.__setattr__(self, "max_subscribed_channels", max_subscribed_channels)

        if TYPE_CHECKING:
            self._protocol: WSTransport
            self.max_subscribed_channels: int
            self._subscribed_channels: set[str]
            self._active_stream: dict[str, asyncio.Task[Any]]

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
        """Returns the set of channel names this client is subscribed to.

        Returns:
            A copy of the internal subscribed channels set.

        """
        return self._subscribed_channels.copy()

    def _write(self, data: bytes | bytearray, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        """Writes serialized bytes to the transport with automatic fragmentation.

        This is the lowest-level send primitive. All higher-level send methods
        serialize their data and then delegate to this method.

        Args:
            data: Serialized bytes to write.
            chunk_size: Max WebSocket frame size before splitting into
                continuation frames.

        """
        if len(data) <= chunk_size:
            self._protocol.send(WSMsgType.BINARY, data)
            return

        payload = memoryview(data)
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

    def send(self, data: Serializable, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        """Sends data over the connection.

        Non-Packet payloads are automatically wrapped in a `Packet` before serialization.
        Framework clients receive fast msgpack bytes; generic clients receive JSON strings.

        .. code-block:: python

            # Send a raw string or dict
            connection.send("Hello World!")
            connection.send({"status": "success"})

            # Or send a pre-constructed Packet
            packet = Packet(data="Custom", source=PacketSource.CUSTOM)
            connection.send(packet)

        Args:
            data (Serializable): The data to send.
            chunk_size (int): Max WebSocket frame size before fragmentation. Defaults to 64 KB.
        """

        if isinstance(data, Packet):
            packet: Serializable = data
        else:
            packet = Packet(
                data=data,
                source=PacketSource.CUSTOM,
                channel=None,
            )

        if self.client_type is ClientType.FRAMEWORK:
            _encoder.encode_into(packet, self._encode_buffer)
            self._write(self._encode_buffer, chunk_size)
        else:
            self._write(_json_encoder.encode(packet), chunk_size)

    def _send_rpc_response(self, rpc_response: "RPCResponse", chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        """Sends an RPC response back to the client.

        For framework clients, encodes directly into the per-connection buffer
        bypassing the generic send() path. Falls back to JSON for generic clients.

        Args:
            rpc_response: The RPC response object to send.
            chunk_size: Max WebSocket frame size before fragmentation.

        """
        packet = Packet(source=PacketSource.RPC, rpc=rpc_response)

        if self.client_type is ClientType.FRAMEWORK:
            _encoder.encode_into(packet, self._encode_buffer)
            self._write(self._encode_buffer, chunk_size)
        else:
            self._write(_json_encoder.encode(packet), chunk_size)

    async def recv(self, timeout: float | None = 30.0) -> Packet:
        """Receives the next message and parses it into a validated Packet object.

        This method receives incoming data and parses it into a validated Packet.
        If the data is plain JSON or msgpack, it's wrapped in a Packet with source set to CUSTOM.

        .. code-block:: python

            # Only works if using DefaultWebSocketHandler (no on_receive callback)
            try:
                packet = await connection.recv(timeout=10.0)
                print(packet.data)
            except ReceiveTimeoutError:
                print("No message received within timeout")

        Args:
            timeout (float | None): Max seconds to wait for a message. Defaults to 30.0. Use None to wait indefinitely.

        Raises:
            ConnectionClosedError: If the client is not connected.
            ReceiveTimeoutError: If no message is received within the timeout period.

        Returns:
            Packet: A validated Packet object containing the received data.

        """
        packet: Packet

        if not self._protocol or self.connection_state != ConnectionState.CONNECTED:
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

        except TimeoutError:
            raise ReceiveTimeoutError(f"Receive operation timed out after {timeout} seconds.") from None

    def subscribe(self, channel: str | Iterable[str]) -> bool:
        """A shortcut method for this connection to join one or more channels.

        .. code-block:: python

            connection.subscribe("room1")
            connection.subscribe(["room2", "room3"])
            connection.subscribe("news.*")  # Wildcard pattern

        Args:
            channel (str | Iterable[str]): A string or iterable that contains lists of channel to join.

        Returns:
            bool: True if subscribed successfully, False if the max channel limit is reached.
        """
        # 0 means no limit
        if self.max_subscribed_channels > len(self._subscribed_channels) and self.max_subscribed_channels != 0:
            self._handler.subscribe(self, channel)
            return True

        return False

    def unsubscribe(self, channel: str | Iterable[str]) -> None:
        """A shortcut method for this connection to leave one or more channels.

        .. code-block:: python

            connection.unsubscribe("room1")
            connection.unsubscribe(["room2", "room3"])

        Args:
            channel (str | Iterable[str]): A string or iterable that contains lists of channel to leave.

        """
        self._handler.unsubscribe(self, channel)

    def close(self, code: WSCloseCode = WSCloseCode.OK, reason: bytes = b"") -> None:
        """Closes the connection."""
        object.__setattr__(self, "connection_state", ConnectionState.CLOSED)
        self._protocol.send_close(code, reason)
        self._protocol.disconnect()

    async def __aiter__(self) -> AsyncGenerator[bytes, None]:
        while self.connection_state != ConnectionState.CLOSED:
            payload = await self._payload_queue.get()

            if payload is None:
                break

            yield payload

        raise ConnectionClosedError

    def __setattr__(self, name: str, value: Any) -> None:
        """Called when setting an attribute. All assignments are redirected
        to the session_state dictionary.
        """
        session_state = object.__getattribute__(self, "session_state")
        session_state[name] = value

    def __getattr__(self, name: str) -> Any:
        """Called when reading `session_state` via attribute access.

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
