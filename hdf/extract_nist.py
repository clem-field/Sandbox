#!/usr/bin/env python3
"""
extract_nist.py – Clear, accurate summary of SAST checks and NIST coverage.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Set, List, Dict, Any


def load_hdf(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_summary(hdf: dict) -> Dict[str, Any]:
    profiles = hdf.get("profiles", [])
    if not profiles:
        return {"unique_checks": 0, "nist_controls": [], "unique_nist_controls": 0}

    controls = profiles[0].get("controls", [])
    seen_checks = set()
    nist_set: Set[str] = set()

    for ctrl in controls:
        # Unique check = (CWE ID, rule title)
        check_key = (ctrl.get("id"), ctrl.get("title"))
        if check_key not in seen_checks:
            seen_checks.add(check_key)

        # Extract short NIST ID: "NIST-800-53:AC-2" → "AC-2"
        for nist in ctrl.get("tags", {}).get("nist", []):
            parts = nist.strip().split(":")
            short_id = parts[-1].strip().split()[0] if parts else ""
            if short_id:
                nist_set.add(short_id)

    nist_list = sorted(nist_set)
    return {
        "unique_checks": len(seen_checks),
        "unique_nist_controls": len(nist_list),
        "nist_controls": nist_list
    }


# -------------------------- Writers --------------------------
def write_json(data: List[Dict[str, Any]], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def write_xlsx(data: List[Dict[str, Any]], out_path: Path) -> None:
    try:
        import pandas as pd
    except ImportError:
        sys.exit("Error: Install pandas & openpyxl: pip install pandas openpyxl")

    if not data:
        df = pd.DataFrame(columns=["profile", "unique_checks", "unique_nist_controls", "nist_controls"])
    else:
        row = data[0].copy()
        row["nist_controls"] = ", ".join(row["nist_controls"])
        df = pd.DataFrame([row])
    df.to_excel(out_path, index=False, engine="openpyxl")


# -------------------------- CLI --------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize SAST checks and NIST control coverage from HDF."
    )
    parser.add_argument("-i", "--input", required=True, type=Path, help="Input HDF JSON file")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Output file")
    parser.add_argument("-p", "--profile", required=True, help="Profile name (e.g. 'AWS Config')")
    parser.add_argument("-f", "--format", choices=["json", "xlsx"], default="json", help="Output format")
    return parser


# -------------------------- Main --------------------------
def main() -> None:
    args = build_parser().parse_args()

    if not args.input.is_file():
        sys.exit(f"Error: Input file not found: {args.input}")

    ext = ".json" if args.format == "json" else ".xlsx"
    out_path = args.output.with_suffix(ext)

    hdf = load_hdf(args.input)
    summary = extract_summary(hdf)

    result = [{
        "profile": args.profile,
        "unique_checks": summary["unique_checks"],
        "unique_nist_controls": summary["unique_nist_controls"],
        "nist_controls": summary["nist_controls"]
    }]

    if args.format == "json":
        write_json(result, out_path)
    else:
        write_xlsx(result, out_path)

    # Pretty feedback
    print(f"Success: Summary saved to {out_path}")
    print(f"   Profile: {args.profile}")
    print(f"   Unique SAST Checks: {summary['unique_checks']}")
    print(f"   Unique NIST Controls: {summary['unique_nist_controls']}")
    if summary["nist_controls"]:
        preview = ", ".join(summary["nist_controls"][:5])
        preview += "..." if len(summary["nist_controls"]) > 5 else ""
        print(f"   NIST IDs: {preview}")


if __name__ == "__main__":
    main()