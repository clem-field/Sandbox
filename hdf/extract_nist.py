#!/usr/bin/env python3
"""
extract_nist.py – Full SAST-to-NIST mapping analysis with gap detection.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Set, List, Dict, Any, Tuple
import re

def load_hdf(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def expand_condensed_nist(raw: str) -> List[str]:
    """
    Handles every real-world condensed NIST format seen in HDF/Heimdall files:
      "AU-12(a)(b)(c)"      → ["AU-12 (a)", "AU-12 (b)", "AU-12 (c)"]
      "AU-12 (a)(b)(c)"     → same
      "AC-2(1)(2)(3)"       → ["AC-2 (1)", "AC-2 (2)", "AC-2 (3)"]
      "SC-7 a b c"          → ["SC-7 a", "SC-7 b", "SC-7 c"]
      "CM-6b"               → ["CM-6 b"]
      "IA-5 (1) (a)"        → handled safely as separate entries
    """
    raw = raw.strip()
    if ":" in raw:
        raw = raw.split(":", 1)[1].strip()

    expanded: List[str] = []

    # 1. Compact no-space parens: AU-12(a)(b)(c) or AU-12 (a)(b)(c)
    compact_paren = re.search(r'([A-Z]{1,4}-\d+(?:\s*\([^()]+?\))+)', raw, re.IGNORECASE)
    if compact_paren:
        base_match = re.search(r'[A-Z]{1,4}-\d+', raw)
        if not base_match:
            expanded.append(raw)
            return expanded
        base = base_match.group()
        # Find all (a), (b), (11), etc.
        subs = re.findall(r'\(\s*([a-zA-Z0-9]+)\s*\)', raw)
        expanded = [f"{base} ({sub})" for sub in subs]
        return expanded

    # 2. Space-separated letters: SC-7 a b c
    letter_match = re.match(r'([A-Z]{1,4}-\d+)\s+([a-z])(?:\s+([a-z]))*(?:\s+([a-z]))?', raw, re.IGNORECASE)
    if letter_match:
        base = letter_match.group(1)
        letters = re.findall(r'\b([a-z])\b', raw, re.IGNORECASE)
        expanded = [f"{base} {let}" for let in letters]
        return expanded

    # 3. Single trailing letter: CM-6b → CM-6 b
    single_letter = re.match(r'([A-Z]{1,4}-\d+)([a-z])$', raw, re.IGNORECASE)
    if single_letter:
        return [f"{single_letter.group(1)} {single_letter.group(2)}"]

    # 4. Fallback: already correct or unknown format
    return [raw]


def extract_summary(hdf: dict) -> Dict[str, Any]:
    profiles = hdf.get("profiles", [])
    if not profiles:
        return {
            "unique_checks": 0,
            "unique_nist_controls": 0,
            "missing_nist_count": 0,
            "nist_controls": [],
            "missing_nist": []
        }

    controls = profiles[0].get("controls", [])
    seen_checks: Set[Tuple[str, str]] = set()
    nist_set: Set[str] = set()
    mapped_checks: Set[Tuple[str, str]] = set()
    missing_nist: List[Dict[str, str]] = []

    for ctrl in controls:
        ctrl_id = ctrl.get("id", "unknown")
        title = ctrl.get("title", "No title")
        check_key = (ctrl_id, title)

        if check_key not in seen_checks:
            seen_checks.add(check_key)

        raw_nist_list = ctrl.get("tags", {}).get("nist", []) or []

        if raw_nist_list:
            mapped_checks.add(check_key)
            for entry in raw_nist_list:
                if not entry:
                    continue
                for expanded in expand_condensed_nist(entry):
                    cleaned = expanded.strip()
                    if cleaned:
                        nist_set.add(cleaned)

    # Build missing list
    for check_key in seen_checks - mapped_checks:
        ctrl_id, title = check_key
        missing_nist.append({"id": ctrl_id, "title": title})

    nist_list = sorted(nist_set)

    return {
        "unique_checks": len(seen_checks),
        "unique_nist_controls": len(nist_list),
        "missing_nist_count": len(missing_nist),
        "nist_controls": nist_list,
        "missing_nist": missing_nist
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
        df = pd.DataFrame(columns=[
            "profile", "unique_checks", "unique_nist_controls",
            "nist_controls", "missing_nist_count", "missing_nist_details"
        ])
    else:
        row = data[0].copy()
        row["nist_controls"] = ", ".join(row["nist_controls"])
        row["missing_nist_count"] = len(row["missing_nist"])
        row["missing_nist_details"] = " | ".join(
            f"{m['id']}:{m['title']}" for m in row["missing_nist"]
        )
        df = pd.DataFrame([row])

    df.to_excel(out_path, index=False, engine="openpyxl")


# -------------------------- CLI --------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze SAST checks vs NIST control coverage with gap detection."
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
        "nist_controls": summary["nist_controls"],
        "missing_nist": summary["missing_nist"]
    }]

    if args.format == "json":
        write_json(result, out_path)
    else:
        write_xlsx(result, out_path)

    # === Pretty Summary ===
    print(f"Success: Analysis saved to {out_path}")
    print(f"   Profile: {args.profile}")
    print(f"   Unique SAST Checks: {summary['unique_checks']}")
    print(f"   Mapped to NIST: {summary['unique_nist_controls']} controls")
    print(f"   Missing NIST Mapping: {len(summary['missing_nist'])} checks")

    if summary["nist_controls"]:
        preview = ", ".join(summary["nist_controls"][:5])
        preview += "..." if len(summary["nist_controls"]) > 5 else ""
        print(f"   NIST Coverage: {preview}")

    if summary["missing_nist"]:
        print(f"   Unmapped Checks (sample):")
        for m in summary["missing_nist"][:3]:
            print(f"     • [{m['id']}] {m['title']}")
        if len(summary["missing_nist"]) > 3:
            print(f"     ... and {len(summary['missing_nist']) - 3} more")
    else:
        print("   All checks have NIST mappings!")


if __name__ == "__main__":
    main()