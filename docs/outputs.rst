Understanding the outputs
=========================

Directory layout
----------------

.. code-block:: text

   incucyte_results/
   ├── tables/
   │   ├── incucyte_long.csv
   │   ├── incucyte_raw_summary.csv
   │   ├── incucyte_normalized_long.csv
   │   ├── incucyte_plot_data.csv
   │   ├── incucyte_log2_plot_data.csv
   │   ├── normalization_audit.csv
   │   ├── plot_layout_template.csv
   │   └── plot_layout_used.csv
   └── plots/
       ├── incucyte_normalized_01_all_sequences.png
       ├── incucyte_log2_01_all_sequences.png
       └── plot_manifest.csv

Raw tables
----------

``incucyte_long.csv`` contains one mapped physical-well measurement per row,
with source file, plate, well, sample, replicate, time, metric, and raw value.

``incucyte_raw_summary.csv`` summarizes raw values by plate, sample, time, and
metric before normalization.

Normalized tables
-----------------

``incucyte_normalized_long.csv`` retains each physical well and adds its baseline
raw value, linear fold change, and log2 fold change.

``incucyte_plot_data.csv`` and ``incucyte_log2_plot_data.csv`` contain the exact
mean and SEM arrays supplied to Matplotlib. Use these files for downstream
statistics or figure reproduction.

Normalization audit
-------------------

``normalization_audit.csv`` gives each sample's raw baseline range, number of
baseline replicates, per-well normalized range, plotted mean, and SEM. The
normalized values and plotted mean must be 1.0 at baseline.

Plot manifest
-------------

``plot_manifest.csv`` records which samples and controls appear in each PNG, the
plot name, color map, scale, normalization description, plotted column, first
plotted hour, and SEM setting.

Plot-layout records
-------------------

``plot_layout_template.csv`` is a ready-to-edit spreadsheet containing every
available sequence. Duplicate and edit rows to create custom figures.

``plot_layout_used.csv`` records the exact layout used for the current run,
including spaces and original display capitalization in every name.
