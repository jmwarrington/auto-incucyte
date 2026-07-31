# auto-incucyte

`auto-incucyte` turns native Incucyte TXT/TSV exports into clean tables, linear
fold-change plots, log2 fold-change plots, and a normalization audit in one run.

Each physical well is divided by its own measurement at the selected baseline
hour. Replicate fold changes are then averaged at each time point and plotted as
mean ± SEM.

## Documentation

The full user guide is in [`docs/`](docs/index.rst), with installation,
input preparation, normalization details, worked examples, output
interpretation, troubleshooting, and API reference. The repository includes
everything needed to publish it at Read the Docs; see
[`docs/readthedocs.rst`](docs/readthedocs.rst) for the one-time online setup.

## Install

```bash
git clone https://github.com/jmwarrington/auto-incucyte.git
cd auto-incucyte
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

Confirm the installation:

```bash
auto-incucyte --help
```

## Quick start

Create a metadata CSV with one row per measured well:

```csv
well,sample,plate
A1,Treatment,1
A2,Treatment,1
A3,WT,1
A4,WT,1
```

Analyze one plate and normalize every well to hour 2:

```bash
auto-incucyte \
  --metadata plate_metadata.csv \
  raw_plate_1.txt \
  --baseline-hour 2 \
  --output incucyte_results
```

When metadata contains multiple plates, label each export explicitly:

```bash
auto-incucyte \
  --metadata plate_metadata.csv \
  1=raw_plate_1.txt 2=raw_plate_2.txt \
  --baseline-hour 0 \
  --output incucyte_results
```

Native tab-delimited `.txt` and `.tsv` exports are supported, as are legacy
comma-delimited `.csv` copies.

## Results

One output folder contains everything:

```text
incucyte_results/
├── tables/
│   ├── incucyte_long.csv
│   ├── incucyte_raw_summary.csv
│   ├── incucyte_normalized_long.csv
│   ├── incucyte_plot_data.csv
│   ├── incucyte_log2_plot_data.csv
│   ├── normalization_audit.csv
│   ├── plot_layout_template.csv
│   └── plot_layout_used.csv
└── plots/
    ├── incucyte_normalized_01_all_sequences.png
    ├── incucyte_log2_01_all_sequences.png
    └── plot_manifest.csv
```

The audit table proves that every sample is exactly 1.0 at the baseline on the
linear scale. The two plot-data tables contain the exact values sent to
Matplotlib.

## Plots: simple by default

By default, every sequence and control is drawn on one graph. The program writes
both a linear fold-change version and a log2 version. No plot setup is required.

The default control names are `WT`, `Shuffle`, and `NALM6`. Change them for the
default graph with a comma-separated list:

```bash
auto-incucyte ... --controls WT,Vehicle,Untreated
```

Use `--controls ''` when there are no controls. Experimental samples are split
from controls only to give controls a stable visual style.

## Choose exactly what appears on each plot

Every run creates `tables/plot_layout_template.csv`. Open it in Excel, Numbers,
or Google Sheets. Each row is one plot:

```csv
plot_name,sequence_1,sequence_2,control_1,control_2
CD28 comparison,CD28 sequence 1,CD28 sequence 2,Wild Type Control,Untransduced Cells
4-1BB comparison,4-1BB sequence 1,4-1BB sequence 2,Wild Type Control,Untransduced Cells
```

Add as many rows and `sequence_3`, `control_3`, etc. columns as needed. Control
names are defined separately for every row, so the same controls can appear on
all plots or different controls can be used on different plots. Then rerun:

```bash
auto-incucyte ... --plot-layout "my plot layout.csv"
```

Sequence names, control names, plot names, and paths may contain spaces. Use the
same sequence spelling as the metadata CSV; matching is case-insensitive. Normal
CSV quoting also supports names containing commas.

## Change the color map

The default remains `plasma`. Select any installed Matplotlib color map:

```bash
auto-incucyte ... --cmap viridis
```

Other common choices include `magma`, `inferno`, `cividis`, `turbo`, and
`tab10`.

## Reproducible example

This repository includes synthetic, non-experimental example data:

```bash
auto-incucyte \
  --metadata examples/plate_metadata.csv \
  examples/plate_1.txt \
  --controls WT,Vehicle \
  --baseline-hour 0 \
  --output example_results
```

## Development

```bash
python -m unittest discover -s tests -v
```

## License

This project is released under the permissive [MIT License](LICENSE).
