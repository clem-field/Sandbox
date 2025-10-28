import libraries as lib


# --------------------------------------------------------------------------- #
# Helper: validation
# --------------------------------------------------------------------------- #
def validate_json_file(file_path: str) -> None:
    if not file_path.lower().endswith('.json'):
        raise ValueError(f"Input file '{file_path}' must have a .json extension.")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lib.json.load(f)
    except lib.json.JSONDecodeError:
        raise ValueError(f"Input file '{file_path}' is not a valid JSON file.")
    except FileNotFoundError:
        raise ValueError(f"Input file '{file_path}' not found.")


# --------------------------------------------------------------------------- #
# Normalisation helpers
# --------------------------------------------------------------------------- #
def _join_list(lst: lib.Any) -> str:
    """Turn a list (or anything) into a comma-separated string."""
    if isinstance(lst, list):
        return ", ".join(str(i).strip() for i in lst if i and str(i).strip())
    return str(lst).strip() if lst else ""


def normalise_r4(control: lib.Dict[str, lib.Any]) -> lib.Dict[str, lib.Any]:
    """Flat R4 control to common dict."""
    return {
        "control_id": control.get("control_id", ""),
        "title": control.get("title", ""),
        "language": control.get("language", ""),
        "supplemental_guidance": control.get("supplemental_guidance", ""),
        "implementation_guidance": control.get("implementation_guidance", ""),
        "org_ref": _join_list(control.get("org_refs") or control.get("org_ref")),
        "overlay": _join_list(control.get("overlay")),
    }


def normalise_r5(control: lib.Dict[str, lib.Any], requested_overlay: lib.Optional[str] = None) -> lib.Dict[str, lib.Any]:
    """
    Nested R5 control to common dict.
    If requested_overlay is Low/Mod/High, pull the matching baseline parameters.
    """
    # Description block (first entry)
    desc = {}
    descriptions = control.get("control_description", [])
    if isinstance(descriptions, list) and descriptions:
        desc = descriptions[0]

    # Extended description (baseline parameters, guidance, etc.)
    ext = {}
    extended = control.get("extended_description", [])
    if isinstance(extended, list) and extended:
        ext = extended[0]

    # Baseline-parameter mapping
    baseline_map = {
        "Low": "low_baseline_parameters",
        "Mod": "moderate_baseline_parameters",
        "High": "high_baseline_parameters",
    }
    baseline_text = ""
    if requested_overlay in baseline_map:
        key = baseline_map[requested_overlay]
        baseline_text = ext.get(key, "")

    # Org refs from references array
    org_refs = []
    for ref in ext.get("references", []):
        if isinstance(ref, dict):
            org_refs.extend(ref.get("org_ref", []))

    return {
        "control_id": control.get("control_id", ""),
        "title": desc.get("title", ""),
        "language": desc.get("language", ""),
        "supplemental_guidance": ext.get("supplemental_guidance", ""),
        "implementation_guidance": ext.get("implementation_guidance", ""),
        "org_ref": _join_list(org_refs),
        "overlay": control.get("overlay", ""),
        "baseline_parameters": baseline_text,
    }


# --------------------------------------------------------------------------- #
# Load & normalise any file (R4 or R5)
# --------------------------------------------------------------------------- #
def load_and_normalise(file_path: str, requested_overlay: lib.Optional[str] = None) -> lib.List[lib.Dict[str, lib.Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        raw = lib.json.load(f)

    normalised: lib.List[lib.Dict[str, lib.Any]] = []

    # R4: single object or list of objects
    if isinstance(raw, dict) and "control_id" in raw:
        normalised.append(normalise_r4(raw))
    elif isinstance(raw, list):
        for ctrl in raw:
            if isinstance(ctrl, dict) and "control_id" in ctrl:
                normalised.append(normalise_r4(ctrl))

    # R5: top-level "controls" array
    if isinstance(raw, dict) and "controls" in raw:
        for ctrl in raw["controls"]:
            if isinstance(ctrl, dict) and "control_id" in ctrl:
                normalised.append(normalise_r5(ctrl, requested_overlay))

    return normalised


# --------------------------------------------------------------------------- #
# Extraction for final Excel
# --------------------------------------------------------------------------- #
def extract_for_excel(control: lib.Dict[str, lib.Any]) -> lib.ict[str, lib.Any]:
    out = {
        "control_id": control.get("control_id", ""),
        "title": control.get("title", ""),
        "language": control.get("language", ""),
        "supplemental_guidance": control.get("supplemental_guidance", ""),
        "implementation_guidance": control.get("implementation_guidance", ""),
        "org_ref": control.get("org_ref", ""),
    }
    if control.get("overlay"):
        out["overlay"] = control["overlay"]
    if control.get("baseline_parameters"):
        out["baseline_parameters"] = control["baseline_parameters"]
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = lib.argparse.ArgumentParser(
        description="Extract NIST controls (R4/R5) – single file or delta comparison."
    )
    parser.add_argument("-i", "--input", required=True, help="First JSON file (used with --filter).")
    parser.add_argument("-t", "--target", help="Second JSON file (used with --delta).")
    parser.add_argument("-o", "--output", required=True, help="Output directory.")
    parser.add_argument("-f", "--filter", required=True, help="Overlay filter for the first file (Low/Mod/High).")
    parser.add_argument("-d", "--delta", help="Overlay filter for the second file. Required with --target.")
    parser.add_argument("-u", "--unidirectional", action="store_true",
                        help="Keep only controls in target overlay not in input overlay.")
    args = parser.parse_args()

    # Print selected options
    print("Selected options:")
    print(f"  Input file       : {args.input}")
    print(f"  Filter overlay   : {args.filter}")
    print(f"  Output directory : {args.output}")
    if args.target:
        print(f"  Target file      : {args.target}")
        print(f"  Delta overlay    : {args.delta}")
    if args.unidirectional:
        print("  Unidirectional   : ENABLED")
    print()

    # Validate files
    try:
        validate_json_file(args.input)
    except ValueError as e:
        print(f"Error: {e}")
        return
    print(f"Input file '{args.input}' validated successfully.")

    if args.target:
        if not args.delta:
            print("Error: --target requires --delta.")
            return
        try:
            validate_json_file(args.target)
        except ValueError as e:
            print(f"Error: {e}")
            return
        print(f"Target file '{args.target}' validated successfully.")
    if args.unidirectional and not args.delta:
        print("Error: --unidirectional requires --delta.")
        return

    # Load & normalise
    print(f"Loading and normalising '{args.input}' ...")
    input_controls = load_and_normalise(args.input, args.filter)
    print(f"  -> {len(input_controls)} control(s) loaded from input file.")

    target_controls: lib.List[lib.Dict[str, lib.Any]] = []
    if args.target:
        print(f"Loading and normalising '{args.target}' ...")
        target_controls = load_and_normalise(args.target, args.delta)
        print(f"  -> {len(target_controls)} control(s) loaded from target file.")

    print("Starting analysis...")

    matched: lib.List[lib.Dict[str, lib.Any]] = []

    # SINGLE-FILE MODE
    if not args.target:
        for ctrl in input_controls:
            overlay_str = ctrl.get("overlay", "")
            if args.filter in [o.strip() for o in overlay_str.split(",") if o.strip()]:
                matched.append(extract_for_excel(ctrl))
        output_filename = f"matched_controls_{args.filter}.xlsx"

    # DUAL-FILE DELTA MODE
    else:
        # Build sets of control_id belonging to each overlay
        filter_ids = {
            c["control_id"]
            for c in input_controls
            if args.filter in [o.strip() for o in c.get("overlay", "").split(",") if o.strip()]
        }
        delta_ids = {
            c["control_id"]
            for c in target_controls
            if args.delta in [o.strip() for o in c.get("overlay", "").split(",") if o.strip()]
        }

        if args.unidirectional:
            diff_ids = delta_ids - filter_ids
            for ctrl in target_controls:
                if ctrl["control_id"] in diff_ids:
                    out = extract_for_excel(ctrl)
                    out["overlay"] = ctrl.get("overlay", "")
                    matched.append(out)
        else:
            diff_ids = filter_ids.symmetric_difference(delta_ids)

            # Input side
            for ctrl in input_controls:
                if ctrl["control_id"] in diff_ids:
                    out = extract_for_excel(ctrl)
                    out["overlay"] = ctrl.get("overlay", "")
                    matched.append(out)

            # Target side (avoid duplicates)
            added = {m["control_id"] for m in matched}
            for ctrl in target_controls:
                if ctrl["control_id"] in diff_ids and ctrl["control_id"] not in added:
                    out = extract_for_excel(ctrl)
                    out["overlay"] = ctrl.get("overlay", "")
                    matched.append(out)

        output_filename = f"delta_{args.filter}_to_{args.delta}.xlsx"

    # Write output
    if not matched:
        msg = f"No controls matched (filter='{args.filter}'"
        if args.delta:
            msg += f", delta='{args.delta}'"
            if args.unidirectional:
                msg += ", unidirectional"
        msg += ")."
        print(msg)
        return

    df = lib.pd.DataFrame(matched)
    out_dir = lib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_filename
    df.to_excel(out_path, index=False)
    print(f"Output written to: {out_path}")


if __name__ == "__main__":
    main()