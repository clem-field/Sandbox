#!/usr/bin/env python3
# cis_convert.py
# Works with ALL CIS Windows Server 2019/2022/2025 benchmark sheets
# Auto-detects column positions – no more hard-coded indices!

import libraries as lib

# ----------------------------------------------------------------------
# Column name → expected header text (case-insensitive, partial match ok)
# ----------------------------------------------------------------------
COLUMN_MAP = {
    "section":              ["Section #"],
    "recommendation":       ["Recommendation #", "Rec #"],
    "profile":              ["Profile"],                     # only in Combined Profiles
    "title":                ["Title"],
    "assessment_status":    ["Assessment Status"],
    "description":          ["Description"],
    "rationale":            ["Rationale Statement", "Rationale"],
    "impact":               ["Impact Statement", "Impact"],
    "remediation":          ["Remediation Procedure", "Remediation"],
    "audit":                ["Audit Procedure", "Audit"],
    "additional_info":      ["Additional Information"],
    "cis_controls":         ["CIS Controls"],
    # Safeguards – v8
    "v8_sg1":               ["CIS Safeguards 1 (v8", "CIS Safeguards 1 (v8)"],
    "v8_sg2":               ["CIS Safeguards 2 (v8)"],
    "v8_sg3":               ["CIS Safeguards 3 (v8)"],
    "v8_ig1":               ["v8 IG1"],
    "v8_ig2":               ["v8 IG2"],
    "v8_ig3":               ["v8 IG3"],
    # Safeguards – v7
    "v7_sg1":               ["CIS Safeguards 1 (v7)"],
    "v7_sg2":               ["CIS Safeguards 2 (v7)"],
    "v7_sg3":               ["CIS Safeguards 3 (v7)"],
    "v7_ig1":               ["v7 IG1"],
    "v7_ig2":               ["v7 IG2"],
    "v7_ig3":               ["v7 IG3"],
    "references":           ["References"],
    "default_value":        ["Default Value"],
}

def find_column_index(header_row, keys):
    """Return the first column index that matches any of the keys (case-insensitive)"""
    header_values = [str(cell.value or "").strip().lower() for cell in header_row]
    for idx, val in enumerate(header_values):
        if any(key.lower() in val for key in keys):
            return idx
    return None

def build_column_indices(header_row):
    """Detect all required column positions from the header row"""
    indices = {}
    for name, keys in COLUMN_MAP.items():
        idx = find_column_index(header_row, keys)
        if idx is None:
            print(f"Warning: Column not found for: {name} (looked for {keys})")
        indices[name] = idx
    return indices

# ----------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------
def parse_cis_controls(text):
    if not text or not isinstance(text, str) or not text.strip():
        return [
            {"cis_control": "0.0", "cis_version": "v8", "title": "", "description": ""},
            {"cis_control": "0.0", "cis_version": "v7", "title": "", "description": ""}
        ]

    v8 = {"cis_control": "0.0", "cis_version": "v8", "title": "", "description": ""}
    v7 = {"cis_control": "0.0", "cis_version": "v7", "title": "", "description": ""}

    # Shared title (usually the same for v7 and v8)
    title_match = lib.re.search(r'TITLE:\s*([^;]+)', text, lib.re.IGNORECASE)
    shared_title = title_match.group(1).strip() if title_match else ""

    for m in lib.re.finditer(r'CONTROL:\s*v?(\d)\s+([\d.]+)\s+DESCRIPTION:\s*([^;]+)', text):
        ver, num, desc = m.group(1), m.group(2).strip(), m.group(3).strip()
        entry = {
            "cis_control": num,
            "title": shared_title or "Explicitly Not Mapped",
            "description": desc.strip()
        }
        if ver == "8":
            v8 = entry
        elif ver == "7":
            v7 = entry

    return [v8, v7]

def parse_safeguards(row, idx):
    def val(col_name, default=""):
        i = idx[col_name]
        if i is None or len(row) <= i:
            return default
        v = row[i].value
        return str(v).strip() if v is not None else default

    def is_x(col_name):
        i = idx[col_name]
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

# ----------------------------------------------------------------------
# Main parsing logic
# ----------------------------------------------------------------------
def parse_sheet(ws):
    rows = list(ws.rows)
    if not rows:
        return []

    header_row = rows[0]
    col_idx = build_column_indices(header_row)

    # Required columns – if any are missing we abort
    required = ["section", "recommendation", "title", "cis_controls"]
    missing = [name for name in required if col_idx[name] is None]
    if missing:
        raise RuntimeError(f"Missing required columns in sheet: {missing}")

    sections = lib.defaultdict(list)
    seen_recs = set()

    for row in rows[1:]:
        cells = list(row)

        sec_idx = col_idx["section"]
        rec_idx = col_idx["recommendation"]
        if sec_idx is None or rec_idx is None or len(cells) <= max(sec_idx, rec_idx):
            continue

        section_num = str(cells[sec_idx].value or "").strip()
        rec_num     = str(cells[rec_idx].value or "").strip()

        if not rec_num or not lib.re.match(r"^\d+(\.\d+)+$", rec_num):
            continue

        # Deduplicate – same recommendation number = same item
        if rec_num in seen_recs:
            continue
        seen_recs.add(rec_num)

        # Build recommendation object safely
        def get(col_name, default=""):
            i = col_idx.get(col_name)
            if i is None or len(cells) <= i:
                return default
            v = cells[i].value
            return str(v).strip() if v is not None else default

        rec_data = {
            "recommendation": rec_num,
            "title": get("title"),
            "assessment_status": get("assessment_status"),
            "description": get("description"),
            "rational_statement": get("rationale"),
            "impact_statement": get("impact"),
            "remediation_procedure": get("remediation"),
            "audit_procedure": get("audit"),
            "additional_information": get("additional_info"),
            "cis_controls": parse_cis_controls(get("cis_controls")),
            "cis_safeguards": [parse_safeguards(cells, col_idx)],
            "references": get("references"),
            "default_value": get("default_value")
        }

        # Determine section – use parent of recommendation (e.g. 18.7.6 → section 18.7)
        section_key = ".".join(rec_num.split(".")[:-1])
        sections[section_key].append(rec_data)

    # Sort everything numerically
    result = []
    for sec in sorted(sections.keys(), key=lambda x: [int(p) for p in x.split('.')]):
        recs = sorted(
            sections[sec],
            key=lambda x: [int(p) for p in x["recommendation"].split('.')]
        )
        result.append({"section": sec, "recommendations": recs})

    return result

# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def main():
    import libraries as lib

    parser = lib.argparse.ArgumentParser(description="CIS Benchmark → Clean JSON (auto column detection)")
    parser.add_argument("-i", "--input", required=True, help="Input .xlsx file")
    parser.add_argument("-b", "--benchmark", required=True)
    parser.add_argument("-v", "--version", required=True)
    parser.add_argument("-p", "--published", required=True)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-s", "--sheet", help='Sheet name, e.g. "Level 1 - Member Server"')

    args = parser.parse_args()

    wb = lib.openpyxl.load_workbook(args.input, read_only=True, data_only=True)

    sheet_name = args.sheet or "Combined Profiles"
    if sheet_name not in wb.sheetnames:
        print(f"Error: Sheet '{sheet_name}' not found!")
        print("Available sheets:", wb.sheetnames)
        exit(1)

    ws = wb[sheet_name]
    print(f"Parsing sheet: '{sheet_name}'")

    sections = parse_sheet(ws)

    output = {
        "benchmark": args.benchmark,
        "version": args.version,
        "published": args.published,
        "sections": sections
    }

    lib.Path(args.output).write_text(lib.json.dumps(output, indent=4, ensure_ascii=False))
    print(f"Success! {len(sections)} sections → {args.output}")

if __name__ == "__main__":
    main()