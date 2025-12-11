import libraries as lib

def parse_cis_controls(controls_text):
    """Parse CIS Controls column into clean v8 and v7 entries"""
    if not controls_text or not isinstance(controls_text, str) or not controls_text.strip():
        blank_v8 = {"cis_control": "0.0", "cis_version": "v8", "title": "", "description": ""}
        blank_v7 = {"cis_control": "0.0", "cis_version": "v7", "title": "", "description": ""}
        return [blank_v8, blank_v7]

    v8 = {"cis_control": "0.0", "cis_version": "v8", "title": "", "description": ""}
    v7 = {"cis_control": "0.0", "cis_version": "v7", "title": "", "description": ""}

    pattern = lib.re.compile(r'CONTROL:\s*v?(\d)\s*([\d.]+)\s*DESCRIPTION:\s*([^;]+)', lib.re.IGNORECASE)
    matches = pattern.finditer(controls_text)

    title = ""
    title_match = lib.re.search(r'TITLE:\s*([^C;]+)', controls_text, lib.re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()

    for match in matches:
        version, number, desc = match.group(1), match.group(2).strip(), match.group(3).strip()
        entry = {
            "cis_control": number,
            "title": title,
            "description": desc.strip()
        }
        if version == "8":
            v8.update(entry)
        elif version == "7":
            v7.update(entry)

    return [v8, v7]


def parse_safeguards(row, start_idx=11):
    def val(idx, default=""):
        v = row[idx].value if len(row) > idx else None
        return str(v).strip() if v is not None else default

    def is_x(idx):
        v = row[idx].value if len(row) > idx else None
        return v == "X" if v is not None else False

    return {
        "v8": [{
            "safeguard_1": val(start_idx),
            "safeguard_2": val(start_idx + 1),
            "safeguard_3": val(start_idx + 2),
            "IG1": is_x(start_idx + 3),
            "IG2": is_x(start_idx + 4),
            "IG3": is_x(start_idx + 5),
        }],
        "v7": [{
            "safeguard_1": val(start_idx + 6),
            "safeguard_2": val(start_idx + 7),
            "safeguard_3": val(start_idx + 8),
            "IG1": is_x(start_idx + 9),
            "IG2": is_x(start_idx + 10),
            "IG3": is_x(start_idx + 11),
        }]
    }


def extract_section_and_rec(cells):
    if len(cells) < 2:
        return None, None

    section_val = cells[0].value
    rec_val = cells[1].value

    if not section_val or not rec_val:
        return None, None

    section = str(section_val).strip()
    rec = str(rec_val).strip()

    # Must be a real recommendation number like 18.7.6
    if not lib.re.fullmatch(r"\d+(\.\d+)+", rec):
        return None, None

    # Extract parent section from recommendation if needed
    rec_parts = rec.split(".")
    if len(rec_parts) >= 2:
        candidate_section = ".".join(rec_parts[:-1])
        if rec.startswith(candidate_section + "."):
            return candidate_section, rec

    return section, rec


def parse_sheet(ws):
    sections = lib.defaultdict(list)
    rows = list(ws.rows)

    for row in rows[1:]:  # Skip header
        cells = list(row)
        if len(cells) < 15:
            continue

        # Skip empty or header-like rows
        if all(cell.value in (None, "", " ") for cell in cells[:8]):
            continue

        section_num, rec_num = extract_section_and_rec(cells)
        if not section_num or not rec_num:
            continue

        rec_data = {
            "recommendation": rec_num,
            "title": str(cells[3].value or ""),
            "assessment_status": str(cells[4].value or ""),
            "description": str(cells[5].value or ""),
            "rational_statement": str(cells[6].value or ""),
            "impact_statement": str(cells[7].value or ""),
            "remediation_procedure": str(cells[8].value or ""),
            "audit_procedure": str(cells[9].value or ""),
            "additional_information": str(cells[10].value or ""),
            "cis_controls": parse_cis_controls(cells[11].value if len(cells) > 11 else None),
            "cis_safeguards": [parse_safeguards(cells, 11)],
            "references": str(cells[-2].value or ""),
            "default_value": str(cells[-1].value or "")
        }

        sections[section_num].append(rec_data)

    # Sort everything numerically
    sorted_sections = []
    for sec in sorted(sections.keys(), key=lambda x: [int(p) for p in x.split('.')]):
        recs = sorted(
            sections[sec],
            key=lambda x: [int(p) for p in x["recommendation"].split('.')]
        )
        sorted_sections.append({
            "section": sec,
            "recommendations": recs
        })

    return sorted_sections


def main():
    parser = lib.argparse.ArgumentParser(
        description="Convert CIS Benchmark XLSX to structured JSON - with sheet selection"
    )
    parser.add_argument("-i", "--input", required=True, help="Input .xlsx file")
    parser.add_argument("-b", "--benchmark", required=True, help="Benchmark name")
    parser.add_argument("-v", "--version", required=True, help="Version e.g. v3.0.1")
    parser.add_argument("-p", "--published", required=True, help="Published date e.g. 7/22/2025")
    parser.add_argument("-o", "--output", required=True, help="Output JSON file")
    parser.add_argument(
        "-s", "--sheet",
        help='Sheet name to parse, e.g. "Level 1 - Member Server" or "Combined Profiles"'
    )

    args = parser.parse_args()

    print(f"Loading workbook: {args.input}")
    wb = lib.openpyxl.load_workbook(args.input, read_only=True, data_only=True)

    # Choose sheet
    if args.sheet:
        if args.sheet not in wb.sheetnames:
            available = [s for s in wb.sheetnames if "level" in s.lower() or "combined" in s.lower()]
            print(f"Error: Sheet '{args.sheet}' not found!")
            print(f"Available sheets: {wb.sheetnames}")
            print(f"Suggested: {available}")
            exit(1)
        ws = wb[args.sheet]
        print(f"Parsing sheet: {args.sheet}")
    else:
        # Default to Combined Profiles if exists, else first non-License sheet
        if "Combined Profiles" in wb.sheetnames:
            ws = wb["Combined Profiles"]
            print("No sheet specified → using 'Combined Profiles' (recommended)")
        else:
            candidates = [s for s in wb.sheetnames if s.lower() != "license"]
            ws = wb[candidates[0]]
            print(f"No sheet specified → using first data sheet: {ws.title}")

    sections = parse_sheet(ws)

    result = {
        "benchmark": args.benchmark,
        "version": args.version,
        "published": args.published,
        "sections": sections
    }

    lib.Path(args.output).write_text(lib.json.dumps(result, indent=4, ensure_ascii=False))
    print(f"Success! {len(sections)} sections written to {args.output}")


if __name__ == "__main__":
    main()