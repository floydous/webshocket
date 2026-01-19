import time
import uuid
import msgspec

from typing import Generic, Optional, Any, TypeVar, Type, Sequence, cast
from msgspec import field

from .enum import PacketSource, RPCErrorCode
from .exceptions import PacketValidationError

T = TypeVar("T", bound=msgspec.Struct)


class RPCRequest(msgspec.Struct, tag="request"):
    """Represents an RPC (Remote Procedure Call) request."""

    method: str
    args: Sequence[Any] = tuple()
    kwargs: dict[str, Any] = dict()
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex)


class RPCResponse(msgspec.Struct, tag="response"):
    """Represents an RPC (Remote Procedure Call) response."""

    call_id: str

    response: Optional[Any] = None
    error: None | RPCErrorCode = None


RType = TypeVar("RType", bound=RPCRequest | RPCResponse)


class Packet(Generic[RType], msgspec.Struct):
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
    rpc: Optional[RType] = None
    channel: Optional[str] = None

    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None


# r = Packet[RPCResponse](source=PacketSource.RPC)


def validate_packet(packet: Packet) -> Packet:
    if packet.rpc is None and packet.data is None:
        raise PacketValidationError("Data must be provided.") from None

    if packet.source == PacketSource.CHANNEL and packet.channel is None:
        raise PacketValidationError("Channel must be provided for CHANNEL packets.")

    if packet.channel is not None and packet.source != PacketSource.CHANNEL:
        raise PacketValidationError("Channel cannot be provided for non-CHANNEL packets.")

    return packet


def deserialize(data: bytes, base_model: Type[T] = cast(Type[T], Packet)) -> T:
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
    packet = msgspec.msgpack.decode(data, type=base_model)

    if isinstance(packet, Packet):
        validate_packet(packet)

    return packet


def serialize(base_model: msgspec.Struct) -> bytes:
    """Serializes a BaseModel object into a bytes.

    Encode the given BaseModel object into a byte array using Msgpack.

    Args:
        base_model: The BaseModel object to be serialized.

    Returns:
        A byte array of the serialized BaseModel object.
    """

    if isinstance(base_model, Packet):
        validate_packet(base_model)

    return msgspec.msgpack.encode(base_model)
