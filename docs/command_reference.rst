Command-line reference
======================

Show the complete reference for the installed version:

.. code-block:: console

   auto-incucyte --help

Core arguments
--------------

``--metadata PATH``
   Required CSV containing ``well``, ``sample``, and ``plate``.

``PLATE_FILES``
   One or more positional native exports. Use a bare path for one metadata plate
   or ``PLATE=FILE`` for each of several plates.

``--output PATH``
   Parent folder for all tables and plots. Default: ``incucyte_results``.

``--baseline-hour NUMBER``
   Per-well normalization hour. Default: 0.

Plot arguments
--------------

``--plot-layout PATH``
   Optional CSV with one row per plot. Columns are ``plot_name``,
   ``sequence_1``, ``sequence_2``, ``control_1``, and so on. Without this
   option, every line is shown on one plot.

``--controls NAMES``
   Comma-separated controls for the default plot or automatic groups. Default:
   ``WT,Shuffle,NALM6``. A custom layout defines controls in its own columns.

``--group-size NUMBER``
   Optional automatic grouping by count. There is no default grouping; the
   normal default is one all-sequences plot. Use ``--plot-layout`` for exact
   membership and names.

``--cmap NAME``
   Any installed Matplotlib color map for sequence lines. Default: ``plasma``.

``--no-sem``
   Hide SEM ribbons.

``--dpi NUMBER``
   PNG resolution. Default: 200.

``--title-prefix``, ``--y-label``, ``--log2-title-prefix``, ``--log2-y-label``
   Customize figure text.

Data-selection arguments
------------------------

``--metric NAME``
   Select one metric when several are available.

``--max-cmap-position NUMBER``
   Upper sampled position in the selected color map. It must be from 0.08
   through 1.0; the default is 0.72. ``--max-plasma-position`` remains an alias
   for older commands.

.. tip::

   The installed ``--help`` output is authoritative for the package version on
   your computer.
