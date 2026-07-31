Quick start
===========

The repository includes synthetic data, so the complete workflow can be tested
without using experimental files.

1. Run the example
------------------

From the repository root:

.. code-block:: console

   auto-incucyte \
     --metadata examples/plate_metadata.csv \
     examples/plate_1.txt \
     --controls 'WT, Vehicle' \
     --baseline-hour 0 \
     --output example_results

2. Check the terminal summary
-----------------------------

A successful run reports:

* the number of plate files parsed;
* the number of mapped well-time observations;
* a maximum baseline error of zero on the linear and log2 scales;
* the number and location of plots created.

3. Open the results
-------------------

The most useful first files are:

.. code-block:: text

   example_results/plots/incucyte_normalized_01_all_sequences.png
   example_results/tables/incucyte_plot_data.csv
   example_results/tables/normalization_audit.csv

The first shows the biological pattern, the second contains the exact values
drawn, and the third verifies the baseline calculation.

The default figure contains every line. To create several named figures, open
``example_results/tables/plot_layout_template.csv``, duplicate or edit its rows,
and rerun with ``--plot-layout``.

If ``example_results`` already exists, the program warns before overwriting
matching generated filenames and never deletes unrelated files. Choose a new,
descriptive output name to preserve separate runs.

4. Substitute your own data
---------------------------

.. code-block:: console

   auto-incucyte \
     --metadata my_plate_metadata.csv \
     my_incucyte_export.txt \
     --baseline-hour 2 \
     --output my_results

.. important::

   Choose a baseline hour that appears exactly once in every physical well's
   time course and has a finite, nonzero measurement.
