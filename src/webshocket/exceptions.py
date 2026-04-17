class WebSocketError(Exception):
    """Base exception class for all errors raised by the webshocket library."""


# --- Connection Errors ---
class ConnectionError(WebSocketError):
    """Base class for connection-related errors."""


class ConnectionFailedError(ConnectionError):
    """Raised when a client fails to establish a connection with the server."""


class ConnectionClosedError(ConnectionError):
    """Raised when attempting an operation on a closed connection."""


class InvalidURIError(ConnectionError):
    """Raised when an invalid WebSocket URI is provided."""


# --- Message/Packet Errors ---
class MessageError(WebSocketError):
    """Base class for message processing errors."""


class PacketError(MessageError):
    """Raised when a packet is malformed or invalid."""


class PacketValidationError(PacketError):
    """Raised when packet data fails validation."""


# --- Timeout Errors ---
class TimeoutError(WebSocketError):
    """Base class for timeout-related errors."""


class ReceiveTimeoutError(TimeoutError):
    """Raised when a receive operation times out."""


class RPCTimeoutError(TimeoutError):
    """Raised when an RPC request times out."""


# --- RPC Errors ---
class RPCError(WebSocketError):
    """Base class for RPC-related errors."""


class RPCMethodNotFoundError(RPCError):
    """Raised when an RPC method is not found."""


class RateLimitError(RPCError):
    """Raised when an RPC call rate limit is exceeded."""
