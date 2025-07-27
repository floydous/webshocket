import time
import uuid
import msgpack

from typing import Optional, Any, Union, Self, TypeVar, Type, cast
from pydantic import BaseModel, model_validator, Field
from .enum import PacketSource, Enum, RPCErrorCode

T = TypeVar("T", bound=BaseModel)


class RPCRequest(BaseModel):
    """Represents an RPC (Remote Procedure Call) request."""

    call_id: str = Field(default_factory=lambda: uuid.uuid4().hex)

    method: str
    args: tuple[Any, ...] = tuple()
    kwargs: dict[str, Any] = dict()


class RPCResponse(BaseModel):
    """Represents an RPC (Remote Procedure Call) response."""

    call_id: str

    response: Optional[Any] = None
    error: None | RPCErrorCode = None


class Packet(BaseModel):
    """A structured data packet for WebSocket communication.

    Attributes:
        data (Any): The data payload.
        source (PacketSource): The source of the packet.
        channel (str | None): The channel associated with the packet.
        timestamp (float): The timestamp when the packet was created.
        correlation_id (uuid.UUID | None): The correlation ID associated with the packet.
        rpc (Union[RPCRequest, RPCResponse, None]): Optional RPC request or response data.
    """

    data: Any = None
    rpc: Optional[Union[RPCRequest, RPCResponse]] = None

    source: PacketSource
    channel: Optional[str] = str()
    timestamp: float = Field(default_factory=time.time)
    correlation_id: Optional[str] = None

    @model_validator(mode="after")
    def validate(self) -> Self:
        if self.rpc is None and self.data is None:
            raise ValueError("Data must be provided.") from None

        return self


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

    decoded_data = msgpack.unpackb(data, raw=False)
    return base_model.model_validate(decoded_data)


def serialize(base_model: BaseModel) -> bytes:
    """Serializes a BaseModel object into a bytes.

    Encode the given BaseModel object into a byte array using Msgpack.

    Args:
        base_model: The BaseModel object to be serialized.

    Returns:
        A byte array of the serialized BaseModel object.
    """

    encoded_data = cast(
        bytes,
        msgpack.packb(
            base_model.model_dump(mode="python"),
            use_bin_type=True,
            default=lambda obj: obj.value if isinstance(obj, Enum) else None,  # type: ignore
        ),
    )

    return encoded_data
