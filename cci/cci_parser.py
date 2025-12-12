#!/usr/bin/env python3
"""
cci_parser.py

Parse DISA CCI List (HTML or XML) → clean Excel (.xlsx) or JSON (exact schema match)

Features:
  • Auto-detects output format from filename extension (.xlsx or .json)
  • Only keeps the most recent version of each CCI
  • Correctly extracts all NIST references from HTML (including multi-row refs)
  • Normalizes control tags: AC-1 a 1 → AC-01(a)(1)
  • Filters by revision: v3, v4, v5, 53a, or all
  • Works perfectly with U_CCI_List.html and U_CCI_List.xml

Usage:
  python cci_parser.py -i U_CCI_List.html -o cci_rev5.json     -r v5 -v "2025-01-23"
  python cci_parser.py -i U_CCI_List.xml  -o full_cci.xlsx     -r all
"""

import argparse
import sys
import re
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


# =============================
# NIST Control Tag Normalizer
# =============================
def normalize_nist_control(tag: str) -> str:
    """Convert any NIST tag format → standard AC-53 format: AC-01(a)(1)"""
    if not tag or not isinstance(tag, str):
        return ""

    t = tag.strip()
    if not t:
        return ""

    # Uppercase + remove all whitespace
    t = re.sub(r'\s+', '', t.upper())

    # Pad family number: AC-1 → AC-01
    t = re.sub(r'([A-Z]{2,})-(\d{1,3})(?=[^0-9]|$)', lambda m: f"{m.group(1)}-{m.group(2).zfill(2)}", t)

    # Lowercase for enhancement parsing
    t = t.lower()

    # .a → (a), a.1 → (a)(1), (a).1 → (a)(1), (a)1 → (a)(1)
    t = re.sub(r'\.([a-z])', r'(\1)', t)
    t = re.sub(r'\(([a-z])\)\.?(\d)', r'(\1)(\2)', t)
    t = re.sub(r'\(([a-z])(\d)', r'(\1)(\2)', t)

    # Expand grouped letters: (abc) → (a)(b)(c)
    def expand(match):
        return '(' + ')('.join(match.group(1)) + ')'
    t = re.sub(r'\(([a-z]+)\)', expand, t)

    return t.upper()


# =============================
# HTML Parser (Corrected)
# =============================
def parse_html(filepath: Path) -> list[dict]:
    soup = BeautifulSoup(filepath.read_text(encoding="utf-8"), "html.parser")
    tables = soup.find_all("table")
    records = []

    for table in tables:
        lines = [line.strip() for line in table.get_text(separator="\n").split("\n") if line.strip()]

        data = {
            "cci": None,
            "published_date": None,
            "definition": None,
            "references": []
        }

        # Extract metadata from text lines
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

        # Extract NIST references from actual <td> cells (critical fix)
        capturing_refs = False
        for td in table.find_all("td"):
            text = td.get_text(strip=True)
            if text == "References:":
                capturing_refs = True
                continue
            if capturing_refs and text.startswith("NIST:"):
                # Clean up: remove any trailing link text, keep only the reference
                ref = text.split("NIST:", 1)[-1].strip()
                if ref:
                    data["references"].append(f"NIST: {ref}")

        if data["cci"] and data["published_date"] and data["definition"]:
            records.append(data)

    return records


# =============================
# XML Parser
# =============================
def parse_xml(filepath: Path) -> list[dict]:
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = {"cci": "http://iase.disa.mil/cci"}
    records = []

    for item in root.findall(".//cci:cci_item", ns):
        refs = []
        for ref in item.findall(".//cci:reference", ns):
            title = ref.get("title", "")
            index = ref.get("index", "")
            if not index:
                continue
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
# Main Processing
# =============================
def process_records(records: list[dict], rev_filter: str):
    if not records:
        return pd.DataFrame(), {}

    df = pd.DataFrame(records)

    # Ensure date is datetime and keep only latest version per CCI
    df['pub_date'] = pd.to_datetime(df['published_date'], errors='coerce')
    df = df.sort_values(['cci', 'pub_date'], ascending=[True, False])
    latest_df = df.drop_duplicates(subset='cci', keep='first').copy()

    # Pre-compute true latest info per CCI
    latest_info = latest_df.set_index('cci')[['published_date', 'definition']].to_dict('index')

    rows = []
    for _, row in latest_df.iterrows():
        cci = row['cci']
        for ref_line in row['references']:
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

            rows.append({
                "cci": cci,
                "published_date": row['published_date'],
                "definition": row['definition'],
                "source": source,
                "control_tag_raw": tag,
                "control_tag": normalize_nist_control(tag),
                "revision": rev
            })

    result_df = pd.DataFrame(rows)

    # Build JSON in your exact schema
    json_output = {
        "version": args.version,
        "date_created": datetime.now().strftime("%d/%m/%Y"),
        "comments": args.notes or "Generated from DISA CCI list",
        "cci_list": []
    }

    for cci in sorted(result_df['cci'].unique()):
        group = result_df[result_df['cci'] == cci]
        tags = []
        for rev_key in ["rev_3", "rev_4", "rev_5", "53a"]:
            if rev_filter != "all" and rev_key != rev_filter:
                continue
            raw_tags = group[group['revision'] == rev_key]['control_tag_raw'].tolist()
            if raw_tags:
                tags.append({rev_key: " | ".join(sorted(set(raw_tags)))})

        info = latest_info[cci]
        json_output["cci_list"].append({
            "cci": cci,
            "published_date": info['published_date'],
            "definition": info['definition'],
            "nist_tags": tags
        })

    # Excel DataFrame
    excel_df = result_df[['cci', 'published_date', 'definition', 'source', 'control_tag']] \
        .drop_duplicates() \
        .sort_values('cci')

    return excel_df, json_output


# =============================
# CLI & Main
# =============================
def main():
    parser = argparse.ArgumentParser(
        description="DISA CCI List → Excel (.xlsx) or JSON (auto-detect from extension)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-i", "--input", type=Path, required=True,
                        help="Input: U_CCI_List.html or U_CCI_List.xml")
    parser.add_argument("-o", "--output", type=Path, required=True,
                        help="Output file (.xlsx or .json)")
    parser.add_argument("-v", "--version", default="unknown",
                        help="Version string for JSON metadata")
    parser.add_argument("-n", "--notes", default=None,
                        help="Optional notes for JSON")
    parser.add_argument("-r", "--revision", choices=['v3', 'v4', 'v5', '53a', 'all'],
                        default='all', help="Filter to specific NIST revision")

    global args
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)

    ext = args.output.suffix.lower()
    if ext not in {".xlsx", ".json"}:
        print("Error: Output must end in .xlsx or .json")
        sys.exit(1)
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
        sys.exit(1)

    rev_map = {'v3': 'rev_3', 'v4': 'rev_4', 'v5': 'rev_5', '53a': '53a', 'all': 'all'}
    filter_rev = rev_map[args.revision]

    excel_df, json_data = process_records(records, filter_rev)

    if excel_df.empty and not json_data["cci_list"]:
        print("No records after filtering.")
        sys.exit(0)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if is_json:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4, ensure_ascii=False)
        print(f"JSON written → {args.output} ({len(json_data['cci_list'])} CCIs)")
    else:
        with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
            excel_df.to_excel(writer, index=False, sheet_name="CCI_List")
        print(f"Excel written → {args.output} ({len(excel_df)} rows)")

if __name__ == "__main__":
    main()