Installation for complete beginners
===================================

``auto-incucyte`` requires Python 3.10 or newer. Python 3.11 through 3.14 are
also supported. Plotting and table packages are installed automatically.

What a virtual environment is
-----------------------------

A virtual environment is a private folder containing this program's Python
packages. It prevents one scientific program from changing another program's
dependencies. In the commands below, that folder is named ``automate``.

First-time installation on a Mac
--------------------------------

Open **Terminal** from Applications → Utilities. Copy each command and press
Return:

.. code-block:: console

   git clone https://github.com/jmwarrington/auto-incucyte.git
   cd auto-incucyte
   python3 --version

The reported Python version must be 3.10 or newer. If it is, continue with:

.. code-block:: console

   python3 -m venv automate
   source automate/bin/activate
   python -m pip install --upgrade pip
   python -m pip install .
   auto-incucyte --help

The word ``(automate)`` at the beginning of the prompt means the environment is
on.

Mac reports Python 3.9
----------------------

Do not create the environment with Python 3.9. If Miniconda Python 3.13 is
installed, check it and create the environment with it:

.. code-block:: console

   /opt/miniconda3/bin/python3.13 --version
   /opt/miniconda3/bin/python3.13 -m venv automate
   source automate/bin/activate
   python --version
   python -m pip install --upgrade pip
   python -m pip install .

The ``python --version`` command after activation should now report 3.13.

Every new Terminal window
-------------------------

Return to the downloaded folder and reactivate the environment:

.. code-block:: console

   cd auto-incucyte
   source automate/bin/activate

Run ``deactivate`` when finished.

Updating
--------

From the cloned project folder with ``automate`` activated:

.. code-block:: console

   git pull
   python -m pip install --upgrade .

Direct installation from GitHub
-------------------------------

Experienced users may install without cloning:

.. code-block:: console

   python -m pip install git+https://github.com/jmwarrington/auto-incucyte.git
