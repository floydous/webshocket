######################
Welcome to Webshocket!
######################

.. image:: https://img.shields.io/pypi/v/webshocket.svg
   :target: https://pypi.org/project/webshocket/
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/webshocket.svg
   :target: https://pypi.org/project/webshocket/
   :alt: Supported Python Versions

**Webshocket** is a lightweight Python framework for WebSocket-based applications. It gives you a high-level API for remote procedure calls, per-client session state, pub/sub channels, and efficient message broadcasting — all built on top of ``asyncio`` and ``picows``.

.. note::
   This documentation is for version |release|.

Key Features
============

* **RPC Framework** — Call server-side functions from the client with ``send_rpc()``. Supports streaming, rate limiting, and access control.
* **Streaming RPC** — Server methods can ``yield`` values as async generators. The client iterates over chunks in real-time.
* **Session State** — Attach data directly to connection objects (``connection.username = "alice"``). No external state store needed.
* **Pub/Sub Channels** — Built-in channels with wildcard pattern matching (``news.*``, ``alerts.region.?``).
* **Rate Limiting** — Decorator-based rate limiting with human-readable periods (``"5/1m"``).
* **Access Control** — Protect RPC methods with composable predicates (``Is``, ``Has``, ``IsEqual``, ``Any``, ``All``).
* **Auto-Retry** — Client reconnects automatically with exponential backoff.
* **Cross-Language** — Framework clients use fast msgpack. Any WebSocket client (JS, Java, C#) can connect with plain JSON.
* **Secure by Default** — Full SSL/TLS support via standard Python ``SSLContext``.

User Guide
==========

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   features
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
