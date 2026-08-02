Important limitations and best practices
========================================

Baseline must be measured
-------------------------

The selected baseline is not interpolated. Every physical well must have exactly
one finite, nonzero measurement at that recorded elapsed hour.

Refeed normalization answers a segment-local question
------------------------------------------------------

Refeed-normalized fold change describes change since the most recent refeed
baseline, not cumulative change since the beginning of the experiment. The
program therefore retains the original globally normalized plots under
``incucyte_global_*`` names. The standard plot names contain the
refeed-normalized view. Interpret both according to the biological question.

The entered refeed hour marks the intervention. The denominator is the first
recorded image at or after that hour. Refeed timing and image timing should be
documented with the experiment.

Positive values are required for log2 plots
--------------------------------------------

Linear normalization can represent a positive raw value divided by a positive
baseline. Log2 fold change additionally requires every resulting fold change to
be greater than zero. A zero or negative value stops the run rather than being
silently omitted.

If zeros occur because a sample was physically removed from the plate, use
``--drop-sample-after`` to end that sample at its removal time. This is an
explicit experimental exclusion, not a general method for discarding genuine
zero measurements.

Replicates are physical wells
-----------------------------

Replicate identity is derived from vessel/source/plate plus well or replicate
metadata. Duplicate measurements for the same replicate and time point are
rejected, commonly revealing that an export was included twice.

The program does not perform hypothesis tests
---------------------------------------------

Plots show mean and SEM. Statistical testing, multiple-comparison correction,
curve fitting, and area-under-the-curve analysis are outside the current scope.

Best practices
--------------

* Keep the original vendor export unchanged.
* Store the metadata CSV with the experimental record.
* Inspect warnings about missing controls or metadata wells.
* Verify the metric name and units before interpreting the y-axis.
* Inspect ``normalization_audit.csv`` for every run.
* For refeeding experiments, archive ``refeed_schedule_used.csv`` and inspect
  ``refeed_normalization_audit.csv``.
* When samples were physically removed, archive
  ``sample_removal_cutoffs_used.csv``.
* Archive ``plot_layout_used.csv`` so figure membership and controls remain
  reproducible.
* Archive ``color_mapping_metadata_used.csv`` so exact plot styling remains
  reproducible.
* Use a new descriptively named output directory for each final analysis. Reruns
  never delete files, so an intentionally reused folder can retain old plots
  whose filenames are not regenerated.
* Use the plot-data tables, not pixels from the PNG, for quantitative follow-up.
