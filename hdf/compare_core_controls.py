#!/usr/bin/env python3
import libraries as lib
import locals as var

def load_json(path: lib.Path):
    with path.open("r", encoding="utf-8") as f:
        return lib.json.load(f)


def normalize_nist(cid: str) -> str:
    if not cid:
        return ""

    c = cid.strip()
    if ":" in c:
        c = c.split(":", 1)[1].strip()

    # AC-08 → AC-8
    c = lib.re.sub(r'AC-0+(\d)', r'AC-\1', c, flags=lib.re.IGNORECASE)

    # Find base control
    base_match = lib.re.search(r'[A-Za-z]{1,4}-\d+(?:\(\d+\))?', c, lib.re.IGNORECASE)
    if not base_match:
        return c.upper()
    base = base_match.group(0).upper()
    base_end = base_match.end()

    # Enhancement
    enh_raw = c[base_end:].strip()
    enh_clean = lib.re.sub(r'[\(\)\.]', ' ', enh_raw)
    enh_clean = lib.re.sub(r'\s+', ' ', enh_clean).strip().lower()

    if enh_clean:
        return f"{base} ({enh_clean})"
    return base


def compare_against_new_baseline(scan_data, baseline_data):
    if not scan_data:
        print("No scan data")
        return []

    # Robust scan extraction
    if isinstance(scan_data, dict):
        scan_profile = scan_data
    elif isinstance(scan_data, list):
        tmp = scan_data
        while tmp and isinstance(tmp[0], list):
            tmp = [item for sublist in tmp for item in sublist]
        scan_profile = tmp[0] if tmp else {}
    else:
        return []

    profile_name = scan_profile.get("profile", "Unknown Scan")
    raw_nist = scan_profile.get("nist_controls", []) or []
    scan_normalized = {normalize_nist(item) for item in raw_nist if isinstance(item, str)}

    # Baseline extraction
    if isinstance(baseline_data, list) and baseline_data:
        baseline_obj = baseline_data[0]
    elif isinstance(baseline_data, dict):
        baseline_obj = baseline_data
    else:
        print("Invalid baseline format")
        return []

    results = []

    # DYNAMIC: Find all keys that contain "controls_"
    period_keys = [k for k in baseline_obj.keys() if "controls_" in k.lower()]

    for period in period_keys:
        controls = baseline_obj.get(period, [])
        total = len(controls)
        met = 0
        missing = []

        for ctrl in controls:
            req = ctrl.get("control_id", "").strip()
            if not req:
                continue

            req_norm = normalize_nist(req)

            # Default: exact normalized match
            satisfied = req_norm in scan_normalized

            # If required is base-only, any enhancement satisfies it
            if " (" not in req_norm:
                base_req = req_norm
                satisfied = any(
                    s == base_req or s.startswith(base_req + " (")
                    for s in scan_normalized
                )

            if satisfied:
                met += 1
            else:
                missing.append(req)

        coverage = round(met / total * 100, 2) if total else 0

        # Friendly period name
        period_name = period.replace("controls_", "").replace("_", " ").upper()

        results.append({
            "input_profile": profile_name,
            "baseline_period": period_name,
            "required_controls": total,
            "controls_met": met,
            "coverage_percent": coverage,
            "missing_controls": missing
        })

    return results


def write_xlsx(data: lib.List[lib.Dict[str, lib.Any]], out_path: lib.Path) -> None:
    rows = []
    for row in data:
        rows.append({
            "Input Profile": row["input_profile"],
            "Baseline Period": row["baseline_period"],
            "Required": row["required_controls"],
            "Met": row["controls_met"],
            "Coverage %": f"{row['coverage_percent']}%",
            "Missing Controls": " | ".join(row["missing_controls"]) if row["missing_controls"] else "None"
        })
    df = lib.pd.DataFrame(rows or [{"Input Profile": "No data", "Baseline Period": "", "Required": 0, "Met": 0, "Coverage %": "0%", "Missing Controls": ""}])
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
        write_xlsx(comparison, out_path)

    for r in comparison:
        print(f"\n{r['baseline_period']} Baseline")
        print(f"   {r['controls_met']} / {r['required_controls']} met → {r['coverage_percent']}%")
        if r['missing_controls']:
            print(f"   Missing: {', '.join(r['missing_controls'][:8])}{'...' if len(r['missing_controls']) > 8 else ''}")

    print(f"\nReport: {out_path}")

if __name__ == "__main__":
    main()