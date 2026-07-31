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

from auto_incucyte.analysis import (
    LOG2_PLOT_MEAN_COLUMN,
    NORMALIZED_COLUMN,
    PLOT_MEAN_COLUMN,
    STYLE_METADATA_FIELDS,
    add_log2_fold_change,
    colormap_colors,
    default_plot_definitions,
    drop_time_points,
    main,
    make_log2_plot_summary,
    make_plot_summary,
    normalize_per_well,
    parse_plate_export,
    read_plot_layout,
    read_color_mapping_metadata,
    resolve_colormap_name,
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
