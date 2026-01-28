"""
A robust, asyncio-based WebSocket library providing easy-to-use
client and server abstractions.
"""

import logging

from .rpc import rpc_method, rate_limit
from .predicate import Has, Is, IsEqual, Any, All
from .handler import DefaultWebSocketHandler, WebSocketHandler
from .enum import ServerState, ConnectionState, PacketSource
from .connection import ClientConnection
from .packets import Packet, RPCRequest, RPCResponse
from .exceptions import (
    # Base
    WebSocketError,
    # Connection
    ConnectionError,
    ConnectionFailedError,
    ConnectionClosedError,
    InvalidURIError,
    # Message/Packet
    MessageError,
    PacketError,
    PacketValidationError,
    # Timeout
    TimeoutError,
    ReceiveTimeoutError,
    RPCTimeoutError,
    # RPC
    RPCError,
    RPCMethodNotFoundError,
)
from .websocket import (
    server as WebSocketServer,
    client as WebSocketClient,
)


__version__ = "0.4.0"
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
