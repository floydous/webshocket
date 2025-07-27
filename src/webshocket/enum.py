from enum import IntEnum, Enum, auto


class ConnectionState(Enum):
    """Represents the various states of a WebSocket connection.

    Attributes:
        DISCONNECTED: The connection is currently not active.
        CONNECTING: The connection is in the process of being established.
        CONNECTED: The connection is successfully established and active.
        CLOSED: The connection has been explicitly closed.
    """

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    CLOSED = auto()


class ServerState(Enum):
    """Represents the various states of the WebSocket server itself.

    Attributes:
        CLOSED: The server is not running and not listening for connections.
        SERVING: The server is actively running and accepting new connections.
    """

    CLOSED = auto()
    SERVING = auto()


class PacketSource(Enum):
    """Represents the source of a packet that is being sent.

    Attributes:
        BROADCAST: A packet broadcast to all connected clients.
        CHANNEL: A packet published to a specific subscribed channel of the client.
        UNKNOWN: A packet with an unknown source.
        CUSTOM: A packet manually sent by the server.
    """

    BROADCAST = auto()
    CHANNEL = auto()
    UNKNOWN = auto()
    CUSTOM = auto()
    RPC = auto()


class TimeUnit(IntEnum):
    """Represents time units for rate limiting."""

    SECOND = 1
    MINUTES = 60
    HOURS = 3600


class RPCErrorCode(IntEnum):
    """
    Defines standard error codes for the RPC system, inspired by the JSON-RPC 2.0 spec.
    """

    # Standard JSON-RPC Error Codes
    METHOD_NOT_FOUND = -32601
    """The requested RPC method does not exist on the handler."""

    INVALID_PARAMS = -32602
    """Invalid method parameters were provided (e.g., wrong type, wrong number of arguments)."""

    INTERNAL_SERVER_ERROR = -32603
    """A generic, unexpected error occurred on the server during the execution of the RPC method."""

    # Custom Server-Side Error Codes (as per JSON-RPC spec, -32000 to -32099 are reserved)
    RATE_LIMIT_EXCEEDED = -32000
    """The client has exceeded the rate limit for the requested method."""

    APPLICATION_ERROR = -32001
    """The RPC method was executed successfully but raised an intentional, application-specific exception."""
