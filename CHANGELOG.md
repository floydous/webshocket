# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

-   Your next great feature!

---

## [0.3.0] - 2025-xx-xx

### Added

-   **Improved compatibility**: Other WebSocket modules from different languages can now interact with the Webshocket server. Check the docs for more information.
-   Added a `requires` keyword argument to `webshocket.rpc_method` for custom access control.
-   `register_rpc_method` added to `WebSocketServer` for manual add to RPC Function
-   Disconnected client will automatically unsubscribed to all channel.

### Fixed

-   Fixed a bug where an RPC function would not respond when it returned a _falsy_ type as its return object.
-   When an RPC method returns no value, an RPC response is sent with None as its result.

### Changed

-   `send_rpc` function now returns the response of the RPC calls.
-   The example code in the folder `example/` was refactored to demonstrate Webshocket's full potential
-   `ClientConnection.publish()` can now accept an Iterable of channel names

---

## [0.2.5] - 2025-07-27

### Added

-   `max_connection` parameter to `WebSocketServer` to limit the number of concurrent connections.
-   Added `RPCErrorCode` Enum to represent RPC Response codes.
-   Few logging for debugging.

### Fixed

-   Fixed the `close()` function for `ClientConnection` where it doesn't immediately change the `connection_state` to `CLOSED`
-   Fixed type hinting for `ClientConnection`

## Changed

-   Serialization method for `Packet` data is switched from base64 to `msgpack` (binary)
-   `Packet` data is no longer restricted for bytes or string, it can be anything as long it's serializeable with `msgpack`
-   `RPCResponse` is now only consisnt of `call_id` (String), `response` (Any), and `error` (RPCErrorCode)

---

## [0.2.0] - 2025-07-09

### Added

-   **RPC Rate Limiting:** Introduced a `@rate_limit` decorator for handler methods to prevent abuse and manage server load by controlling how frequently clients can call specific functions.

### Changed

-   **Enhanced Data Protocol:** The internal packet system now supports sending raw `bytes` payloads. Binary data is automatically and safely transported by Base64-encoding it within the standard JSON packet structure, making the protocol more flexible.

---

## [0.1.5] - 2025-06-27

### Added

-   **RPC (Remote Procedure Call) Support:**
    -   Implemented the `@rpc_method` decorator to easily expose handler methods as callable by clients.
    -   Added a `send_rpc` method to the client for initiating remote calls.
    -   Packets can now carry RPC request and response data.

### Fixed

-   Resolved several internal type hinting and import issues related to the new RPC feature.

---

## [0.1.0] - 2025-06-24

### Added

-   Initial public release of the `webshocket` library.
-   Core `WebSocketServer` and `WebSocketClient` classes.
-   Support for secure `wss://` connections via TLS.
-   `WebSocketHandler` pattern for server-side logic.
-   Broadcasting and channel-based communication.
-   Per-connection `session_state` management.
-   Basic client reconnection logic.
