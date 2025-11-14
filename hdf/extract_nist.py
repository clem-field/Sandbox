#!/usr/bin/env python3
"""
extract_nist.py – Extract profile name, total unique controls, and NIST IDs.

Output format:
  [
    {
      "profile": "<user-provided name>",
      "unique_controls": <int>,
      "nist_controls": ["AC-2", "AU-12", ...]
    }
  ]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Set, List, Dict, Any


# -------------------------------------------------
# Load HDF JSON
# -------------------------------------------------
def load_hdf(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------
# Extract data
# -------------------------------------------------
def extract_profile_data(hdf: dict) -> Dict[str, Any]:
    profiles = hdf.get("profiles", [])
    if not profiles:
        return {"unique_controls": 0, "nist_controls": []}

    # Count unique controls (by id + title)
    seen = set()
    nist_set: Set[str] = set()
    controls = profiles[0].get("controls", [])

    for ctrl in controls:
        ctrl_id = ctrl.get("id")
        title = ctrl.get("title")
        key = (ctrl_id, title)
        if key not in seen:
            seen.add(key)

        # Extract NIST IDs: "NIST-800-53:AC-2" → "AC-2"
        for nist in ctrl.get("tags", {}).get("nist", []):
            # Handle formats: "NIST-800-53:AC-2", "AC-2", or just "AC-2 (a)"
            short_id = nist.split(":")[-1].strip().split()[0]
            if short_id:
                nist_set.add(short_id)

    return {
        "unique_controls": len(seen),
        "nist_controls": sorted(nist_set)
    }


# -------------------------------------------------
# Writers
# -------------------------------------------------
def write_json(data: List[Dict[str, Any]], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_xlsx(data: List[Dict[str, Any]], out_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        sys.exit("Error: pandas + openpyxl required for XLSX. Run: pip install pandas openpyxl")

    if not data:
        df = pd.DataFrame(columns=["profile", "unique_controls", "nist_controls"])
    else:
        row = data[0].copy()
        row["nist_controls"] = ", ".join(row["nist_controls"])
        df = pd.DataFrame([row])

    df.to_excel(out_path, index=False, engine="openpyxl")


# -------------------------------------------------
# CLI
# -------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract profile summary + NIST controls from HDF JSON."
    )
    parser.add_argument("-i", "--input", required=True, type=Path, help="Input HDF JSON file")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output file (.json or .xlsx)")
    parser.add_argument("-p", "--profile", required=True, help="Profile name (e.g. 'AWS Config')")
    parser.add_argument(
        "-f", "--format",
        choices=["json", "xlsx"],
        default="json",
        help="Output format: json (default) or xlsx"
    )
    return parser


# -------------------------------------------------
# Main
# -------------------------------------------------
def main() -> None:
    args = build_parser().parse_args()

    # Validate input
    if not args.input.is_file():
        sys.exit(f"Error: Input file not found: {args.input}")

    # Force correct extension
    ext = ".json" if args.format == "json" else ".xlsx"
    out_path = args.output.with_suffix(ext)

    # Load and process
    hdf = load_hdf(args.input)
    summary = extract_profile_data(hdf)

    # Build final output
    result = [{
        "profile": args.profile,
        "unique_controls": summary["unique_controls"],
        "nist_controls": summary["nist_controls"]
    }]

    # Write
    if args.format == "json":
        write_json(result, out_path)
    else:
        write_xlsx(result, out_path)

    # Feedback
    print(f"Success: Profile summary written to {out_path}")
    print(f"   Profile: {args.profile}")
    print(f"   Unique Controls: {summary['unique_controls']}")
    print(f"   NIST Controls ({len(summary['nist_controls'])}): {', '.join(summary['nist_controls'][:5])}{'...' if len(summary['nist_controls']) > 5 else ''}")


if __name__ == "__main__":
    main()