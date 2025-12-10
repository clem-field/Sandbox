#!/usr/bin/env python3
"""
Accurate NIST 800-53 control extractor for InSpec profiles.
Correctly expands:
  AC-2 (1) (2) (3) → AC-2 (1), AC-2 (2), AC-2 (3)
  AC-6(9)(10)      → AC-6 (9), AC-6 (10)
Preserves: AC-3(4), AC-11 a
Excludes: Rev 4, Revision 5, etc.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------------
# Regex patterns
# ------------------------------------------------------------------
CONTROL_ID_PATTERN = re.compile(r"^control\s+['\"]([^'\"]+)['\"]\s+do", re.MULTILINE)

TAG_NIST_ARRAY = re.compile(
    r"tag\s+(?:nist|'nist'|:nist)\s*:\s*\[\s*([^]]+?)\s*\]",
    re.DOTALL | re.IGNORECASE
)
TAG_NIST_SINGLE = re.compile(
    r"tag\s+(?:nist|'nist'|:nist)\s*:\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE
)

EXCLUDE_REV = re.compile(r'\brev\b', re.IGNORECASE)  # whole word "rev"


def expand_nist_control(raw: str):
    """
    Takes raw string like 'AC-2 (1) (2) (3)' or 'AC-6(9)(10)' or 'AC-11 a'
    Returns list of individual, clean controls.
    """
    tag = raw.strip().strip('\'"')
    if not tag or EXCLUDE_REV.search(tag):
        return []

    # Case 1: Multiple enhancements with spaces → AC-2 (1) (2) (3)
    m_space = re.match(r"([A-Za-z]{1,2}-?\d+)\s+(.+)", tag)
    if m_space:
        base = m_space.group(1)
        rest = m_space.group(2).strip()
        # Find all (1), (2), (a), etc.
        enhancements = re.findall(r"\(([^()]+)\)", rest)
        if enhancements:
            return [f"{base} ({e.strip()})" for e in enhancements]

    # Case 2: No-space multiple → AC-6(9)(10)
    m_nospace = re.match(r"([A-Za-z]{1,2}-?\d+)(\([^)]+\))+", tag)
    if m_nospace:
        base = m_nospace.group(1)
        enhancements = re.findall(r"\(([^()]+)\)", tag)
        return [f"{base} ({e})" for e in enhancements]

    # Case 3: Single enhancement or letter → AC-3(4), AC-11 a, AC-2 (10)
    m_single = re.match(r"([A-Za-z]{1,2}-?\d+)(?:\s+(\([^(]+\)|\w+))?", tag)
    if m_single:
        base = m_single.group(1)
        suffix = m_single.group(2)
        if suffix:
            suffix = suffix.strip()
            if suffix.startswith('('):
                return [f"{base} {suffix}"]
            else:
                return [f"{base} {suffix}"]
        return [base]

    # Case 4: Just base control → AC-7
    if re.match(r"^[A-Za-z]{1,2}-?\d+$", tag):
        return [tag]

    # Case 5: Fallback – if it looks like a control, keep it
    if re.match(r"^[A-Za-z]{1,2}-?\d+.*", tag):
        return [tag]

    return []  # junk


def extract_nist_tags(content: str):
    """Extract and expand all NIST controls from a control file."""
    controls = set()

    # Array format
    for match in TAG_NIST_ARRAY.findall(content):
        items = re.split(r',\s*', match)
        for item in items:
            expanded = expand_nist_control(item)
            controls.update(expanded)

    # Single string format
    for match in TAG_NIST_SINGLE.findall(content):
        expanded = expand_nist_control(match)
        controls.update(expanded)

    return sorted(controls) if controls else None


def extract_control_id(content: str):
    match = CONTROL_ID_PATTERN.search(content)
    return match.group(1) if match else None


def scan_path(path: Path, quiet: bool = False):
    with_nist = []
    without_nist = []
    all_nist = set()

    files = [path] if path.is_file() else list(path.rglob("*.rb"))
    total = len(files)

    if not quiet:
        kind = "file" if path.is_file() else "directory"
        print(f"Scanning {total} .rb {kind}(s): {path}")

    for i, file_path in enumerate(files, 1):
        if not quiet and total > 10 and (i % 100 == 0 or i == total):
            print(f"  Processed {i}/{total} files...", end="\r")

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"\nWarning: Failed to read {file_path}: {e}", file=sys.stderr)
            continue

        control_id = extract_control_id(content)
        if not control_id:
            continue

        nist_list = extract_nist_tags(content)

        rel_path = file_path.relative_to(path.parent if path.is_file() else path)
        entry = {
            "control": control_id,
            "file": str(rel_path),
            "nist": nist_list or []
        }

        if nist_list:
            with_nist.append(entry)
            all_nist.update(nist_list)
        else:
            without_nist.append(entry)

    if not quiet and total > 10:
        print("\nScan complete!\n")

    return with_nist, without_nist, sorted(all_nist)


def main():
    parser = argparse.ArgumentParser(
        description="Generate accurate NIST 800-53 mapping from InSpec controls",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--directory", type=Path, help="Directory with .rb controls")
    group.add_argument("-i", "--input", type=Path, dest="input_file", help="Single .rb file")

    parser.add_argument("-o", "--output", type=Path, default="nist_control_summary.json",
                        help="Output JSON file")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")

    args = parser.parse_args()
    input_path = args.input_file or args.directory

    if not input_path.exists():
        print(f"Error: Path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    with_nist, without_nist, unique_nist = scan_path(input_path, quiet=args.quiet)

    summary = {
        "profile": input_path.name,
        "source_path": str(input_path.resolve()),
        "generated_on": datetime.now().isoformat(),
        "total_controls": len(with_nist) + len(without_nist),
        "controls_with_nist": len(with_nist),
        "controls_missing_nist": len(without_nist),
        "unique_nist_controls": len(unique_nist),
        "nist_controls": unique_nist,
        "missing_nist_controls": [c["control"] for c in without_nist],
        "details": with_nist + without_nist
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if not args.quiet:
        print("="*70)
        print("NIST 800-53 MAPPING REPORT")
        print("="*70)
        print(f"Source           : {input_path}")
        print(f"Total controls   : {summary['total_controls']}")
        print(f"With NIST tags   : {len(with_nist)}")
        print(f"Missing tags     : {len(without_nist)}")
        print(f"Unique NIST      : {len(unique_nist)}")
        print(f"Output           : {args.output.resolve()}")
        print("="*70)

        if without_nist:
            print(f"\nControls missing NIST tags ({len(without_nist)}):")
            for c in without_nist[:20]:
                print(f"  → {c['control']}  ({c['file']})")
            if len(without_nist) > 20:
                print(f"  ... and {len(without_nist)-20} more")

        print(f"\nSample NIST controls found:")
        for ctrl in list(unique_nist)[:12]:
            print(f"  • {ctrl}")
        if len(unique_nist) > 12:
            print(f"  ... and {len(unique_nist)-12} more")
        print()


if __name__ == "__main__":
    main()