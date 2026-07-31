Installation
============

Requirements
------------

``auto-incucyte`` requires Python 3.10 or newer. Plotting and table dependencies
are installed automatically with the package.

Install from GitHub
-------------------

Use a virtual environment so the analysis has a reproducible set of Python
packages:

.. code-block:: console

   git clone https://github.com/jmwarrington/auto-incucyte.git
   cd auto-incucyte
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install .

Confirm the command works:

.. code-block:: console

   auto-incucyte --help

Install directly without cloning
--------------------------------

After the GitHub repository is online:

.. code-block:: console

   python -m pip install git+https://github.com/jmwarrington/auto-incucyte.git

Updating
--------

If you cloned the repository:

.. code-block:: console

   git pull
   python -m pip install --upgrade .

.. note::

   Activate the environment in each new terminal with
   ``source .venv/bin/activate`` before running the command.
