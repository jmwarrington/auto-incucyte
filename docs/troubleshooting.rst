Troubleshooting
===============

``No 'Time Stamp:' blocks found``
---------------------------------

Confirm that the file is a native Incucyte tab-delimited export or compatible
legacy CSV. Opening and resaving in spreadsheet software can change delimiters
or header rows.

Could not infer or assign the plate
-----------------------------------

For one plate, metadata must contain exactly one plate identifier. For multiple
plates, label every argument as ``PLATE=FILE``.

No measured wells matched metadata
----------------------------------

Compare plate identifiers and well labels in the export and metadata. Metadata
well names should look like ``B2``, not ``B02`` or ``2B``.

No baseline measurements found
-------------------------------

Inspect the ``elapsed_hours`` values in ``incucyte_long.csv`` and choose one of
those exact recorded hours with ``--baseline-hour``.

Baseline is zero or non-finite
------------------------------

The affected well cannot be divided by its baseline. Check the raw export and
experimental plate, then choose a scientifically appropriate baseline or remove
the invalid well from metadata with a documented reason.

Duplicate replicate/time rows
-----------------------------

The same export may have been supplied twice, or two files may represent the
same plate. Each metadata plate must map to one export per run.

Multiple metrics detected
-------------------------

Rerun with ``--metric`` and the exact desired metric name printed in the error.

Missing control warning
-----------------------

This warning does not stop analysis. Correct the metadata label or update
``--controls`` to the controls used in this experiment.

Controls with spaces are split or rejected
-------------------------------------------

Quote the entire comma-separated value, not the individual words:

.. code-block:: console

   auto-incucyte \
     --metadata 'plate metadata.csv' \
     'raw plate 1.txt' \
     --controls 'WT, Wild Type Control, Shuffle' \
     --output 'incucyte_results'

``Plot layout name ... was not found``
--------------------------------------

Copy the name from the metadata ``sample`` column or from the generated
``plot_layout_template.csv``. Spaces are supported and capitalization does not
matter. If a name contains a comma, keep it in one quoted spreadsheet cell.

``Unknown Matplotlib color map``
--------------------------------

Check the spelling passed to ``--cmap``. Common choices are ``plasma``,
``viridis``, ``magma``, ``inferno``, ``cividis``, ``turbo``, and ``tab10``.

Matplotlib font warning
-----------------------

The program prefers Avenir and falls back to DejaVu Sans when Avenir is not
installed. This changes typography, not values or normalization.

``Font ... is not installed``
-----------------------------

The value passed to ``--font`` must be installed on the current computer. Try
``Avenir``, ``Arial``, ``Times New Roman``, or ``DejaVu Sans`` depending on the
system. Quote font names containing spaces.

Color-mapping metadata error
----------------------------

Start from ``color_mapping_metadata_template.csv``. Confirm that every sample
matches the plate metadata and that colors, markers, line styles, and numeric
sizes are valid. The error reports the problematic spreadsheet row.

Requested drop time was not found
---------------------------------

Inspect the exact ``elapsed_hours`` values in ``incucyte_long.csv``. This is a
warning; the analysis continues and reports which requested values were absent.

``Log2 fold change requires every normalized measurement to be positive``
-------------------------------------------------------------------------

If the listed samples were physically removed from the plate, the instrument
may have exported zero readings afterward. End those samples at the removal
time, for example:

.. code-block:: console

   auto-incucyte ... --drop-sample-after '119.5: 72, 74, 75, Shuffle'

This retains their earlier data and excludes readings at or after the cutoff.
Do not use this merely to hide genuine biological zero values; log2 is
mathematically undefined for those values and the scientific handling must be
chosen explicitly.

``Cannot drop baseline hour``
-----------------------------

Normalization requires that measurement. Remove it from ``--drop-time`` or
select a different scientifically appropriate ``--baseline-hour``.

Refeed has no recorded image afterward
---------------------------------------

The entered event occurs after the final Incucyte measurement. Correct the
event time or provide an export that includes later images.

Missing refeed baseline for a physical well
-------------------------------------------

The program found the first recorded image at or after the event, but at least
one physical well that has later retained data lacks a value at that elapsed
hour. Inspect ``incucyte_long.csv`` and the source export. The run stops rather
than silently using different baseline images for different wells; that would
invalidate replicate comparisons. A sample intentionally removed before this
segment should be ended with ``--drop-sample-after``.

Two refeeds resolve to the same image
-------------------------------------

The refeed events are closer together than the image-acquisition interval.
Correct the entered times or decide which single event should define that
segment.

``Cannot drop ... first recorded image after a refeed``
-------------------------------------------------------

That image is required as a segment denominator. Remove it from ``--drop-time``
or remove/correct the associated ``--refeed-time``.

Existing output directory warning
---------------------------------

This warning protects the experiment record. Matching generated filenames will
be overwritten, but no other files are deleted. Choose a new descriptive
``--output`` folder to keep runs completely separate.
