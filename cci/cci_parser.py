#!/usr/bin/python3
import libraries as lib

# =============================
# NIST Control Tag Normalizer
# =============================
def normalize_nist_control(tag: str) -> str:
    if not tag or not isinstance(tag, str):
        return ""
    t = lib.re.sub(r'\s+', '', tag.strip().upper())
    t = lib.re.sub(r'([A-Z]{2,})-(\d{1,3})(?=[^0-9]|$)', lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", t)
    t = t.lower()
    t = lib.re.sub(r'\.([a-z])', r'(\1)', t)
    t = lib.re.sub(r'\(([a-z])\)\.?(\d)', r'(\1)(\2)', t)
    t = lib.re.sub(r'\(([a-z])(\d)', r'(\1)(\2)', t)
    def expand(match):
        return '(' + ')('.join(match.group(1)) + ')'
    t = lib.re.sub(r'\(([a-z]+)\)', expand, t)
    return t.upper()


# =============================
# HTML & XML Parsers
# =============================
def parse_html(filepath: lib.Path) -> list[dict]:
    soup = lib.BeautifulSoup(filepath.read_text(encoding="utf-8"), "html.parser")
    tables = soup.find_all("table")
    records = []
    for table in tables:
        lines = [line.strip() for line in table.get_text(separator="\n").split("\n") if line.strip()]
        data = {"cci": None, "published_date": None, "definition": None, "references": []}
        i = 0
        while i < len(lines):
            line = lines[i]
            if line == "CCI:" and i + 1 < len(lines):
                data["cci"] = lines[i + 1]
            elif line == "Published Date:" and i + 1 < len(lines):
                data["published_date"] = lines[i + 1]
            elif line == "Definition:":
                def_parts = []
                j = i + 1
                while j < len(lines) and lines[j] not in {"CCI:", "Status:", "Contributor:", "Published Date:", "Type:", "References:"}:
                    def_parts.append(lines[j])
                    j += 1
                data["definition"] = " ".join(def_parts).strip()
                i = j - 1
            i += 1

        capturing_refs = False
        for td in table.find_all("td"):
            text = td.get_text(strip=True)
            if text == "References:":
                capturing_refs = True
                continue
            if capturing_refs and text.startswith("NIST:"):
                ref = text.split("NIST:", 1)[-1].strip()
                if ref:
                    data["references"].append(f"NIST: {ref}")

        if data["cci"] and data["published_date"] and data["definition"]:
            records.append(data)
    return records


def parse_xml(filepath: lib.Path) -> list[dict]:
    tree = lib.ET.parse(filepath)
    root = tree.getroot()
    ns = {"cci": "http://iase.disa.mil/cci"}
    records = []
    for item in root.findall(".//cci:cci_item", ns):
        refs = []
        for ref in item.findall(".//cci:reference", ns):
            title = ref.get("title", "")
            index = ref.get("index", "")
            if not index: continue
            if "Revision 3" in title or "(v3)" in title:
                refs.append(f"NIST: NIST SP 800-53 (v3): {index}")
            elif "Revision 4" in title:
                refs.append(f"NIST: NIST SP 800-53 Revision 4 (v4): {index}")
            elif "Revision 5" in title:
                refs.append(f"NIST: NIST SP 800-53 Revision 5 (v5): {index}")
            elif "800-53A" in title:
                refs.append(f"NIST: NIST SP 800-53A (v1): {index}")
        records.append({
            "cci": item.get("id"),
            "published_date": item.findtext("cci:publishdate", namespaces=ns),
            "definition": item.findtext("cci:definition", namespaces=ns) or "",
            "references": refs
        })
    return records


# =============================
# Main Processing - Fixed to dedup per rev + tag by latest date
# =============================
def process_records(records: list[dict], rev_filter: str):
    if not records:
        return lib.pd.DataFrame(), {}

    flat_rows = []
    for rec in records:
        cci = rec["cci"]
        pub_date = rec["published_date"]
        definition = rec["definition"]
        try:
            dt = lib.pd.to_datetime(pub_date)
        except:
            continue

        for ref_line in rec["references"]:
            if not ref_line.startswith("NIST:"):
                continue
            parts = ref_line.split(":", 2)
            if len(parts) < 3:
                continue
            source = parts[1].strip()
            tag = parts[2].strip()

            if "v3" in source or "Revision 3" in source:
                rev = "rev_3"
            elif "Revision 4" in source:
                rev = "rev_4"
            elif "Revision 5" in source:
                rev = "rev_5"
            elif "53A" in source:
                rev = "53a"
            else:
                continue

            if rev_filter != "all" and rev != rev_filter:
                continue

            norm_tag = normalize_nist_control(tag)
            flat_rows.append({
                "cci": cci,
                "published_date": pub_date,
                "pub_dt": dt,
                "definition": definition,
                "source": source,
                "control_tag_raw": tag,
                "control_tag": norm_tag,
                "revision": rev
            })

    if not flat_rows:
        return lib.pd.DataFrame(), {}

    df = lib.pd.DataFrame(flat_rows)

    # Dedup: for each rev + norm_tag, keep only the CCI with latest pub_dt
    df = df.sort_values("pub_dt", ascending=False).drop_duplicates(subset=["revision", "control_tag"], keep="first")

    # Excel output
    excel_df = df[['cci', 'published_date', 'definition', 'source', 'control_tag']].sort_values("cci")

    # JSON output - group by CCI, with tags only if it's the latest for that rev+tag
    json_output = {
        "version": args.version,
        "date_created": lib.datetime.now().strftime("%d/%m/%Y"),
        "comments": args.notes or "Generated from DISA CCI list",
        "cci_list": []
    }

    for cci in sorted(df['cci'].unique()):
        group = df[df['cci'] == cci]
        tags = []
        rev_groups = group.groupby('revision')
        for rev_key, rev_group in rev_groups:
            if rev_filter != "all" and rev_key != rev_filter:
                continue
            raw_tags = rev_group['control_tag_raw'].unique().tolist()
            if raw_tags:
                tags.append({rev_key: " | ".join(sorted(raw_tags))})

        if tags:
            row = group.iloc[0]
            json_output["cci_list"].append({
                "cci": cci,
                "published_date": row['published_date'],
                "definition": row['definition'],
                "nist_tags": tags
            })

    return excel_df, json_output


# =============================
# CLI & Main
# =============================
def main():
    parser = lib.argparse.ArgumentParser(
        description="DISA CCI List → Excel (.xlsx) or JSON (auto-detect from extension)",
        formatter_class=lib.argparse.RawTextHelpFormatter
    )
    parser.add_argument("-i", "--input", type=lib.Path, required=True, help="Input: U_CCI_List.html or U_CCI_List.xml")
    parser.add_argument("-o", "--output", type=lib.Path, required=True, help="Output file (.xlsx or .json)")
    parser.add_argument("-v", "--version", default="unknown", help="Version string for JSON metadata")
    parser.add_argument("-n", "--notes", default=None, help="Optional notes for JSON")
    parser.add_argument("-r", "--revision", choices=['v3', 'v4', 'v5', '53a', 'all'], default='all', help="Filter to specific NIST revision")

    global args
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        lib.sys.exit(1)

    ext = args.output.suffix.lower()
    if ext not in {".xlsx", ".json"}:
        print("Error: Output must end in .xlsx or .json")
        lib.sys.exit(1)
    is_json = ext == ".json"

    # Parse input
    if args.input.suffix.lower() == ".html":
        print(f"Parsing HTML: {args.input}")
        records = parse_html(args.input)
    elif args.input.suffix.lower() == ".xml":
        print(f"Parsing XML: {args.input}")
        records = parse_xml(args.input)
    else:
        print("Error: Input must be .html or .xml")
        lib.sys.exit(1)

    rev_map = {'v3': 'rev_3', 'v4': 'rev_4', 'v5': 'rev_5', '53a': '53a', 'all': 'all'}
    filter_rev = rev_map[args.revision]

    excel_df, json_data = process_records(records, filter_rev)

    if excel_df.empty and not json_data["cci_list"]:
        print("No records after filtering.")
        lib.sys.exit(0)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if is_json:
        with open(args.output, "w", encoding="utf-8") as f:
            lib.json.dump(json_data, f, indent=4, ensure_ascii=False)
        print(f"JSON written → {args.output} ({len(json_data['cci_list'])} CCIs)")
    else:
        with lib.pd.ExcelWriter(args.output, engine="openpyxl") as writer:
            excel_df.to_excel(writer, index=False, sheet_name="CCI_List")
        print(f"Excel written → {args.output} ({len(excel_df)} rows)")

if __name__ == "__main__":
    main()