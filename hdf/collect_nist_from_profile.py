#!/usr/bin/env python3
"""
Generate NIST control mapping summary from InSpec Ruby (.rb) controls.
Supports single file or full directory scanning.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# Regex patterns
CONTROL_ID_PATTERN = re.compile(r"^control\s+['\"]([^'\"]+)['\"]\s+do", re.MULTILINE)
NIST_TAG_ARRAY_PATTERN = re.compile(r"tag\s+(?:nist|'nist'|:nist)\s*:\s*\[\s*([^]]+?)\s*\]", re.DOTALL | re.IGNORECASE)
NIST_TAG_SINGLE_PATTERN = re.compile(r"tag\s+(?:nist|'nist'|:nist)\s*:\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)


def extract_control_id(content: str):
    match = CONTROL_ID_PATTERN.search(content)
    return match.group(1) if match else None


def extract_nist_tags(content: str):
    nist_tags = set()

    # Array format: tag nist: ['AC-1', 'AC-2']
    for match in NIST_TAG_ARRAY_PATTERN.findall(content):
        tags = re.findall(r"['\"]?([^'\",\s]+)['\"]?", match)
        nist_tags.update(t.strip() for t in tags if t.strip())

    # Single string: tag nist: 'AC-1'
    for tag in NIST_TAG_SINGLE_PATTERN.findall(content):
        nist_tags.add(tag.strip())

    return sorted(nist_tags) if nist_tags else None


def scan_path(path: Path, quiet: bool = False):
    controls_with_nist = []
    controls_missing_nist = []
    all_nist_controls = set()

    if path.is_file():
        files = [path]
        total = 1
    else:
        files = list(path.rglob("*.rb"))
        total = len(files)

    if not quiet:
        source = "file" if path.is_file() else "directory"
        print(f"Scanning {total} .rb file(s) in {source}: {path}")

    for i, file_path in enumerate(files, 1):
        if not quiet and total > 1 and (i % 50 == 0 or i == total):
            print(f"  Processed {i}/{total} files...", end="\r")

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"\nWarning: Could not read {file_path}: {e}", file=sys.stderr)
            continue

        control_id = extract_control_id(content)
        if not control_id:
            continue  # Not a valid control file

        nist_tags = extract_nist_tags(content)

        relative_path = file_path.relative_to(path.parent if path.is_file() else path)
        entry = {
            "control": control_id,
            "file": str(relative_path),
            "nist": nist_tags or []
        }

        if nist_tags:
            controls_with_nist.append(entry)
            all_nist_controls.update(nist_tags)
        else:
            controls_missing_nist.append(entry)

    if not quiet and total > 1:
        print("\nScan complete!")

    return controls_with_nist, controls_missing_nist, sorted(all_nist_controls)


def main():
    parser = argparse.ArgumentParser(
        description="Generate NIST control summary from InSpec Ruby controls",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--directory", type=Path, help="Directory containing .rb control files")
    group.add_argument("-i", "--input", type=Path, dest="input_file", help="Single .rb control file to analyze")

    parser.add_argument("-o", "--output", type=Path, default="nist_control_summary.json",
                        help="Output JSON filename")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress and summary output")

    args = parser.parse_args()

    # Determine the input path (handles mutually exclusive args)
    input_path = args.input_file or args.directory

    # Validate path exists
    if not input_path.exists():
        print(f"Error: Path not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Scan
    with_nist, without_nist, unique_nist = scan_path(input_path, quiet=args.quiet)

    total_controls = len(with_nist) + len(without_nist)

    # Profile name: use path name (works for both files and dirs)
    profile_name = input_path.name

    summary = {
        "profile": profile_name,
        "source_path": str(input_path.resolve()),
        "generated_on": datetime.now().isoformat(),
        "total_controls": total_controls,
        "controls_with_nist": len(with_nist),
        "controls_missing_nist": len(without_nist),
        "unique_nist_controls": len(unique_nist),
        "nist_controls": unique_nist,
        "missing_nist_controls": [c["control"] for c in without_nist],
        "details": with_nist + without_nist
    }

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not args.quiet:
        print("=" * 70)
        print("NIST CONTROL MAPPING SUMMARY")
        print("=" * 70)
        print(f"Source              : {input_path}")
        print(f"Total Controls      : {total_controls}")
        print(f"With NIST Mapping   : {len(with_nist)}")
        print(f"Missing NIST        : {len(without_nist)}")
        print(f"Unique NIST Controls: {len(unique_nist)}")
        print(f"Output File         : {args.output.resolve()}")
        print("=" * 70)

        if without_nist:
            print(f"\nControls missing NIST tags ({len(without_nist)}):")
            for item in without_nist[:15]:
                print(f"  → {item['control']}  ({item['file']})")
            if len(without_nist) > 15:
                print(f"  ... and {len(without_nist) - 15} more")
            print(f"\nFull list in: {args.output}")

if __name__ == "__main__":
    main()