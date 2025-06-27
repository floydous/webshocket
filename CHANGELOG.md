# Changelog

All notable changes to this project will be documented in this file.

- v0.1.5

  - Added: RPC (Remote Procedure Call) Support

    - Added `@rpc_method` to easily make your handler methods callable.
    - New `send_rpc` method on the client to kick off remote calls.
    - `client.recv` now automatically grabs RPC results/errors for you.
    - `Packet`s can now carry RPC stuff.

  - Fixed: Type Stuff and Imports
    - Cleaned up some type hints and import issues for the new RPC feature.

- v0.1.0
  - First release
