Command-line reference
======================

Show the exact reference for the installed version:

.. code-block:: console

   auto-incucyte --help

Maintenance
-----------

``--update``
   Download and install the newest release from the official GitHub repository
   into the currently active Python environment, then exit. No metadata or
   plate files are needed.

``--version``
   Print the installed auto-incucyte version and exit.

Input and output
----------------

``--metadata PATH``
   Required CSV containing ``well``, ``sample``, and ``plate``.

``PLATE_FILES``
   One or more native exports. Use a bare path for one metadata plate or
   ``PLATE=FILE`` for each of several plates.

``--output PATH``
   Folder for all tables and plots. Default: ``incucyte_results``. Existing
   unrelated files are never deleted; matching generated filenames are
   overwritten after a warning.

``--baseline-hour NUMBER``
   Per-well normalization hour. Default: 0.

``--refeed-time '48, 120, 192'``
   Comma-separated actual refeed event hours. For each event, the first
   recorded image at or after that time becomes the next per-well baseline.
   Decimal values are accepted and the option may be repeated.
   ``--refeed-times`` is an alias.

``--metric NAME``
   Select one metric when exports contain several.

Selecting plots and data
------------------------

``--controls 'NAME 1, NAME 2'``
   Controls for default or automatic-group plots. The default is
   ``WT,Shuffle,NALM6``. Quote the whole comma-separated list. Use
   ``--controls ''`` for none.

``--plot-layout PATH``
   CSV with one row per desired plot and ``plot_name``, ``sequence_1``,
   ``control_1``, and similar columns.

``--group-size NUMBER``
   Add automatic plots containing this many non-control sequences. The complete
   all-sequences plot is always created first. Cannot be combined with
   ``--plot-layout``.

``--drop-time '22, 55'``
   Remove comma-separated elapsed hours from normalized tables and every plot.
   Raw reshaped tables retain them. May be repeated. Neither the initial
   baseline nor a resolved post-refeed baseline can be dropped.

``--hide-sample '70, NALM6'``
   Hide comma-separated samples from every plot while retaining their data in
   the tables. Matching is case-insensitive and the option may be repeated.

``--drop-sample-after '119.5: 72, 74, 75, Shuffle'``
   Retain each named sample before the cutoff and exclude it at and after that
   elapsed hour. Use this when samples were physically removed and later plate
   readings are zero or invalid. The cutoff need not exactly match an imaging
   time. Quote the complete rule, and repeat the option for different cutoffs.
   Names containing spaces are supported. ``--drop-samples-after`` is an alias.

Colors and per-sample styling
-----------------------------

``--cmap NAME``
   Matplotlib color map for sequence lines. Default: ``plasma``.

``--max-cmap-position NUMBER``
   Upper sampled position in the color map, from 0.08 through 1.0. Default:
   0.72. ``--max-plasma-position`` is a backward-compatible alias.

``--color-mapping-metadata PATH``
   Optional CSV assigning exact per-sample ``color``, ``marker``,
   ``linestyle``, ``linewidth``, ``markersize``, ``markeredgewidth``,
   ``zorder``, and ``legend_label`` values. Start from the automatically
   generated template.

Typography and labels
---------------------

``--font NAME``
   Installed font family, such as ``Avenir``, ``Arial``, or
   ``'Times New Roman'``. The default prefers Avenir and falls back safely.

``--font-size NUMBER``
   Base font size. Default: 12.

``--title-font-size NUMBER``, ``--axis-font-size NUMBER``, ``--tick-font-size NUMBER``, ``--legend-font-size NUMBER``
   Optional precise sizes for individual figure elements.

``--title-prefix TEXT``, ``--y-label TEXT``, ``--log2-title-prefix TEXT``, ``--log2-y-label TEXT``
   Customize figure text. Quote values containing spaces.

``--refeed-title-prefix TEXT``, ``--refeed-y-label TEXT``, ``--refeed-log2-title-prefix TEXT``, ``--refeed-log2-y-label TEXT``
   Customize only the refeed-normalized linear and log2 plot text.

Legend, axes, and reference lines
---------------------------------

``--legend-location LOCATION``
   ``best``, ``upper right``, ``upper left``, ``lower left``, ``lower right``,
   ``right``, ``center left``, ``center right``, ``lower center``,
   ``upper center``, or ``center``. Default: ``best``.

``--legend-columns NUMBER``
   Number of legend columns. Default: 2.

``--x-axis-linewidth NUMBER``, ``--y-axis-linewidth NUMBER``
   Horizontal and vertical axis-spine thickness. Default: 1.

``--h-line Y``
   Add a horizontal line to linear plots. Repeat the flag for multiple lines.

``--log2-h-line Y``
   Add a horizontal line to log2 plots. Repeat the flag for multiple lines.

``--h-line-color COLOR``, ``--h-line-style STYLE``, ``--h-line-width NUMBER``, ``--h-line-alpha NUMBER``
   Shared appearance of custom horizontal lines. Alpha ranges from 0 through 1.
   For a value beginning with dashes, use ``--h-line-style='--'``.

``--refeed-line-color COLOR``, ``--refeed-line-style STYLE``, ``--refeed-line-width NUMBER``, ``--refeed-line-alpha NUMBER``
   Appearance of the vertical refeed-event markers. Defaults are teal, dotted,
   1.2 points, and 0.65 alpha.

``--no-refeed-labels``
   Keep the vertical refeed lines but hide their rotated text labels.

Other plotting controls
-----------------------

``--no-sem``
   Hide SEM ribbons.

``--dpi NUMBER``
   PNG resolution. Default: 200.

.. tip::

   Paths, font names, titles, and comma-separated lists containing spaces should
   be enclosed in straight quotation marks.
