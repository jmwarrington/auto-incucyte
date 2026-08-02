import csv
import os
import sys
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest import mock

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "auto_incucyte_mpl"))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from auto_incucyte.analysis import (
    HOURS_SINCE_REFEED_COLUMN,
    LOG2_PLOT_MEAN_COLUMN,
    NORMALIZED_COLUMN,
    PLOT_MEAN_COLUMN,
    RefeedEvent,
    SampleCutoff,
    SEGMENT_BASELINE_COLUMN,
    SEGMENT_COLUMN,
    STYLE_METADATA_FIELDS,
    add_log2_fold_change,
    colormap_colors,
    default_plot_definitions,
    drop_time_points,
    drop_samples_after,
    main,
    make_log2_plot_summary,
    make_plot_summary,
    normalize_by_refeed_segments,
    normalize_per_well,
    parse_plate_export,
    parse_sample_cutoffs,
    plot_sample,
    read_plot_layout,
    read_color_mapping_metadata,
    resolve_colormap_name,
    resolve_refeed_events,
    style_plot_axis,
)


class AnalysisTests(unittest.TestCase):
    def test_update_uses_active_python_and_official_github_repository(self):
        completed = mock.Mock(returncode=0)
        with mock.patch(
            "auto_incucyte.analysis.subprocess.run", return_value=completed
        ) as run:
            status = main(["--update"], prog="auto-incucyte")
        command = run.call_args.args[0]
        self.assertEqual(status, 0)
        self.assertEqual(
            command[:5], [sys.executable, "-m", "pip", "install", "--upgrade"]
        )
        self.assertEqual(
            command[5],
            "git+https://github.com/jmwarrington/auto-incucyte.git",
        )
        self.assertEqual(run.call_args.kwargs, {"check": False})

    def test_default_is_one_plot_with_every_sequence_and_control(self):
        definitions = default_plot_definitions(
            ["Sequence Alpha", "Sequence Beta", "Wild Type Control"],
            ["Wild Type Control"],
        )
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0].name, "All sequences")
        self.assertEqual(
            definitions[0].sequences, ["Sequence Alpha", "Sequence Beta"]
        )
        self.assertEqual(definitions[0].controls, ["Wild Type Control"])

    def test_group_size_keeps_all_sequences_plot_and_adds_groups(self):
        definitions = default_plot_definitions(
            ["Sequence 1", "Sequence 2", "Sequence 3", "WT"],
            ["WT"],
            group_size=2,
        )
        self.assertEqual(
            [definition.name for definition in definitions],
            ["All sequences", "Group 1", "Group 2"],
        )
        self.assertEqual(definitions[0].sequences, ["Sequence 1", "Sequence 2", "Sequence 3"])
        self.assertEqual(definitions[1].controls, ["WT"])

    def test_drop_times_protects_baseline(self):
        raw = pd.DataFrame(
            {"elapsed_hours": [0.0, 2.0, 4.0], "sample": ["A", "A", "A"]}
        )
        filtered = drop_time_points(raw, [2.0], 0.0)
        self.assertEqual(filtered["elapsed_hours"].tolist(), [0.0, 4.0])
        with self.assertRaisesRegex(ValueError, "Cannot drop baseline hour"):
            drop_time_points(raw, [0.0], 0.0)
        with self.assertRaisesRegex(ValueError, "first recorded image after a refeed"):
            drop_time_points(raw, [2.0], 0.0, [2.0])

    def test_refeed_events_resolve_to_first_recorded_image_after_event(self):
        raw = pd.DataFrame(
            {
                "elapsed_hours": [0.0, 47.0, 49.0, 119.0, 121.0],
                "sample": ["A"] * 5,
            }
        )
        events = resolve_refeed_events(raw, [48.0, 120.0], 0.0)
        self.assertEqual(
            events,
            [RefeedEvent(48.0, 49.0), RefeedEvent(120.0, 121.0)],
        )

    def test_piecewise_refeed_normalization_resets_every_well(self):
        times = [0.0, 24.0, 49.0, 72.0, 121.0, 144.0]
        raw = pd.DataFrame(
            {
                "sample": ["A"] * 12,
                "series_id": ["well1"] * 6 + ["well2"] * 6,
                "elapsed_hours": times + times,
                "raw_value": (
                    [10.0, 20.0, 100.0, 200.0, 50.0, 100.0]
                    + [20.0, 40.0, 200.0, 400.0, 100.0, 200.0]
                ),
            }
        )
        events = [RefeedEvent(48.0, 49.0), RefeedEvent(120.0, 121.0)]
        normalized = normalize_by_refeed_segments(raw, 0.0, events)
        self.assertTrue(
            np.allclose(
                normalized[NORMALIZED_COLUMN],
                [1.0, 2.0, 1.0, 2.0, 1.0, 2.0] * 2,
            )
        )
        self.assertEqual(set(normalized[SEGMENT_COLUMN]), {0, 1, 2})
        self.assertEqual(
            normalized.loc[
                normalized["elapsed_hours"].eq(121.0), SEGMENT_BASELINE_COLUMN
            ].unique().tolist(),
            [121.0],
        )
        self.assertEqual(
            normalized.loc[
                normalized["elapsed_hours"].eq(144.0), HOURS_SINCE_REFEED_COLUMN
            ].unique().tolist(),
            [23.0],
        )
        summary = make_plot_summary(normalized, 0.0, [49.0, 121.0])
        reset_rows = summary.loc[summary["elapsed_hours"].isin([0.0, 49.0, 121.0])]
        self.assertTrue(np.allclose(reset_rows[PLOT_MEAN_COLUMN], 1.0))

    def test_removed_sample_can_end_before_a_later_refeed_segment(self):
        raw = pd.DataFrame(
            {
                "sample": ["A", "A", "A", "B", "B"],
                "series_id": ["well1", "well1", "well1", "well2", "well2"],
                "elapsed_hours": [0.0, 2.0, 4.0, 0.0, 1.0],
                "raw_value": [10.0, 20.0, 30.0, 10.0, 15.0],
            }
        )
        normalized = normalize_by_refeed_segments(
            raw, 0.0, [RefeedEvent(1.5, 2.0)]
        )
        self.assertEqual(
            set(normalized.loc[normalized["sample"].eq("B"), SEGMENT_COLUMN]),
            {0},
        )

    def test_refeed_normalization_rejects_a_missing_well_baseline(self):
        raw = pd.DataFrame(
            {
                "sample": ["A", "A", "A", "A"],
                "series_id": ["well1", "well1", "well2", "well2"],
                "elapsed_hours": [0.0, 2.0, 0.0, 4.0],
                "raw_value": [10.0, 20.0, 10.0, 30.0],
            }
        )
        with self.assertRaisesRegex(ValueError, "Every physical replicate needs"):
            normalize_by_refeed_segments(raw, 0.0, [RefeedEvent(1.0, 2.0)])

    def test_drop_samples_after_removes_zero_readings_and_keeps_earlier_data(self):
        raw = pd.DataFrame(
            {
                "sample": ["Sample 72"] * 3 + ["Control With Spaces"] * 3,
                "series_id": ["well1"] * 3 + ["well2"] * 3,
                "elapsed_hours": [0.0, 96.0, 119.533333] * 2,
                "raw_value": [10.0, 20.0, 0.0, 5.0, 7.5, 0.0],
            }
        )
        cutoffs = parse_sample_cutoffs(
            ["119.5: sample 72, Control With Spaces"],
            ["Sample 72", "Control With Spaces"],
            0.0,
        )
        self.assertEqual(
            cutoffs,
            [
                SampleCutoff("Control With Spaces", 119.5),
                SampleCutoff("Sample 72", 119.5),
            ],
        )
        filtered, audit_rows = drop_samples_after(raw, cutoffs)
        self.assertEqual(sorted(filtered["elapsed_hours"].unique()), [0.0, 96.0])
        self.assertEqual(sum(row["rows_removed"] for row in audit_rows), 2)
        normalized = normalize_per_well(filtered, 0.0)
        log2_normalized = add_log2_fold_change(normalized, 0.0)
        self.assertTrue(np.isfinite(log2_normalized["log2_fold_change"]).all())

    def test_refeed_plot_does_not_connect_across_segment_reset(self):
        summary = pd.DataFrame(
            {
                "sample": ["A", "A", "A"],
                "elapsed_hours": [0.0, 2.0, 4.0],
                SEGMENT_COLUMN: [0, 1, 1],
                "mean_fold_change": [1.0, 1.0, 2.0],
                "sem_fold_change": [0.1, 0.1, 0.2],
            }
        )
        fig, ax = plt.subplots()
        try:
            plot_sample(
                ax,
                summary,
                "A",
                color="navy",
                marker="o",
                segment_column=SEGMENT_COLUMN,
            )
            self.assertEqual(len(ax.lines), 2)
            self.assertEqual(ax.lines[0].get_xdata().tolist(), [0.0])
            self.assertEqual(ax.lines[1].get_xdata().tolist(), [2.0, 4.0])
        finally:
            plt.close(fig)

    def test_refeed_label_is_near_the_bottom_of_the_plot(self):
        fig, ax = plt.subplots()
        try:
            style_plot_axis(
                ax,
                title="Test",
                y_label="Fold change",
                baseline=1.0,
                baseline_hour=0.0,
                title_font_size=14.0,
                axis_font_size=12.0,
                tick_font_size=10.0,
                legend_font_size=9.0,
                legend_location="best",
                legend_columns=1,
                x_axis_linewidth=1.0,
                y_axis_linewidth=1.0,
                additional_hlines=[],
                h_line_color="gray",
                h_line_style="--",
                h_line_width=1.0,
                h_line_alpha=0.5,
                refeed_events=[RefeedEvent(48.0, 49.0)],
                refeed_line_color="teal",
                refeed_line_style=":",
                refeed_line_width=1.2,
                refeed_line_alpha=0.65,
                show_refeed_labels=True,
            )
            self.assertEqual(len(ax.texts), 1)
            self.assertAlmostEqual(ax.texts[0].xy[1], 0.06)
            self.assertEqual(ax.texts[0].get_verticalalignment(), "bottom")
        finally:
            plt.close(fig)

    def test_color_mapping_metadata_supports_spaces_and_exact_styles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "my exact colors.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "sample",
                        "color",
                        "marker",
                        "linestyle",
                        "linewidth",
                        "markersize",
                        "legend_label",
                    ]
                )
                writer.writerow(
                    ["Sequence with spaces", "#123ABC", "o", "--", "3", "8", "My label"]
                )
            styles = read_color_mapping_metadata(path, ["Sequence with spaces"])
        self.assertEqual(styles["Sequence with spaces"]["color"], "#123ABC")
        self.assertEqual(styles["Sequence with spaces"]["linewidth"], 3.0)
        self.assertEqual(styles["Sequence with spaces"]["label"], "My label")

    def test_plot_layout_preserves_spaces_and_assigns_controls_per_plot(self):
        available = [
            "CD28 sequence one",
            "4-1BB sequence, long name",
            "Wild Type Control",
            "Untransduced Cells",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "my plot layout.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["plot_name", "sequence_1", "sequence_2", "control_1"]
                )
                writer.writerow(
                    [
                        "Costimulatory comparison",
                        "CD28 sequence one",
                        "4-1BB sequence, long name",
                        "Wild Type Control",
                    ]
                )
                writer.writerow(
                    [
                        "CD28 only",
                        "CD28 sequence one",
                        "",
                        "Untransduced Cells",
                    ]
                )
            definitions = read_plot_layout(path, available)

        self.assertEqual(len(definitions), 2)
        self.assertEqual(
            definitions[0].sequences,
            ["CD28 sequence one", "4-1BB sequence, long name"],
        )
        self.assertEqual(definitions[0].controls, ["Wild Type Control"])
        self.assertEqual(definitions[1].controls, ["Untransduced Cells"])

    def test_colormap_is_configurable_and_plasma_remains_default_behavior(self):
        self.assertEqual(resolve_colormap_name("ViRiDiS"), "viridis")
        plasma = colormap_colors(2, "plasma", 0.72)
        self.assertEqual(len(plasma), 2)
        self.assertTrue(np.allclose(plasma[0], __import__("matplotlib").colormaps["plasma"](0.08)))
        with self.assertRaisesRegex(ValueError, "Unknown Matplotlib color map"):
            resolve_colormap_name("definitely not a cmap")

    def test_per_well_baseline_normalization(self):
        raw = pd.DataFrame(
            {
                "sample": ["A", "A", "A", "A"],
                "series_id": ["well1", "well1", "well2", "well2"],
                "elapsed_hours": [0.0, 2.0, 0.0, 2.0],
                "raw_value": [10.0, 20.0, 20.0, 30.0],
            }
        )
        normalized = normalize_per_well(raw, 0.0)
        baseline = normalized.loc[normalized["elapsed_hours"].eq(0), NORMALIZED_COLUMN]
        self.assertTrue(np.allclose(baseline, 1.0))

        normalized = add_log2_fold_change(normalized, 0.0)
        linear = make_plot_summary(normalized, 0.0)
        log2 = make_log2_plot_summary(normalized, 0.0)
        self.assertEqual(linear.loc[linear["elapsed_hours"].eq(0), PLOT_MEAN_COLUMN].iloc[0], 1.0)
        self.assertEqual(log2.loc[log2["elapsed_hours"].eq(0), LOG2_PLOT_MEAN_COLUMN].iloc[0], 0.0)

    def test_parses_bundled_native_export(self):
        example = Path(__file__).parents[1] / "examples" / "plate_1.txt"
        rows = parse_plate_export(example, plate_override="1")
        self.assertEqual(len(rows), 18)
        self.assertEqual({row["elapsed_hours"] for row in rows}, {0.0, 2.0, 4.0})

    def test_custom_layout_creates_named_plots_with_per_plot_controls(self):
        example_export = Path(__file__).parents[1] / "examples" / "plate_1.txt"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata = root / "metadata with spaces.csv"
            with metadata.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["well", "sample", "plate"])
                writer.writerows(
                    [
                        ["A1", "Treatment Alpha", 1],
                        ["A2", "Treatment Alpha", 1],
                        ["A3", "Wild Type Control", 1],
                        ["A4", "Wild Type Control", 1],
                        ["A5", "Vehicle Control", 1],
                        ["A6", "Vehicle Control", 1],
                    ]
                )
            layout = root / "plots I want.csv"
            with layout.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["plot_name", "sequence_1", "control_1", "control_2"]
                )
                writer.writerow(
                    [
                        "Treatment versus wild type",
                        "Treatment Alpha",
                        "Wild Type Control",
                        "",
                    ]
                )
                writer.writerow(
                    [
                        "Treatment with both controls",
                        "Treatment Alpha",
                        "Wild Type Control",
                        "Vehicle Control",
                    ]
                )
            output = root / "results with spaces"
            status = main(
                [
                    "--metadata",
                    str(metadata),
                    str(example_export),
                    "--plot-layout",
                    str(layout),
                    "--cmap",
                    "viridis",
                    "--output",
                    str(output),
                ],
                prog="auto-incucyte",
            )
            manifest = pd.read_csv(output / "plots" / "plot_manifest.csv")
            layout_used = pd.read_csv(output / "tables" / "plot_layout_used.csv")
            pngs = sorted((output / "plots").glob("*.png"))

        self.assertEqual(status, 0)
        self.assertEqual(len(pngs), 4)
        self.assertEqual(set(manifest["plot_name"]), {
            "Treatment versus wild type",
            "Treatment with both controls",
        })
        self.assertEqual(set(manifest["cmap"]), {"viridis"})
        self.assertEqual(layout_used.loc[0, "control_1"], "Wild Type Control")
        self.assertEqual(layout_used.loc[1, "control_1"], "Wild Type Control")
        self.assertEqual(layout_used.loc[1, "control_2"], "Vehicle Control")

    def test_refeed_command_writes_global_and_segmented_results(self):
        example_export = Path(__file__).parents[1] / "examples" / "plate_1.txt"
        example_metadata = (
            Path(__file__).parents[1] / "examples" / "plate_metadata.csv"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "refeed results"
            status = main(
                [
                    "--metadata",
                    str(example_metadata),
                    str(example_export),
                    "--controls",
                    "WT, Vehicle",
                    "--refeed-time",
                    "1",
                    "--output",
                    str(output),
                ],
                prog="auto-incucyte",
            )
            png_names = {path.name for path in (output / "plots").glob("*.png")}
            schedule = pd.read_csv(output / "tables" / "refeed_schedule_used.csv")
            audit = pd.read_csv(
                output / "tables" / "refeed_normalization_audit.csv"
            )
            refeed_data = pd.read_csv(output / "tables" / "incucyte_plot_data.csv")
            refeed_log2_data = pd.read_csv(
                output / "tables" / "incucyte_log2_plot_data.csv"
            )
            global_data = pd.read_csv(
                output / "tables" / "incucyte_global_plot_data.csv"
            )
            manifest = pd.read_csv(output / "plots" / "plot_manifest.csv")

        self.assertEqual(status, 0)
        self.assertEqual(len(png_names), 4)
        self.assertIn("incucyte_normalized_01_all_sequences.png", png_names)
        self.assertIn("incucyte_global_normalized_01_all_sequences.png", png_names)
        self.assertEqual(schedule.loc[1, "requested_refeed_hour"], 1.0)
        self.assertEqual(schedule.loc[1, SEGMENT_BASELINE_COLUMN], 2.0)
        self.assertTrue(np.allclose(audit[PLOT_MEAN_COLUMN], 1.0))
        self.assertTrue(
            np.allclose(
                refeed_data.loc[refeed_data["elapsed_hours"].eq(2.0), PLOT_MEAN_COLUMN],
                1.0,
            )
        )
        self.assertTrue(
            np.allclose(
                refeed_log2_data.loc[
                    refeed_log2_data["elapsed_hours"].eq(2.0),
                    LOG2_PLOT_MEAN_COLUMN,
                ],
                0.0,
            )
        )
        treatment_global = global_data.loc[
            global_data["sample"].eq("Treatment")
            & global_data["elapsed_hours"].eq(2.0),
            PLOT_MEAN_COLUMN,
        ].iloc[0]
        self.assertEqual(treatment_global, 2.0)
        standard_manifest = manifest.loc[
            manifest["png"].str.startswith("incucyte_normalized_")
        ]
        self.assertTrue(standard_manifest["lines_broken_at_refeeds"].all())
        self.assertEqual(set(manifest["lines_broken_at_refeeds"]), {False, True})

    def test_custom_filters_grouping_and_existing_output_are_safe(self):
        example_export = Path(__file__).parents[1] / "examples" / "plate_1.txt"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata = root / "metadata.csv"
            with metadata.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["well", "sample", "plate"])
                writer.writerows(
                    [
                        ["A1", "Treatment Alpha", 1],
                        ["A2", "Treatment Alpha", 1],
                        ["A3", "WT", 1],
                        ["A4", "WT", 1],
                        ["A5", "Sample to hide", 1],
                        ["A6", "Sample to hide", 1],
                    ]
                )
            colors = root / "colors.csv"
            with colors.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(STYLE_METADATA_FIELDS)
                writer.writerow(
                    ["Treatment Alpha", "#0055AA", "o", "--", 3, 7, 1, 12, "Treatment A"]
                )
            output = root / "existing results"
            output.mkdir()
            existing = output / "do not delete me.txt"
            existing.write_text("important", encoding="utf-8")
            existing_plots = output / "plots"
            existing_plots.mkdir()
            old_plot = existing_plots / "incucyte_normalized_99_old_plot.png"
            old_plot.write_bytes(b"old plot placeholder")
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                status = main(
                    [
                        "--metadata", str(metadata), str(example_export),
                        "--controls", "WT",
                        "--group-size", "1",
                        "--drop-time", "2, 55",
                        "--hide-sample", "sample TO HIDE",
                        "--color-mapping-metadata", str(colors),
                        "--font", "DejaVu Sans",
                        "--font-size", "11",
                        "--legend-location", "upper left",
                        "--x-axis-linewidth", "2",
                        "--y-axis-linewidth", "2.5",
                        "--h-line", "2",
                        "--log2-h-line", "1",
                        "--output", str(output),
                    ],
                    prog="auto-incucyte",
                )
            manifest = pd.read_csv(output / "plots" / "plot_manifest.csv")
            plot_data = pd.read_csv(output / "tables" / "incucyte_plot_data.csv")
            raw_data = pd.read_csv(output / "tables" / "incucyte_long.csv")
            style_used = pd.read_csv(output / "tables" / "color_mapping_metadata_used.csv")
            pngs = sorted((output / "plots").glob("*.png"))

            self.assertTrue(existing.exists())
            self.assertEqual(existing.read_text(encoding="utf-8"), "important")
            self.assertEqual(old_plot.read_bytes(), b"old plot placeholder")
        self.assertEqual(status, 0)
        self.assertEqual(len(pngs), 5)
        self.assertEqual(set(manifest["plot_name"]), {"All sequences", "Group 1"})
        self.assertNotIn("Sample to hide", ";".join(manifest["sequence_names"]))
        self.assertEqual(set(plot_data["elapsed_hours"]), {0.0, 4.0})
        self.assertEqual(set(raw_data["elapsed_hours"]), {0.0, 2.0, 4.0})
        self.assertIn("Sample to hide", set(plot_data["sample"]))
        self.assertEqual(style_used.loc[style_used["sample"].eq("Treatment Alpha"), "color"].iloc[0], "#0055aa")
        self.assertTrue(any("no other files will be deleted" in str(item.message) for item in caught))


if __name__ == "__main__":
    unittest.main()
