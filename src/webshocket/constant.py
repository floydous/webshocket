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
#   - Matches the CHANGELOG claim of "64KB chunks" from the v0.5.0 entry
#   - Under every known proxy/tunnel limit by orders of magnitude

DEFAULT_CHUNK_SIZE = 64 * 1024  # 64 KB
