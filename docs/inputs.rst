Preparing input files
=====================

Plate metadata
--------------

Create a comma-delimited CSV with three required columns:

.. code-block:: text

   well,sample,plate
   B2,Shuffle,1
   B3,Construct_65,1
   B4,Construct_67,1
   C2,Shuffle,1
   C3,Construct_65,1
   C4,Construct_67,1

``well``
   Physical plate position such as ``B2``. Rows A–P and columns 1–24 are
   accepted.

``sample``
   Label shown in tables and plot legends. Repeated labels define replicates.
   Spaces are fully supported, for example ``CD28 sequence 1`` or
   ``Wild Type Control``. Keep the spelling consistent between metadata and an
   optional plot-layout CSV. Capitalization differences are accepted.

``plate``
   Plate identifier used to match metadata with an export. Numeric identifiers
   such as ``1`` and text identifiers are supported.

Each plate/well combination may appear only once. Wells not listed in metadata
are ignored, so unused plate positions do not need placeholder rows.

Native Incucyte export
----------------------

Export the desired Incucyte metric as its native tab-delimited TXT or TSV file.
The parser looks for the export's ``Vessel Name``, ``Metric``, ``Analysis``,
``Time Stamp``, ``Elapsed``, plate-column header, and well rows.

Do not manually reshape the native file. Keeping the vendor export unchanged
makes the analysis easier to reproduce and audit.

One plate
---------

When metadata contains one plate, supply one bare file path:

.. code-block:: console

   auto-incucyte --metadata metadata.csv plate_1.txt

Multiple plates
---------------

Map every plate explicitly as ``PLATE=FILE``:

.. code-block:: console

   auto-incucyte \
     --metadata metadata.csv \
     1=plate_1.txt 2=plate_2.txt \
     --output combined_results

Explicit labels prevent a file from being silently assigned to the wrong plate.

Multiple assay metrics
----------------------

If the reshaped data contains more than one nonblank metric, select exactly one:

.. code-block:: console

   auto-incucyte ... --metric "Total green object area"

Plot-layout CSV
---------------

This optional spreadsheet controls how many plots are created and which lines
appear on each one. Start from the automatically generated
``tables/plot_layout_template.csv`` instead of making the headers manually.

``plot_name``
   The title suffix and filename label for that row's plot. Spaces are allowed.

``sequence_1``, ``sequence_2``, ...
   Experimental sequence names copied from the metadata ``sample`` column.

``control_1``, ``control_2``, ...
   Control names for this specific plot. Repeat the same names on multiple rows
   when those controls should appear on multiple plots.
