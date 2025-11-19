import libraries as lib
import locals as var
"""
compare_nist_coverage.py

Compares an HDF-derived NIST report (your existing script's JSON output)
against a baseline of required controls.

Usage:
  python compare_nist_coverage.py \\
    -i report.json \\
    -b baseline.json \\
    [-o comparison_report.json] [--format json|xlsx]

Baseline format (baseline.json):
[
  {
    "profile": "Core Controls",
    "primary_controls": ["AC-2", "AC-3 (1)", "AU-12 (a)", "CM-6 b"],
    "target_controls": ["IA-5 (1)", "SC-7 (3)", "SI-4 a"]
  }
]
"""



def load_json(path: lib.Path) -> lib.List[lib.Dict[str, lib.Any]]:
    with path.open("r", encoding="utf-8") as f:
        return lib.json.load(f)


def compare_against_baseline(
    input_data: lib.List[lib.Dict[str, lib.Any]],
    baseline_data: lib.List[lib.Dict[str, lib.Any]]
) -> lib.List[lib.Dict[str, lib.Any]]:
    """
    Compares the nist_controls from input against primary + target in baseline.
    """
    if not input_data:
        print("Warning: Input file is empty.")
        return []

    if not baseline_data:
        print("Warning: Baseline file is empty.")
        return []

    # Assume single profile per file (common case)
    scan_profile = input_data[0]
    scan_nist_set: lib.Set[str] = set(scan_profile.get("nist_controls", []))

    results = []

    for baseline in baseline_data:
        profile_name = baseline.get("profile", "Unknown Baseline")
        primary = set(baseline.get("primary_controls", []))
        target = set(baseline.get("target_controls", []))

        all_required = primary.union(target)

        primary_met = len(primary & scan_nist_set)
        target_met = len(target & scan_nist_set)
        total_met = primary_met + target_met
        total_required = len(all_required)
        coverage_pct = (total_met / total_required * 100) if total_required > 0 else 0

        result = {
            "input_profile": scan_profile.get("profile", "Unknown Scan"),
            "baseline_profile": profile_name,
            "primary_controls_required": len(primary),
            "primary_controls_met": primary_met,
            "target_controls_required": len(target),
            "target_controls_met": target_met,
            "total_controls_required": total_required,
            "total_controls_met": total_met,
            "total_coverage_percent": round(coverage_pct, 2),
            # Optional: list missing ones for deep dives
            "missing_primary": sorted(primary - scan_nist_set),
            "missing_target": sorted(target - scan_nist_set)
        }
        results.append(result)

    return results


def write_json(data: lib.List[lib.Dict[str, lib.Any]], out_path: lib.Path) -> None:
    with out_path.open("w", encoding="utf-8") as f:
        lib.json.dump(data, f, indent=2)


def write_xlsx(data: lib.List[lib.Dict[str, lib.Any]], out_path: lib.Path) -> None:
    if not data:
        df = lib.pd.DataFrame(columns=[
            "input_profile", "baseline_profile", "primary_controls_met",
            "target_controls_met", "total_coverage_percent"
        ])
    else:
        # Flatten for Excel friendliness
        rows = []
        for row in data:
            flat = {
                "Input Profile": row["input_profile"],
                "Baseline Profile": row["baseline_profile"],
                "Primary Required": row["primary_controls_required"],
                "Primary Met": row["primary_controls_met"],
                "Target Required": row["target_controls_required"],
                "Target Met": row["target_controls_met"],
                "Total Required": row["total_controls_required"],
                "Total Met": row["total_controls_met"],
                "Coverage %": row["total_coverage_percent"],
                "Missing Primary": " | ".join(row["missing_primary"]),
                "Missing Target": " | ".join(row["missing_target"])
            }
            rows.append(flat)
        df = lib.pd.DataFrame(rows)

    df.to_excel(out_path, index=False, engine="openpyxl")


def build_parser() -> lib.argparse.ArgumentParser:
    parser = lib.argparse.ArgumentParser(
        description="Compare HDF NIST scan results against a required baseline."
    )
    parser.add_argument("-i", "--input", required=True, type=lib.Path,
                        help="Your existing HDF scan JSON output (with nist_controls array)")
    parser.add_argument("-b", "--baseline", required=True, type=lib.Path,
                        help="Baseline JSON with primary_controls and target_controls")
    parser.add_argument("-o", "--output", type=lib.Path, default=lib.Path("comparison_report.json"),
                        help="Output file (default: comparison_report.json or .xlsx)")
    parser.add_argument("-f", "--format", choices=["json", "xlsx"], default="json",
                        help="Output format")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    for p in (args.input, args.baseline):
        if not p.is_file():
            lib.sys.exit(f"Error: File not found: {p}")

    ext = ".json" if args.format == "json" else ".xlsx"
    out_path = args.output.with_suffix(ext)

    input_data = load_json(args.input)
    baseline_data = load_json(args.baseline)

    comparison = compare_against_baseline(input_data, baseline_data)

    if args.format == "json":
        write_json(comparison, out_path)
    else:
        try:
            write_xlsx(comparison, out_path)
        except ImportError:
            lib.sys.exit("Error: For XLSX output, run: pip install pandas openpyxl")

    # Pretty console summary
    if comparison:
        r = comparison[0]
        print("\nNIST Coverage Comparison Summary")
        print("=" * 50)
        print(f"Scan Profile       : {r['input_profile']}")
        print(f"Baseline           : {r['baseline_profile']}")
        print(f"Primary Met        : {r['primary_controls_met']} / {r['primary_controls_required']}")
        print(f"Target Met         : {r['target_controls_met']} / {r['target_controls_required']}")
        print(f"TOTAL COVERAGE     : {r['total_controls_met']} / {r['total_controls_required']} "
              f"({r['total_coverage_percent']}%)")
        print(f"Report saved to    : {out_path}")
    else:
        print("No comparison results generated.")


if __name__ == "__main__":
    main()