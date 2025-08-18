class PacketError(Exception):
    """Base exception class for all errors raised by the webshocket library.

    This allows users to catch all library-specific errors with a single
    'except PacketError:' block.
    """


class WebSocketError(Exception):
    """Base exception class for all errors raised by the webshocket library.

    This allows users to catch all library-specific errors with a single
    'except WebSocketError:' block.
    """

    pass


class ConnectionFailedError(WebSocketError):
    """Raised when a client fails to establish a connection with the server.

    This can be due to network issues, SSL/TLS errors, or the server
    rejecting the handshake.
    """

    pass


class MessageError(WebSocketError):
    """Raised when an error occurs while processing a WebSocket message."""

    pass


class RPCError(Exception):
    """Raised when an error occurs while processing an RPC request."""

    pass


class NotFoundError(RPCError):
    """Raised when an RPC method is not found."""

    pass
