from typing import TypedDict


class CertificatePaths(TypedDict):
    """A TypedDict defining the structure for SSL/TLS certificate paths.

    Attributes:
        cert_path (str): The file path to the SSL certificate.
        key_path (str): The file path to the SSL key.
    """

    cert_path: str
    key_path: str
