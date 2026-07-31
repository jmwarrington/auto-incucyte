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
