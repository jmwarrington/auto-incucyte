Configuring the analysis
========================

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

   auto-incucyte ... --controls WT,Vehicle,Untreated

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

Automatic grouping remains available with ``--group-size``, but the layout CSV
is recommended when exact plot membership and titles matter.

Color map
---------

The default color map remains ``plasma``. Any Matplotlib color map can be used:

.. code-block:: console

   auto-incucyte ... --cmap viridis

Common choices include ``magma``, ``inferno``, ``cividis``, ``turbo``, and
``tab10``. The chosen map is recorded in ``plot_manifest.csv``.

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
