Configuring the analysis
========================

.. important::

   On this page, ``...`` means “keep the metadata file, plate export, and output
   parts of the complete command from the :doc:`quickstart`.” Do not type the
   three dots. The quick-start and :doc:`examples` pages contain complete
   copy-and-paste commands.

Baseline hour
-------------

The default is 0 hours:

.. code-block:: console

   auto-incucyte ... --baseline-hour 0

Normalize to another recorded hour when the experimental design requires it:

.. code-block:: console

   auto-incucyte ... --baseline-hour 2

Measurements before the selected baseline are retained in output tables but are
not drawn on the plots. Every physical replicate must contain exactly one row at
the chosen hour.

Controls
--------

The default controls are ``WT``, ``Shuffle``, and ``NALM6``. Present controls
receive stable control styles on the default all-sequences plot. Provide
another comma-separated list:

.. code-block:: console

   auto-incucyte ... --controls 'WT, Vehicle, Untreated'

Names are matched case-insensitively to metadata labels. Disable special control
handling with an empty string:

.. code-block:: console

   auto-incucyte ... --controls ''

Default plot
------------

Without any plotting options, every sequence and control is shown on one graph.
The program makes one linear PNG and one log2 PNG from that same layout.

Custom plot layout spreadsheet
------------------------------

Every run writes ``tables/plot_layout_template.csv``. Open it in Excel,
Numbers, or Google Sheets. Each row defines one plot:

.. code-block:: text

   plot_name,sequence_1,sequence_2,control_1,control_2
   CD28 comparison,CD28 sequence 1,CD28 sequence 2,Wild Type Control,Untransduced Cells
   4-1BB comparison,4-1BB sequence 1,4-1BB sequence 2,Wild Type Control,Untransduced Cells

Add rows to create more plots. Add ``sequence_3`` or ``control_3`` columns when
a plot needs more lines. Each control column applies only to its row, so control
sets are completely user-defined per plot. To use the edited file:

.. code-block:: console

   auto-incucyte ... --plot-layout "my plot layout.csv"

Names are matched case-insensitively against the metadata. Spaces are preserved
in plot titles and legends. A correctly quoted CSV cell can also contain commas.
If a name does not match, the error lists every available sequence name.

Automatic grouping remains available with ``--group-size``. It always adds
group plots after the complete ``All sequences`` plot; it never replaces that
complete plot. The layout CSV is recommended when exact membership and titles
matter.

Drop time points or hide samples
--------------------------------

Remove selected recorded hours from normalized tables and every plot:

.. code-block:: console

   auto-incucyte ... --drop-time '22, 55'

The original reshaped raw tables retain those measurements, and the baseline
hour cannot be dropped. Hide samples from plots without removing their table
data with:

.. code-block:: console

   auto-incucyte ... --hide-sample '70, NALM6'

Color map
---------

The default color map remains ``plasma``. Any Matplotlib color map can be used:

.. code-block:: console

   auto-incucyte ... --cmap viridis

Common choices include ``magma``, ``inferno``, ``cividis``, ``turbo``, and
``tab10``. The chosen map is recorded in ``plot_manifest.csv``.

Exact per-sample styles
-----------------------

Every run writes ``tables/color_mapping_metadata_template.csv``. Edit it in a
spreadsheet to set an exact color, marker, line style, line width, marker size,
marker-edge width, drawing order, and legend label for each sample. Then run:

.. code-block:: console

   auto-incucyte ... \
     --color-mapping-metadata 'my exact plot styles.csv'

Colors may be names such as ``navy`` or hex values such as ``#2A6FDB``. Common
markers are ``o``, ``s``, ``^``, ``D``, ``X``, and ``P``. Common line styles
are ``-``, ``--``, ``:``, and ``-.``. The final resolved styles are recorded in
``color_mapping_metadata_used.csv``.

Typography, legends, axes, and reference lines
-----------------------------------------------

Choose an installed font and either a base size or exact component sizes:

.. code-block:: console

   auto-incucyte ... \
     --font 'Times New Roman' \
     --title-font-size 16 \
     --axis-font-size 13 \
     --tick-font-size 11 \
     --legend-font-size 10

Move the legend and change axis-spine thickness:

.. code-block:: console

   auto-incucyte ... \
     --legend-location 'upper left' \
     --legend-columns 1 \
     --x-axis-linewidth 2 \
     --y-axis-linewidth 2.5

Add separate reference values to linear and log2 plots. Repeat either line flag
to add more values:

.. code-block:: console

   auto-incucyte ... \
     --h-line 2 \
     --h-line 3 \
     --log2-h-line 1 \
     --h-line-color '#555555' \
     --h-line-style='--' \
     --h-line-width 1.5 \
     --h-line-alpha 0.7

Standard error
--------------

SEM ribbons are shown when at least two physical replicates are available. Hide
them with:

.. code-block:: console

   auto-incucyte ... --no-sem

Titles and axis labels
----------------------

.. code-block:: console

   auto-incucyte ... \
     --title-prefix "Incucyte killing assay" \
     --y-label "Normalized NALM6 area (µm²/image)" \
     --log2-title-prefix "Incucyte killing assay — log2" \
     --log2-y-label "Log2 fold change"

Output resolution is controlled with ``--dpi``; the default is 200.
