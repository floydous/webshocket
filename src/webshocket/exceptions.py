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
    """Custom exception for RPC-related errors."""

    class NotFoundError(Exception):
        pass
