from typing import TypedDict, Any, Awaitable, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .connection import ClientConnection

DEFAULT_WEBSHOCKET_SUBPROTOCOL = "webshocket.v1"


class RPC_Function(Protocol):
    def __call__(self, connection: "ClientConnection", /, *args: Any, **kwargs: Any) -> Awaitable[Any]: ...


class CertificatePaths(TypedDict):
    """A TypedDict defining the structure for SSL/TLS certificate paths.

    Attributes:
        cert_path (str): The file path to the SSL certificate.
        key_path (str): The file path to the SSL key.
    """

    cert_path: str
    key_path: str
