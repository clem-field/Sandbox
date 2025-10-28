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
            lib.json.load(f)
    except lib.json.JSONDecodeError:
        raise ValueError(f"Input file '{file_path}' is not a valid JSON file.")
    except FileNotFoundError:
        raise ValueError(f"Input file '{file_path}' not found.")


# --------------------------------------------------------------------------- #
# Normalisation helpers
# --------------------------------------------------------------------------- #
def _join_list(lst: lib.Any) -> str:
    if isinstance(lst, list):
        return ", ".join(str(i).strip() for i in lst if i and str(i).strip())
    return str(lst).strip() if lst else ""


def normalise_r4(control: lib.Dict[str, lib.Any]) -> lib.Dict[str, lib.Any]:
    """Flat R4 control to common dict."""
    # Extract NIST tag (preferred canonical ID)
    nist_tag = ""
    tags = control.get("tags", [])
    if isinstance(tags, list) and tags:
        nist = tags[0].get("nist", [])
        if isinstance(nist, list) and nist:
            nist_tag = nist[0]  # e.g., "AC-02(b)"

    return {
        "control_id": control.get("control_id", ""),
        "nist_tag": nist_tag,
        "title": control.get("title", ""),
        "language": control.get("language", ""),
        "supplemental_guidance": control.get("supplemental_guidance", ""),
        "implementation_guidance": control.get("implementation_guidance", ""),
        "org_ref": _join_list(control.get("org_refs") or control.get("org_ref")),
        "overlay": _join_list(control.get("overlay")),
    }


def normalise_r5(control: lib.Dict[str, lib.Any], requested_overlay: lib.Optional[str] = None) -> lib.Dict[str, lib.Any]:
    desc = {}
    descriptions = control.get("control_description", [])
    if isinstance(descriptions, list) and descriptions:
        desc = descriptions[0]

    ext = {}
    extended = control.get("extended_description", [])
    if isinstance(extended, list) and extended:
        ext = extended[0]

    baseline_map = {
        "Low": "low_baseline_parameters",
        "Mod": "moderate_baseline_parameters",
        "High": "high_baseline_parameters",
    }
    baseline_text = ""
    if requested_overlay in baseline_map:
        key = baseline_map[requested_overlay]
        baseline_text = ext.get(key, "")

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
# Load & normalise
# --------------------------------------------------------------------------- #
def load_and_normalise(file_path: str, requested_overlay: lib.Optional[str] = None) -> lib.List[lib.Dict[str, lib.Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        raw = lib.json.load(f)

    normalised: lib.List[lib.Dict[str, lib.Any]] = []

    # R4: single object or list
    if isinstance(raw, dict) and "control_id" in raw:
        normalised.append(normalise_r4(raw))
    elif isinstance(raw, list):
        for ctrl in raw:
            if isinstance(ctrl, dict) and "control_id" in ctrl:
                normalised.append(normalise_r4(ctrl))

    # R5: "controls" array
    if isinstance(raw, dict) and "controls" in raw:
        for ctrl in raw["controls"]:
            if isinstance(ctrl, dict) and "control_id" in ctrl:
                normalised.append(normalise_r5(ctrl, requested_overlay))

    return normalised


# --------------------------------------------------------------------------- #
# Load mapping file: rev4 to rev5 (1 to many)
# --------------------------------------------------------------------------- #
def load_mapping(mapping_path: str) -> lib.Dict[str, lib.Set[str]]:
    """
    Returns: { "AC-2 (b)": {"AC-02.b"}, "AC-2 (d)": {"AC-02.d.1", "AC-02.d.2"} }
    """
    if not mapping_path:
        return {}
    validate_json_file(mapping_path)
    with open(mapping_path, "r", encoding="utf-8") as f:
        data = lib.json.load(f)
    mapping: lib.Dict[str, lib.Set[str]] = {}
    for entry in data:
        r4 = entry.get("rev4", "").strip()
        r5_list = entry.get("rev5", "")
        if not r4 or not r5_list:
            continue
        r5_ids = {x.strip() for x in r5_list.split(",") if x.strip()}
        mapping[r4] = r5_ids
    return mapping


# --------------------------------------------------------------------------- #
# ID normalisation for comparison
# --------------------------------------------------------------------------- #
def normalize_id(cid: str) -> str:
    """AC-2 (b) to AC-02.b, AC-02.b to AC-02.b"""
    cid = cid.strip().upper()
    # Replace (x) with .x
    import re
    cid = re.sub(r"\s*\(\s*([A-Za-z0-9]+)\s*\)", r".\1", cid)
    # Pad single digit: AC-2 to AC-02
    cid = re.sub(r"-(\d)\b", r"-0\1", cid)
    return cid


# --------------------------------------------------------------------------- #
# Extraction for Excel
# --------------------------------------------------------------------------- #
def extract_for_excel(control: lib.Dict[str, lib.Any]) -> lib.Dict[str, lib.Any]:
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
        description="Extract NIST controls (R4/R5) – single file or delta comparison with optional R4 to R5 mapping."
    )
    parser.add_argument("-i", "--input", required=True, help="First JSON file (R4 or R5).")
    parser.add_argument("-t", "--target", help="Second JSON file (R5).")
    parser.add_argument("-o", "--output", required=True, help="Output directory.")
    parser.add_argument("-f", "--filter", required=True, help="Overlay filter for input file (Low/Mod/High).")
    parser.add_argument("-d", "--delta", help="Overlay filter for target file. Required with --target.")
    parser.add_argument("-u", "--unidirectional", action="store_true",
                        help="Keep only controls in target overlay not in input overlay.")
    parser.add_argument("-m", "--mapping", help="Optional JSON mapping file: rev4 to rev5 control IDs.")
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
    if args.mapping:
        print(f"  Mapping file     : {args.mapping}")
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

    # Load mapping
    mapping = {}
    if args.mapping:
        try:
            mapping = load_mapping(args.mapping)
            print(f"Mapping loaded: {len(mapping)} R4 to R5 entries.")
        except Exception as e:
            print(f"Error loading mapping file: {e}")
            return

    # Load & normalise
    print(f"Loading and normalising '{args.input}' ...")
    input_controls = load_and_normalise(args.input, args.filter)
    print(f"  -> {len(input_controls)} control(s) loaded from input file.")

    target_controls: lib.List[lib.Dict[str, lib.Any]] = []
    target_controls: lib.List[lib.Dict[str, lib.Any]] = []
    if args.target:
        print(f"Loading and normalising '{args.target}' ...")
        target_controls = load_and_normalise(args.target, args.delta)
        print(f"  -> {len(target_controls)} control(s) loaded from target file.")

    print("Starting analysis...")

    matched: lib.List[lib.Dict[str, lib.Any]] = []
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
        # Build R4 control IDs (use nist_tag if available, else control_id)
        r4_ids: lib.Set[str] = set()
        for ctrl in input_controls:
            overlay_str = ctrl.get("overlay", "")
            if args.filter not in [o.strip() for o in overlay_str.split(",") if o.strip()]:
                continue
            # Prefer nist_tag, fallback to control_id
            raw_id = ctrl.get("nist_tag") or ctrl.get("control_id", "")
            if raw_id:
                r4_ids.add(normalize_id(raw_id))

        # Build R5 control IDs
        r5_ids: lib.Set[str] = {
            normalize_id(c["control_id"])
            for c in target_controls
            if args.delta in [o.strip() for o in c.get("overlay", "").split(",") if o.strip()]
        }

        # Apply mapping: expand R4 IDs to R5 IDs
        mapped_r5_ids: lib.Set[str] = set()
        for r4_raw in r4_ids:
            # Try direct match first
            if r4_raw in r5_ids:
                mapped_r5_ids.add(r4_raw)
                continue
            # Try mapping file
            for rev4, rev5_set in mapping.items():
                if normalize_id(rev4) == r4_raw:
                    mapped_r5_ids.update(normalize_id(x) for x in rev5_set)

        # Final sets for comparison
        filter_mapped = mapped_r5_ids  # R4 mapped to R5
        delta_set = r5_ids

        if args.unidirectional:
            diff_ids = delta_set - filter_mapped
            for ctrl in target_controls:
                if normalize_id(ctrl["control_id"]) in diff_ids:
                    out = extract_for_excel(ctrl)
                    out["overlay"] = ctrl.get("overlay", "")
                    matched.append(out)
        else:
            diff_ids = filter_mapped.symmetric_difference(delta_set)

            # Add R4-mapped controls (from target file if present)
            for ctrl in target_controls:
                cid = normalize_id(ctrl["control_id"])
                if cid in diff_ids and cid in filter_mapped:
                    out = extract_for_excel(ctrl)
                    out["overlay"] = ctrl.get("overlay", "")
                    out["source"] = "R4 (mapped)"
                    matched.append(out)

            # Add R5-only controls
            for ctrl in target_controls:
                cid = normalize_id(ctrl["control_id"])
                if cid in diff_ids and cid not in filter_mapped:
                    out = extract_for_excel(ctrl)
                    out["overlay"] = ctrl.get("overlay", "")
                    out["source"] = "R5"
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

    df = lib.d.DataFrame(matched)
    out_dir = lib.Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_filename
    df.to_excel(out_path, index=False)
    print(f"Output written to: {out_path}")


if __name__ == "__main__":
    main()