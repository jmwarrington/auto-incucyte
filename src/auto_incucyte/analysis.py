#!/usr/bin/env python3
"""Analyze raw Incucyte exports and create baseline-normalized plots.

Each physical well is divided by its own value at ``--baseline-hour``. The
per-well fold changes are averaged across replicates at each time point, and
mean ± SEM is plotted on both linear and log2 scales. The program also writes
the reshaped raw data, exact plot data, and a normalization audit table.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import glob
import math
import re
import statistics
import subprocess
import sys
import warnings
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib as mpl

# Non-interactive plotting is faster and works on headless systems.
mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SCRIPT_VERSION = "0.4.0"
PACKAGE_GITHUB_URL = "https://github.com/jmwarrington/auto-incucyte.git"
BASELINE_ATOL = 1e-9
NORMALIZED_COLUMN = "fold_change"
PLOT_MEAN_COLUMN = "mean_fold_change"
PLOT_SEM_COLUMN = "sem_fold_change"
LOG2_NORMALIZED_COLUMN = "log2_fold_change"
LOG2_PLOT_MEAN_COLUMN = "mean_log2_fold_change"
LOG2_PLOT_SEM_COLUMN = "sem_log2_fold_change"
SEGMENT_COLUMN = "normalization_segment"
SEGMENT_BASELINE_COLUMN = "segment_baseline_hour"
HOURS_SINCE_REFEED_COLUMN = "hours_since_refeed"
REFEED_EVENT_COLUMN = "refeed_event_hour"

WELL_RE = re.compile(r"^([A-Pa-p])(\d{1,2})$")
PLATE_FROM_VESSEL_RE = re.compile(r"(?:plate|plt)[_\s-]*(\d+)\s*$", re.IGNORECASE)
TRAILING_NUMBER_RE = re.compile(r"(\d+)\s*$")

CONTROL_ALIASES = {
    "wt": "WT",
    "wildtype": "WT",
    "wild type": "WT",
    "shuffle": "Shuffle",
    "shuffled": "Shuffle",
    "nalm6": "NALM6",
}

CONTROL_STYLE: dict[str, dict[str, Any]] = {
    "WT": {"color": "black", "marker": "s", "linestyle": "-", "zorder": 10},
    "Shuffle": {"color": "#808080", "marker": "o", "linestyle": "-", "zorder": 9},
    "NALM6": {"color": "#55a630", "marker": "^", "linestyle": "-", "zorder": 8},
}

EXPERIMENTAL_MARKERS = ["D", "p", "X", "P", "h"]
STYLE_METADATA_FIELDS = [
    "sample",
    "color",
    "marker",
    "linestyle",
    "linewidth",
    "markersize",
    "markeredgewidth",
    "zorder",
    "legend_label",
]


@dataclasses.dataclass(frozen=True)
class PlotDefinition:
    """One user-defined figure and the samples assigned to it."""

    name: str
    sequences: list[str]
    controls: list[str]


@dataclasses.dataclass(frozen=True)
class RefeedEvent:
    """One user-entered refeed time and its first recorded post-refeed image."""

    event_hour: float
    baseline_hour: float


def clean(text: object) -> str:
    return "" if text is None else str(text).strip().lstrip("\ufeff")


def normalize_plate(value: object) -> str:
    text = clean(value)
    if not text:
        raise ValueError("Missing plate value")
    try:
        number = float(text)
        if number.is_integer():
            return str(int(number))
    except ValueError:
        pass
    return text


def normalize_well(value: object) -> str:
    text = clean(value).upper()
    match = WELL_RE.fullmatch(text)
    if not match:
        raise ValueError(f"Invalid well name: {value!r}")
    row, column = match.groups()
    column_number = int(column)
    if not 1 <= column_number <= 24:
        raise ValueError(f"Invalid well column in {value!r}")
    return f"{row}{column_number}"


def parse_number(value: object) -> float | None:
    text = clean(value)
    if not text or text.lower() in {"na", "nan", "n/a", "null"}:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError as exc:
        raise ValueError(f"Expected a numeric measurement, got {value!r}") from exc


def read_export_rows(path: Path) -> list[list[str]]:
    """Read a native tab-delimited TXT/TSV export or a legacy CSV copy."""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".tsv"}:
        delimiter = "\t"
    elif suffix == ".csv":
        delimiter = ","
    else:
        raise ValueError(
            f"Unsupported plate export type for {path}. Use .txt, .tsv, or .csv."
        )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle, delimiter=delimiter))


def extract_prefixed_value(rows: list[list[str]], prefix: str) -> str:
    prefix_lower = prefix.lower()
    for row in rows[:30]:
        if not row:
            continue
        first = clean(row[0])
        if first.lower().startswith(prefix_lower):
            return clean(first.split(":", 1)[1]) if ":" in first else ""
    return ""


def infer_plate(rows: list[list[str]], path: Path) -> tuple[str, str]:
    vessel_name = extract_prefixed_value(rows, "Vessel Name:")
    for source in (vessel_name, path.stem):
        match = PLATE_FROM_VESSEL_RE.search(source) or TRAILING_NUMBER_RE.search(source)
        if match:
            return normalize_plate(match.group(1)), vessel_name
    raise ValueError(
        f"Could not infer plate number from Vessel Name or filename for {path}. "
        "Expected text ending in something like 'plate_1'."
    )


def parse_timestamp(text: str) -> str:
    text = clean(text)
    formats = (
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%y %I:%M %p",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%y %H:%M",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).isoformat(sep=" ")
        except ValueError:
            continue
    return text


def find_elapsed(row: list[str]) -> float:
    lowered = [clean(value).lower() for value in row]
    try:
        index = lowered.index("elapsed:")
        return float(clean(row[index + 1]))
    except (ValueError, IndexError):
        pass
    if len(row) > 3:
        try:
            return float(clean(row[3]))
        except ValueError:
            pass
    raise ValueError(f"Could not parse elapsed time from row: {row}")


def find_column_header(rows: list[list[str]], start_index: int) -> tuple[int, dict[int, int]]:
    """Return the header row index and export-column to plate-column mapping."""
    for index in range(start_index + 1, min(start_index + 8, len(rows))):
        mapping: dict[int, int] = {}
        for export_column, value in enumerate(rows[index]):
            text = clean(value)
            if text.isdigit():
                mapping[export_column] = int(text)
        if len(mapping) >= 6:
            return index, mapping
    raise ValueError(f"Could not locate plate column header after row {start_index + 1}")


def parse_plate_export(
    path: Path, plate_override: str | None = None
) -> list[dict[str, object]]:
    rows = read_export_rows(path)
    if plate_override is None:
        plate, vessel_name = infer_plate(rows, path)
    else:
        plate = normalize_plate(plate_override)
        vessel_name = extract_prefixed_value(rows, "Vessel Name:")
    metric = extract_prefixed_value(rows, "Metric:")
    analysis_name = extract_prefixed_value(rows, "Analysis:")
    records: list[dict[str, object]] = []

    time_row_indices = [
        index
        for index, row in enumerate(rows)
        if row and clean(row[0]).lower() == "time stamp:"
    ]
    if not time_row_indices:
        raise ValueError(f"No 'Time Stamp:' blocks found in {path}")

    for block_number, time_index in enumerate(time_row_indices, start=1):
        time_row = rows[time_index]
        timestamp_raw = clean(time_row[1]) if len(time_row) > 1 else ""
        elapsed_hours = find_elapsed(time_row)
        header_index, column_map = find_column_header(rows, time_index)

        row_index = header_index + 1
        wells_seen = 0
        while row_index < len(rows):
            row = rows[row_index]
            row_label = clean(row[0]).upper() if row else ""
            if row_label == "TIME STAMP:" or not re.fullmatch(r"[A-P]", row_label):
                break

            for export_column, plate_column in column_map.items():
                value = row[export_column] if export_column < len(row) else ""
                measurement = parse_number(value)
                if measurement is None:
                    continue
                records.append(
                    {
                        "plate": plate,
                        "vessel_name": vessel_name,
                        "source_file": path.name,
                        "metric": metric,
                        "analysis": analysis_name,
                        "block": block_number,
                        "timestamp": parse_timestamp(timestamp_raw),
                        "elapsed_hours": elapsed_hours,
                        "well": f"{row_label}{plate_column}",
                        "value": measurement,
                    }
                )
                wells_seen += 1
            row_index += 1

        if wells_seen == 0:
            raise ValueError(
                f"Found elapsed time {elapsed_hours} in {path.name}, but no numeric well values."
            )

    return records


def read_metadata(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Metadata file {path} has no header")
        normalized_headers = {clean(header).lower(): header for header in reader.fieldnames}
        missing = {"well", "sample", "plate"} - normalized_headers.keys()
        if missing:
            raise ValueError(f"Metadata is missing columns: {sorted(missing)}")

        records: list[dict[str, str]] = []
        for row_number, row in enumerate(reader, start=2):
            well = normalize_well(row[normalized_headers["well"]])
            sample = clean(row[normalized_headers["sample"]])
            plate = normalize_plate(row[normalized_headers["plate"]])
            if not sample:
                raise ValueError(f"Missing sample in metadata row {row_number}")
            records.append({"plate": plate, "well": well, "sample": sample})

    keys = [(row["plate"], row["well"]) for row in records]
    duplicates = [key for key, count in Counter(keys).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate plate/well entries in metadata: {duplicates[:10]}")
    return records


def add_replicate_numbers(
    metadata: list[dict[str, str]],
) -> dict[tuple[str, str], dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in metadata:
        grouped[(row["plate"], row["sample"])].append(row)

    lookup: dict[tuple[str, str], dict[str, object]] = {}
    for (plate, sample), rows in grouped.items():
        def well_sort_key(item: dict[str, str]) -> tuple[int, int]:
            match = WELL_RE.fullmatch(item["well"])
            assert match
            return ord(match.group(1).upper()) - ord("A"), int(match.group(2))

        for replicate, row in enumerate(sorted(rows, key=well_sort_key), start=1):
            lookup[(plate, row["well"])] = {
                "sample": sample,
                "replicate": replicate,
                "replicate_id": f"{sample}_rep{replicate}",
            }
    return lookup


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def metadata_plate_ids(metadata_path: Path) -> list[str]:
    """Return unique plate identifiers in metadata, preserving natural order."""
    return sorted(
        {row["plate"] for row in read_metadata(metadata_path)},
        key=natural_key,
    )


def resolve_plate_specs(
    specs: list[str], metadata_path: Path
) -> list[tuple[str, Path]]:
    """Resolve CLI plate inputs into explicit ``(plate_id, file_path)`` pairs.

    Accepted forms:
      * One bare file: ``--plates export.txt``. This is assigned to the only
        plate identifier present in metadata.
      * Explicit mappings: ``--plates 1=plate1.txt 2=plate2.txt``.

    Bare glob patterns remain supported only when they resolve to one file and
    metadata contains one plate. Multiple files must be mapped explicitly so
    their plate identities are unambiguous.
    """
    plate_ids = metadata_plate_ids(metadata_path)
    resolved: list[tuple[str | None, Path]] = []

    for spec in specs:
        if "=" in spec:
            plate_text, file_pattern = spec.split("=", 1)
            plate_id = normalize_plate(plate_text)
            if not clean(file_pattern):
                raise ValueError(f"Missing file after plate mapping {spec!r}")
        else:
            plate_id = None
            file_pattern = spec

        matches = [Path(match).resolve() for match in glob.glob(file_pattern)]
        if not matches and Path(file_pattern).is_file():
            matches = [Path(file_pattern).resolve()]
        if not matches:
            raise ValueError(f"No plate export file matched {file_pattern!r}")
        if plate_id is not None and len(matches) != 1:
            raise ValueError(
                f"Plate mapping {spec!r} matched {len(matches)} files; "
                "each explicit plate mapping must identify exactly one file."
            )
        resolved.extend((plate_id, path) for path in matches)

    if not resolved:
        raise ValueError("No plate export files matched --plates")

    bare = [(plate, path) for plate, path in resolved if plate is None]
    if bare:
        if len(resolved) != 1:
            raise ValueError(
                "When multiple plate files are supplied, label every file as "
                "PLATE=FILE (for example: --plates 1=plate1.txt 2=plate2.txt)."
            )
        if len(plate_ids) != 1:
            raise ValueError(
                "A bare single plate file can only be auto-assigned when metadata "
                f"contains exactly one plate; found metadata plates {plate_ids}."
            )
        resolved = [(plate_ids[0], resolved[0][1])]

    explicit_plate_ids = [str(plate) for plate, _ in resolved]
    duplicates = [
        plate for plate, count in Counter(explicit_plate_ids).items() if count > 1
    ]
    if duplicates:
        raise ValueError(f"Plate identifiers were supplied more than once: {duplicates}")

    unknown = sorted(set(explicit_plate_ids) - set(plate_ids), key=natural_key)
    if unknown:
        raise ValueError(
            f"Input mappings contain plate(s) not found in metadata: {unknown}. "
            f"Metadata plates are {plate_ids}."
        )

    missing = sorted(set(plate_ids) - set(explicit_plate_ids), key=natural_key)
    if missing:
        warnings.warn(
            f"No export was supplied for metadata plate(s): {missing}",
            stacklevel=2,
        )

    return [(str(plate), path) for plate, path in resolved]


def reshape_exports(
    metadata_path: Path,
    plate_patterns: list[str],
    output_dir: Path,
    long_name: str,
    summary_name: str,
) -> Path:
    """Parse exports, join metadata, write cleaned tables, and return long-table path."""
    plate_specs = resolve_plate_specs(plate_patterns, metadata_path)
    metadata_lookup = add_replicate_numbers(read_metadata(metadata_path))

    raw_records: list[dict[str, object]] = []
    for plate_id, path in plate_specs:
        raw_records.extend(parse_plate_export(path, plate_override=plate_id))

    source_files_by_plate: dict[str, set[str]] = defaultdict(set)
    for row in raw_records:
        source_files_by_plate[str(row["plate"])].add(str(row["source_file"]))
    duplicate_plate_files = {
        plate: sorted(files)
        for plate, files in source_files_by_plate.items()
        if len(files) > 1
    }
    if duplicate_plate_files:
        raise ValueError(
            f"Multiple export files resolved to the same plate: {duplicate_plate_files}"
        )

    long_rows: list[dict[str, object]] = []
    unmapped: set[tuple[str, str]] = set()
    for record in raw_records:
        key = (str(record["plate"]), str(record["well"]))
        metadata_row = metadata_lookup.get(key)
        if metadata_row is None:
            unmapped.add(key)
            continue
        long_rows.append({**record, **metadata_row})
    if not long_rows:
        raise ValueError("No measured wells matched the plate metadata.")

    long_rows.sort(
        key=lambda row: (
            str(row["sample"]),
            float(row["elapsed_hours"]),
            str(row["plate"]),
            int(row["replicate"]),
        )
    )

    groups: dict[tuple[str, str, float, str], list[dict[str, object]]] = defaultdict(list)
    for row in long_rows:
        key = (
            str(row["plate"]),
            str(row["sample"]),
            float(row["elapsed_hours"]),
            str(row["metric"]),
        )
        groups[key].append(row)

    summary_rows: list[dict[str, object]] = []
    for (plate, sample, elapsed, metric), rows in groups.items():
        values = [float(row["value"]) for row in rows]
        n = len(values)
        sd = statistics.stdev(values) if n >= 2 else math.nan
        sem = sd / math.sqrt(n) if n >= 2 else math.nan
        summary_rows.append(
            {
                "plate": plate,
                "sample": sample,
                "elapsed_hours": elapsed,
                "metric": metric,
                "n": n,
                "mean": sum(values) / n,
                "sd": sd,
                "sem": sem,
                "min": min(values),
                "max": max(values),
                "values": ";".join(f"{value:g}" for value in values),
                "wells": ";".join(str(row["well"]) for row in rows),
                "plates": ";".join(sorted({str(row["plate"]) for row in rows})),
            }
        )
    summary_rows.sort(
        key=lambda row: (str(row["plate"]), str(row["sample"]), float(row["elapsed_hours"]))
    )

    long_fields = [
        "sample", "replicate", "replicate_id", "plate", "well", "elapsed_hours",
        "timestamp", "value", "metric", "vessel_name", "analysis", "source_file", "block",
    ]
    summary_fields = [
        "plate", "sample", "elapsed_hours", "metric", "n", "mean", "sd", "sem",
        "min", "max", "values", "wells", "plates",
    ]
    long_path = output_dir / long_name
    summary_path = output_dir / summary_name
    write_csv(long_path, long_rows, long_fields)
    write_csv(summary_path, summary_rows, summary_fields)

    mapped_keys = {(str(row["plate"]), str(row["well"])) for row in long_rows}
    missing_metadata_wells = sorted(set(metadata_lookup) - mapped_keys)
    plate_description = ", ".join(
        f"plate {plate_id}={path.name}" for plate_id, path in plate_specs
    )
    print(f"Parsed {len(plate_specs)} plate file(s): {plate_description}")
    print(f"Wrote {len(long_rows):,} mapped well-time observations to {long_path}")
    print(f"Wrote {len(summary_rows):,} sample-time summaries to {summary_path}")
    if unmapped:
        print(f"Ignored {len(unmapped)} measured plate/well combinations not present in metadata.")
    if missing_metadata_wells:
        preview = ", ".join(
            f"plate {plate} well {well}" for plate, well in missing_metadata_wells[:10]
        )
        print(
            f"WARNING: {len(missing_metadata_wells)} metadata wells had no measurement ({preview})."
        )
    return long_path

def natural_key(value: object) -> tuple[object, ...]:
    """Sort sample 2 before sample 10."""
    parts = re.split(r"(\d+)", str(value))
    return tuple(int(part) if part.isdigit() else part.lower() for part in parts)


def canonical_sample(value: object) -> str:
    """Standardize control labels while preserving experimental labels."""
    text = str(value).strip()
    key = re.sub(r"[_-]+", " ", text).lower().strip()
    key = re.sub(r"\s+", " ", key)
    return CONTROL_ALIASES.get(key, text)


def set_plot_font(requested: str | None) -> str:
    """Select an installed font by name while preserving the original default."""
    available = {font.name for font in mpl.font_manager.fontManager.ttflist}
    available_by_case = {name.casefold(): name for name in available}
    generic_families = {"sans-serif", "serif", "monospace", "cursive", "fantasy"}

    if requested:
        cleaned = clean(requested)
        generic = cleaned.casefold()
        if generic in generic_families:
            selected = generic
        else:
            selected = available_by_case.get(generic)
            if selected is None:
                examples = "Avenir, Arial, Times New Roman, DejaVu Sans"
                raise ValueError(
                    f"Font {requested!r} is not installed on this computer. "
                    f"Examples of commonly installed fonts: {examples}."
                )
    elif "Avenir" in available:
        selected = "Avenir"
    elif "Avenir Next" in available:
        selected = "Avenir Next"
    else:
        selected = "DejaVu Sans"
        warnings.warn(
            "Avenir/Avenir Next is not installed; using DejaVu Sans.",
            stacklevel=2,
        )

    mpl.rcParams.update(
        {
            "font.family": selected,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 1.0,
        }
    )
    return selected


def nonblank_text(series: pd.Series) -> pd.Series:
    """Return stripped strings and represent missing values as blank strings."""
    return series.where(series.notna(), "").astype(str).str.strip()


def build_series_id(df: pd.DataFrame) -> pd.Series:
    """Build one identifier for each physical well/time course.

    The run identity is chosen row-by-row from vessel_name, source_file, then
    plate. The replicate identity is chosen from well, replicate_id, then
    replicate. The sample name is kept as a separate grouping key.
    """
    run_identity = pd.Series("", index=df.index, dtype="object")
    for column in ("vessel_name", "source_file", "plate"):
        if column not in df.columns:
            continue
        candidate = nonblank_text(df[column])
        use = run_identity.eq("") & candidate.ne("")
        run_identity.loc[use] = candidate.loc[use]
    run_identity = run_identity.mask(run_identity.eq(""), "single_run")

    replicate_identity = pd.Series("", index=df.index, dtype="object")
    for column in ("well", "replicate_id", "replicate"):
        if column not in df.columns:
            continue
        candidate = nonblank_text(df[column])
        use = replicate_identity.eq("") & candidate.ne("")
        replicate_identity.loc[use] = candidate.loc[use]

    missing = replicate_identity.eq("")
    if missing.any():
        raise ValueError(
            "Could not identify some physical replicates. The CSV needs a nonblank "
            "well, replicate_id, or replicate column. Problem row indices: "
            f"{df.index[missing].tolist()[:10]}"
        )

    return run_identity + "::" + replicate_identity


def prepare_input(path: Path, requested_metric: str | None) -> pd.DataFrame:
    """Read and validate the long-format data while preserving raw measurements."""
    if not path.exists():
        raise FileNotFoundError(f"Input CSV does not exist: {path}")

    df = pd.read_csv(path)
    required = {"sample", "elapsed_hours"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    # Prefer an explicitly named raw column when rerunning on an audit export.
    if "raw_value" in df.columns:
        raw_source = "raw_value"
    elif "value" in df.columns:
        raw_source = "value"
    else:
        raise ValueError("Input needs a raw measurement column named 'value' or 'raw_value'.")

    if "metric" in df.columns:
        metric_text = nonblank_text(df["metric"])
        available_metrics = sorted(metric_text.loc[metric_text.ne("")].unique().tolist())
        if requested_metric is not None:
            df = df.loc[metric_text.eq(requested_metric)].copy()
            if df.empty:
                raise ValueError(
                    f"Metric {requested_metric!r} was not found. "
                    f"Available metrics: {available_metrics}"
                )
        elif len(available_metrics) > 1:
            raise ValueError(
                "The CSV contains multiple assay metrics. Choose one with --metric. "
                f"Available metrics: {available_metrics}"
            )
    elif requested_metric is not None:
        raise ValueError("--metric was supplied, but the CSV has no 'metric' column.")

    out = df.copy()
    out["sample"] = out["sample"].map(canonical_sample)
    out["elapsed_hours"] = pd.to_numeric(out["elapsed_hours"], errors="coerce")
    out["raw_value"] = pd.to_numeric(out[raw_source], errors="coerce")

    invalid = out[["sample", "elapsed_hours", "raw_value"]].isna().any(axis=1)
    if invalid.any():
        warnings.warn(f"Dropping {int(invalid.sum())} rows with missing/non-numeric values.", stacklevel=2)
        out = out.loc[~invalid].copy()
    if out.empty:
        raise ValueError("No valid rows remain after numeric conversion.")

    # Remove the ambiguous generic name. Downstream code cannot accidentally use it.
    if "value" in out.columns:
        out = out.drop(columns="value")

    out["series_id"] = build_series_id(out)

    measurement_key = ["sample", "series_id", "elapsed_hours"]
    duplicate = out.duplicated(measurement_key, keep=False)
    if duplicate.any():
        columns = [
            c
            for c in ("sample", "plate", "well", "series_id", "elapsed_hours", "raw_value", "source_file")
            if c in out.columns
        ]
        raise ValueError(
            "Duplicate rows exist for the same physical replicate and time point. "
            "This usually means the same export was included twice. Examples:\n"
            + out.loc[duplicate, columns].head(12).to_string(index=False)
        )

    return out


def normalize_per_well(df: pd.DataFrame, baseline_hour: float) -> pd.DataFrame:
    """Divide every physical well by its own raw measurement at the baseline."""
    out = df.copy()
    trajectory_keys = ["sample", "series_id"]
    is_baseline = np.isclose(
        out["elapsed_hours"].to_numpy(dtype=float),
        baseline_hour,
        atol=BASELINE_ATOL,
        rtol=0.0,
    )

    baseline_rows = out.loc[is_baseline, trajectory_keys + ["raw_value"]].copy()
    if baseline_rows.empty:
        raise ValueError(
            f"No measurements were found at baseline hour {baseline_hour:g}. "
            "Choose an elapsed hour that exists in the input data."
        )

    baseline_counts = baseline_rows.groupby(trajectory_keys, dropna=False).size()
    duplicate_baselines = baseline_counts.loc[baseline_counts != 1]
    if not duplicate_baselines.empty:
        raise ValueError(
            f"Every physical replicate must have exactly one row at baseline hour {baseline_hour:g}. "
            f"Problem trajectories: {duplicate_baselines.head(10).to_dict()}"
        )

    baselines = baseline_rows.rename(columns={"raw_value": "baseline_raw_value"})
    all_trajectories = out[trajectory_keys].drop_duplicates()
    missing = all_trajectories.merge(
        baselines[trajectory_keys],
        on=trajectory_keys,
        how="left",
        indicator=True,
    )
    missing = missing.loc[missing["_merge"].eq("left_only"), trajectory_keys]
    if not missing.empty:
        raise ValueError(
            f"Some physical replicates have no value at baseline hour {baseline_hour:g}. Examples:\n"
            + missing.head(12).to_string(index=False)
        )

    invalid_baseline = (~np.isfinite(baselines["baseline_raw_value"])) | baselines[
        "baseline_raw_value"
    ].eq(0)
    if invalid_baseline.any():
        raise ValueError(
            f"Values at baseline hour {baseline_hour:g} must be finite and nonzero. Examples:\n"
            + baselines.loc[invalid_baseline].head(12).to_string(index=False)
        )

    out = out.merge(baselines, on=trajectory_keys, how="left", validate="many_to_one")
    out[NORMALIZED_COLUMN] = out["raw_value"] / out["baseline_raw_value"]

    if not np.isfinite(out[NORMALIZED_COLUMN]).all():
        raise RuntimeError("Normalization produced non-finite values.")

    normalized_t0 = out.loc[
        np.isclose(
            out["elapsed_hours"].to_numpy(dtype=float),
            baseline_hour,
            atol=BASELINE_ATOL,
            rtol=0.0,
        ),
        NORMALIZED_COLUMN,
    ].to_numpy(dtype=float)
    if not np.allclose(normalized_t0, 1.0, atol=1e-12, rtol=0.0):
        raise RuntimeError(
            f"Internal normalization check failed: every individual well must equal 1.0 at baseline hour {baseline_hour:g}."
        )

    return out


def normalize_by_refeed_segments(
    df: pd.DataFrame,
    initial_baseline_hour: float,
    refeed_events: list[RefeedEvent],
) -> pd.DataFrame:
    """Normalize each well to the most recent post-refeed baseline measurement."""
    if not refeed_events:
        raise ValueError("At least one refeed event is required for refeed normalization")

    out = df.copy()
    trajectory_keys = ["sample", "series_id"]
    baseline_hours = np.array(
        [initial_baseline_hour] + [event.baseline_hour for event in refeed_events],
        dtype=float,
    )
    event_hours = np.array(
        [np.nan] + [event.event_hour for event in refeed_events], dtype=float
    )
    elapsed = out["elapsed_hours"].to_numpy(dtype=float)
    segment_indices = np.searchsorted(baseline_hours, elapsed, side="right") - 1
    segment_indices = np.clip(segment_indices, 0, len(baseline_hours) - 1)
    out[SEGMENT_COLUMN] = segment_indices.astype(int)
    out[SEGMENT_BASELINE_COLUMN] = baseline_hours[segment_indices]
    out[REFEED_EVENT_COLUMN] = event_hours[segment_indices]
    out[HOURS_SINCE_REFEED_COLUMN] = (
        out["elapsed_hours"] - out[SEGMENT_BASELINE_COLUMN]
    )

    is_segment_baseline = np.isclose(
        elapsed,
        out[SEGMENT_BASELINE_COLUMN].to_numpy(dtype=float),
        atol=BASELINE_ATOL,
        rtol=0.0,
    )
    baseline_rows = out.loc[
        is_segment_baseline,
        trajectory_keys + [SEGMENT_COLUMN, "raw_value"],
    ].copy()
    baseline_counts = baseline_rows.groupby(
        trajectory_keys + [SEGMENT_COLUMN], dropna=False
    ).size()
    duplicate_baselines = baseline_counts.loc[baseline_counts != 1]
    if not duplicate_baselines.empty:
        raise ValueError(
            "Every physical replicate must have exactly one measurement at every "
            "resolved refeed baseline. Problem trajectories/segments: "
            f"{duplicate_baselines.head(12).to_dict()}"
        )

    all_trajectories = out[trajectory_keys].drop_duplicates().copy()
    expected = all_trajectories.merge(
        pd.DataFrame({SEGMENT_COLUMN: range(len(baseline_hours))}), how="cross"
    )
    observed = baseline_rows[trajectory_keys + [SEGMENT_COLUMN]].drop_duplicates()
    missing = expected.merge(
        observed,
        on=trajectory_keys + [SEGMENT_COLUMN],
        how="left",
        indicator=True,
    )
    missing = missing.loc[
        missing["_merge"].eq("left_only"), trajectory_keys + [SEGMENT_COLUMN]
    ]
    if not missing.empty:
        schedule_text = ", ".join(f"{hour:g}" for hour in baseline_hours)
        raise ValueError(
            "Every physical replicate needs a measurement at every resolved refeed "
            f"baseline ({schedule_text} h). Missing examples:\n"
            + missing.head(12).to_string(index=False)
        )

    baselines = baseline_rows.rename(
        columns={"raw_value": "segment_baseline_raw_value"}
    )
    invalid_baseline = (~np.isfinite(baselines["segment_baseline_raw_value"])) | (
        baselines["segment_baseline_raw_value"].eq(0)
    )
    if invalid_baseline.any():
        raise ValueError(
            "Every refeed baseline must be finite and nonzero. Examples:\n"
            + baselines.loc[invalid_baseline].head(12).to_string(index=False)
        )

    out = out.merge(
        baselines,
        on=trajectory_keys + [SEGMENT_COLUMN],
        how="left",
        validate="many_to_one",
    )
    out[NORMALIZED_COLUMN] = out["raw_value"] / out["segment_baseline_raw_value"]
    if not np.isfinite(out[NORMALIZED_COLUMN]).all():
        raise RuntimeError("Refeed normalization produced non-finite values")

    normalized_is_baseline = np.isclose(
        out["elapsed_hours"].to_numpy(dtype=float),
        out[SEGMENT_BASELINE_COLUMN].to_numpy(dtype=float),
        atol=BASELINE_ATOL,
        rtol=0.0,
    )
    normalized_baselines = out.loc[
        normalized_is_baseline, NORMALIZED_COLUMN
    ].to_numpy(dtype=float)
    if not np.allclose(normalized_baselines, 1.0, atol=1e-12, rtol=0.0):
        raise RuntimeError(
            "Internal refeed-normalization check failed: every physical well must "
            "equal 1.0 at every segment baseline"
        )
    return out


def normalization_group_keys(normalized: pd.DataFrame) -> list[str]:
    """Retain segment metadata in summaries when refeed normalization is active."""
    keys = ["sample", "elapsed_hours"]
    for column in (
        SEGMENT_COLUMN,
        SEGMENT_BASELINE_COLUMN,
        REFEED_EVENT_COLUMN,
        HOURS_SINCE_REFEED_COLUMN,
    ):
        if column in normalized.columns:
            keys.append(column)
    return keys


def validate_summary_at_baselines(
    summary: pd.DataFrame,
    baseline_hours: list[float],
    value_column: str,
    expected_value: float,
    description: str,
) -> None:
    """Require every summarized sample to reset exactly at every baseline."""
    for baseline_hour in baseline_hours:
        baseline = summary.loc[
            np.isclose(
                summary["elapsed_hours"].to_numpy(dtype=float),
                baseline_hour,
                atol=BASELINE_ATOL,
                rtol=0.0,
            )
        ]
        if baseline.empty or not np.allclose(
            baseline[value_column], expected_value, atol=1e-12, rtol=0.0
        ):
            raise RuntimeError(
                f"Refusing to plot: {description} sample means are not all "
                f"{expected_value:g} at baseline hour {baseline_hour:g}."
            )


def make_plot_summary(
    normalized: pd.DataFrame,
    baseline_hour: float,
    additional_baseline_hours: list[float] | None = None,
) -> pd.DataFrame:
    """Calculate the exact normalized mean and SEM sent to Matplotlib."""
    summary = (
        normalized.groupby(normalization_group_keys(normalized), dropna=False)
        .agg(
            n=("series_id", "nunique"),
            mean_fold_change=(NORMALIZED_COLUMN, "mean"),
            sd_fold_change=(NORMALIZED_COLUMN, "std"),
            min_fold_change=(NORMALIZED_COLUMN, "min"),
            max_fold_change=(NORMALIZED_COLUMN, "max"),
        )
        .reset_index()
        .sort_values(["sample", "elapsed_hours"])
    )
    summary[PLOT_SEM_COLUMN] = summary["sd_fold_change"] / np.sqrt(summary["n"])
    summary.loc[summary["n"] <= 1, PLOT_SEM_COLUMN] = np.nan

    validate_summary_at_baselines(
        summary,
        [baseline_hour] + (additional_baseline_hours or []),
        PLOT_MEAN_COLUMN,
        1.0,
        "linear",
    )

    return summary


def add_log2_fold_change(
    normalized: pd.DataFrame,
    baseline_hour: float,
    additional_baseline_hours: list[float] | None = None,
) -> pd.DataFrame:
    """Calculate per-well log2 fold change after baseline normalization."""
    out = normalized.copy()
    invalid = (~np.isfinite(out[NORMALIZED_COLUMN])) | out[NORMALIZED_COLUMN].le(0)
    if invalid.any():
        columns = [
            column
            for column in ("sample", "plate", "well", "elapsed_hours", NORMALIZED_COLUMN)
            if column in out.columns
        ]
        raise ValueError(
            "Log2 fold change requires every normalized measurement to be positive. "
            "Examples:\n" + out.loc[invalid, columns].head(12).to_string(index=False)
        )

    out[LOG2_NORMALIZED_COLUMN] = np.log2(out[NORMALIZED_COLUMN])
    for check_hour in [baseline_hour] + (additional_baseline_hours or []):
        baseline_values = out.loc[
            np.isclose(
                out["elapsed_hours"].to_numpy(dtype=float),
                check_hour,
                atol=BASELINE_ATOL,
                rtol=0.0,
            ),
            LOG2_NORMALIZED_COLUMN,
        ].to_numpy(dtype=float)
        if baseline_values.size == 0 or not np.allclose(
            baseline_values, 0.0, atol=1e-12, rtol=0.0
        ):
            raise RuntimeError(
                "Internal check failed: every per-well log2 value must be 0 at "
                f"baseline hour {check_hour:g}."
            )
    return out


def make_log2_plot_summary(
    normalized: pd.DataFrame,
    baseline_hour: float,
    additional_baseline_hours: list[float] | None = None,
) -> pd.DataFrame:
    """Average per-well log2 fold changes and calculate SEM for plotting."""
    summary = (
        normalized.groupby(normalization_group_keys(normalized), dropna=False)
        .agg(
            n=("series_id", "nunique"),
            mean_log2_fold_change=(LOG2_NORMALIZED_COLUMN, "mean"),
            sd_log2_fold_change=(LOG2_NORMALIZED_COLUMN, "std"),
            min_log2_fold_change=(LOG2_NORMALIZED_COLUMN, "min"),
            max_log2_fold_change=(LOG2_NORMALIZED_COLUMN, "max"),
        )
        .reset_index()
        .sort_values(["sample", "elapsed_hours"])
    )
    summary[LOG2_PLOT_SEM_COLUMN] = summary["sd_log2_fold_change"] / np.sqrt(
        summary["n"]
    )
    summary.loc[summary["n"] <= 1, LOG2_PLOT_SEM_COLUMN] = np.nan

    validate_summary_at_baselines(
        summary,
        [baseline_hour] + (additional_baseline_hours or []),
        LOG2_PLOT_MEAN_COLUMN,
        0.0,
        "log2",
    )
    return summary


def resolve_colormap_name(value: str) -> str:
    """Return a registered Matplotlib color map name, ignoring case."""
    requested = clean(value)
    by_casefold = {name.casefold(): name for name in mpl.colormaps}
    resolved = by_casefold.get(requested.casefold())
    if resolved is None:
        examples = "plasma, viridis, magma, inferno, cividis, tab10, turbo"
        raise ValueError(
            f"Unknown Matplotlib color map {value!r}. Common choices: {examples}."
        )
    return resolved


def colormap_colors(
    n: int,
    cmap_name: str,
    max_position: float,
) -> list[tuple[float, float, float, float]]:
    """Choose evenly spaced colors while preserving the original plasma default."""
    if n <= 0:
        return []
    positions = np.linspace(0.08, max_position, n)
    colormap = mpl.colormaps[cmap_name]
    return [colormap(float(position)) for position in positions]


def parse_controls(value: str) -> list[str]:
    """Parse comma-separated control names and apply known label aliases."""
    names = [canonical_sample(item) for item in value.split(",") if item.strip()]
    return list(dict.fromkeys(names))


def parse_comma_options(values: list[str] | None) -> list[str]:
    """Combine repeatable comma-separated command-line values."""
    if not values:
        return []
    return list(
        dict.fromkeys(
            clean(item)
            for value in values
            for item in value.split(",")
            if clean(item)
        )
    )


def parse_drop_times(values: list[str] | None) -> list[float]:
    """Parse repeatable comma-separated time points."""
    times: list[float] = []
    for item in parse_comma_options(values):
        try:
            time = float(item)
        except ValueError as exc:
            raise ValueError(
                f"Invalid time {item!r} in --drop-time. Use numbers such as "
                "--drop-time '22, 55'."
            ) from exc
        if not math.isfinite(time):
            raise ValueError("--drop-time values must be finite numbers")
        if time not in times:
            times.append(time)
    return times


def parse_refeed_times(values: list[str] | None) -> list[float]:
    """Parse refeed event times and return them in chronological order."""
    times: list[float] = []
    for item in parse_comma_options(values):
        try:
            time = float(item)
        except ValueError as exc:
            raise ValueError(
                f"Invalid time {item!r} in --refeed-time. Use numbers such as "
                "--refeed-time '48, 120, 192'."
            ) from exc
        if not math.isfinite(time):
            raise ValueError("--refeed-time values must be finite numbers")
        if time not in times:
            times.append(time)
    return sorted(times)


def resolve_refeed_events(
    raw: pd.DataFrame,
    requested_times: list[float],
    initial_baseline_hour: float,
) -> list[RefeedEvent]:
    """Map each event to the first recorded image at or after that refeed."""
    if not requested_times:
        return []
    if any(time <= initial_baseline_hour + BASELINE_ATOL for time in requested_times):
        raise ValueError(
            "Every --refeed-time must occur after --baseline-hour. The initial "
            "baseline already covers the first segment."
        )

    available_times = np.array(
        sorted(raw["elapsed_hours"].astype(float).unique()), dtype=float
    )
    events: list[RefeedEvent] = []
    previous_baseline = initial_baseline_hour
    for requested_time in requested_times:
        candidates = available_times[
            available_times >= requested_time - BASELINE_ATOL
        ]
        if candidates.size == 0:
            raise ValueError(
                f"Refeed at {requested_time:g} h has no recorded image at or after "
                f"it. The final recorded time is {available_times.max():g} h."
            )
        resolved = float(candidates[0])
        if resolved <= previous_baseline + BASELINE_ATOL:
            raise ValueError(
                f"Refeed at {requested_time:g} h resolves to {resolved:g} h, which "
                "is not later than the previous segment baseline. Refeed events may "
                "be too close together for the imaging interval."
            )
        events.append(RefeedEvent(requested_time, resolved))
        previous_baseline = resolved
    return events


def drop_time_points(
    raw: pd.DataFrame,
    times: list[float],
    baseline_hour: float,
    protected_refeed_baselines: list[float] | None = None,
) -> pd.DataFrame:
    """Remove requested time points while protecting the normalization baseline."""
    if not times:
        return raw
    if any(math.isclose(time, baseline_hour, abs_tol=BASELINE_ATOL) for time in times):
        raise ValueError(
            f"Cannot drop baseline hour {baseline_hour:g}. Choose another "
            "--baseline-hour or remove it from --drop-time."
        )
    protected_refeed_baselines = protected_refeed_baselines or []
    for time in times:
        for refeed_baseline in protected_refeed_baselines:
            if math.isclose(
                time, refeed_baseline, rel_tol=0.0, abs_tol=BASELINE_ATOL
            ):
                raise ValueError(
                    f"Cannot drop {time:g} h because it is the first recorded image "
                    "after a refeed and is required as a segment baseline."
                )
    elapsed = raw["elapsed_hours"].to_numpy(dtype=float)
    drop_mask = np.zeros(len(raw), dtype=bool)
    unmatched: list[float] = []
    for time in times:
        matches = np.isclose(elapsed, time, atol=BASELINE_ATOL, rtol=0.0)
        if not matches.any():
            unmatched.append(time)
        drop_mask |= matches
    if unmatched:
        warnings.warn(
            "Requested --drop-time value(s) not found: "
            + ", ".join(f"{value:g}" for value in unmatched),
            stacklevel=2,
        )
    filtered = raw.loc[~drop_mask].copy()
    print(
        "Dropped time point(s) from normalized tables and plots: "
        + ", ".join(f"{value:g}" for value in times if value not in unmatched)
    )
    return filtered


def resolve_sample_name(requested: object, available_samples: list[str]) -> str:
    """Match a spreadsheet name without altering spaces or display capitalization."""
    text = clean(requested)
    if not text:
        raise ValueError("A plot layout contains a blank sequence/control name")
    by_casefold = {sample.casefold(): sample for sample in available_samples}
    for candidate in (text, canonical_sample(text)):
        resolved = by_casefold.get(candidate.casefold())
        if resolved is not None:
            return resolved
    available = ", ".join(available_samples)
    raise ValueError(
        f"Plot layout name {text!r} was not found in the metadata. "
        f"Available sequence names: {available}"
    )


def normalized_layout_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", clean(value).lower()).strip("_")


def read_plot_layout(path: Path, available_samples: list[str]) -> list[PlotDefinition]:
    """Read a beginner-friendly, one-row-per-plot layout spreadsheet."""
    if not path.exists():
        raise FileNotFoundError(f"Plot layout CSV does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Plot layout {path} has no header row")
        header_pairs = [
            (header, normalized_layout_header(header)) for header in reader.fieldnames
        ]
        plot_headers = [
            original
            for original, normalized in header_pairs
            if normalized in {"plot_name", "plot", "title"}
        ]
        sequence_headers = [
            original
            for original, normalized in header_pairs
            if normalized == "sequence" or normalized.startswith("sequence_")
        ]
        control_headers = [
            original
            for original, normalized in header_pairs
            if normalized == "control" or normalized.startswith("control_")
        ]
        if not plot_headers:
            raise ValueError(
                "Plot layout needs a 'plot_name' column. Start from the generated "
                "plot_layout_template.csv file."
            )
        if not sequence_headers and not control_headers:
            raise ValueError(
                "Plot layout needs at least one sequence_1 or control_1 column."
            )

        definitions: list[PlotDefinition] = []
        for row_number, row in enumerate(reader, start=2):
            plot_name = clean(row.get(plot_headers[0], ""))
            if not plot_name and not any(clean(value) for value in row.values()):
                continue
            if not plot_name:
                raise ValueError(f"Missing plot_name in plot layout row {row_number}")
            sequences = [
                resolve_sample_name(row.get(header, ""), available_samples)
                for header in sequence_headers
                if clean(row.get(header, ""))
            ]
            controls = [
                resolve_sample_name(row.get(header, ""), available_samples)
                for header in control_headers
                if clean(row.get(header, ""))
            ]
            sequences = list(dict.fromkeys(sequences))
            controls = list(dict.fromkeys(controls))
            if not sequences and not controls:
                raise ValueError(
                    f"Plot {plot_name!r} in row {row_number} has no sequence or control names"
                )
            overlap = sorted(set(sequences) & set(controls), key=natural_key)
            if overlap:
                raise ValueError(
                    f"Plot {plot_name!r} lists the same name as both sequence and "
                    f"control: {overlap}"
                )
            definitions.append(PlotDefinition(plot_name, sequences, controls))

    if not definitions:
        raise ValueError(f"Plot layout {path} contains no plot rows")
    duplicate_names = [
        name
        for name, count in Counter(
            definition.name.casefold() for definition in definitions
        ).items()
        if count > 1
    ]
    if duplicate_names:
        raise ValueError(f"Plot names must be unique; duplicates: {duplicate_names}")
    return definitions


def hide_samples_from_plots(
    definitions: list[PlotDefinition], hidden_samples: list[str]
) -> list[PlotDefinition]:
    """Remove selected samples from plot definitions without touching data tables."""
    hidden = set(hidden_samples)
    if not hidden:
        return definitions
    filtered = [
        PlotDefinition(
            definition.name,
            [sample for sample in definition.sequences if sample not in hidden],
            [sample for sample in definition.controls if sample not in hidden],
        )
        for definition in definitions
    ]
    empty_names = [
        definition.name
        for definition in filtered
        if not definition.sequences and not definition.controls
    ]
    if empty_names:
        warnings.warn(
            "Skipping plot(s) left empty by --hide-sample: " + ", ".join(empty_names),
            stacklevel=2,
        )
    return [
        definition
        for definition in filtered
        if definition.sequences or definition.controls
    ]


def default_plot_definitions(
    samples: list[str],
    controls: list[str],
    group_size: int | None = None,
) -> list[PlotDefinition]:
    """Always include every line together, then add optional automatic groups."""
    control_set = set(controls)
    sequences = sorted(
        [sample for sample in samples if sample not in control_set], key=natural_key
    )
    definitions = [PlotDefinition("All sequences", sequences, controls)]
    if group_size is None:
        return definitions
    groups = [
        sequences[start : start + group_size]
        for start in range(0, len(sequences), group_size)
    ]
    definitions.extend(
        PlotDefinition(f"Group {index}", group, controls)
        for index, group in enumerate(groups, start=1)
    )
    return definitions


def write_plot_layout_csv(
    path: Path,
    definitions: list[PlotDefinition],
    *,
    minimum_sequence_columns: int = 1,
    minimum_control_columns: int = 1,
) -> None:
    """Write a layout that opens cleanly in Excel, Numbers, or Google Sheets."""
    sequence_count = max(
        minimum_sequence_columns,
        max((len(definition.sequences) for definition in definitions), default=0),
    )
    control_count = max(
        minimum_control_columns,
        max((len(definition.controls) for definition in definitions), default=0),
    )
    fieldnames = ["plot_name"] + [
        f"sequence_{index}" for index in range(1, sequence_count + 1)
    ] + [f"control_{index}" for index in range(1, control_count + 1)]
    rows: list[dict[str, object]] = []
    for definition in definitions:
        row: dict[str, object] = {"plot_name": definition.name}
        row.update(
            {
                f"sequence_{index}": sample
                for index, sample in enumerate(definition.sequences, start=1)
            }
        )
        row.update(
            {
                f"control_{index}": sample
                for index, sample in enumerate(definition.controls, start=1)
            }
        )
        rows.append(row)
    write_csv(path, rows, fieldnames)


def validate_style_value(field: str, value: str, row_number: int) -> Any:
    """Validate one nonblank value from the optional style spreadsheet."""
    if field == "color":
        if not mpl.colors.is_color_like(value):
            raise ValueError(
                f"Invalid color {value!r} in color metadata row {row_number}. "
                "Use a name such as navy or a hex code such as #2A6FDB."
            )
        return value
    if field == "marker":
        try:
            mpl.markers.MarkerStyle(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid marker {value!r} in color metadata row {row_number}."
            ) from exc
        return value
    if field == "linestyle":
        try:
            mpl.lines.Line2D([], [], linestyle=value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid linestyle {value!r} in color metadata row {row_number}."
            ) from exc
        return value
    if field in {"linewidth", "markersize", "markeredgewidth"}:
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(
                f"{field} must be a number in color metadata row {row_number}."
            ) from exc
        if number < 0:
            raise ValueError(
                f"{field} cannot be negative in color metadata row {row_number}."
            )
        return number
    if field == "zorder":
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(
                f"zorder must be a number in color metadata row {row_number}."
            ) from exc
    if field == "legend_label":
        return value
    raise ValueError(f"Unsupported style field: {field}")


def read_color_mapping_metadata(
    path: Path, available_samples: list[str]
) -> dict[str, dict[str, Any]]:
    """Read optional per-sample colors, markers, line styles, and legend labels."""
    if not path.exists():
        raise FileNotFoundError(f"Color mapping metadata CSV does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Color mapping metadata {path} has no header row")
        headers = {
            normalized_layout_header(header): header for header in reader.fieldnames
        }
        if "sample" not in headers:
            raise ValueError(
                "Color mapping metadata needs a 'sample' column. Start from the "
                "generated color_mapping_metadata_template.csv file."
            )
        unknown = sorted(set(headers) - set(STYLE_METADATA_FIELDS))
        if unknown:
            warnings.warn(
                "Ignoring unrecognized color metadata column(s): " + ", ".join(unknown),
                stacklevel=2,
            )

        overrides: dict[str, dict[str, Any]] = {}
        for row_number, row in enumerate(reader, start=2):
            requested_sample = clean(row.get(headers["sample"], ""))
            if not requested_sample and not any(clean(value) for value in row.values()):
                continue
            if not requested_sample:
                raise ValueError(
                    f"Missing sample in color mapping metadata row {row_number}"
                )
            sample = resolve_sample_name(requested_sample, available_samples)
            if sample in overrides:
                raise ValueError(
                    f"Sample {sample!r} appears more than once in color mapping metadata"
                )
            style: dict[str, Any] = {}
            for field in STYLE_METADATA_FIELDS[1:]:
                original_header = headers.get(field)
                if original_header is None:
                    continue
                value = clean(row.get(original_header, ""))
                if value:
                    target = "label" if field == "legend_label" else field
                    style[target] = validate_style_value(field, value, row_number)
            overrides[sample] = style
    return overrides


def build_plot_styles(
    plot_definitions: list[PlotDefinition],
    cmap_name: str,
    max_cmap_position: float,
    overrides: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build one stable style per sample and apply spreadsheet overrides."""
    sequences = list(
        dict.fromkeys(
            sample for definition in plot_definitions for sample in definition.sequences
        )
    )
    controls = list(
        dict.fromkeys(
            sample for definition in plot_definitions for sample in definition.controls
        )
    )
    sequence_colors = colormap_colors(len(sequences), cmap_name, max_cmap_position)
    styles = {
        sample: {
            "color": color,
            "marker": EXPERIMENTAL_MARKERS[index % len(EXPERIMENTAL_MARKERS)],
            "linestyle": "-",
            "linewidth": 2.0,
            "markersize": 5.5,
            "markeredgewidth": 0.8,
            "zorder": 5,
        }
        for index, (sample, color) in enumerate(zip(sequences, sequence_colors))
    }
    styles.update(styles_for_controls(controls))
    for sample, custom_style in overrides.items():
        if sample in styles:
            styles[sample].update(custom_style)
    return styles


def write_color_mapping_csv(
    path: Path,
    samples: list[str],
    styles: dict[str, dict[str, Any]],
) -> None:
    """Write styles in a spreadsheet-friendly, reusable format."""
    rows: list[dict[str, object]] = []
    for sample in samples:
        style = styles[sample]
        rows.append(
            {
                "sample": sample,
                "color": mpl.colors.to_hex(style["color"], keep_alpha=False),
                "marker": style["marker"],
                "linestyle": style["linestyle"],
                "linewidth": style["linewidth"],
                "markersize": style["markersize"],
                "markeredgewidth": style["markeredgewidth"],
                "zorder": style["zorder"],
                "legend_label": style.get("label", ""),
            }
        )
    write_csv(path, rows, STYLE_METADATA_FIELDS)


def styles_for_controls(controls: list[str]) -> dict[str, dict[str, Any]]:
    """Return stable styles for built-in and user-defined controls."""
    fallback_colors = mpl.colormaps["tab10"].colors
    fallback_markers = ["s", "o", "^", "v", "P", "X"]
    styles: dict[str, dict[str, Any]] = {}
    for index, control in enumerate(controls):
        styles[control] = {
            **CONTROL_STYLE.get(
                control,
                {
                "color": fallback_colors[index % len(fallback_colors)],
                "marker": fallback_markers[index % len(fallback_markers)],
                "linestyle": "--",
                "zorder": 8,
                },
            ),
            "linewidth": 2.0,
            "markersize": 5.5,
            "markeredgewidth": 0.8,
        }
    return styles


def plot_sample(
    ax: plt.Axes,
    summary: pd.DataFrame,
    sample: str,
    *,
    color: Any,
    marker: str,
    linestyle: str = "-",
    linewidth: float = 2.0,
    markersize: float = 5.5,
    markeredgewidth: float = 0.8,
    zorder: float = 5,
    label: str | None = None,
    show_sem: bool = True,
    mean_column: str = PLOT_MEAN_COLUMN,
    sem_column: str = PLOT_SEM_COLUMN,
    segment_column: str | None = None,
) -> pd.DataFrame:
    """Plot normalized columns only and return the exact rows plotted."""
    sub = summary.loc[summary["sample"].eq(sample)].sort_values("elapsed_hours").copy()
    if sub.empty:
        return sub

    if segment_column is not None and segment_column in sub.columns:
        segments = [group for _, group in sub.groupby(segment_column, sort=True)]
    else:
        segments = [sub]

    for segment_index, segment in enumerate(segments):
        x = segment["elapsed_hours"].to_numpy(dtype=float)
        y = segment[mean_column].to_numpy(dtype=float)
        sem = segment[sem_column].to_numpy(dtype=float)
        ax.plot(
            x,
            y,
            label=(label or sample) if segment_index == 0 else "_nolegend_",
            color=color,
            marker=marker,
            linestyle=linestyle,
            linewidth=linewidth,
            markersize=markersize,
            markeredgewidth=markeredgewidth,
            zorder=zorder,
        )

        if show_sem and np.isfinite(sem).any():
            ax.fill_between(
                x,
                y - sem,
                y + sem,
                color=color,
                alpha=0.14,
                linewidth=0,
                zorder=zorder - 1,
            )

    return sub


def style_plot_axis(
    ax: plt.Axes,
    *,
    title: str,
    y_label: str,
    baseline: float,
    baseline_hour: float,
    title_font_size: float,
    axis_font_size: float,
    tick_font_size: float,
    legend_font_size: float,
    legend_location: str,
    legend_columns: int,
    x_axis_linewidth: float,
    y_axis_linewidth: float,
    additional_hlines: list[float],
    h_line_color: str,
    h_line_style: str,
    h_line_width: float,
    h_line_alpha: float,
    refeed_events: list[RefeedEvent],
    refeed_line_color: str,
    refeed_line_style: str,
    refeed_line_width: float,
    refeed_line_alpha: float,
    show_refeed_labels: bool,
) -> None:
    """Apply one shared visual style to every user-defined plot."""
    ax.axhline(
        baseline,
        color="black",
        linewidth=0.8,
        linestyle="--",
        alpha=0.25,
        zorder=0,
    )
    for y_value in additional_hlines:
        ax.axhline(
            y_value,
            color=h_line_color,
            linewidth=h_line_width,
            linestyle=h_line_style,
            alpha=h_line_alpha,
            zorder=0,
        )
    for event in refeed_events:
        ax.axvline(
            event.event_hour,
            color=refeed_line_color,
            linewidth=refeed_line_width,
            linestyle=refeed_line_style,
            alpha=refeed_line_alpha,
            zorder=1,
        )
        if show_refeed_labels:
            ax.annotate(
                f"Refeed {event.event_hour:g} h",
                xy=(event.event_hour, 0.98),
                xycoords=("data", "axes fraction"),
                xytext=(3, 0),
                textcoords="offset points",
                rotation=90,
                ha="left",
                va="top",
                fontsize=tick_font_size,
                color=refeed_line_color,
                alpha=min(1.0, refeed_line_alpha + 0.2),
            )
    ax.set_title(title, fontsize=title_font_size, pad=12)
    ax.set_xlabel("Elapsed time (hours)", fontsize=axis_font_size)
    ax.set_ylabel(y_label, fontsize=axis_font_size)
    ax.tick_params(axis="both", labelsize=tick_font_size)
    ax.ticklabel_format(axis="y", style="plain", useOffset=False)
    ax.grid(axis="y", alpha=0.22, linewidth=0.8)
    ax.margins(x=0.02)
    ax.set_xlim(left=baseline_hour)
    for spine_name in ("bottom", "top"):
        ax.spines[spine_name].set_linewidth(x_axis_linewidth)
    for spine_name in ("left", "right"):
        ax.spines[spine_name].set_linewidth(y_axis_linewidth)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles,
        labels,
        frameon=False,
        fontsize=legend_font_size,
        ncol=legend_columns,
        loc=legend_location,
        handlelength=2.4,
    )


def safe_plot_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return slug or "plot"


def create_plot_set(
    summary: pd.DataFrame,
    plot_definitions: list[PlotDefinition],
    *,
    output_dir: Path,
    filename_prefix: str,
    title_prefix: str,
    y_label: str,
    mean_column: str,
    sem_column: str,
    baseline: float,
    baseline_hour: float,
    normalization_description: str,
    scale_name: str,
    show_sem: bool,
    dpi: int,
    plot_styles: dict[str, dict[str, Any]],
    cmap_name: str,
    title_font_size: float,
    axis_font_size: float,
    tick_font_size: float,
    legend_font_size: float,
    legend_location: str,
    legend_columns: int,
    x_axis_linewidth: float,
    y_axis_linewidth: float,
    additional_hlines: list[float],
    h_line_color: str,
    h_line_style: str,
    h_line_width: float,
    h_line_alpha: float,
    refeed_events: list[RefeedEvent],
    refeed_line_color: str,
    refeed_line_style: str,
    refeed_line_width: float,
    refeed_line_alpha: float,
    show_refeed_labels: bool,
    segment_column: str | None = None,
) -> list[dict[str, object]]:
    """Create one figure per spreadsheet row with stable styles across plots."""
    manifest: list[dict[str, object]] = []

    # Keep the normalization point and all later measurements, but never plot
    # measurements collected before the selected normalization hour.
    plot_summary = summary.loc[
        summary["elapsed_hours"].ge(baseline_hour - BASELINE_ATOL)
    ].copy()
    if plot_summary.empty:
        raise ValueError(
            f"No measurements remain at or after baseline hour {baseline_hour:g}."
        )

    for plot_number, definition in enumerate(plot_definitions, start=1):
        fig, ax = plt.subplots(figsize=(8.2, 5.8), constrained_layout=True)
        for sample in definition.sequences:
            plot_sample(
                ax,
                plot_summary,
                sample,
                show_sem=show_sem,
                mean_column=mean_column,
                sem_column=sem_column,
                segment_column=segment_column,
                **plot_styles[sample],
            )

        for control in definition.controls:
            plot_sample(
                ax,
                plot_summary,
                control,
                show_sem=show_sem,
                mean_column=mean_column,
                sem_column=sem_column,
                segment_column=segment_column,
                **plot_styles[control],
            )

        style_plot_axis(
            ax,
            title=f"{title_prefix}: {definition.name}",
            y_label=y_label,
            baseline=baseline,
            baseline_hour=baseline_hour,
            title_font_size=title_font_size,
            axis_font_size=axis_font_size,
            tick_font_size=tick_font_size,
            legend_font_size=legend_font_size,
            legend_location=legend_location,
            legend_columns=legend_columns,
            x_axis_linewidth=x_axis_linewidth,
            y_axis_linewidth=y_axis_linewidth,
            additional_hlines=additional_hlines,
            h_line_color=h_line_color,
            h_line_style=h_line_style,
            h_line_width=h_line_width,
            h_line_alpha=h_line_alpha,
            refeed_events=refeed_events,
            refeed_line_color=refeed_line_color,
            refeed_line_style=refeed_line_style,
            refeed_line_width=refeed_line_width,
            refeed_line_alpha=refeed_line_alpha,
            show_refeed_labels=show_refeed_labels,
        )

        png_name = (
            f"{filename_prefix}_{plot_number:02d}_"
            f"{safe_plot_slug(definition.name)}.png"
        )
        fig.savefig(output_dir / png_name, dpi=dpi)
        plt.close(fig)
        manifest.append(
            {
                "scale": scale_name,
                "plot_number": plot_number,
                "plot_name": definition.name,
                "sequence_names": ";".join(definition.sequences),
                "controls": ";".join(definition.controls),
                "cmap": cmap_name,
                "normalization": normalization_description,
                "matplotlib_y_column": mean_column,
                "first_plotted_hour": baseline_hour,
                "sem_shown": show_sem,
                "horizontal_lines": ";".join(str(value) for value in additional_hlines),
                "legend_location": legend_location,
                "refeed_event_hours": ";".join(
                    f"{event.event_hour:g}" for event in refeed_events
                ),
                "lines_broken_at_refeeds": segment_column is not None,
                "png": png_name,
            }
        )
    return manifest


def warn_existing_output(output_dir: Path) -> None:
    """Explain the safe overwrite behavior before writing into an existing folder."""
    if not output_dir.exists():
        return
    existing_files = sum(1 for path in output_dir.rglob("*") if path.is_file())
    if existing_files:
        suggested_name = (
            f"incucyte_results_{datetime.now().strftime('%Y-%m-%d')}_experiment_name"
        )
        warnings.warn(
            f"Output directory {output_dir} already contains {existing_files} file(s). "
            "Files with the same names will be overwritten, but no other files will "
            "be deleted. To keep this run completely separate, choose a clear new "
            f"folder such as --output '{suggested_name}'.",
            stacklevel=2,
        )


def make_audit(
    normalized: pd.DataFrame, summary: pd.DataFrame, baseline_hour: float
) -> pd.DataFrame:
    """Show raw baselines alongside normalized values at the selected hour."""
    normalized_baseline = normalized.loc[
        np.isclose(
            normalized["elapsed_hours"].to_numpy(dtype=float),
            baseline_hour,
            atol=BASELINE_ATOL,
            rtol=0.0,
        )
    ]
    baseline_audit = (
        normalized_baseline.groupby("sample", dropna=False)
        .agg(
            n_replicates_at_baseline=("series_id", "nunique"),
            raw_baseline_mean=("raw_value", "mean"),
            raw_baseline_min=("raw_value", "min"),
            raw_baseline_max=("raw_value", "max"),
            individual_normalized_baseline_min=(NORMALIZED_COLUMN, "min"),
            individual_normalized_baseline_max=(NORMALIZED_COLUMN, "max"),
        )
        .reset_index()
    )
    plotted_baseline = summary.loc[
        np.isclose(
            summary["elapsed_hours"].to_numpy(dtype=float),
            baseline_hour,
            atol=BASELINE_ATOL,
            rtol=0.0,
        ),
        ["sample", PLOT_MEAN_COLUMN, PLOT_SEM_COLUMN],
    ]
    return baseline_audit.merge(
        plotted_baseline, on="sample", how="left", validate="one_to_one"
    )


def refeed_schedule_rows(
    initial_baseline_hour: float, refeed_events: list[RefeedEvent]
) -> list[dict[str, object]]:
    """Create a plain-language record of every normalization segment."""
    baseline_hours = [initial_baseline_hour] + [
        event.baseline_hour for event in refeed_events
    ]
    rows: list[dict[str, object]] = []
    for segment, baseline_hour in enumerate(baseline_hours):
        event_hour: object = ""
        if segment > 0:
            event_hour = refeed_events[segment - 1].event_hour
        end_hour: object = ""
        if segment + 1 < len(baseline_hours):
            end_hour = baseline_hours[segment + 1]
        rows.append(
            {
                SEGMENT_COLUMN: segment,
                "requested_refeed_hour": event_hour,
                SEGMENT_BASELINE_COLUMN: baseline_hour,
                "segment_applies_until_hour": end_hour,
                "baseline_rule": (
                    "initial user-selected baseline"
                    if segment == 0
                    else "first recorded image at or after refeed"
                ),
            }
        )
    return rows


def make_refeed_audit(
    normalized: pd.DataFrame,
    summary: pd.DataFrame,
    initial_baseline_hour: float,
    refeed_events: list[RefeedEvent],
) -> pd.DataFrame:
    """Audit per-well and plotted resets for every refeed normalization segment."""
    elapsed = normalized["elapsed_hours"].to_numpy(dtype=float)
    segment_baselines = normalized[SEGMENT_BASELINE_COLUMN].to_numpy(dtype=float)
    baseline_rows = normalized.loc[
        np.isclose(elapsed, segment_baselines, atol=BASELINE_ATOL, rtol=0.0)
    ]
    group_keys = ["sample", SEGMENT_COLUMN, SEGMENT_BASELINE_COLUMN]
    audit = (
        baseline_rows.groupby(group_keys, dropna=False)
        .agg(
            n_replicates_at_baseline=("series_id", "nunique"),
            raw_baseline_mean=("raw_value", "mean"),
            raw_baseline_min=("raw_value", "min"),
            raw_baseline_max=("raw_value", "max"),
            individual_normalized_baseline_min=(NORMALIZED_COLUMN, "min"),
            individual_normalized_baseline_max=(NORMALIZED_COLUMN, "max"),
        )
        .reset_index()
    )
    plotted = summary.loc[
        np.isclose(
            summary["elapsed_hours"].to_numpy(dtype=float),
            summary[SEGMENT_BASELINE_COLUMN].to_numpy(dtype=float),
            atol=BASELINE_ATOL,
            rtol=0.0,
        ),
        group_keys + [PLOT_MEAN_COLUMN, PLOT_SEM_COLUMN],
    ]
    audit = audit.merge(
        plotted, on=group_keys, how="left", validate="one_to_one"
    )
    schedule = pd.DataFrame(
        refeed_schedule_rows(initial_baseline_hour, refeed_events)
    ).rename(columns={"requested_refeed_hour": REFEED_EVENT_COLUMN})
    return audit.merge(
        schedule[[SEGMENT_COLUMN, REFEED_EVENT_COLUMN]],
        on=SEGMENT_COLUMN,
        how="left",
        validate="many_to_one",
    )


def build_parser(prog: str | None = None) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Analyze raw Incucyte exports and create normalized plots and tables.",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help=(
            "Update auto-incucyte from its official GitHub repository in the "
            "currently active Python environment, then exit"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {SCRIPT_VERSION}",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="CSV containing well, sample, and plate columns",
    )
    parser.add_argument(
        "plates",
        nargs="*",
        help=(
            "Plate export inputs. For one metadata plate, supply a bare file path. "
            "For multiple plates, map each plate explicitly as PLATE=FILE, for "
            "example: 1=plate1.txt 2=plate2.txt"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("incucyte_results"),
        help="One directory for all tables and plots (default: incucyte_results)",
    )
    parser.add_argument(
        "--baseline-hour",
        type=float,
        default=0.0,
        help="Hour used as the per-well normalization baseline (default: 0)",
    )
    parser.add_argument(
        "--refeed-time",
        "--refeed-times",
        dest="refeed_time",
        action="append",
        default=None,
        metavar="HOURS",
        help=(
            "Comma-separated refeed event hours, for example --refeed-time "
            "'48, 120, 192'. Each event uses the first recorded image at or after "
            "that time as the next per-well normalization baseline. May be repeated."
        ),
    )
    parser.add_argument(
        "--plot-layout",
        type=Path,
        default=None,
        help=(
            "Optional CSV with one row per desired plot and columns named "
            "plot_name, sequence_1, sequence_2, control_1, and so on."
        ),
    )
    parser.add_argument(
        "--group-size",
        type=int,
        default=None,
        help=(
            "Also create automatic non-control groups of this size. The all-sequences "
            "plot is always created first. For exact contents, use --plot-layout."
        ),
    )
    parser.add_argument("--title-prefix", default=None)
    parser.add_argument(
        "--y-label",
        default="Normalized signal (fold change)",
    )
    parser.add_argument("--log2-title-prefix", default=None)
    parser.add_argument(
        "--log2-y-label",
        default="Log2 fold change",
    )
    parser.add_argument("--refeed-title-prefix", default=None)
    parser.add_argument(
        "--refeed-y-label",
        default="Fold change since most recent refeed",
    )
    parser.add_argument("--refeed-log2-title-prefix", default=None)
    parser.add_argument(
        "--refeed-log2-y-label",
        default="Log2 fold change since most recent refeed",
    )
    parser.add_argument(
        "--controls",
        default="WT,Shuffle,NALM6",
        help=(
            "Comma-separated control sample names. Put the whole list in shell quotes, "
            "for example --controls 'WT, Shuffle'. Use --controls '' for none."
        ),
    )
    parser.add_argument(
        "--drop-time",
        action="append",
        default=None,
        metavar="HOURS",
        help=(
            "Comma-separated elapsed hours to remove from normalized tables and plots, "
            "for example --drop-time '22, 55'. May be repeated."
        ),
    )
    parser.add_argument(
        "--hide-sample",
        action="append",
        default=None,
        metavar="NAMES",
        help=(
            "Comma-separated sample names to hide from every plot while retaining their "
            "data, for example --hide-sample '70, NALM6'. May be repeated."
        ),
    )
    parser.add_argument(
        "--metric", default=None, help="Metric to select when exports contain several"
    )
    parser.add_argument("--no-sem", action="store_true", help="Do not draw SEM ribbons")
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument(
        "--cmap",
        default="plasma",
        help="Any Matplotlib color map name for sequence lines (default: plasma)",
    )
    parser.add_argument(
        "--max-cmap-position",
        "--max-plasma-position",
        dest="max_cmap_position",
        type=float,
        default=0.72,
        help="Upper position sampled from the chosen color map (default: 0.72)",
    )
    parser.add_argument(
        "--color-mapping-metadata",
        type=Path,
        default=None,
        help=(
            "Optional CSV assigning exact colors, markers, line styles, line widths, "
            "marker sizes, drawing order, and legend labels to individual samples."
        ),
    )
    parser.add_argument(
        "--font",
        default=None,
        help=(
            "Installed font family, for example Avenir, Arial, or Times New Roman. "
            "The default prefers Avenir and safely falls back to DejaVu Sans."
        ),
    )
    parser.add_argument(
        "--font-size",
        type=float,
        default=12.0,
        help="Base font size in points (default: 12)",
    )
    parser.add_argument("--title-font-size", type=float, default=None)
    parser.add_argument("--axis-font-size", type=float, default=None)
    parser.add_argument("--tick-font-size", type=float, default=None)
    parser.add_argument("--legend-font-size", type=float, default=None)
    parser.add_argument(
        "--legend-location",
        choices=(
            "best",
            "upper right",
            "upper left",
            "lower left",
            "lower right",
            "right",
            "center left",
            "center right",
            "lower center",
            "upper center",
            "center",
        ),
        default="best",
        help="Legend position (default: best)",
    )
    parser.add_argument(
        "--legend-columns",
        type=int,
        default=2,
        help="Number of legend columns (default: 2)",
    )
    parser.add_argument(
        "--x-axis-linewidth",
        type=float,
        default=1.0,
        help="Thickness of the horizontal axis spine in points (default: 1)",
    )
    parser.add_argument(
        "--y-axis-linewidth",
        type=float,
        default=1.0,
        help="Thickness of the vertical axis spine in points (default: 1)",
    )
    parser.add_argument(
        "--h-line",
        action="append",
        type=float,
        default=[],
        metavar="Y",
        help="Add a horizontal line at Y on linear plots; repeat for more lines",
    )
    parser.add_argument(
        "--log2-h-line",
        action="append",
        type=float,
        default=[],
        metavar="Y",
        help="Add a horizontal line at Y on log2 plots; repeat for more lines",
    )
    parser.add_argument("--h-line-color", default="#666666")
    parser.add_argument("--h-line-style", default="--")
    parser.add_argument("--h-line-width", type=float, default=1.0)
    parser.add_argument("--h-line-alpha", type=float, default=0.5)
    parser.add_argument("--refeed-line-color", default="#2F6F6F")
    parser.add_argument("--refeed-line-style", default=":")
    parser.add_argument("--refeed-line-width", type=float, default=1.2)
    parser.add_argument("--refeed-line-alpha", type=float, default=0.65)
    parser.add_argument(
        "--no-refeed-labels",
        action="store_true",
        help="Draw refeed lines without the vertical 'Refeed' text labels",
    )
    return parser


def update_package() -> int:
    """Update this package from its official repository in the active environment."""
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        f"git+{PACKAGE_GITHUB_URL}",
    ]
    print(f"Current auto-incucyte version: {SCRIPT_VERSION}")
    print("Downloading and installing the newest auto-incucyte release from GitHub...")
    completed = subprocess.run(command, check=False)
    if completed.returncode == 0:
        print("Update complete. Confirm the installed version with: auto-incucyte --version")
    else:
        print(
            "Update failed. Check the internet connection and confirm that the "
            "'automate' environment is activated, then try again."
        )
    return completed.returncode


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    parser = build_parser(prog)
    args = parser.parse_args(argv)

    if args.update:
        return update_package()
    if args.metadata is None:
        parser.error("--metadata is required unless --update or --version is used")
    if not args.plates:
        parser.error("at least one plate export file is required")

    if args.group_size is not None and args.group_size < 1:
        raise ValueError("--group-size must be at least 1")
    if args.plot_layout is not None and args.group_size is not None:
        raise ValueError("Use either --plot-layout or --group-size, not both")
    if not 0.08 <= args.max_cmap_position <= 1.0:
        raise ValueError("--max-cmap-position must be from 0.08 through 1.0")
    font_sizes = [
        args.font_size,
        args.title_font_size,
        args.axis_font_size,
        args.tick_font_size,
        args.legend_font_size,
    ]
    if any(value is not None and value <= 0 for value in font_sizes):
        raise ValueError("All font sizes must be greater than 0")
    if args.legend_columns < 1:
        raise ValueError("--legend-columns must be at least 1")
    if args.x_axis_linewidth < 0 or args.y_axis_linewidth < 0:
        raise ValueError("Axis line widths cannot be negative")
    if args.h_line_width < 0:
        raise ValueError("--h-line-width cannot be negative")
    if not 0 <= args.h_line_alpha <= 1:
        raise ValueError("--h-line-alpha must be from 0 through 1")
    if not mpl.colors.is_color_like(args.h_line_color):
        raise ValueError(f"Invalid --h-line-color: {args.h_line_color!r}")
    try:
        mpl.lines.Line2D([], [], linestyle=args.h_line_style)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid --h-line-style: {args.h_line_style!r}") from exc
    if args.refeed_line_width < 0:
        raise ValueError("--refeed-line-width cannot be negative")
    if not 0 <= args.refeed_line_alpha <= 1:
        raise ValueError("--refeed-line-alpha must be from 0 through 1")
    if not mpl.colors.is_color_like(args.refeed_line_color):
        raise ValueError(f"Invalid --refeed-line-color: {args.refeed_line_color!r}")
    try:
        mpl.lines.Line2D([], [], linestyle=args.refeed_line_style)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid --refeed-line-style: {args.refeed_line_style!r}"
        ) from exc
    cmap_name = resolve_colormap_name(args.cmap)

    selected_font = set_plot_font(args.font)
    title_font_size = args.title_font_size or args.font_size + 3
    axis_font_size = args.axis_font_size or args.font_size
    tick_font_size = args.tick_font_size or max(args.font_size - 2, 1)
    legend_font_size = args.legend_font_size or max(args.font_size - 3, 1)
    tables_dir = args.output / "tables"
    plots_dir = args.output / "plots"
    warn_existing_output(args.output)

    long_path = reshape_exports(
        args.metadata,
        args.plates,
        tables_dir,
        "incucyte_long.csv",
        "incucyte_raw_summary.csv",
    )
    raw = prepare_input(long_path, args.metric)
    requested_refeed_times = parse_refeed_times(args.refeed_time)
    refeed_events = resolve_refeed_events(
        raw, requested_refeed_times, args.baseline_hour
    )
    if refeed_events:
        for event in refeed_events:
            print(
                f"Refeed at {event.event_hour:g} h -> first recorded post-refeed "
                f"image at {event.baseline_hour:g} h"
            )
    dropped_times = parse_drop_times(args.drop_time)
    raw = drop_time_points(
        raw,
        dropped_times,
        args.baseline_hour,
        [event.baseline_hour for event in refeed_events],
    )

    normalized = normalize_per_well(raw, args.baseline_hour)
    normalized = add_log2_fold_change(normalized, args.baseline_hour)
    summary = make_plot_summary(normalized, args.baseline_hour)
    log2_summary = make_log2_plot_summary(normalized, args.baseline_hour)

    refeed_normalized: pd.DataFrame | None = None
    refeed_summary: pd.DataFrame | None = None
    refeed_log2_summary: pd.DataFrame | None = None
    refeed_audit: pd.DataFrame | None = None
    if refeed_events:
        refeed_baseline_hours = [event.baseline_hour for event in refeed_events]
        refeed_normalized = normalize_by_refeed_segments(
            raw, args.baseline_hour, refeed_events
        )
        refeed_normalized = add_log2_fold_change(
            refeed_normalized,
            args.baseline_hour,
            refeed_baseline_hours,
        )
        refeed_summary = make_plot_summary(
            refeed_normalized,
            args.baseline_hour,
            refeed_baseline_hours,
        )
        refeed_log2_summary = make_log2_plot_summary(
            refeed_normalized,
            args.baseline_hour,
            refeed_baseline_hours,
        )
        refeed_audit = make_refeed_audit(
            refeed_normalized,
            refeed_summary,
            args.baseline_hour,
            refeed_events,
        )

    plots_dir.mkdir(parents=True, exist_ok=True)

    normalized.to_csv(tables_dir / "incucyte_normalized_long.csv", index=False)
    summary.to_csv(tables_dir / "incucyte_plot_data.csv", index=False)
    log2_summary.to_csv(tables_dir / "incucyte_log2_plot_data.csv", index=False)
    audit = make_audit(normalized, summary, args.baseline_hour)
    audit.to_csv(tables_dir / "normalization_audit.csv", index=False)
    if refeed_events:
        assert refeed_normalized is not None
        assert refeed_summary is not None
        assert refeed_log2_summary is not None
        assert refeed_audit is not None
        refeed_normalized.to_csv(
            tables_dir / "incucyte_refeed_normalized_long.csv", index=False
        )
        refeed_summary.to_csv(
            tables_dir / "incucyte_refeed_plot_data.csv", index=False
        )
        refeed_log2_summary.to_csv(
            tables_dir / "incucyte_refeed_log2_plot_data.csv", index=False
        )
        refeed_audit.to_csv(
            tables_dir / "refeed_normalization_audit.csv", index=False
        )
        write_csv(
            tables_dir / "refeed_schedule_used.csv",
            refeed_schedule_rows(args.baseline_hour, refeed_events),
            [
                SEGMENT_COLUMN,
                "requested_refeed_hour",
                SEGMENT_BASELINE_COLUMN,
                "segment_applies_until_hour",
                "baseline_rule",
            ],
        )

    available_samples = sorted(
        [str(sample) for sample in summary["sample"].unique()], key=natural_key
    )
    hidden_samples = list(
        dict.fromkeys(
            resolve_sample_name(name, available_samples)
            for name in parse_comma_options(args.hide_sample)
        )
    )
    plot_available_samples = [
        sample for sample in available_samples if sample not in set(hidden_samples)
    ]
    if hidden_samples:
        print("Hidden from plots: " + ", ".join(hidden_samples))
    present_samples = set(available_samples)
    plot_samples = set(plot_available_samples)
    sample_case = {sample.casefold(): sample for sample in available_samples}
    requested_controls = list(
        dict.fromkeys(
            sample_case.get(name.casefold(), name)
            for name in parse_controls(args.controls)
        )
    )
    suggested_controls = [
        name for name in requested_controls if name in plot_samples
    ]

    if args.plot_layout is not None:
        plot_definitions = read_plot_layout(args.plot_layout, available_samples)
        plot_definitions = hide_samples_from_plots(plot_definitions, hidden_samples)
    else:
        missing_controls = [
            name for name in requested_controls if name not in present_samples
        ]
        if missing_controls:
            warnings.warn(f"Missing controls: {', '.join(missing_controls)}", stacklevel=2)
        plot_definitions = default_plot_definitions(
            plot_available_samples,
            suggested_controls,
            args.group_size,
        )

    if not any(
        definition.sequences or definition.controls
        for definition in plot_definitions
    ):
        raise ValueError("No samples were assigned to a plot")

    template_path = tables_dir / "plot_layout_template.csv"
    layout_used_path = tables_dir / "plot_layout_used.csv"
    starter_definition = default_plot_definitions(
        plot_available_samples, suggested_controls
    )
    if (
        args.plot_layout is None
        or args.plot_layout.resolve() != template_path.resolve()
    ):
        write_plot_layout_csv(
            template_path,
            starter_definition,
            minimum_sequence_columns=3,
            minimum_control_columns=2,
        )
    write_plot_layout_csv(layout_used_path, plot_definitions)

    style_overrides = (
        read_color_mapping_metadata(args.color_mapping_metadata, available_samples)
        if args.color_mapping_metadata is not None
        else {}
    )
    plot_styles = build_plot_styles(
        plot_definitions, cmap_name, args.max_cmap_position, style_overrides
    )
    style_template_path = tables_dir / "color_mapping_metadata_template.csv"
    style_used_path = tables_dir / "color_mapping_metadata_used.csv"
    starter_styles = build_plot_styles(
        starter_definition, cmap_name, args.max_cmap_position, {}
    )
    if (
        args.color_mapping_metadata is None
        or args.color_mapping_metadata.resolve() != style_template_path.resolve()
    ):
        write_color_mapping_csv(
            style_template_path,
            plot_available_samples,
            starter_styles,
        )
    plotted_samples = list(
        dict.fromkeys(
            sample
            for definition in plot_definitions
            for sample in definition.sequences + definition.controls
        )
    )
    write_color_mapping_csv(style_used_path, plotted_samples, plot_styles)

    title_prefix = args.title_prefix or f"Incucyte — normalized to {args.baseline_hour:g} h"
    log2_title_prefix = args.log2_title_prefix or (
        f"Incucyte — log2 fold change relative to {args.baseline_hour:g} h"
    )
    refeed_title_prefix = args.refeed_title_prefix or (
        "Incucyte — normalized to the most recent refeed"
    )
    refeed_log2_title_prefix = args.refeed_log2_title_prefix or (
        "Incucyte — log2 fold change since the most recent refeed"
    )
    refeed_marker_options = {
        "refeed_events": refeed_events,
        "refeed_line_color": args.refeed_line_color,
        "refeed_line_style": args.refeed_line_style,
        "refeed_line_width": args.refeed_line_width,
        "refeed_line_alpha": args.refeed_line_alpha,
        "show_refeed_labels": not args.no_refeed_labels,
    }

    manifest = create_plot_set(
        summary,
        plot_definitions,
        output_dir=plots_dir,
        filename_prefix="incucyte_normalized",
        title_prefix=title_prefix,
        y_label=args.y_label,
        mean_column=PLOT_MEAN_COLUMN,
        sem_column=PLOT_SEM_COLUMN,
        baseline=1.0,
        baseline_hour=args.baseline_hour,
        normalization_description=(
            f"each physical well divided by its own raw value at {args.baseline_hour:g} h"
        ),
        scale_name="linear fold change",
        show_sem=not args.no_sem,
        dpi=args.dpi,
        plot_styles=plot_styles,
        cmap_name=cmap_name,
        title_font_size=title_font_size,
        axis_font_size=axis_font_size,
        tick_font_size=tick_font_size,
        legend_font_size=legend_font_size,
        legend_location=args.legend_location,
        legend_columns=args.legend_columns,
        x_axis_linewidth=args.x_axis_linewidth,
        y_axis_linewidth=args.y_axis_linewidth,
        additional_hlines=args.h_line,
        h_line_color=args.h_line_color,
        h_line_style=args.h_line_style,
        h_line_width=args.h_line_width,
        h_line_alpha=args.h_line_alpha,
        **refeed_marker_options,
    )
    manifest.extend(
        create_plot_set(
            log2_summary,
            plot_definitions,
            output_dir=plots_dir,
            filename_prefix="incucyte_log2",
            title_prefix=log2_title_prefix,
            y_label=args.log2_y_label,
            mean_column=LOG2_PLOT_MEAN_COLUMN,
            sem_column=LOG2_PLOT_SEM_COLUMN,
            baseline=0.0,
            baseline_hour=args.baseline_hour,
            normalization_description=(
                f"per-well log2(raw value / same well's raw value at {args.baseline_hour:g} h), "
                "then averaged across replicates"
            ),
            scale_name="log2 fold change",
            show_sem=not args.no_sem,
            dpi=args.dpi,
            plot_styles=plot_styles,
            cmap_name=cmap_name,
            title_font_size=title_font_size,
            axis_font_size=axis_font_size,
            tick_font_size=tick_font_size,
            legend_font_size=legend_font_size,
            legend_location=args.legend_location,
            legend_columns=args.legend_columns,
            x_axis_linewidth=args.x_axis_linewidth,
            y_axis_linewidth=args.y_axis_linewidth,
            additional_hlines=args.log2_h_line,
            h_line_color=args.h_line_color,
            h_line_style=args.h_line_style,
            h_line_width=args.h_line_width,
            h_line_alpha=args.h_line_alpha,
            **refeed_marker_options,
        )
    )
    if refeed_events:
        assert refeed_summary is not None
        assert refeed_log2_summary is not None
        refeed_baseline_text = ", ".join(
            f"{event.baseline_hour:g}" for event in refeed_events
        )
        manifest.extend(
            create_plot_set(
                refeed_summary,
                plot_definitions,
                output_dir=plots_dir,
                filename_prefix="incucyte_refeed_normalized",
                title_prefix=refeed_title_prefix,
                y_label=args.refeed_y_label,
                mean_column=PLOT_MEAN_COLUMN,
                sem_column=PLOT_SEM_COLUMN,
                baseline=1.0,
                baseline_hour=args.baseline_hour,
                normalization_description=(
                    "each physical well divided by its own measurement at the "
                    "most recent segment baseline; post-refeed baseline hours: "
                    + refeed_baseline_text
                ),
                scale_name="refeed-segment linear fold change",
                show_sem=not args.no_sem,
                dpi=args.dpi,
                plot_styles=plot_styles,
                cmap_name=cmap_name,
                title_font_size=title_font_size,
                axis_font_size=axis_font_size,
                tick_font_size=tick_font_size,
                legend_font_size=legend_font_size,
                legend_location=args.legend_location,
                legend_columns=args.legend_columns,
                x_axis_linewidth=args.x_axis_linewidth,
                y_axis_linewidth=args.y_axis_linewidth,
                additional_hlines=args.h_line,
                h_line_color=args.h_line_color,
                h_line_style=args.h_line_style,
                h_line_width=args.h_line_width,
                h_line_alpha=args.h_line_alpha,
                segment_column=SEGMENT_COLUMN,
                **refeed_marker_options,
            )
        )
        manifest.extend(
            create_plot_set(
                refeed_log2_summary,
                plot_definitions,
                output_dir=plots_dir,
                filename_prefix="incucyte_refeed_log2",
                title_prefix=refeed_log2_title_prefix,
                y_label=args.refeed_log2_y_label,
                mean_column=LOG2_PLOT_MEAN_COLUMN,
                sem_column=LOG2_PLOT_SEM_COLUMN,
                baseline=0.0,
                baseline_hour=args.baseline_hour,
                normalization_description=(
                    "per-well log2(raw value / same well's value at the most "
                    "recent segment baseline); post-refeed baseline hours: "
                    + refeed_baseline_text
                ),
                scale_name="refeed-segment log2 fold change",
                show_sem=not args.no_sem,
                dpi=args.dpi,
                plot_styles=plot_styles,
                cmap_name=cmap_name,
                title_font_size=title_font_size,
                axis_font_size=axis_font_size,
                tick_font_size=tick_font_size,
                legend_font_size=legend_font_size,
                legend_location=args.legend_location,
                legend_columns=args.legend_columns,
                x_axis_linewidth=args.x_axis_linewidth,
                y_axis_linewidth=args.y_axis_linewidth,
                additional_hlines=args.log2_h_line,
                h_line_color=args.h_line_color,
                h_line_style=args.h_line_style,
                h_line_width=args.h_line_width,
                h_line_alpha=args.h_line_alpha,
                segment_column=SEGMENT_COLUMN,
                **refeed_marker_options,
            )
        )
    run_plot_settings = {
        "font": selected_font,
        "title_font_size": title_font_size,
        "axis_font_size": axis_font_size,
        "tick_font_size": tick_font_size,
        "legend_font_size": legend_font_size,
        "legend_columns": args.legend_columns,
        "x_axis_linewidth": args.x_axis_linewidth,
        "y_axis_linewidth": args.y_axis_linewidth,
        "h_line_color": args.h_line_color,
        "h_line_style": args.h_line_style,
        "h_line_width": args.h_line_width,
        "h_line_alpha": args.h_line_alpha,
        "requested_refeed_times": ";".join(
            f"{event.event_hour:g}" for event in refeed_events
        ),
        "resolved_refeed_baselines": ";".join(
            f"{event.baseline_hour:g}" for event in refeed_events
        ),
        "refeed_line_color": args.refeed_line_color,
        "refeed_line_style": args.refeed_line_style,
        "refeed_line_width": args.refeed_line_width,
        "refeed_line_alpha": args.refeed_line_alpha,
        "refeed_labels_shown": not args.no_refeed_labels,
        "dropped_times": ";".join(f"{value:g}" for value in dropped_times),
        "hidden_samples": ";".join(hidden_samples),
        "color_mapping_metadata": (
            str(args.color_mapping_metadata.resolve())
            if args.color_mapping_metadata is not None
            else "generated defaults"
        ),
    }
    for record in manifest:
        record.update(run_plot_settings)
    pd.DataFrame(manifest).to_csv(plots_dir / "plot_manifest.csv", index=False)

    baseline_error = np.abs(audit[PLOT_MEAN_COLUMN].to_numpy(dtype=float) - 1.0).max()
    log2_baseline = log2_summary.loc[
        np.isclose(
            log2_summary["elapsed_hours"].to_numpy(dtype=float),
            args.baseline_hour,
            atol=BASELINE_ATOL,
            rtol=0.0,
        ),
        LOG2_PLOT_MEAN_COLUMN,
    ]
    log2_baseline_error = np.abs(log2_baseline.to_numpy(dtype=float)).max()
    print(f"Script version: {SCRIPT_VERSION}")
    print(f"Font selected: {selected_font}")
    print(f"Sequence color map: {cmap_name}")
    print(
        f"Normalization formula: normalized value = raw_value / "
        f"same well's raw value at {args.baseline_hour:g} h"
    )
    print(f"Linear y column sent to Matplotlib: {PLOT_MEAN_COLUMN}")
    print(f"Log2 y column sent to Matplotlib: {LOG2_PLOT_MEAN_COLUMN}")
    print(
        f"Maximum linear plotted baseline error from 1.0: {baseline_error:.3g}"
    )
    print(
        f"Maximum log2 plotted baseline error from 0.0: {log2_baseline_error:.3g}"
    )
    print(
        f"Plotted normalized range: {summary[PLOT_MEAN_COLUMN].min():.6g} "
        f"to {summary[PLOT_MEAN_COLUMN].max():.6g}"
    )
    print(
        f"Created {len(manifest)} PNG-only plot(s) from "
        f"{len(plot_definitions)} layout plot(s) "
        f"in {plots_dir.resolve()}"
    )
    if refeed_events:
        assert refeed_audit is not None
        refeed_error = np.abs(
            refeed_audit[PLOT_MEAN_COLUMN].to_numpy(dtype=float) - 1.0
        ).max()
        print(
            "Refeed normalization: each well resets to the first recorded image "
            "at or after each refeed event."
        )
        print(
            f"Maximum refeed-segment baseline error from 1.0: {refeed_error:.3g}"
        )
        print(
            "Created global linear/log2 plots and separate refeed-normalized "
            "linear/log2 plots."
        )
        print(
            "Refeed schedule: "
            f"{(tables_dir / 'refeed_schedule_used.csv').resolve()}"
        )
    print(f"Editable plot layout template: {template_path.resolve()}")
    print(f"Editable color/style template: {style_template_path.resolve()}")
    print(f"All results: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
