#!/usr/bin/env python3
import libraries as lib

COLUMN_MAP = {
    "section":           ["Section #"],
    "recommendation":    ["Recommendation #", "Rec #"],
    "profile":           ["Profile"],
    "title":             ["Title"],
    "assessment_status": ["Assessment Status"],
    "description":       ["Description"],
    "rationale":         ["Rationale Statement", "Rationale"],
    "impact":            ["Impact Statement", "Impact"],
    "remediation":       ["Remediation Procedure", "Remediation"],
    "audit":             ["Audit Procedure", "Audit"],
    "additional_info":   ["Additional Information"],
    "cis_controls":      ["CIS Controls"],
    "v8_sg1":            ["CIS Safeguards 1 (v8"],
    "v8_sg2":            ["CIS Safeguards 2 (v8)"],
    "v8_sg3":            ["CIS Safeguards 3 (v8)"],
    "v8_ig1":            ["v8 IG1"],
    "v8_ig2":             ["v8 IG2"],
    "v8_ig3":            ["v8 IG3"],
    "v7_sg1":            ["CIS Safeguards 1 (v7)"],
    "v7_sg2":            ["CIS Safeguards 2 (v7)"],
    "v7_sg3":            ["CIS Safeguards 3 (v7)"],
    "v7_ig1":            ["v7 IG1"],
    "v7_ig2":            ["v7 IG2"],
    "v7_ig3":            ["v7 IG3"],
    "references":        ["References"],
    "default_value":     ["Default Value"],
}

def find_column(header_row, keys):
    header_vals = [str(c.value or "").strip().lower() for c in header_row]
    for idx, val in enumerate(header_vals):
        if any(k.lower() in val for k in keys):
            return idx
    return None

def build_columns(header_row):
    cols = {}
    for name, keys in COLUMN_MAP.items():
        cols[name] = find_column(header_row, keys)
    return cols

def parse_cis_controls(text):
    if not text or not isinstance(text, str) or not text.strip():
        return []

    controls = []
    text = text.strip()

    title_blocks = [m.group(1).strip() for m in lib.re.finditer(r'TITLE:\s*([^;]+)', text, lib.re.IGNORECASE)]
    title_idx = 0

    for match in lib.re.finditer(r'CONTROL:\s*v?(\d)\s+([\d.]+)\s+DESCRIPTION:\s*([^;]+)', text):
        version_num = match.group(1)
        control_num = match.group(2).strip()
        description = match.group(3).strip()

        title = title_blocks[title_idx] if title_idx < len(title_blocks) else "Explicitly Not Mapped"
        controls.append({
            "cis_control": control_num,
            "cis_version": "v8" if version_num == "8" else "v7",
            "title": title,
            "description": description
        })

        # Advance title only when version changes or end
        if title_idx + 1 < len(title_blocks):
            try:
                next_match = list(lib.re.finditer(r'CONTROL:\s*v?(\d)', text[match.end():]))[0]
                if next_match.group(1) != version_num:
                    title_idx += 1
            except:
                title_idx += 1

    return controls

def parse_safeguards(row, col):
    def val(name, default=""):
        i = col.get(name)
        if i is None or len(row) <= i: return default
        v = row[i].value
        return str(v).strip() if v is not None else default

    def is_x(name):
        i = col.get(name)
        return i is not None and len(row) > i and row[i].value == "X"

    return {
        "v8": [{
            "safeguard_1": val("v8_sg1"),
            "safeguard_2": val("v8_sg2"),
            "safeguard_3": val("v8_sg3"),
            "IG1": is_x("v8_ig1"),
            "IG2": is_x("v8_ig2"),
            "IG3": is_x("v8_ig3"),
        }],
        "v7": [{
            "safeguard_1": val("v7_sg1"),
            "safeguard_2": val("v7_sg2"),
            "safeguard_3": val("v7_sg3"),
            "IG1": is_x("v7_ig1"),
            "IG2": is_x("v7_ig2"),
            "IG3": is_x("v7_ig3"),
        }]
    }

def detect_profile(ws, cells, col):
    if ws.title == "Combined Profiles" and col.get("profile") is not None:
        idx = col["profile"]
        if len(cells) > idx and cells[idx].value:
            return str(cells[idx].value).strip()

    # Fallback mapping from sheet name
    name = ws.title
    mapping = {
        "Level 1 - Domain Controller": "Level 1 - Domain Controller",
        "Level 1 - Member Server":     "Level 1 - Member Server",
        "Level 2 - Domain Controller": "Level 2 - Domain Controller",
        "Level 2 - Member Server":     "Level 2 - Member Server",
    }
    for key, value in mapping.items():
        if key in name:
            return value
    return name

def parse_sheet(ws):
    rows = list(ws.rows)
    if not rows:
        return []

    header = rows[0]
    col = build_columns(header)

    if col["recommendation"] is None:
        raise RuntimeError("Missing 'Recommendation #' column")

    sections = lib.defaultdict(list)

    # Unique key is (recommendation_number, profile) when on Combined sheet
    # On single-profile sheets, profile is same → no conflict
    seen_keys = set()

    for row in rows[1:]:
        cells = list(row)

        rec_cell = cells[col["recommendation"]] if col["recommendation"] < len(cells) else None
        if not rec_cell or not rec_cell.value:
            continue
        rec_num = str(rec_cell.value).strip()
        if not lib.re.match(r"^\d+(\.\d+)+$", rec_num):
            continue

        profile = detect_profile(ws, cells, col)

        # Unique key: (rec_num + profile
        unique_key = f"{rec_num}|{profile}"
        if unique_key in seen_keys:
            continue
        seen_keys.add(unique_key)

        def get(name, default=""):
            i = col.get(name)
            if i is None or len(cells) <= i:
                return default
            v = cells[i].value
            return str(v).strip() if v is not None else default

        rec_data = {
            "recommendation": rec_num,
            "profile": profile,
            "title": get("title"),
            "assessment_status": get("assessment_status"),
            "description": get("description"),
            "rational_statement": get("rationale"),
            "impact_statement": get("impact"),
            "remediation_procedure": get("remediation"),
            "audit_procedure": get("audit"),
            "additional_information": get("additional_info"),
            "cis_controls": parse_cis_controls(get("cis_controls")),
            "cis_safeguards": [parse_safeguards(cells, col)],
            "references": get("references"),
            "default_value": get("default_value"),
            "nist_controls": []
        }

        section_key = ".".join(rec_num.split(".")[:-1])
        sections[section_key].append(rec_data)

    # Sort everything
    result = []
    for sec in sorted(sections.keys(), key=lambda x: [int(p) for p in x.split('.')]):
        recs = sorted(sections[sec], key=lambda x: (x["recommendation"], x["profile"]))
        result.append({"section": sec, "recommendations": recs})

    return result

def main():
    parser = lib.argparse.ArgumentParser(description="CIS Benchmark → Perfect JSON (Combined Profiles ready)")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-b", "--benchmark", required=True)
    parser.add_argument("-v", "--version", required=True)
    parser.add_argument("-p", "--published", required=True)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-s", "--sheet", help="Sheet name (default: Combined Profiles)")

    args = parser.parse_args()

    wb = lib.openpyxl.load_workbook(args.input, read_only=True, data_only=True)

    sheet_name = args.sheet or "Combined Profiles"
    if sheet_name not in wb.sheetnames:
        print(f"Sheet '{sheet_name}' not found!")
        print("Available:", wb.sheetnames)
        exit(1)

    ws = wb[sheet_name]
    print(f"Parsing: '{sheet_name}'")

    sections = parse_sheet(ws)

    output = {
        "benchmark": args.benchmark,
        "version": args.version,
        "published": args.published,
        "sections": sections
    }

    lib.Path(args.output).write_text(lib.json.dumps(output, indent=4, ensure_ascii=False))
    print(f"PERFECT! {len(sections)} sections → {args.output}")

if __name__ == "__main__":
    main()