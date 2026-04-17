from collections.abc import Sequence
from typing import Any, Generic, TypeVar, cast

import msgspec
from msgspec import field

from .enum import PacketSource, RPCErrorCode
from .utils import generate_uuid

T = TypeVar("T", bound=msgspec.Struct)


class RPCRequest(msgspec.Struct, tag="request", gc=False):
    """Represents an RPC (Remote Procedure Call) request."""

    method: str
    args: Sequence[Any] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=generate_uuid)


class RPCResponse(msgspec.Struct, tag="response", gc=False):
    """Represents an RPC (Remote Procedure Call) response."""

    call_id: str

    response: Any = None
    error: None | RPCErrorCode = None

    is_stream: bool = False
    is_end: bool = False


RType = TypeVar("RType", bound=RPCRequest | RPCResponse)


class Packet(msgspec.Struct, Generic[RType], gc=False, omit_defaults=True):
    """A structured data packet for WebSocket communication.

    Attributes:
        data (Any): The data payload.
        source (PacketSource): The source of the packet.
        channel (str | None): The channel associated with the packet.
        timestamp (float): The timestamp when the packet was created.
        correlation_id (uuid.UUID | None): The correlation ID associated with the packet.
        rpc (RType | None): Optional RPC request or response data.

    """

    source: PacketSource

    data: Any = None
    rpc: RType | None = None
    channel: str | None = None

    timestamp: float | None = None
    correlation_id: str | None = None


_encoder = msgspec.msgpack.Encoder()
_decoder = msgspec.msgpack.Decoder(Packet)
_json_encoder = msgspec.json.Encoder()
_json_decoder = msgspec.json.Decoder(Packet)


def deserialize(data: bytes) -> Packet:
    """Deserializes a byte array into a BaseModel object.

    Decode the given byte data using Msgpack and validate it into the
    specified BaseModel object.

    Args:
        data: The byte array to be deserialized.
        base_model: The BaseModel type to deserialize the data into.

    Returns:
        A BaseModel object of the specified type if deserialization and
        validation are successful.

    """
    return cast("Packet", _decoder.decode(data))


def serialize(base_model: msgspec.Struct) -> bytes:
    """Serializes a BaseModel object into msgpack bytes.

    Encode the given BaseModel object into a byte string using Msgpack.

    Args:
        base_model: The BaseModel object to be serialized.

    Returns:
        A bytes object containing the serialized data.

    """
    return _encoder.encode(base_model)
