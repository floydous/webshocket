# OpenCode Instructions for webshocket

This repository is an asyncio-based WebSocket library for Python, built on top of `picows` and `msgspec`.

## Setup & Tooling

- **Package Manager**: `uv`
- **Task Runner**: `poethepoet`
- **Virtual Environment Setup**: `uv venv && uv pip install -e ".[dev]"`

## Key Commands

Always use `uv run poe` to execute tasks defined in `pyproject.toml`.

- **Run all checks** (format, lint, test): `uv run poe all` (Run this before committing)
- **Run tests**: `uv run poe test`
- **Run tests with coverage**: `uv run poe cov`
- **Format code**: `uv run poe format` (Uses `ruff`, enforces 135 line length)
- **Lint code**: `uv run poe lint` (Uses `ruff check --fix`)
- **Build docs**: `uv run poe docs`

## Architecture & Conventions

- **Entrypoints**: The core API elements (`WebSocketServer`, `WebSocketClient`, `ClientConnection`, `rpc_method`, etc.) are exposed in `src/webshocket/__init__.py`.
- **Dependencies**: The project relies on `picows` for WebSocket protocol handling and `msgspec` for fast validation/serialization. Note: `websockets` is only included as a dev dependency for testing compatibility, not for core functionality.
- **Testing**: Tests are located in `tests/` and heavily rely on `pytest-asyncio` due to the async nature of the library.
