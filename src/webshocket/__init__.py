"""A robust, asyncio-based WebSocket library providing easy-to-use
client and server abstractions.
"""

import logging

from .connection import ClientConnection
from .enum import ClientType, ConnectionState, PacketSource, RPCErrorCode, ServerState
from .exceptions import (
    ConnectionClosedError,
    # Connection
    ConnectionError,
    ConnectionFailedError,
    InvalidURIError,
    # Message/Packet
    MessageError,
    PacketError,
    PacketValidationError,
    ReceiveTimeoutError,
    RPCTimeoutError,
    # RPC
    RateLimitError,
    RPCError,
    RPCMethodNotFoundError,
    # Timeout
    TimeoutError,
    # Base
    WebSocketError,
)
from .handler import DefaultWebSocketHandler, WebSocketHandler
from .packets import Packet, RPCRequest, RPCResponse
from .predicate import All, Any, Has, Is, IsEqual
from .rpc import rate_limit, rpc_method
from .websocket import (
    client as WebSocketClient,
)
from .websocket import (
    server as WebSocketServer,
)

__version__ = "0.5.2"
__author__ = "Floydous"
__license__ = "MIT"

__all__ = [
    # Handler
    "DefaultWebSocketHandler",
    "WebSocketHandler",
    # Enums
    "ServerState",
    "ConnectionState",
    "PacketSource",
    "ClientType",
    "RPCErrorCode",
    # Exceptions
    "WebSocketError",
    "ConnectionError",
    "ConnectionFailedError",
    "ConnectionClosedError",
    "InvalidURIError",
    "MessageError",
    "PacketError",
    "PacketValidationError",
    "TimeoutError",
    "ReceiveTimeoutError",
    "RPCTimeoutError",
    "RPCError",
    "RateLimitError",
    "RPCMethodNotFoundError",
    # Connection
    "ClientConnection",
    # Packets
    "Packet",
    "RPCRequest",
    "RPCResponse",
    # Websocket
    "WebSocketServer",
    "WebSocketClient",
    # RPC
    "rpc_method",
    "rate_limit",
    # Predicates
    "Has",
    "Is",
    "IsEqual",
    "Any",
    "All",
]

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
