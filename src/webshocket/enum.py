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


class DataType(Enum):
    """Represents the data type of a packet."""

    PLAIN = auto()
    BINARY = auto()


class TimeUnit(IntEnum):
    """Represents time units for rate limiting."""

    SECOND = 1
    MINUTES = 60
    HOURS = 3600
