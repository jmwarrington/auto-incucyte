Important limitations and best practices
========================================

Baseline must be measured
-------------------------

The selected baseline is not interpolated. Every physical well must have exactly
one finite, nonzero measurement at that recorded elapsed hour.

Positive values are required for log2 plots
--------------------------------------------

Linear normalization can represent a positive raw value divided by a positive
baseline. Log2 fold change additionally requires every resulting fold change to
be greater than zero. A zero or negative value stops the run rather than being
silently omitted.

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
* Archive ``plot_layout_used.csv`` so figure membership and controls remain
  reproducible.
* Use the plot-data tables, not pixels from the PNG, for quantitative follow-up.
