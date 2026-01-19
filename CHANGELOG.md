# Changelog

All notable changes to the `webshocket` library will be documented in this file.

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
