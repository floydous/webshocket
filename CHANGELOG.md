# Changelog

All notable changes to the `webshocket` library will be documented in this file.

## [0.5.2] - 2026-04-17

### Performance Gains
**v0.5.2** represents a massive leap in raw throughput and memory efficiency. By eliminating heap allocations and consolidating the serialization/fragmentation pipeline, Webshocket now hits staggering numbers:
- **RPC:** ~45,000 RPCs/s at 1.1 ms latency (asyncio, 50 concurrent clients)
- **Streaming:** 289 MB/s on asyncio, 421 MB/s with winloop

> Measured on AMD Ryzen 5 5600G, 14 GB RAM, Windows, Python 3.13. Results vary by hardware.

### Changed

- **Zero-Allocation Serialization**: Replaced `msgspec.encode()` with `encode_into()` using a pre-allocated `bytearray` per connection, eliminating heap allocations on every send.
- **Unified `_send_rpc_response` Fast Path**: Merged `_send_rpc_response` and `_send_rpc_packet` into a single method that encodes directly into the per-connection buffer.
- **Extracted `_write` Primitive**: Consolidated all fragmentation logic into `ClientConnection._write()`. All send paths delegate to it.
- **Broadcast & Publish Serialize-Once**: Serialize the `Packet` once per wire format, then fan out pre-encoded bytes to all recipients.
- **Wire Format Reduction**: Enabled `omit_defaults=True` on `Packet`, reducing typical RPC payload size by ~20-35%.
- **Client Frame Queue Hardening**: Increased client `_frame_queue` capacity to 8192 for burst tolerance. Added graceful `QueueFull` handling (log + drop) to prevent process crashes at the sync/async boundary.
- **Python 3.10 Support**: Replaced `typing.Self` with a string literal return annotation. Lowered `requires-python` to `>=3.10`. Added 3.10 to CI matrix.

### Added

- **`RateLimitError`**, **`ClientType`**, **`RPCErrorCode`** exported from `webshocket` top-level.
- **`DEFAULT_ENCODE_BUFFER_SIZE`** constant (512 bytes) in `constant.py`.
- **Benchmark Suite**: `benchmark/benchmark.py` with 2×2 grid (RPC throughput, RPC latency, stream throughput, stream depth) and `benchmark/README.md` with event loop selection guidance.

### Fixed

- **ReadTheDocs Build**: `.readthedocs.yaml` now installs the package itself (`method: pip, path: .`), fixing empty API docs on the hosted site.

## [0.5.1] - 2026-04-14

### Added

- **Streaming RPC**: Server-side RPC methods can now `yield` values as async generators. The client iterates over streamed packets in real-time using `client.stream_rpc()`, enabling use cases like AI token streaming, live data feeds, and progressive result delivery.
- **Subscription Limits**: Added a configurable `max_subscribed_channels` parameter to `ClientConnection`, allowing servers to cap the number of channels a single client can subscribe to.
- **Wildcard Subscriptions**: Pub/Sub channels now support glob patterns (`*`, `?`, `[]`) for topic matching. Clients can subscribe to patterns like `news.*` or `alerts.region.?` to receive messages across multiple matching channels.
- **Pattern Cache**: Replaced `lru_cache` with a manual `_pattern_cache` dictionary on `WebSocketHandler` for channel pattern matching, avoiding memory leaks from unbounded caching.
- **Comprehensive Test Suite**: Added 50+ new tests distributed across feature-specific files:
  - `test_utils.py` — `parse_duration` edge cases (empty string, invalid unit).
  - `test_predicate.py` — `__repr__` methods on `Has`, `Is`, `IsEqual`, `Any`, `All`.
  - `test_connection.py` — `recv` disconnect guard, JSON decode fallback, timeout, subscribe limits, dict-style access, `__repr__`, `__eq__`/`__hash__`.
  - `test_internal.py` — Picows server pending payload flush, double-serve rejection, client send-before-connect, extra headers.
  - `test_stream.py` — Streaming RPC end-to-end, mid-stream failure, concurrent streams, client-initiated abort.
  - Additions to `test_handler.py`, `test_rpc.py`, `test_rate_limit.py`, `test_context_manager.py`, `test_packet.py`.

### Changed

- **`RPCResponse` Packet**: Added `is_stream` and `is_end` boolean flags to `RPCResponse` to support the streaming protocol. `is_stream=True` marks a response as part of a streaming sequence; `is_end=True` signals the final packet.
- **`RPCMethod` Metadata**: The RPC decorator now detects async generator functions and tags them as streaming methods via `RPCMethod.is_stream`.
- **`rpc.py` Decorator Validation**: Both `@rpc_method()` and `@rate_limit()` now raise `TypeError` immediately if applied to a non-async function, preventing silent runtime failures.

### Fixed

- **Streaming Error Propagation**: Fixed a protocol bug where rate-limit and access-denied errors in streaming RPCs were not flagged with `is_stream=True` and `is_end=True`, causing client-side `stream_rpc()` iterators to hang indefinitely waiting for an end signal.
- **`stream_rpc` Rate Limit**: `stream_rpc()` now correctly raises `RateLimitError` locally when `raise_on_rate_limit=True` is set, matching the behavior of `send_rpc()`.
- **Port Collision in Tests**: Shifted integration test ports to higher ranges (5003-5050) to avoid `OSError: [Errno 10048]` on Windows caused by TCP `TIME_WAIT` state from prior test runs.

## [0.5.0] - 2026-02-11

### Changed

- **Picows Migration**: Replaced `websockets` with `picows` for handling WebSocket frames. This significantly improves performance and reduces memory usage.
- **Native Fragmentation**: Implemented native WebSocket fragmentation support. Large payloads are now automatically split into 64KB chunks.
- **Async Mismatch Fixes**: Fixed type hint inconsistencies where `client.send` was marked as `async` but implemented as synchronous.

### Added

- **Graceful Shutdown**: Improved `server.close()` to send proper Close frames (GOAWAY) to all clients before shutting down.
- **Chunking Tests**: Added comprehensive tests for 64KB payload boundaries and large message handling.

## [0.4.0] - 2026-01-20

### Added

- **New Logging System**: You can now easily see what is happening inside the server, client, and connections. This makes it much easier to debug your apps by turning logs on or off.
- **Better IDE Support**: Improved type hints for session states and RPC responses. This means better "autocomplete" and fewer coding errors while you work in your code editor.
- **Better Debug Info**: When you look at connections or filters in a debugger, they now show much clearer information.
- **Access Control Rules**: Introduced a simple way to set rules for who can call your functions. You can use rules like `IsEqual`, `Has`, `Any`, or `All` to quickly secure your server.

### Changed

- **Much Faster Performance**: Changed how data is handled to make it much faster. This reduces the delay and CPU usage for every message sent and received.
- **Faster RPC Calls**: Redesigned the RPC engine to be much more efficient, making remote function calls feel snappy even when the server is busy.
- **Better Binary Support**: Improved the way raw data and structured packets are handled so the library runs smoother.

### Fixed

- **Better Data Validation**: Fixed the rules for checking data to make sure messages are always correct and consistent.
- **Channel Fixes**: Fixed a bug where data sent to channels was sometimes labeled incorrectly.
- **General Cleanup**: Removed old debug messages and internal code that was slowing things down.

### Breaking Changes

- **Updated Dependencies**: Removed `pydantic` and `msgpack` to use a faster, built-in way of handling data.
- **Compatibility**: The message format has changed to improve speed. Both your client and server need to be updated to version 0.3.0 to work together.
