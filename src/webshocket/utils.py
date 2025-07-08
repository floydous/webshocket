# You could put this in a new `utils.py` or `rpc.py` file
import base64
from typing import Any


def encode_bytes_for_json(data: Any) -> Any:
    """Recursively traverses a data structure and Base64-encodes bytes."""

    if isinstance(data, bytes):
        # This is the core logic: convert bytes to our special dict
        return {"__type__": "bytes", "data": base64.b64encode(data).decode("ascii")}
    elif isinstance(data, list):
        # If it's a list, process each item
        return [encode_bytes_for_json(item) for item in data]
    elif isinstance(data, tuple):
        # If it's a tuple, process each item and return a tuple
        return tuple(encode_bytes_for_json(item) for item in data)
    elif isinstance(data, dict):
        # If it's a dict, process each value
        return {key: encode_bytes_for_json(value) for key, value in data.items()}
    else:
        # For anything else (int, str, bool, None), return it as is
        return data


def decode_bytes_from_json(data: Any) -> Any:
    """Recursively traverses a data structure and decodes our special bytes dicts."""
    if isinstance(data, dict) and data.get("__type__") == "bytes":
        # This is the core logic: convert our special dict back to bytes
        return base64.b64decode(data["data"])
    elif isinstance(data, list):
        return [decode_bytes_from_json(item) for item in data]
    elif isinstance(data, tuple):
        # Note: JSON doesn't have tuples, so data will arrive as a list.
        # This case is here for completeness if you use it internally.
        return tuple(decode_bytes_from_json(item) for item in data)
    elif isinstance(data, dict):
        return {key: decode_bytes_from_json(value) for key, value in data.items()}
    else:
        return data
