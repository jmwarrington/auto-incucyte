# auto-incucyte

`auto-incucyte` turns native Incucyte TXT/TSV exports into clean data tables,
linear fold-change plots, log2 fold-change plots, and a normalization audit.
It is simple by default and highly customizable when publication-ready styling
is needed. Long experiments can be renormalized after each cell refeed while
retaining the original globally normalized results.

Each physical well is divided by its own measurement at the selected baseline
hour. Replicate fold changes are then averaged at each time point and plotted as
mean ± SEM.

## START HERE: choose your computer

Follow **only one** setup section:

- **Mac users:** follow “Mac setup” immediately below.
- **Windows PC users:** skip to “Windows PC setup.”

Do not mix Mac and Windows activation commands. Both sections create a private
Python environment named `automate`. This is only a folder containing the
packages required by auto-incucyte; it does not alter experimental data.

## Mac setup

### Mac 1: open Terminal and download auto-incucyte

Open **Terminal** from Applications → Utilities. Copy one line at a time:

```bash
git clone https://github.com/jmwarrington/auto-incucyte.git
cd auto-incucyte
```

If `git` is not found, install Git from [git-scm.com](https://git-scm.com/download/mac),
then reopen Terminal and try again.

### Mac 2: confirm Python 3.10 or newer

```bash
python3 --version
```

Continue if this reports Python 3.10, 3.11, 3.12, 3.13, or 3.14. If it reports
Python 3.9 and Miniconda is installed, check its newer Python:

```bash
/opt/miniconda3/bin/python3.13 --version
```

### Mac 3: create and activate `automate`

If `python3 --version` reported 3.10 or newer:

```bash
python3 -m venv automate
source automate/bin/activate
```

If the Mac Python was 3.9 but Miniconda Python 3.13 worked:

```bash
/opt/miniconda3/bin/python3.13 -m venv automate
source automate/bin/activate
```

The Terminal prompt should now begin with `(automate)`.

### Mac 4: install and check auto-incucyte

```bash
python -m pip install --upgrade pip
python -m pip install .
auto-incucyte --version
auto-incucyte --help
```

### Mac: activate it again in a new Terminal window

```bash
cd auto-incucyte
source automate/bin/activate
```

Run `deactivate` when finished.

## Windows PC setup

These instructions use **PowerShell**, which is included with Windows.

### Windows 1: install the two prerequisites

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/).
   During installation, select **Add python.exe to PATH** if that option appears.
2. Install Git for Windows from [git-scm.com](https://git-scm.com/download/win).
3. Close and reopen PowerShell after installing them.

### Windows 2: open PowerShell and download auto-incucyte

Open the Start menu, type **PowerShell**, and open **Windows PowerShell**. Copy
one line at a time:

```powershell
git clone https://github.com/jmwarrington/auto-incucyte.git
cd auto-incucyte
```

### Windows 3: confirm Python 3.10 or newer

```powershell
py --version
```

Continue only if this reports Python 3.10 or newer.

### Windows 4: create and activate `automate`

```powershell
py -m venv automate
.\automate\Scripts\Activate.ps1
```

The PowerShell prompt should now begin with `(automate)`.

If PowerShell says that running scripts is disabled, run these two commands.
The first change applies only to the current PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\automate\Scripts\Activate.ps1
```

### Windows 5: install and check auto-incucyte

```powershell
python -m pip install --upgrade pip
python -m pip install .
auto-incucyte --version
auto-incucyte --help
```

### Windows: activate it again in a new PowerShell window

```powershell
cd auto-incucyte
.\automate\Scripts\Activate.ps1
```

If script activation is blocked again, use the temporary `Set-ExecutionPolicy`
command above. Run `deactivate` when finished.

## Updating on either Mac or Windows

First activate `automate` using the command for your computer. Then run:

```text
auto-incucyte --update
auto-incucyte --version
```

The first command installs the newest release from the official GitHub
repository. The second confirms the installed version. No metadata or plate
files are needed.

If an old installation does not recognize `--update`, run this standard command
once. It works in both Mac Terminal and Windows PowerShell:

```text
python -m pip install --upgrade "git+https://github.com/jmwarrington/auto-incucyte.git"
```

## The simplest analysis

All analysis commands below are written on one line so they work unchanged in
both Mac Terminal and Windows PowerShell.

Create a metadata CSV with one row per measured well:

```csv
well,sample,plate
A1,Treatment Alpha,1
A2,Treatment Alpha,1
A3,WT,1
A4,WT,1
```

Then run:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --controls 'WT' --baseline-hour 0 --output 'incucyte_results_experiment_1'
```

Quotation marks are important whenever a path or a name contains spaces. For a
list of controls, quote the **entire comma-separated list**:

```text
--controls 'WT, Shuffle'
```

Use this when there are no controls:

```text
--controls ''
```

The default controls are `WT`, `Shuffle`, and `NALM6`. Names are matched without
regard to capitalization, and sample names containing spaces are supported.

For multiple plates, label each plate file explicitly:

```text
auto-incucyte --metadata 'plate metadata.csv' '1=raw plate 1.txt' '2=raw plate 2.txt' --controls 'WT, Shuffle' --output 'incucyte_results_experiment_1'
```

Native tab-delimited `.txt` and `.tsv` exports are supported, as are legacy
comma-delimited `.csv` copies.

## Refeeding experiments

Use `--refeed-time` when cells are refed during a long time course:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --baseline-hour 0 --refeed-time '48, 120, 192' --output 'refeed_results'
```

Enter the **actual elapsed hours when the cells were refed**. Decimal values
such as `48.5` are accepted. For each entered time, auto-incucyte finds the
first recorded Incucyte image at or after the refeed and uses that image as the
new per-well baseline.

For example:

| Measurements | Each well is divided by its own value at |
|---|---|
| 0 to before the first post-48 h image | 0 h |
| First post-48 h image to before the first post-120 h image | first image at or after 48 h |
| First post-120 h image to before the first post-192 h image | first image at or after 120 h |
| First post-192 h image onward | first image at or after 192 h |

At every segment baseline, each physical well equals exactly `1.0` on the
linear scale and `0.0` on the log2 scale. Replicates are averaged only after
that per-well calculation.

The program creates **both** interpretations:

- Existing global plots normalized to `--baseline-hour`.
- Additional refeed-normalized plots measuring change since the most recent
  refeed.

Refeed-normalized lines are deliberately broken between segments. A line is
never drawn from the end of one normalization segment to the `1.0` reset in the
next segment. Vertical labeled lines show the entered refeed events while the
x-axis continues to show absolute experiment time.

The terminal prints how every event was resolved. For example:

```text
Refeed at 48 h -> first recorded post-refeed image at 49 h
```

Important safeguards:

- Every physical well must have a measurement at every resolved segment
  baseline; otherwise the run stops with a clear error.
- A resolved refeed baseline cannot also be removed with `--drop-time`.
- Refeed times must occur after `--baseline-hour`, and there must be a recorded
  image at or after each event.
- If two refeed events resolve to the same image, the run stops rather than
  silently creating an invalid segment.

The option can also be repeated:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --refeed-time '48, 120' --refeed-time '192' --output 'refeed_results'
```

### Customize the vertical refeed markers

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --refeed-time '48, 120' --refeed-line-color '#2F6F6F' --refeed-line-style=':' --refeed-line-width 1.5 --refeed-line-alpha 0.7 --output 'refeed_results'
```

Use `--no-refeed-labels` to keep the vertical lines but hide their text labels.
Custom titles and y-axis labels are available through
`--refeed-title-prefix`, `--refeed-y-label`, `--refeed-log2-title-prefix`, and
`--refeed-log2-y-label`.

## Safe output folders

The program never clears an output folder. If the folder already contains
files, it prints a warning. Files with the same generated filename are
overwritten, but unrelated files and old plots with different names are left
alone.

For the cleanest record, give each run a clear new folder:

```text
--output 'incucyte_results_2026-07-31_CD28_screen'
```

## Choose which data appear

### Always make an all-sequences plot

Without extra options, every sequence and control appears on one graph. Both a
linear and log2 version are created.

`--group-size` adds smaller graphs but never replaces the complete graph. This
command creates `All sequences`, `Group 1`, `Group 2`, and so on:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --controls 'WT, Shuffle' --group-size 5 --output 'grouped_results'
```

Controls are repeated on every automatic group plot.

### Drop unwanted time points

Quote one comma-separated list. These hours are removed from normalized tables
and all plots; the original reshaped raw-data tables still retain them:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --drop-time '22, 55' --output 'filtered_results'
```

The normalization baseline cannot be dropped. The option may be repeated:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --drop-time '22, 55' --drop-time '72' --output 'filtered_results'
```

### Hide samples from every plot

Hidden samples remain in all analysis tables but are removed from every graph:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --hide-sample '70, NALM6' --output 'hidden_sample_results'
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

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --plot-layout 'my plot layout.csv' --output 'custom_layout_results'
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

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --color-mapping-metadata 'my exact plot styles.csv' --output 'custom_style_results'
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

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --cmap viridis --output 'viridis_results'
```

Common choices include `magma`, `inferno`, `cividis`, `turbo`, and `tab10`.

### Font family and font sizes

The font must be installed on the computer. Names containing spaces must be
quoted:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --font 'Avenir' --font-size 12 --output 'avenir_results'
```

Replace `'Avenir'` with `'Arial'` or `'Times New Roman'` to use either of those
fonts when it is installed.

`--font-size` changes the overall scale. Each part can be set precisely:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --font 'Arial' --title-font-size 16 --axis-font-size 13 --tick-font-size 11 --legend-font-size 10 --output 'font_customized_results'
```

### Legend position and columns

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --legend-location 'upper left' --legend-columns 1 --output 'legend_customized_results'
```

Locations are `best`, `upper right`, `upper left`, `lower left`, `lower right`,
`right`, `center left`, `center right`, `lower center`, `upper center`, or
`center`.

### Axis spine thickness

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --x-axis-linewidth 2 --y-axis-linewidth 2.5 --output 'axis_customized_results'
```

### Horizontal reference lines

Use one flag per line. Linear and log2 plots have separate line positions:

```text
auto-incucyte --metadata 'plate metadata.csv' 'raw plate 1.txt' --h-line 2 --h-line 3 --log2-h-line 1 --h-line-color '#555555' --h-line-style='--' --h-line-width 1.5 --h-line-alpha 0.7 --output 'reference_line_results'
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
│   ├── incucyte_refeed_normalized_long.csv
│   ├── incucyte_refeed_plot_data.csv
│   ├── incucyte_refeed_log2_plot_data.csv
│   ├── refeed_normalization_audit.csv
│   ├── refeed_schedule_used.csv
│   ├── plot_layout_template.csv
│   ├── plot_layout_used.csv
│   ├── color_mapping_metadata_template.csv
│   └── color_mapping_metadata_used.csv
└── plots/
    ├── incucyte_normalized_01_all_sequences.png
    ├── incucyte_log2_01_all_sequences.png
    ├── incucyte_refeed_normalized_01_all_sequences.png
    ├── incucyte_refeed_log2_01_all_sequences.png
    └── plot_manifest.csv
```

The files containing `refeed` are created only when `--refeed-time` is used.

The audit table verifies that every sample is exactly 1.0 at baseline on the
linear scale. The two plot-data tables contain the exact values sent to
Matplotlib.

## Complete reproducible example

The repository includes synthetic, non-experimental data:

```text
auto-incucyte --metadata 'examples/plate_metadata.csv' 'examples/plate_1.txt' --controls 'WT, Vehicle' --baseline-hour 0 --refeed-time '1' --font 'DejaVu Sans' --legend-location 'upper left' --output 'example_results_customized'
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
