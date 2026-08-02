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
   │   ├── incucyte_global_normalized_long.csv
   │   ├── incucyte_global_plot_data.csv
   │   ├── incucyte_global_log2_plot_data.csv
   │   ├── global_normalization_audit.csv
   │   ├── refeed_normalization_audit.csv
   │   ├── refeed_schedule_used.csv
   │   ├── sample_removal_cutoffs_used.csv
   │   ├── plot_layout_template.csv
   │   ├── plot_layout_used.csv
   │   ├── color_mapping_metadata_template.csv
   │   └── color_mapping_metadata_used.csv
   └── plots/
       ├── incucyte_normalized_01_all_sequences.png
       ├── incucyte_log2_01_all_sequences.png
       ├── incucyte_global_normalized_01_all_sequences.png
       ├── incucyte_global_log2_01_all_sequences.png
       └── plot_manifest.csv

The ``global`` and ``refeed`` audit files are created only when
``--refeed-time`` is used. The sample-removal record is created only when
``--drop-sample-after`` is used.

Raw tables
----------

``incucyte_long.csv`` contains one mapped physical-well measurement per row,
with source file, plate, well, sample, replicate, time, metric, and raw value.

``incucyte_raw_summary.csv`` summarizes raw values by plate, sample, time, and
metric before normalization.

Normalized tables
-----------------

``incucyte_normalized_long.csv`` retains each physical well and adds its
baseline raw value, linear fold change, and log2 fold change. When refeeds are
specified, this standard file uses the most recent segment baseline and includes
the segment metadata.

``incucyte_plot_data.csv`` and ``incucyte_log2_plot_data.csv`` contain the exact
mean and SEM arrays supplied to Matplotlib. Use these files for downstream
statistics or figure reproduction.

Global comparison and refeed records
------------------------------------

When ``--refeed-time`` is used, the standard normalized tables and plots are
the refeed-normalized results. They add ``normalization_segment``,
``segment_baseline_hour``, ``refeed_event_hour``, ``hours_since_refeed``, the
raw segment baseline, and segment-local fold change.

``incucyte_global_normalized_long.csv``, ``incucyte_global_plot_data.csv``, and
``incucyte_global_log2_plot_data.csv`` retain the original interpretation using
only ``--baseline-hour``. ``global_normalization_audit.csv`` verifies it.

``refeed_schedule_used.csv`` maps each entered event to the first recorded
post-refeed image chosen as its baseline. ``refeed_normalization_audit.csv``
shows that every individual well and plotted sample equals 1.0 at every segment
baseline.

Sample-removal record
---------------------

``sample_removal_cutoffs_used.csv`` records each sample passed to
``--drop-sample-after``, its requested cutoff, first removed recorded hour, last
retained hour, and number of excluded rows. The original ``incucyte_long.csv``
continues to contain every raw measurement.

Normalization audit
-------------------

Without refeeds, ``normalization_audit.csv`` gives each sample's raw baseline
range, number of baseline replicates, per-well normalized range, plotted mean,
and SEM. With refeeds, it instead audits every retained sample and segment. The
linear values must be 1.0 at every applicable baseline.

Plot manifest
-------------

``plot_manifest.csv`` records which samples and controls appear in each PNG, the
plot name, color map, scale, normalization description, plotted column, first
plotted hour, SEM setting, font sizes, legend configuration, axis widths,
horizontal lines, dropped times, sample-removal cutoffs, hidden samples, and
style-metadata source.
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
