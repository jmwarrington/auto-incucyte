What is auto-incucyte?
======================

``auto-incucyte`` is a one-command analysis workflow for Incucyte time-course
exports. It keeps normalization at the physical-well level, then summarizes
replicates for plotting.

What can it do?
---------------

* Read native tab-delimited Incucyte ``.txt`` and ``.tsv`` exports.
* Read legacy comma-delimited ``.csv`` copies.
* Map plate wells to samples with a simple metadata CSV.
* Combine multiple explicitly labeled plates.
* Select one assay metric when an export contains several.
* Normalize each well to a user-selected baseline hour.
* Renormalize each well after repeated cell refeeds while retaining global
  normalization as a companion view.
* Calculate replicate mean and SEM on linear and log2 fold-change scales.
* Put every line on one plot by default.
* Define any number of named plots, their sequence lines, and per-plot controls
  with an editable CSV spreadsheet.
* Preserve sequence names containing spaces and match capitalization
  forgivingly.
* Keep ``plasma`` as the default color map or select any Matplotlib color map.
* Write the raw, normalized, plotted, and audited values as CSV files.
* Create presentation-ready PNG plots without requiring a graphical desktop.

How normalization works
-----------------------

For every physical well independently:

.. math::

   \mathrm{fold\ change}_{well,t} =
   \frac{\mathrm{raw\ value}_{well,t}}
        {\mathrm{raw\ value}_{well,baseline}}

The fold changes—not the raw measurements—are averaged across replicate wells
at each time point. Every valid well must therefore equal exactly 1.0 at the
baseline. The log2 plot uses ``log2(fold change)`` and equals 0.0 at baseline.

For a refeeding experiment, the denominator changes piecewise. Each
measurement is divided by the same well's value at the most recent segment
baseline: the initial ``--baseline-hour`` or the first recorded image at or
after the most recent ``--refeed-time``. Every segment therefore begins at 1.0
on the linear scale and 0.0 on the log2 scale.

Workflow at a glance
--------------------

.. code-block:: text

   native export(s) + well/sample metadata
                      |
                      v
       reshaped and validated per-well table
                      |
                      v
          baseline normalization per well
                      |
                      v
        replicate summaries + plots + audit

The program never uploads Incucyte data. All analysis happens locally.
