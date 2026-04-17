# Frame Fragmentation

# Max size of a single WebSocket frame before splitting into continuation frames.
#
# Why 64 KB (65,536 bytes):
#   - Small enough that 1000 concurrent connections = ~62 MB in flight (manageable)
#   - Large enough to amortize WebSocket frame overhead (2-14 bytes per frame)
#   - Aligns with WebSocket's 2-byte extended payload encoding threshold:
#       * Payloads ≤ 125 bytes   → 2-byte header
#       * Payloads ≤ 65535 bytes → 4-byte header (16-bit length)
#       * Payloads > 65535 bytes → 10-byte header (64-bit length)
#     At exactly 64 KB, you stay within the 4-byte header tier.
#   - Under every known proxy/tunnel limit by orders of magnitude

DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KB


# Default WebSocket subprotocol for application-level messaging.
#
# This subprotocol identifies native webshocket clients. When a client connects
# with this subprotocol, the server uses optimized binary encoding for messages.
# Clients connecting without this subprotocol are treated as unknown clients
# and will receive raw JSON instead.

DEFAULT_WEBSHOCKET_SUBPROTOCOL = "webshocket.v1"


# Serialization Buffer
#
# Initial size of the pre-allocated bytearray used by `serialize()` to avoid
# per-message heap allocations. `msgspec.Encoder.encode_into()` writes directly
# into this buffer, and will automatically grow it if a message exceeds the
# current capacity (the buffer never shrinks back).
#
# Why 512 bytes:
#   - A typical RPC response Packet (with omit_defaults) is ~80-200 bytes,
#     so 512 comfortably fits the vast majority of messages without reallocation
#   - Small enough that the memory footprint is negligible (one buffer per process)
#   - msgspec uses doubling growth when the buffer is too small, so even if the
#     first oversized message triggers a resize, subsequent messages reuse the
#     enlarged buffer at zero cost

DEFAULT_ENCODE_BUFFER_SIZE = 512
