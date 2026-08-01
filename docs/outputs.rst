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
   │   ├── incucyte_refeed_normalized_long.csv
   │   ├── incucyte_refeed_plot_data.csv
   │   ├── incucyte_refeed_log2_plot_data.csv
   │   ├── refeed_normalization_audit.csv
   │   ├── refeed_schedule_used.csv
   │   ├── plot_layout_template.csv
   │   ├── plot_layout_used.csv
   │   ├── color_mapping_metadata_template.csv
   │   └── color_mapping_metadata_used.csv
   └── plots/
       ├── incucyte_normalized_01_all_sequences.png
       ├── incucyte_log2_01_all_sequences.png
       ├── incucyte_refeed_normalized_01_all_sequences.png
       ├── incucyte_refeed_log2_01_all_sequences.png
       └── plot_manifest.csv

The files containing ``refeed`` are created only when ``--refeed-time`` is
used.

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

Refeed-normalized tables
------------------------

``incucyte_refeed_normalized_long.csv`` retains every physical well and adds
``normalization_segment``, ``segment_baseline_hour``, ``refeed_event_hour``,
``hours_since_refeed``, the raw segment baseline, and segment-local fold change.

``incucyte_refeed_plot_data.csv`` and
``incucyte_refeed_log2_plot_data.csv`` contain the exact segment-local mean and
SEM values plotted. The absolute ``elapsed_hours`` column remains the x-axis.

``refeed_schedule_used.csv`` maps each entered event to the first recorded
post-refeed image chosen as its baseline. ``refeed_normalization_audit.csv``
shows that every individual well and plotted sample equals 1.0 at every segment
baseline.

Normalization audit
-------------------

``normalization_audit.csv`` gives each sample's raw baseline range, number of
baseline replicates, per-well normalized range, plotted mean, and SEM. The
normalized values and plotted mean must be 1.0 at baseline.

Plot manifest
-------------

``plot_manifest.csv`` records which samples and controls appear in each PNG, the
plot name, color map, scale, normalization description, plotted column, first
plotted hour, SEM setting, font sizes, legend configuration, axis widths,
horizontal lines, dropped times, hidden samples, and style-metadata source.
When refeeds are used, it also records requested event times, resolved baseline
images, marker styling, and whether lines were broken between segments.

Plot-layout records
-------------------

``plot_layout_template.csv`` is a ready-to-edit spreadsheet containing every
available sequence. Duplicate and edit rows to create custom figures.

``plot_layout_used.csv`` records the exact layout used for the current run,
including spaces and original display capitalization in every name.

Color and style records
-----------------------

``color_mapping_metadata_template.csv`` contains editable defaults for each
plotted sample. ``color_mapping_metadata_used.csv`` records the exact resolved
color, marker, line style, dimensions, drawing order, and optional legend label
used in the current run.

Safe reruns
-----------

An existing output directory is never cleared. The program warns, overwrites
generated files with matching names, and leaves every unrelated file or old
plot with a different name untouched. A new descriptively named output folder
is recommended when separate run histories are needed.

When ``--drop-time`` is used, the raw tables retain all original time points;
normalized and plot-data tables omit the selected hours. When ``--hide-sample``
is used, all tables retain the sample while plot layout records and figures
omit it.
