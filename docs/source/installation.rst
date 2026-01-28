############
Installation
############

Prerequisites
=============

Webshocket requires **Python 3.8** or higher. It is built on top of the modern `asyncio` stack and leverages type hinting extensively.

Installing via pip
==================

The easiest way to install Webshocket is from PyPI:

.. code-block:: bash

   pip install webshocket

Installing from Source
======================

If you want the latest development version, you can install directly from GitHub:

.. code-block:: bash

   git clone https://github.com/floydous/webshocket.git
   cd webshocket
   pip install .

Performance Optimization
========================

For production environments on Linux or macOS, we highly recommend installing `uvloop` for a significant performance boost. Webshocket is fully compatible with it.

.. code-block:: bash

   pip install uvloop
