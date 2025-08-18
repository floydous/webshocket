"""
A robust, asyncio-based WebSocket library providing easy-to-use
client and server abstractions.
"""

import logging


from .exceptions import (
    NotFoundError,
    RPCError,
    MessageError,
    ConnectionFailedError,
    WebSocketError,
    PacketError,
)
from .rpc import rate_limit, rpc_method
from .handler import DefaultWebSocketHandler, WebSocketHandler
from .enum import ServerState, ConnectionState, PacketSource, TimeUnit
from .typing import CertificatePaths
from .connection import ClientConnection
from .packets import Packet, RPCRequest, RPCResponse
from .websocket import (
    server as WebSocketServer,
    client as WebSocketClient,
)


__version__ = "0.3.0"
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
    "TimeUnit",
    # Exceptions
    "NotFoundError",
    "RPCError",
    "MessageError",
    "ConnectionFailedError",
    "WebSocketError",
    "PacketError",
    # Typing
    "CertificatePaths",
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
]

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
