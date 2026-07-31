Worked examples
===============

Example 1: normalize a single plate to 2 hours
------------------------------------------------

.. code-block:: console

   auto-incucyte \
     --metadata plate_metadata.csv \
     2026_07_28_total_integrated_intensity.txt \
     --baseline-hour 2 \
     --output incucyte_results

Example 2: combine two plates
-----------------------------

.. code-block:: console

   auto-incucyte \
     --metadata two_plate_metadata.csv \
     1=plate_1.txt 2=plate_2.txt \
     --baseline-hour 0 \
     --output combined_results

Example 3: custom plots and controls
------------------------------------

Create ``my_plots.csv`` in a spreadsheet editor:

.. code-block:: text

   plot_name,sequence_1,sequence_2,control_1
   CD28 sequences,CD28 sequence A,CD28 sequence B,Wild Type Control
   4-1BB sequences,4-1BB sequence A,4-1BB sequence B,Untransduced Cells

Then run:

.. code-block:: console

   auto-incucyte \
     --metadata metadata.csv \
     plate.txt \
     --plot-layout my_plots.csv \
     --output custom_plot_results

Example 4: choose one metric and hide SEM
-----------------------------------------

.. code-block:: console

   auto-incucyte \
     --metadata metadata.csv \
     plate.txt \
     --metric "Total green object area" \
     --no-sem \
     --output green_area_results

Example 5: filenames containing spaces
--------------------------------------

Quote any shell path containing spaces:

.. code-block:: console

   auto-incucyte \
     --metadata "metadata files/plate layout.csv" \
     "raw exports/plate 1.txt" \
     --output "analysis results"

Example 6: another color map
----------------------------------------

In the short option examples below, ``...`` means to retain the metadata,
plate-file, and output arguments from one of the complete commands above. Do not
type the three dots.

Keep the same analysis and use ``viridis`` for experimental sequences:

.. code-block:: console

   auto-incucyte ... --cmap viridis

Example 7: groups plus a complete plot
--------------------------------------

Create the complete all-sequences figure and additional groups of five. The
quoted controls appear on every group:

.. code-block:: console

   auto-incucyte ... --controls 'WT, Shuffle' --group-size 5

Example 8: drop time points and hide samples
--------------------------------------------

.. code-block:: console

   auto-incucyte ... \
     --drop-time '22, 55' \
     --hide-sample '70, NALM6'

Example 9: manuscript styling
-----------------------------

After editing ``color_mapping_metadata_template.csv``:

.. code-block:: console

   auto-incucyte ... \
     --color-mapping-metadata 'manuscript plot styles.csv' \
     --font 'Arial' \
     --title-font-size 16 \
     --axis-font-size 13 \
     --legend-location 'upper left' \
     --legend-columns 1 \
     --x-axis-linewidth 2 \
     --y-axis-linewidth 2 \
     --h-line 2 \
     --log2-h-line 1

The repository's ``examples/color_mapping_metadata.csv`` is a ready-to-run
style file using the bundled synthetic data.

Expected plotting behavior
--------------------------

At the baseline hour every sample is exactly 1.0 on the linear plot and 0.0 on
the log2 plot. After baseline, increasing signal appears above 1.0, decreasing
signal below 1.0, and unchanged signal near 1.0.
