import csv
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "auto_incucyte_mpl"))

import numpy as np
import pandas as pd

from auto_incucyte.analysis import (
    LOG2_PLOT_MEAN_COLUMN,
    NORMALIZED_COLUMN,
    PLOT_MEAN_COLUMN,
    add_log2_fold_change,
    colormap_colors,
    default_plot_definitions,
    main,
    make_log2_plot_summary,
    make_plot_summary,
    normalize_per_well,
    parse_plate_export,
    read_plot_layout,
    resolve_colormap_name,
)


class AnalysisTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
