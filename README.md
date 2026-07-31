# auto-incucyte

`auto-incucyte` turns native Incucyte TXT/TSV exports into clean data tables,
linear fold-change plots, log2 fold-change plots, and a normalization audit.
It is simple by default and highly customizable when publication-ready styling
is needed.

Each physical well is divided by its own measurement at the selected baseline
hour. Replicate fold changes are then averaged at each time point and plotted as
mean ± SEM.

## First-time setup for someone new to coding

### 1. Open Terminal and download the project

On a Mac, open **Terminal** from Applications → Utilities. Copy and paste these
two commands one at a time:

```bash
git clone https://github.com/jmwarrington/auto-incucyte.git
cd auto-incucyte
```

The second command moves Terminal into the downloaded project folder.

### 2. Check Python

```bash
python3 --version
```

The result must be Python 3.10 or newer. Python 3.11, 3.12, 3.13, and 3.14 are
also supported. If the command shows Python 3.9, but Miniconda is installed, use
this Python for the next step:

```bash
/opt/miniconda3/bin/python3.13 --version
```

### 3. Create a private Python environment

A virtual environment is simply a private folder containing the Python tools
for this program. Creating it does not modify experimental data.

If `python3 --version` showed 3.10 or newer:

```bash
python3 -m venv automate
```

If the Mac's `python3` was 3.9 and the Miniconda command worked:

```bash
/opt/miniconda3/bin/python3.13 -m venv automate
```

Turn the environment on:

```bash
source automate/bin/activate
```

The word `(automate)` should appear at the beginning of the Terminal prompt.
Now install the program:

```bash
python -m pip install --upgrade pip
python -m pip install .
auto-incucyte --help
```

### 4. Use it again later

Each time a new Terminal window is opened:

```bash
cd auto-incucyte
source automate/bin/activate
```

To turn the environment off, run `deactivate`.

### 5. Update later with one command

With the `automate` environment activated, run:

```bash
auto-incucyte --update
auto-incucyte --version
```

The first command downloads and installs the newest release from the official
GitHub repository. The second confirms the installed version. No metadata or
plate files are needed when updating.

If an older installation does not recognize `--update`, update it once with the
standard Python command below. Future updates can use the shorter command.

```bash
python -m pip install --upgrade \
  'git+https://github.com/jmwarrington/auto-incucyte.git'
```

## The simplest analysis

Create a metadata CSV with one row per measured well:

```csv
well,sample,plate
A1,Treatment Alpha,1
A2,Treatment Alpha,1
A3,WT,1
A4,WT,1
```

Then run:

```bash
auto-incucyte \
  --metadata 'plate metadata.csv' \
  'raw plate 1.txt' \
  --controls 'WT' \
  --baseline-hour 0 \
  --output 'incucyte_results_experiment_1'
```

Quotation marks are important whenever a path or a name contains spaces. For a
list of controls, quote the **entire comma-separated list**:

```bash
--controls 'WT, Shuffle'
```

Use this when there are no controls:

```bash
--controls ''
```

The default controls are `WT`, `Shuffle`, and `NALM6`. Names are matched without
regard to capitalization, and sample names containing spaces are supported.

For multiple plates, label each plate file explicitly:

```bash
auto-incucyte \
  --metadata 'plate metadata.csv' \
  '1=raw plate 1.txt' '2=raw plate 2.txt' \
  --controls 'WT, Shuffle' \
  --output 'incucyte_results_experiment_1'
```

Native tab-delimited `.txt` and `.tsv` exports are supported, as are legacy
comma-delimited `.csv` copies.

## Safe output folders

The program never clears an output folder. If the folder already contains
files, it prints a warning. Files with the same generated filename are
overwritten, but unrelated files and old plots with different names are left
alone.

For the cleanest record, give each run a clear new folder:

```bash
--output 'incucyte_results_2026-07-31_CD28_screen'
```

## Choose which data appear

### Always make an all-sequences plot

Without extra options, every sequence and control appears on one graph. Both a
linear and log2 version are created.

`--group-size` adds smaller graphs but never replaces the complete graph. This
command creates `All sequences`, `Group 1`, `Group 2`, and so on:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --controls 'WT, Shuffle' --group-size 5 --output 'grouped_results'
```

Controls are repeated on every automatic group plot.

### Drop unwanted time points

Quote one comma-separated list. These hours are removed from normalized tables
and all plots; the original reshaped raw-data tables still retain them:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --drop-time '22, 55' --output 'filtered_results'
```

The normalization baseline cannot be dropped. The option may be repeated:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --drop-time '22, 55' --drop-time '72' --output 'filtered_results'
```

### Hide samples from every plot

Hidden samples remain in all analysis tables but are removed from every graph:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --hide-sample '70, NALM6' --output 'hidden_sample_results'
```

Matching is case-insensitive, spaces are supported, and the option may be
repeated.

### Choose exact plot contents and names

Every run creates `tables/plot_layout_template.csv`. Open it in Excel, Numbers,
or Google Sheets. Each row defines one plot:

```csv
plot_name,sequence_1,sequence_2,control_1,control_2
CD28 comparison,CD28 sequence 1,CD28 sequence 2,Wild Type Control,Untransduced Cells
4-1BB comparison,4-1BB sequence 1,4-1BB sequence 2,Wild Type Control,Untransduced Cells
```

Add more rows or columns such as `sequence_3` and `control_3`, save the file,
then run:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --plot-layout 'my plot layout.csv' --output 'custom_layout_results'
```

The controls are user-defined for each plot. Sequence, control, and plot names
may contain spaces. Normal CSV quoting supports names containing commas.

## Maximum plot customization

The default `plasma` colors and plot style require no setup. Every major visual
choice can also be controlled so these figures match the rest of a manuscript.

### Exact colors, shapes, lines, and legend labels

Every run creates:

```text
tables/color_mapping_metadata_template.csv
```

Open that file in a spreadsheet. It already contains every plotted sample and
its default style. Change any value, save it under a descriptive name such as
`my exact plot styles.csv`, and rerun:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --color-mapping-metadata 'my exact plot styles.csv' \
  --output 'custom_style_results'
```

Example:

```csv
sample,color,marker,linestyle,linewidth,markersize,markeredgewidth,zorder,legend_label
CD28 sequence 1,#2A6FDB,o,-,2.5,7,1,5,CD28-1
4-1BB sequence 1,#D1495B,^,--,3,8,1.2,6,4-1BB-1
Wild Type Control,black,s,-,2.5,7,1,10,WT
```

The columns mean:

- `sample`: exact sample name from the metadata; spaces are allowed.
- `color`: a color name such as `navy`, or an exact hex color such as `#2A6FDB`.
- `marker`: point shape, for example `o` circle, `s` square, `^` triangle, `D`
  diamond, `X`, or `P`.
- `linestyle`: `-` solid, `--` dashed, `:` dotted, or `-.` dash-dot.
- `linewidth`: line thickness.
- `markersize`: point size.
- `markeredgewidth`: thickness of the point outline.
- `zorder`: drawing order; larger numbers are drawn on top.
- `legend_label`: optional display name in the legend.

The program validates the spreadsheet and writes the exact final choices to
`tables/color_mapping_metadata_used.csv` for reproducibility.

For fast palette changes without a spreadsheet, keep using any installed
Matplotlib color map. The default remains `plasma`:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --cmap viridis --output 'viridis_results'
```

Common choices include `magma`, `inferno`, `cividis`, `turbo`, and `tab10`.

### Font family and font sizes

The font must be installed on the computer. Names containing spaces must be
quoted:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --font 'Avenir' --font-size 12 --output 'avenir_results'
```

Replace `'Avenir'` with `'Arial'` or `'Times New Roman'` to use either of those
fonts when it is installed.

`--font-size` changes the overall scale. Each part can be set precisely:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --font 'Arial' \
  --title-font-size 16 \
  --axis-font-size 13 \
  --tick-font-size 11 \
  --legend-font-size 10 \
  --output 'font_customized_results'
```

### Legend position and columns

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --legend-location 'upper left' --legend-columns 1 \
  --output 'legend_customized_results'
```

Locations are `best`, `upper right`, `upper left`, `lower left`, `lower right`,
`right`, `center left`, `center right`, `lower center`, `upper center`, or
`center`.

### Axis spine thickness

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --x-axis-linewidth 2 --y-axis-linewidth 2.5 \
  --output 'axis_customized_results'
```

### Horizontal reference lines

Use one flag per line. Linear and log2 plots have separate line positions:

```bash
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' \
  --h-line 2 \
  --h-line 3 \
  --log2-h-line 1 \
  --h-line-color '#555555' \
  --h-line-style='--' \
  --h-line-width 1.5 \
  --h-line-alpha 0.7 \
  --output 'reference_line_results'
```

## Results

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
│   ├── plot_layout_used.csv
│   ├── color_mapping_metadata_template.csv
│   └── color_mapping_metadata_used.csv
└── plots/
    ├── incucyte_normalized_01_all_sequences.png
    ├── incucyte_log2_01_all_sequences.png
    └── plot_manifest.csv
```

The audit table verifies that every sample is exactly 1.0 at baseline on the
linear scale. The two plot-data tables contain the exact values sent to
Matplotlib.

## Complete reproducible example

The repository includes synthetic, non-experimental data:

```bash
auto-incucyte \
  --metadata 'examples/plate_metadata.csv' \
  'examples/plate_1.txt' \
  --controls 'WT, Vehicle' \
  --baseline-hour 0 \
  --drop-time '2' \
  --font 'DejaVu Sans' \
  --legend-location 'upper left' \
  --output 'example_results_customized'
```

It also includes `examples/color_mapping_metadata.csv`, which can be supplied
with `--color-mapping-metadata` as a working style-spreadsheet example.

## Full online-style documentation

The Read the Docs guide is in [`docs/`](docs/index.rst), including installation,
input preparation, examples, every command, output interpretation, and
troubleshooting. [`docs/readthedocs.rst`](docs/readthedocs.rst) explains the
one-time steps for publishing it at Read the Docs.

## Development

```bash
python -m unittest discover -s tests -v
```

## License

This project is released under the permissive [MIT License](LICENSE).
