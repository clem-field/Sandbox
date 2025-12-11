#!/usr/bin/env python3
import libraries as lib

def parse_cis_controls(text):
    """Parse CIS Controls column correctly → clean v8 and v7 entries"""
    if not text or not isinstance(text, str):
        return [
            {"cis_control": "0.0", "cis_version": "v8", "title": "", "description": ""},
            {"cis_control": "0.0", "cis_version": "v7", "title": "", "description": ""}
        ]

    v8 = {"cis_control": "0.0", "cis_version": "v8", "title": "", "description": ""}
    v7 = {"cis_control": "0.0", "cis_version": "v7", "title": "", "description": ""}

    # Extract TITLE first (shared across controls)
    title_match = lib.re.search(r'TITLE:([^;]+?)(?=;\s*TITLE:|;*$)', text.strip())
    shared_title = title_match.group(1).strip() if title_match else ""

    # Match CONTROL:v8 X.X and CONTROL:v7 X.X
    for match in lib.re.finditer(r'CONTROL:\s*v?(\d)\s+([\d.]+)\s+DESCRIPTION:([^;]+)', text):
        version, number, desc = match.group(1), match.group(2).strip(), match.group(3).strip()
        title = shared_title or "Explicitly Not Mapped"

        entry = {
            "cis_control": number,
            "title": title,
            "description": desc.strip()
        }

        if version == "8":
            v8 = entry
        elif version == "7":
            v7 = entry

    return [v8, v7]


def parse_safeguards(row):
    """
    Parse correct safeguard columns:
    Col 12–14: v8 Safeguard 1/2/3
    Col 15–17: v8 IG1/IG2/IG3 (X = true)
    Col 18–20: v7 Safeguard 1/2/3
    Col 21–23: v7 IG1/IG2/IG3
    """
    def get(idx, default=""):
        return str(row[idx].value).strip() if len(row) > idx and row[idx].value else default

    def is_x(idx):
        return len(row) > idx and row[idx].value == "X"

    return {
        "v8": [{
            "safeguard_1": get(12),   # v8 Safeguard 1
            "safeguard_2": get(13),
            "safeguard_3": get(14),
            "IG1": is_x(15),
            "IG2": is_x(16),
            "IG3": is_x(17),
        }],
        "v7": [{
            "safeguard_1": get(18),   # v7 Safeguard 1
            "safeguard_2": get(19),
            "safeguard_3": get(20),
            "IG1": is_x(21),
            "IG2": is_x(22),
            "IG3": is_x(23),
        }]
    }


def extract_section_and_rec(cells):
    if len(cells) < 2:
        return None, None
    sec = cells[0].value
    rec = cells[1].value
    if not sec or not rec:
        return None, None

    sec = str(sec).strip()
    rec = str(rec).strip()

    if not lib.re.match(r"^\d+(\.\d+)+$", rec):
        return None, None

    # Use parent of recommendation as section (e.g. 18.7.6 → section 18.7)
    parts = rec.split(".")
    section = ".".join(parts[:-1])
    return section, rec


def parse_sheet(ws):
    seen = set()
    sections = lib.defaultdict(list)
    rows = list(ws.rows)

    for row in rows[1:]:  # skip header
        cells = list(row)
        if len(cells) < 20:
            continue
        if all(c.value in (None, "", " ") for c in cells[:10]):
            continue

        section_num, rec_num = extract_section_and_rec(cells)
        if not section_num or not rec_num:
            continue

        # DEDUPLICATION: same rec ID = same recommendation
        rec_key = rec_num
        if rec_key in seen:
            continue  # skip duplicates
        seen.add(rec_key)

        rec_data = {
            "recommendation": rec_num,
            "title": str(cells[3].value or "").strip(),
            "assessment_status": str(cells[4].value or ""),
            "description": str(cells[5].value or ""),
            "rational_statement": str(cells[6].value or ""),
            "impact_statement": str(cells[7].value or ""),
            "remediation_procedure": str(cells[8].value or ""),
            "audit_procedure": str(cells[9].value or ""),
            "additional_information": str(cells[10].value or ""),
            "cis_controls": parse_cis_controls(cells[11].value),
            "cis_safeguards": [parse_safeguards(cells)],
            "references": str(cells[-2].value or ""),
            "default_value": str(cells[-1].value or "")
        }

        sections[section_num].append(rec_data)

    # Sort sections and recommendations numerically
    result = []
    for sec in sorted(sections, key=lambda x: [int(p) for p in x.split('.')]):
        recs = sorted(
            sections[sec],
            key=lambda x: [int(p) for p in x["recommendation"].split('.')]
        )
        result.append({"section": sec, "recommendations": recs})

    return result


def main():
    parser = lib.argparse.ArgumentParser(description="CIS Benchmark XLSX → Clean JSON")
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-b", "--benchmark", required=True)
    parser.add_argument("-v", "--version", required=True)
    parser.add_argument("-p", "--published", required=True)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-s", "--sheet", help="Sheet name, e.g. 'Level 1 - Member Server'")

    args = parser.parse_args()

    wb = lib.openpyxl.load_workbook(args.input, read_only=True, data_only=True)

    sheet_name = args.sheet or "Combined Profiles"
    if sheet_name not in wb.sheetnames:
        print(f"Sheet '{sheet_name}' not found. Available: {wb.sheetnames}")
        exit(1)

    ws = wb[sheet_name]
    print(f"Parsing: {sheet_name}")

    sections = parse_sheet(ws)

    output = {
        "benchmark": args.benchmark,
        "version": args.version,
        "published": args.published,
        "sections": sections
    }

    lib.Path(args.output).write_text(lib.json.dumps(output, indent=4, ensure_ascii=False))
    print(f"Success: {len(sections)} sections → {args.output}")


if __name__ == "__main__":
    main()