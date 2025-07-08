# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Your next great feature!

---

## [0.2.0] - 2025-07-09

_Note: This is a development release. The API may be subject to change._

### Added

- **RPC Rate Limiting:** Introduced a `@rate_limit` decorator for handler methods to prevent abuse and manage server load by controlling how frequently clients can call specific functions.

### Changed

- **Enhanced Data Protocol:** The internal packet system now supports sending raw `bytes` payloads. Binary data is automatically and safely transported by Base64-encoding it within the standard JSON packet structure, making the protocol more flexible.

---

## [0.1.5] - 2025-06-27

### Added

- **RPC (Remote Procedure Call) Support:**
  - Implemented the `@rpc_method` decorator to easily expose handler methods as callable by clients.
  - Added a `send_rpc` method to the client for initiating remote calls.
  - Packets can now carry RPC request and response data.

### Fixed

- Resolved several internal type hinting and import issues related to the new RPC feature.

---

## [0.1.0] - 2025-06-24

### Added

- Initial public release of the `webshocket` library.
- Core `WebSocketServer` and `WebSocketClient` classes.
- Support for secure `wss://` connections via TLS.
- `WebSocketHandler` pattern for server-side logic.
- Broadcasting and channel-based communication.
- Per-connection `session_state` management.
- Basic client reconnection logic.
