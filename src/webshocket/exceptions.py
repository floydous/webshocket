class WebSocketError(Exception):
    """Base exception class for all errors raised by the webshocket library."""

    pass


# --- Connection Errors ---
class ConnectionError(WebSocketError):
    """Base class for connection-related errors."""

    pass


class ConnectionFailedError(ConnectionError):
    """Raised when a client fails to establish a connection with the server."""

    pass


class ConnectionClosedError(ConnectionError):
    """Raised when attempting an operation on a closed connection."""

    pass


class InvalidURIError(ConnectionError):
    """Raised when an invalid WebSocket URI is provided."""

    pass


# --- Message/Packet Errors ---
class MessageError(WebSocketError):
    """Base class for message processing errors."""

    pass


class PacketError(MessageError):
    """Raised when a packet is malformed or invalid."""

    pass


class PacketValidationError(PacketError):
    """Raised when packet data fails validation."""

    pass


# --- Timeout Errors ---
class TimeoutError(WebSocketError):
    """Base class for timeout-related errors."""

    pass


class ReceiveTimeoutError(TimeoutError):
    """Raised when a receive operation times out."""

    pass


class RPCTimeoutError(TimeoutError):
    """Raised when an RPC request times out."""

    pass


# --- RPC Errors ---
class RPCError(WebSocketError):
    """Base class for RPC-related errors."""

    pass


class RPCMethodNotFoundError(RPCError):
    """Raised when an RPC method is not found."""

    pass


class RateLimitError(RPCError):
    """Raised when an RPC method is not found."""

    pass
