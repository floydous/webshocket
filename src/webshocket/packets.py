import time
import uuid

from typing import Optional, Any, Union, Self
from pydantic import BaseModel, model_validator, Field
from .enum import PacketSource, DataType


class RPCRequest(BaseModel):
    """Represents an RPC (Remote Procedure Call) request."""

    method: str
    args: Optional[tuple[Any, ...]] = None
    kwargs: Optional[dict[str, Any]] = None
    call_id: uuid.UUID = Field(default_factory=uuid.uuid4)


class RPCResponse(BaseModel):
    """Represents an RPC (Remote Procedure Call) response."""

    call_id: uuid.UUID
    result: Optional[Any] = None
    error: Optional[str] = None
    content_type: DataType = DataType.PLAIN


class Packet(BaseModel):
    """A structured data packet for WebSocket communication.

    Attributes:
        data (str | bytes): The data payload.
        source (PacketSource): The source of the packet.
        channel (str | None): The channel associated with the packet.
        timestamp (float): The timestamp when the packet was created.
        correlation_id (uuid.UUID | None): The correlation ID associated with the packet.
        rpc (Union[RPCRequest, RPCResponse, None]): Optional RPC request or response data.
    """

    data: Optional[str | bytes] = None
    rpc: Optional[Union[RPCRequest, RPCResponse]] = None
    content_type: DataType = DataType.PLAIN

    source: PacketSource
    channel: Optional[str] = ""
    timestamp: float = Field(default_factory=time.time)
    correlation_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validate(self) -> Self:
        if self.rpc is None and self.data is None:
            raise ValueError("Data must be provided.") from None

        return self
