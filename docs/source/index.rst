######################
Welcome to Webshocket!
######################

.. image:: https://img.shields.io/pypi/v/webshocket.svg
   :target: https://pypi.org/project/webshocket/
   :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/webshocket.svg
   :target: https://pypi.org/project/webshocket/
   :alt: Supported Python Versions

**Webshocket** is a production-grade, `asyncio`-based Python library that reimagines WebSocket programming. It abstracts away the low-level handshake and protocol details, providing a **socket-like, object-oriented API** that feels familiar to developers while offering powerful features out of the box.

Whether you are building a real-time chat app, an IoT device command center, or a high-performance streaming server, Webshocket scales with you.

.. note::
   This documentation is for version |release|.

Key Features
============

* **Modern AsyncIO Design**: Built on top of `asyncio` and `picows` for high-performance, non-blocking I/O.
* **Standard Security**: Full support for **SSL/TLS** via standard Python `SSLContext`, including Mutual TLS (mTLS).
* **Pub/Sub System**: Built-in **Channels** and **Broadcasting** capabilities make multi-user chat and notification systems invalid trivial.
* **Stateful Connections**: Every client connection is a rich object capable of storing state (like `username`, `auth_token`) directly on the socket instance.
* **RPC Framework**: Call server-side Python functions directly from the client using the built-in **Remote Procedure Call (RPC)** decorator system.
* **Connection Stability**: Automated **Ping/Pong** heartbeats ensure broken connections are detected and cleaned up instantly.

User Guide
==========

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   examples
   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
