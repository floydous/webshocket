############
Installation
############

Prerequisites
=============

Webshocket requires **Python 3.10** or higher.

Installing via pip
==================

.. code-block:: bash

   pip install webshocket

Installing from Source
======================

.. code-block:: bash

   git clone https://github.com/floydous/webshocket.git
   cd webshocket
   pip install .

Performance Tip
===============

On Linux or macOS, install ``uvloop`` for a 20-30% throughput boost:

.. code-block:: bash

   pip install uvloop

On Windows, ``winloop`` provides the equivalent benefit:

.. code-block:: bash

   pip install winloop
