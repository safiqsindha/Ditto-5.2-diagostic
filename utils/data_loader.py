"""
Data loading utilities for v5.1 raw outputs, v5 corpus, and v1 corpus.

Expected data formats
---------------------
v5.1 raw outputs (data/v5.1_raw/*.csv):
    chain_id, model, domain, condition, response,
    predicted_label (YES/NO), ground_truth_label (YES/NO)

v5 corpus (data/v5_corpus/*.csv or *.jsonl):
    chain_id, domain, chain_type (real/shuffled),
    elements (list serialized as JSON string)

v1 corpus (data/v1_corpus/*.csv or *.jsonl):
    chain_id, domain (pokemon), chain_type (real/shuffled),
    elements (list serialized as JSON string)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


def load_v51_raw(data_dir: Path) -> pd.DataFrame:
    """Load and concatenate all v5.1 raw output CSVs.

    Returns long-form DataFrame with one row per (chain_id, model, condition).
    Raises FileNotFoundError if no CSV files found.
    """
    data_dir = Path(data_dir)
    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)

    required = {
        "chain_id", "model", "domain", "condition",
        "response", "predicted_label", "ground_truth_label",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["correct"] = (
        df["predicted_label"].str.strip().str.upper()
        == df["ground_truth_label"].str.strip().str.upper()
    )
    return df


def load_corpus(corpus_dir: Path) -> pd.DataFrame:
    """Load a chain corpus (v5 or v1) from CSV or JSONL files."""
    corpus_dir = Path(corpus_dir)
    frames = []

    for csv_file in sorted(corpus_dir.glob("*.csv")):
        frames.append(pd.read_csv(csv_file))

    for jsonl_file in sorted(corpus_dir.glob("*.jsonl")):
        rows = [json.loads(line) for line in jsonl_file.read_text().splitlines() if line.strip()]
        frames.append(pd.DataFrame(rows))

    if not frames:
        raise FileNotFoundError(f"No CSV/JSONL files found in {corpus_dir}")

    df = pd.concat(frames, ignore_index=True)

    required = {"chain_id", "domain", "chain_type", "elements"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing corpus columns: {missing}")

    if df["elements"].dtype == object:
        df["elements"] = df["elements"].apply(
            lambda x: json.loads(x) if isinstance(x, str) else x
        )

    return df


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def verify_data_hashes(paths: list[Path], expected_hashes: dict[str, str]) -> bool:
    """Verify SHA-256 hashes of data files. Returns True if all match."""
    ok = True
    for path in paths:
        key = str(path)
        if key in expected_hashes:
            actual = sha256_file(path)
            if actual != expected_hashes[key]:
                print(f"[HASH MISMATCH] {path}")
                print(f"  Expected: {expected_hashes[key]}")
                print(f"  Actual:   {actual}")
                ok = False
    return ok
