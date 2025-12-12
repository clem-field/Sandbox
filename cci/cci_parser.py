#!/usr/bin/python3
"""
cci_parser.py

Parse DISA CCI lists (HTML or XML) and export to:
  - Excel (.xlsx) with clean columns
  - JSON matching your cci_schema.json format

Features:
  - Supports both U_CCI_List.html and U_CCI_List.xml
  - CLI arguments: -i input, -o output, -v version, -n notes, -r rev_filter
  - Only keeps the most recent version of each CCI
  - Normalizes NIST control tags (e.g., AC-1 a 1 → AC-01(a)(1))
  - Smart revision filtering: v3, v4, v5, 53a, or all

Usage example:
  python cci_parser.py -i U_CCI_List.html -o output/cci_data.xlsx -v "2025-01-23" -n "Parsed from DISA HTML" -r v5
  python cci_parser.py -i U_CCI_List.xml   -o output/cci_rev5.json  -v "2025-01-23" -r v5 --json
"""

import argparse
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import pandas as pd
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


# ======================
# NIST Control Normalizer
# ======================
def normalize_nist_control(tag: str) -> str:
    """Normalize NIST control tags to standard format: AC-01(a)(1)"""
    if not tag or not isinstance(tag, str):
        return ""

    tag = tag.strip().upper()

    # Remove all whitespace
    tag = re.sub(r'\s+', '', tag)

    # Pad family number: AC-1 → AC-01
    tag = re.sub(r'([A-Za-z]{2,})-(\d{1,3})(?=[^0-9]|$)', lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", tag)

    # Handle .a → (a), a.1 → (a)(1), (a).1 → (a)(1), etc.
    tag = tag.lower()
    tag = re.sub(r'\.([a-z])', r'(\1)', tag)
    tag = re.sub(r'\(([a-z])\)\.?(\d)', r'(\1)(\2)', tag)
    tag = re.sub(r'\(([a-z])\)(\d)', r'(\1)(\2)', tag)

    # Collapse multiple letters: (abc) → (a)(b)(c)
    def expand_letters(match):
        letters = match.group(1)
        return '(' + ')('.join(letters) + ')'

    tag = re.sub(r'\(([a-z]+)\)', expand_letters, tag)

    # Ensure digits have parentheses
    tag = re.sub(r'\((\d+)\)', r'(\1)', tag)

    return tag.upper()


# ======================
# Parser Functions
# ======================
def parse_html_file(filepath: Path) -> list:
    """Parse the DISA HTML CCI export"""
    soup = BeautifulSoup(filepath.read_text(encoding="utf-8"), "html.parser")
    tables = soup.find_all("table")

    records = []

    for table in tables:
        rows = [td.get_text(strip=True) for td in table.find_all("td")]
        text_lines = [line.strip() for line in table.get_text(separator="\n").split("\n") if line.strip()]

        data = {
            "cci": None,
            "status": None,
            "contributor": None,
            "published_date": None,
            "definition": None,
            "references": []
        }

        # Extract key fields using text index (robust against layout changes)
        for i, line in enumerate(text_lines):
            if line == "CCI:" and i + 1 < len(text_lines):
                data["cci"] = text_lines[i + 1]
            elif line == "Status:" and i + 1 < len(text_lines):
                data["status"] = text_lines[i + 1]
            elif line == "Contributor:" and i + 1 < len(text_lines):
                data["contributor"] = text_lines[i + 1]
            elif line == "Published Date:" and i + 1 < len(text_lines):
                data["published_date"] = text_lines[i + 1]
            elif line == "Definition:" and i + 1 < len(text_lines):
                # Definition may span multiple lines
                def_start = i + 1
                def_end = len(text_lines)
                for j in range(i + 1, len(text_lines)):
                    if text_lines[j] in {"Type:", "References:", "CCI:", "Status:"}:
                        def_end = j
                        break
                data["definition"] = " ".join(text_lines[def_start:def_end]).strip()

        # Extract references
        ref_block = table.find("td", string=lambda t: t and "References:" in t)
        if ref_block:
            parent = ref_block.find_parent("tr")
            if parent:
                next_trs = parent.find_next_siblings("tr")
                ref_lines = [ref_block.get_text(strip=True)]
                for tr in next_trs:
                    txt = tr.get_text(strip=True)
                    if txt.startswith("NIST:"):
                        ref_lines.append(txt)
                    else:
                        break
                data["references"] = ref_lines[1:]  # skip "References:" header

        if data["cci"] and data["published_date"] and data["definition"]:
            records.append(data)

    return records


def parse_xml_file(filepath: Path) -> list:
    """Parse the DISA XML CCI export"""
    tree = ET.parse(filepath)
    root = tree.getroot()

    ns = {"cci": "http://iase.disa.mil/cci"}
    records = []

    for item in root.findall(".//cci:cci_item", ns):
        cci_id = item.get("id")
        status = item.find("cci:status", ns).text if item.find("cci:status", ns) is not None else None
        pubdate = item.find("cci:publishdate", ns).text if item.find("cci:publishdate", ns) is not None else None
        contrib = item.find("cci:contributor", ns).text if item.find("cci:contributor", ns) is not None else None
        definition = item.find("cci:definition", ns).text if item.find("cci:definition", ns) is not None else None

        refs = []
        for ref in item.findall(".//cci:reference", ns):
            title = ref.get("title", "")
            index = ref.get("index", "")
            if "Revision 3" in title or "v3" in title:
                refs.append(f"NIST: NIST SP 800-53 (v3): {index}")
            elif "Revision 4" in title:
                refs.append(f"NIST: NIST SP 800-53 Revision 4 (v4): {index}")
            elif "Revision 5" in title:
                refs.append(f"NIST: NIST SP 800-53 Revision 5 (v5): {index}")
            elif "800-53A" in title:
                refs.append(f"NIST: NIST SP 800-53A (v1): {index}")

        records.append({
            "cci": cci_id,
            "status": status,
            "contributor": contrib,
            "published_date": pubdate,
            "definition": definition or "",
            "references": refs
        })

    return records


# ======================
# Main Processing
# ======================
def process_cci_data(records: list, revision_filter: str) -> tuple[pd.DataFrame, dict]:
    """
    Returns (dataframe for Excel, dict for JSON)
    revision_filter: 'v3', 'v4', 'v5', '53a', 'all'
    """
    df = pd.DataFrame(records)

    if df.empty:
        print("No records found.")
        return pd.DataFrame(), {}

    # Convert date and sort
    df['published_date_dt'] = pd.to_datetime(df['published_date'], errors='coerce')
    df = df.sort_values(['cci', 'published_date_dt'], ascending=[True, False])

    # Keep only latest version per CCI
    df_latest = df.drop_duplicates(subset=['cci'], keep='first').copy()

    # Parse references into structured form
    ref_rows = []
    for _, row in df_latest.iterrows():
        for ref_str in row['references']:
            if not ref_str.startswith("NIST:"):
                continue
            parts = ref_str.split(":", 2)
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

            if revision_filter != "all" and rev != revision_filter:
                continue

            ref_rows.append({
                "cci": row['cci'],
                "published_date": row['published_date'],
                "definition": row['definition'],
                "control_tag_raw": tag,
                "control_tag": normalize_nist_control(tag),
                "revision": rev,
                "source": source
            })

    result_df = pd.DataFrame(ref_rows)
    if result_df.empty:
        print("No records matched the revision filter.")
        return pd.DataFrame(), {}

    # For Excel output
    excel_df = result_df[['cci', 'published_date', 'definition', 'source', 'control_tag']].drop_duplicates()

    # For JSON output – group by CCI
    json_data = {
        "version": args.version,
        "date_created": datetime.now().strftime("%Y-%m-%d"),
        "comments": args.notes or "Generated from DISA CCI list",
        "cci_list": []
    }

    for cci, group in result_df.groupby('cci', sort=False):
        nist_tags = []
        for rev in ['rev_3', 'rev_4', 'rev_5', '53a']:
            tags = group[group['revision'] == rev]['control_tag_raw'].tolist()
            if tags and (revision_filter == "all" or rev == revision_filter):
                nist_tags.append({rev: " | ".join(sorted(set(tags)))})

        # Get definition from latest record
        defn = group.iloc[0]['definition']

        json_data["cci_list"].append({
            "cci": cci,
            "published_date": group.iloc[0]['published_date'],
            "definition": defn,
            "nist_tags": nist_tags
        })

    return excel_df, json_data


# ======================
# CLI & Main
# ======================
def main():
    parser = argparse.ArgumentParser(description="DISA CCI List Parser → XLSX or JSON")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input file: U_CCI_List.html or .xml")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output file (.xlsx or .json)")
    parser.add_argument("-v", "--version", default="unknown", help="Version string for JSON metadata")
    parser.add_argument("-n", "--notes", default="", help="Optional notes/comment field")
    parser.add_argument("-r", "--revision", choices=['v3', 'v4', 'v5', '53a', 'all'], default='all',
                        help="Filter: only include this NIST revision (or 'all')")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of XLSX")

    global args
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input file not found: {args.input}")
        sys.exit(1)

    # Detect file type
    if args.input.suffix.lower() == ".html":
        print(f"Parsing HTML file: {args.input}")
        records = parse_html_file(args.input)
    elif args.input.suffix.lower() == ".xml":
        print(f"Parsing XML file: {args.input}")
        records = parse_xml_file(args.input)
    else:
        print("Unsupported file type. Use .html or .xml")
        sys.exit(1)

    rev_map = {'v3': 'rev_3', 'v4': 'rev_4', 'v5': 'rev_5', '53a': '53a', 'all': 'all'}
    rev_filter = rev_map[args.revision]

    excel_df, json_data = process_cci_data(records, rev_filter)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.json or args.output.suffix.lower() == ".json":
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        print(f"JSON written to {args.output}")
    else:
        # Write Excel
        with pd.ExcelWriter(args.output, engine='openpyxl') as writer:
            excel_df.to_excel(writer, index=False, sheet_name="CCI_List")
        print(f"Excel written to {args.output}")

    print(f"Processed {len(excel_df)} CCIs → {len(excel_df)} rows after filtering.")


if __name__ == "__main__":
    main()