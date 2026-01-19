import logging
import asyncio
import websockets
import ssl
import pathlib
import random
import time
import msgspec

from contextlib import suppress
from typing import Optional, Callable, Awaitable, Union, Any, Self, Sequence, TypeVar, Generic, cast

from .packets import RPCResponse
from .handler import WebSocketHandler, DefaultWebSocketHandler
from .typing import (
    CertificatePaths,
    RPCMethod,
    RateLimitConfig,
    RPC_Predicate,
    DEFAULT_WEBSHOCKET_SUBPROTOCOL,
)
from .enum import ConnectionState, PacketSource, ServerState, RPCErrorCode
from .packets import Packet, RPCRequest, serialize, deserialize
from .connection import ClientConnection
from .exceptions import (
    ConnectionFailedError,
    ConnectionClosedError,
    WebSocketError,
    RPCError,
    InvalidURIError,
    RPCTimeoutError,
    ReceiveTimeoutError,
    RateLimitError,
)

import websockets.asyncio.server

H = TypeVar("H", bound=WebSocketHandler)


class server(Generic[H]):
    """Represents a WebSocket server that handles incoming connections and messages.

    This class provides functionality to start, manage, and close a WebSocket server,
    integrating with a custom WebSocketHandler for application-specific logic.
    It supports both secure (WSS) and unsecure (WS) connections.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        clientHandler: type[H] = DefaultWebSocketHandler,
        certificate: Optional[CertificatePaths] = None,
        max_connection: Optional[int] = None,
        packet_qsize: int = 1,
    ) -> None:
        """Initializes a new WebSocket server instance.

        Args:
            host (str): The hostname or IP address to bind the server to.
            port (int): The port number to listen on.
            max_connection (int | None): The maximum number of concurrent connections. Unlimited if None
            websocket_handler (type[WebSocketHandler]): The class type of the handler
                                                        to manage WebSocket events (connect, receive, disconnect).
            certificate (Optional[CertificatePaths]): A dictionary containing paths to
                                                      the SSL certificate and key files for WSS connections.
                                                      Defaults to None for WS connections.
        """
        self.logger = logging.getLogger("webshocket.server")
        self.state: ServerState = ServerState.CLOSED
        self.host, self.port = host, port
        self.handler = clientHandler()
        self.certificate = certificate
        self.max_connection = max_connection

        self._packet_qsize = packet_qsize
        self._server: websockets.Server | None = None
        self._context: ssl.SSLContext | None = None
        self._client_bucket: asyncio.Queue[ClientConnection] = asyncio.Queue()

        if self.certificate is not None:
            self._context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            cert_path = self.certificate["cert_path"]
            key_path = self.certificate["key_path"]

            self._context.load_cert_chain(
                pathlib.Path(cert_path).resolve(),
                pathlib.Path(key_path).resolve(),
            )

    @staticmethod
    def _to_packet(data: str | bytes, subprotocol: websockets.Subprotocol | None) -> Packet:
        """Converts raw data or json-model data into structured Packet-type data"""

        packet = Packet(data=data, source=PacketSource.UNKNOWN, channel=None)

        with suppress(msgspec.ValidationError, msgspec.DecodeError, TypeError):
            if subprotocol is not None:
                if not isinstance(data, bytes):
                    raise TypeError("Data to be deserialize must be a bytes, not %s" % type(data))

                if DEFAULT_WEBSHOCKET_SUBPROTOCOL in subprotocol:
                    packet = deserialize(cast(bytes, data), Packet)

            else:
                packet = msgspec.json.decode(data, type=Packet)

        return packet

    async def _handle_rpc_request(
        self,
        connection: "ClientConnection",
        rpc_request: RPCRequest,
    ) -> None:
        """
        Handles an incoming RPC request by dispatching it to the appropriate
        RPC method on the handler and sending back a response.

        Args:
            connection (ClientConnection): The client connection that sent the request.
            rpc_request (RPCRequest): The parsed RPC request.
        """

        method_name = rpc_request.method
        call_id = rpc_request.call_id

        error: RPCErrorCode | None = None
        error_message: Optional[str] = None
        result: Any = None

        try:
            rpc_function: RPCMethod | None = self.handler._rpc_methods.get(method_name, None)

            if rpc_function is None:
                await connection._send_rpc_response(
                    RPCResponse(
                        call_id=call_id,
                        response=f"RPC method '{method_name}' not found.",
                        error=RPCErrorCode.METHOD_NOT_FOUND,
                    ),
                )
                return

            if restriction := rpc_function.restricted:
                access_error = self._check_restricted_access(connection, restriction, call_id, method_name)

                if access_error:
                    await connection._send_rpc_response(access_error)
                    return

            if rate_limit := rpc_function.rate_limit:
                limit_error = await self._check_rate_limit(connection, rpc_function.func, rate_limit, call_id, method_name)

                if limit_error:
                    await connection._send_rpc_response(limit_error)
                    return

            result = await self._execute_rpc_method(
                connection,
                rpc_function.func,
                rpc_request,
            )

        except RPCError as rcp_error:
            error_message = str(rcp_error)
            error = RPCErrorCode.APPLICATION_ERROR

        except TypeError as e:
            error_message = f"Server error ({type(e).__name__}): {e}"
            error = RPCErrorCode.INVALID_PARAMS

        except Exception as e:
            error_message = f"Server error ({type(e).__name__}): {e}"
            error = RPCErrorCode.INTERNAL_SERVER_ERROR

            self.logger.exception("RPC execution failed for method '%s'", method_name)

        finally:
            rpc_response = RPCResponse(
                response=error_message or result,
                call_id=call_id,
                error=error,
            )

            if connection.connection_state == ConnectionState.CONNECTED:
                await connection._send_rpc_response(rpc_response)

    def _check_restricted_access(
        self,
        connection: "ClientConnection",
        restricted: RPC_Predicate,
        call_id: str,
        method_name: str,
    ) -> Optional[RPCResponse]:
        """Checks if the client has access to the RPC method."""
        if not restricted(connection):
            return RPCResponse(
                call_id=call_id,
                response=f"Access denied for RPC method '{method_name}'.",
                error=RPCErrorCode.ACCESS_DENIED,
            )

        return None

    async def _check_rate_limit(
        self,
        connection: "ClientConnection",
        rpc_func: Callable,
        rate_limit: RateLimitConfig,
        call_id: str,
        method_name: str,
    ) -> Optional[RPCResponse]:
        """Checks and enforces the rate limit for the RPC method."""
        currentTime = time.time()
        storageKey = "_rate_limit_" + rpc_func.__name__

        if storageKey not in connection.session_state:
            connection.session_state[storageKey] = {
                "last_called": currentTime,
                "count": 0,
            }

        if currentTime - connection.session_state[storageKey]["last_called"] >= rate_limit.period:
            connection.session_state[storageKey]["last_called"] = currentTime
            connection.session_state[storageKey]["count"] = 0

        if connection.session_state[storageKey]["count"] >= rate_limit.limit:
            if rate_limit.disconnect_on_limit_exceeded:
                await connection.close(code=1008, reason="Rate limit exceeded")

            return RPCResponse(
                call_id=call_id,
                response=f"Rate limit exceeded for RPC method '{method_name}'.",
                error=RPCErrorCode.RATE_LIMIT_EXCEEDED,
            )

        connection.session_state[storageKey]["count"] += 1
        return None

    async def _execute_rpc_method(
        self,
        connection: "ClientConnection",
        rpc_func: Callable,
        rpc_request: RPCRequest,
    ) -> Any:
        """Executes the RPC method with the provided arguments."""
        return await rpc_func(
            connection,
            *rpc_request.args,
            **cast(dict[str, Any], rpc_request.kwargs),
        )

    async def _handler(self, websocket_protocol: websockets.ServerConnection) -> None:
        """Internal handler for new WebSocket connections.

        This method is called by the websockets library for each new connection.
        It initializes a ClientConnection, adds it to the handler's clients,
        and manages the message reception loop and disconnection.

        Args:
            websocket_protocol (websockets.ServerConnection): The underlying
                                                              WebSocket protocol object for the connection.
        """

        if isinstance(self.max_connection, int) and len(self.handler.clients) >= self.max_connection:
            await websocket_protocol.close(
                code=websockets.frames.CloseCode.TRY_AGAIN_LATER,
                reason="Server is currently at maximum capacity. Please try again later.",
            )
            return

        _remote_address = ":".join(tuple(map(str, websocket_protocol.remote_address)))

        _websocket: ClientConnection = ClientConnection(
            websocket_protocol=websocket_protocol,
            packet_qsize=self._packet_qsize,
            handler=self.handler,
        )

        if isinstance(self.handler, DefaultWebSocketHandler):
            await self._client_bucket.put(_websocket)

        self.handler.clients.add(_websocket)
        await self.handler.on_connect(_websocket)
        self.logger.info("New connection from %s", _remote_address)

        try:
            async for data in websocket_protocol:
                packet = self._to_packet(
                    subprotocol=websocket_protocol.subprotocol,
                    data=data,
                )

                if packet.source == PacketSource.RPC and isinstance(packet.rpc, RPCRequest):
                    asyncio.create_task(self._handle_rpc_request(_websocket, packet.rpc))
                    continue

                if isinstance(self.handler, DefaultWebSocketHandler):
                    await cast(asyncio.Queue, _websocket._packet_queue).put(packet)
                    continue

                await self.handler.on_receive(_websocket, packet)

        except websockets.exceptions.ConnectionClosedError:  # Expected error when client disconnects.
            pass

        finally:
            self.logger.info("Connection (%s) closed.", _remote_address)

            _websocket.connection_state = ConnectionState.DISCONNECTED
            self.handler.clients.discard(_websocket)

            for channel_name in list(self.handler.channels.keys()):
                _websocket.unsubscribe(channel_name)

            await self.handler.on_disconnect(_websocket)

    async def accept(self) -> ClientConnection:
        """Accepts a new WebSocket connection and returns the ClientConnection object.

        This method is only available when using the DefaultWebSocketHandler.
        Breakdown of the method:

            - If no client is connected, it will wait until a client is connected and returns the ClientConnection object.
            - If the handler callback is active, this method will raise a TypeError.
            - If the server is not started, this method will raise a WebSocketError.

        Returns:
            ClientConnection: The ClientConnection object for the accepted connection.
        """

        if not isinstance(self.handler, DefaultWebSocketHandler):
            raise TypeError("Cannot use manual accept() when handler callback is active.")

        if self._server is None:
            raise WebSocketError("Error getting client: server is not started")

        websocket = await self._client_bucket.get()
        return websocket

    async def start(self, *args, **kwargs) -> Self:
        """Starts the WebSocket server.

        If an SSL certificate is provided, the server will run securely (WSS).
        This method initializes the server and makes it ready to accept connections.

        Args:
            *args: Positional arguments to pass to `websockets.asyncio.server.serve`.
            **kwargs: Keyword arguments to pass to `websockets.asyncio.server.serve`.
        """

        if self._context is not None:
            kwargs.update({"ssl": self._context})

        if self._server is None:
            self._server = await websockets.asyncio.server.serve(
                select_subprotocol=self._select_subprotocol,
                handler=self._handler,
                host=self.host,
                port=self.port,
                *args,
                **kwargs,
            )

            self.state = ServerState.SERVING
            self.logger.info("Server started on %s:%s" % (self.host, self.port))

        return self

    async def serve_forever(self, *args, **kwargs) -> None:
        """Starts the WebSocket server and keeps it running indefinitely.

        This method calls `start()` and then waits for the server to be closed.

        Args:
            *args: Positional arguments to pass to `websockets.asyncio.server.serve`.
            **kwargs: Keyword arguments to pass to `websockets.asyncio.server.serve`.
        """
        await self.start(*args, **kwargs)

        if self._server is not None:
            await self._server.wait_closed()
            return

    async def close(self) -> None:
        """Closes the WebSocket server gracefully.

        This method stops the server from accepting new connections and
        waits for all existing connections to close.
        """
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

            self.state = ServerState.CLOSED
            self._server = None

    def _select_subprotocol(self, _, subprotocols: Sequence[websockets.Subprotocol]) -> websockets.Subprotocol | None:
        if DEFAULT_WEBSHOCKET_SUBPROTOCOL in subprotocols:
            return cast(websockets.Subprotocol, DEFAULT_WEBSHOCKET_SUBPROTOCOL)

        return None

    def __getattr__(self, name: str) -> Any:
        """Called when reading `handler` via `connection._example_data`"""
        try:
            return getattr(self.handler, name)
        except AttributeError:
            raise AttributeError(f"'{type(self).__name__}' object and its handler have no attribute '{name}'") from None

    async def __aenter__(self) -> Self:
        """
        Enters the asynchronous context manager, starting the server.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Exits the asynchronous context manager, closing the server.
        """
        if self._server is not None:
            await self.close()


class client:
    """Represents a WebSocket client for connecting to a WebSocket server.

    This class provides functionality to connect, send, receive, and close
    WebSocket connections, supporting both secure (WSS) and unsecure (WS) connections.
    """

    def __init__(
        self,
        uri: str,
        on_receive: Optional[Callable[[Packet], Awaitable[None]]] = None,
        *,
        ca_cert_path: Optional[str] = None,
        max_packet_qsize: int = 128,
    ) -> None:
        """Initializes a new WebSocket client instance.

        Args:
            uri (str): The URI of the WebSocket server to connect to (e.g., "ws://localhost:8000").
                       Must include the protocol "ws://" or "wss://".

            on_receive (Optional[Callable[[Any], Awaitable[None]]]): An asynchronous callback
                                                                      function to be called when a message is received.
                                                                      Defaults to None.
            ca_cert_path (Optional[str]): Path to a CA certificate file for verifying the server's
                                          certificate in WSS connections. Defaults to None.

        Raises:
            ValueError: If the URI does not include a valid WebSocket protocol.
        """
        self._protocol: Optional[websockets.ClientConnection] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._context: Optional[ssl.SSLContext] = None

        self._packet_queue: asyncio.Queue[Packet] = asyncio.Queue(maxsize=max_packet_qsize)
        self._rpc_pending_request: dict[str, asyncio.Future] = {}

        self.state = ConnectionState.DISCONNECTED
        self.logger = logging.getLogger("webshocket.client")
        self.on_receive_callback = on_receive
        self.cert = ca_cert_path
        self.uri = uri

        if not (uri.startswith("ws://") or uri.startswith("wss://")):
            raise InvalidURIError("Please include the websocket protocol `wss://` or `ws://` on the address")

        if self.uri.startswith("wss://"):
            self._context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

            if ca_cert_path:
                self._context.load_verify_locations(cafile=pathlib.Path(ca_cert_path).resolve())

    async def _handler(self) -> None:
        """Internal handler for receiving messages from the WebSocket server.

        This method continuously listens for incoming messages and calls the
        `on_receive_callback` if it's implemented. It manages the client's
        connection state upon disconnection.

        Raises:
            NotImplementedError: If the client is not connected or `on_receive_callback` is not set.
        """
        if self._protocol is None:
            raise ConnectionClosedError("Cannot handle server: not connected")

        if not self._protocol:
            return

        try:
            async for data in self._protocol:
                packet: Packet = server._to_packet(data, cast(websockets.Subprotocol, DEFAULT_WEBSHOCKET_SUBPROTOCOL))

                if isinstance(packet.rpc, RPCResponse) and packet.source == PacketSource.RPC:
                    packet.data = packet.rpc.response

                    if packet.rpc.call_id in self._rpc_pending_request:
                        future = self._rpc_pending_request.pop(packet.rpc.call_id)
                        future.set_result(packet)

                    continue

                if self.on_receive_callback:
                    await self.on_receive_callback(packet)
                    continue

                await self._packet_queue.put(packet)

        except websockets.exceptions.ConnectionClosed:
            pass

        finally:
            self.state = ConnectionState.DISCONNECTED

    async def _connect_once(self, **kwargs) -> None:
        """Attempts to establish a single WebSocket connection.

        If an existing connection or listener task is active, they will be closed first.
        Updates the connection state and creates a listener task if `on_receive_callback` is set.

        Args:
            **kwargs: Keyword arguments to pass to `websockets.connect`.
        """
        if (self._listener_task and not self._listener_task.done()) or self._protocol:
            await self.close()

        self.state = ConnectionState.CONNECTING

        self._protocol = await websockets.connect(
            uri=self.uri,
            **kwargs,
        )
        self.state = ConnectionState.CONNECTED
        self.logger.info("Successfully connected to %s", self.uri)
        self._listener_task = asyncio.create_task(self._handler())

    async def connect(
        self,
        retry: bool = False,
        max_retry_attempt: int = 3,
        retry_interval: int = 2,
        **kwargs,
    ) -> Self:
        """Connects the WebSocket client to the server.

        Supports optional retry logic with exponential backoff.

        Args:
            retry (bool): If True, attempts to reconnect multiple times on failure. Defaults to False.
            max_retry_attempt (int): The maximum number of retry attempts. Defaults to 3.
            retry_interval (int): The base interval in seconds between retry attempts. Defaults to 2.
            **kwargs: Keyword arguments to pass to `websockets.connect`.

        Raises:
            ConnectionFailedError: If all connection attempts fail when `retry` is True.
        """
        kwargs.update({"subprotocols": [DEFAULT_WEBSHOCKET_SUBPROTOCOL]})

        if self._context is not None:
            kwargs.update({"ssl": self._context})

        if not retry:
            await self._connect_once(**kwargs)
            return self

        for attempt in range(max_retry_attempt):
            delay = retry_interval * (2**attempt) + random.uniform(0, 1)

            try:
                await self._connect_once(**kwargs)
                return self

            except (ConnectionFailedError, ConnectionRefusedError):
                await asyncio.sleep(delay)

        await self.close()
        raise ConnectionFailedError("All connection attempts failed after multiple retries.")

    async def send(self, data: Union[Any, Packet]) -> None:
        """Sends data over the WebSocket connection.

        Args:
            data (Any | Packet): The data to send. Could be anything as long it's serializeable by `msgpack`

        Raises:
            WebSocketError: If the client is not connected.
        """
        packet: Packet

        if (not self._protocol) or self.state != ConnectionState.CONNECTED:
            raise WebSocketError("Cannot send data: client is not connected.")

        if isinstance(data, Packet):
            packet = data

        else:
            packet = Packet(
                data=data,
                source=PacketSource.CUSTOM,
                channel=None,
            )

        await self._protocol.send(serialize(packet))

    async def send_rpc(self, method_name: str, /, *args, raise_on_rate_limit: bool = False, **kwargs) -> Packet[RPCResponse]:
        """Sends an RPC message to the WebSocket server.

        Args:
            method_name (str): The name of the RPC method to call.
            raise_on_rate_limit (bool): If True, raises an exception if the RPC call fails.

        Raises:
            WebSocketError: If the client is not connected.
        """

        if (not self._protocol) or self.state != ConnectionState.CONNECTED:
            raise WebSocketError("Cannot send RPC: client is not connected.")

        rpc_request = RPCRequest(method=method_name, args=args, kwargs=kwargs)
        packet: Packet = Packet(rpc=rpc_request, source=PacketSource.RPC)
        future = asyncio.Future()

        try:
            self._rpc_pending_request[rpc_request.call_id] = future
            await self._protocol.send(serialize(packet))

            response_packet = await asyncio.wait_for(future, timeout=30)
            rpc_response = cast(Packet[RPCResponse], response_packet)

            if isinstance(rpc_response.rpc, RPCResponse) and rpc_response.rpc.error == RPCErrorCode.RATE_LIMIT_EXCEEDED:
                if raise_on_rate_limit:
                    raise RateLimitError("RPC call rate limit exceeded.")

        except asyncio.TimeoutError:
            raise RPCTimeoutError("RPC request timed out.")

        finally:
            if rpc_request.call_id in self._rpc_pending_request:
                self._rpc_pending_request.pop(rpc_request.call_id)

        return rpc_response

    async def recv(self, timeout: int | None = 30) -> Packet:
        """Receives data from the WebSocket connection.

        Args:
            timeout (int | None): The maximum time in seconds to wait for a message.
                                  Defaults to 30 seconds. Set to None for no timeout.

        Returns:
            str | bytes: The received data

        Raises:
            WebSocketError: If the client is not connected.
            TimeoutError: If the receive operation times out.
        """

        if (not self._protocol or self.state != ConnectionState.CONNECTED) and self._packet_queue.empty():
            raise WebSocketError("Cannot receive data: client is not connected.")

        try:
            packet = await asyncio.wait_for(self._packet_queue.get(), timeout=timeout)
            return packet

        except TimeoutError:
            raise ReceiveTimeoutError(f"Receive operation timed out after {timeout} seconds.")

    async def close(self) -> None:
        """Closes the WebSocket client connection gracefully.

        Cancels the listener task and closes the underlying protocol.
        Updates the connection state to DISCONNECTED.
        """
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()

            with suppress(asyncio.CancelledError):
                await self._listener_task

        if self._protocol:
            await self._protocol.close()

        self._protocol = None
        self._listener_task = None
        self.state = ConnectionState.CLOSED

    async def __aenter__(self):
        """Enters the asynchronous context manager, connecting the client if not already connected."""
        if not self._protocol:
            await self.connect()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exits the asynchronous context manager, closing the client connection."""
        await self.close()
