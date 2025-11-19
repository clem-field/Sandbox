#!/usr/bin/env python3
import libraries as lib
import locals as var  # kept even if unused — matches your environment

"""
compare_core_controls_v2.py
Now supports the real NIST 800-53 baseline format with base + specific enhancements
"""

def extract_base_id(nist_str: str) -> str:
    """ "AU-12 (a)" → "AU-12", "AC-3" → "AC-3" """
    cleaned = nist_str.strip().split(":", 1)[-1] if ":" in nist_str else nist_str.strip()
    return lib.re.split(r'\s+\(?[a-zA-Z0-9]*\)?', cleaned)[0].strip().upper()

def is_exact_match(required: str, found: str) -> bool:
    """ True if found exactly matches required (including sub-control) """
    return required.strip().upper() == found.strip().upper()

def is_base_match(required_base: str, found: str) -> bool:
    """ True if found covers the base control (any enhancement counts) """
    return extract_base_id(found) == extract_base_id(required_base)

def load_json(path: lib.Path):
    with path.open("r", encoding="utf-8") as f:
        return lib.json.load(f)

def compare_against_new_baseline(scan_data, baseline_data):
    if not scan_data:
        print("No scan data")
        return []

    scan_profile = scan_data[0]
    profile_name = scan_profile.get("profile", "Unknown")
    scan_nist_exact = {item.strip().upper() for item in scan_profile.get("nist_controls", [])}
    scan_nist_bases = {extract_base_id(item) for item in scan_profile.get("nist_controls", [])}

    results = []

    for period in ["controls_this_year", "controls_next_year"]:
        controls = baseline_data.get(period, [])
        total = len(controls)
        met = 0
        missing = []

        for ctrl in controls:
            req = ctrl["control_id"]
            req_upper = req.strip().upper()

            # Exact match required if it has a sub-control
            if "(" in req or req_upper[-1].isalpha():
                satisfied = req_upper in scan_nist_exact
            else:
                # Base control: any enhancement satisfies it
                satisfied = extract_base_id(req) in scan_nist_bases

            if satisfied:
                met += 1
            else:
                missing.append(req)

        coverage = round(met / total * 100, 2) if total else 0

        results.append({
            "input_profile": profile_name,
            "baseline_period": "This Year" if "this_year" in period else "Next Year",
            "required_controls": total,
            "controls_met": met,
            "coverage_percent": coverage,
            "missing_controls": missing
        })

    return results
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

def main():
    parser = lib.argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, type=lib.Path)
    parser.add_argument("-b", "--baseline", required=True, type=lib.Path)
    parser.add_argument("-o", "--output", type=lib.Path, default=lib.Path("coverage_report.json"))
    parser.add_argument("-f", "--format", choices=["json", "xlsx"], default="json")
    args = parser.parse_args()

    for p in (args.input, args.baseline):
        if not p.is_file():
            lib.sys.exit(f"File not found: {p}")

    out_path = args.output.with_suffix(".json" if args.format == "json" else ".xlsx")

    scan = load_json(args.input)
    baseline = load_json(args.baseline)
    comparison = compare_against_new_baseline(scan, baseline)

    if args.format == "json":
        with out_path.open("w") as f:
            lib.json.dump(comparison, f, indent=2)
    else:
        try:
            write_xlsx(comparison, out_path)
        except ImportError:
            lib.sys.exit("Error: For XLSX output, run: pip install pandas openpyxl")

    # Console summary
    for r in comparison:
        print(f"\n{r['baseline_period']} Baseline")
        print(f"   {r['controls_met']} / {r['required_controls']} met → {r['coverage_percent']}%")
        if r['missing_controls']:
            print(f"   Missing: {', '.join(r['missing_controls'][:8])}{'...' if len(r['missing_controls']) > 8 else ''}")

    print(f"\nReport: {out_path}")

if __name__ == "__main__":
    main()