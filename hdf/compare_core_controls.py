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

    
    if isinstance(scan_data, dict):
        scan_profile = scan_data
    elif isinstance(scan_data, list):
        while scan_data and isinstance(scan_data[0],  # flatten double lists
            list):
            scan_data = [item for sublist in scan_data for item in sublist]
        scan_profile = scan_data[0] if scan_data else {}
    else:
        print("Unknown scan data format")
        return []

    profile_name = scan_profile.get("profile", "Unknown Scan")
    raw_nist = scan_profile.get("nist_controls", [])
    scan_nist_exact = {s.strip().upper() for s in raw_nist if isinstance(s, str)}
    scan_nist_bases = {extract_base_id(s) for s in raw_nist if isinstance(s, str)}

    
    if isinstance(baseline_data, list) and baseline_data:
        baseline_obj = baseline_data[0]
    elif isinstance(baseline_data, dict):
        baseline_obj = baseline_data
    else:
        print("Invalid baseline format")
        return []

    results = []
    for period in ["controls_25.4", "controls_2026cmca"]:
        controls = baseline_obj.get(period, [])
        total = len(controls)
        met = 0
        missing = []

        for ctrl in controls:
            req = ctrl.get("control_id", "").strip()
            if not req:
                continue
            req_upper = req.upper()

            # Has enhancement? Require exact match
            has_enhancement = "(" in req or (len(req_upper) > 5 and req_upper[-1].isalpha())

            if has_enhancement:
                satisfied = req_upper in scan_nist_exact
            else:
                satisfied = extract_base_id(req) in scan_nist_bases

            if satisfied:
                met += 1
            else:
                missing.append(req)

        coverage = round(met / total * 100, 2) if total else 0

        results.append({
            "input_profile": profile_name,
            "baseline_period": "This Year" if "controls_25.4" in period else "controls_2026cmca",
            "required_controls": total,
            "controls_met": met,
            "coverage_percent": coverage,
            "missing_controls": missing
        })

    return results

def write_xlsx(data: lib.List[lib.Dict[str, lib.Any]], out_path: lib.Path) -> None:
    if not data:
        df = lib.pd.DataFrame(columns=[
            "Input Profile", "Baseline Period", "Required", "Met", "Coverage %", "Missing Controls"
        ])
    else:
        rows = []
        for row in data:
            flat = {
                "Input Profile": row["input_profile"],
                "Baseline Period": row["baseline_period"],
                "Required": row["required_controls"],
                "Met": row["controls_met"],
                "Coverage %": f"{row['coverage_percent']}%",
                "Missing Controls": " | ".join(row["missing_controls"]) if row["missing_controls"] else "None"
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