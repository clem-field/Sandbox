#!/usr/bin/env python3
"""
Parse and compare security rules from rules.xml and cas_schema.json
Output: JSON, XLSX (Excel), and/or Markdown table

use cases
# All formats
python compare_rules.py --xml rules.xml --json cas_schema.json --output my_rules --format all

# Only JSON
python compare_rules.py --xml rules.xml --json cas_schema.json --format json

# Custom name + Markdown only
python compare_rules.py --xml rules.xml --json cas_schema.json -o security_rules_2025 --format md

"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd


def parse_rules_xml(xml_path: Path) -> Dict[str, Dict[str, Any]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    rules = {}
    for rule_elem in root.findall(".//rule"):
        rule_id = rule_elem.get("id")
        if not rule_id:
            continue

        description = ""
        desc_elem = rule_elem.find("description")
        if desc_elem is not None and desc_elem.text:
            description = desc_elem.text.strip()

        checkov = ""
        checkov_elem = rule_elem.find("checkov_rule")
        if checkov_elem is not None and checkov_elem.text is None:
            checkov = checkov_elem.text.strip()

        resources = [r.text.strip() for r in rule_elem.findall("resource") if r.text]

        rules[rule_id] = {
            "severity": rule_elem.get("severity"),
            "dpath": rule_elem.get("dpath"),
            "description": description,
            "checkov_rule": checkov,
            "resource": resources,
            "source": "xml"
        }
    return rules


def parse_cas_schema_json(json_path: Path) -> Dict[str, Dict[str, Any]]:
    with open(json_path, "r") as f:
        data = json.load(f)

    rules = {}
    for container in data:
        if "rules" not in container:
            continue
        for rule in container["rules"]:
            rule_id = rule.get("id")
            if not rule_id:
                continue

            # Normalize resource to list
            res = rule.get("resource", [])
            if isinstance(res, str):
                res = [res]

            rules[rule_id] = {
                "severity": rule.get("severity"),
                "dpath": rule.get("dpath"),
                "description": rule.get("description", "").strip(),
                "checkov_rule": rule.get("checkov_rule", ""),
                "resource": res,
                "source": "json"
            }
    return rules


def merge_rules(xml_rules: Dict, json_rules: Dict) -> List[Dict[str, Any]]:
    all_ids = sorted(set(xml_rules.keys()) | set(json_rules.keys()))
    merged = []

    for rid in all_ids:
        xml = xml_rules.get(rid, {})
        jsn = json_rules.get(rid, {})

        row = {"id": rid}

        for field in ["severity", "dpath", "description", "checkov_rule", "resource"]:
            xml_val = xml.get(field)
            jsn_val = jsn.get(field)

            # Prioritize non-empty JSON value, fallback to XML
            if jsn_val not in (None, "", [], {}):
                row[field] = jsn_val
                row[f"{field}_source"] = "json"
            elif xml_val not in (None, "", [], {}):
                row[field] = xml_val
                row[f"{field}_source"] = "xml"
            else:
                row[field] = None
                row[f"{field}_source"] = "missing"

        # Overall source presence
        sources = set()
        if rid in xml_rules:
            sources.add("xml")
        if rid in json_rules:
            sources.add("json")
        row["available_in"] = ", ".join(sorted(sources))

        merged.append(row)

    return merged

def save_json(output_path: Path, data: List[Dict]) -> None:
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON -> {output_path}")


def save_xlsx(output_path: Path, data: List[Dict]) -> None:
    df = pd.DataFrame(data)
    # Nice column order
    base_cols = ["id", "available_in"]
    for field in ["severity", "dpath", "description", "checkov_rule", "resource"]:
        base_cols += [field, f"{field}_source"]
    df = df[base_cols]
    df.to_excel(output_path, index=False)
    print(f"Saved XLSX -> {output_path}")


def save_markdown(output_path: Path, data: List[Dict]) -> None:
    df = pd.DataFrame(data)
    # Select and order columns for clean markdown
    display_cols = ["id", "available_in", "severity", "severity_source",
                    "description", "checkov_rule", "resource"]
    df_display = df[[c for c in display_cols if c in df.columns]]
    markdown_table = df_display.to_markdown(index=False)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Security Rules Comparison\n\n")
        f.write(markdown_table + "\n")
    print(f"Saved Markdown -> {output_path}")



def main():
    parser = argparse.ArgumentParser(description="Compare rules.xml and cas_schema.json")
    parser.add_argument("--xml", required=True, help="Path to rules.xml")
    parser.add_argument("--json", required=True, help="Path to cas_schema.json")
    parser.add_argument("--output", "-o", help="Base output filename (without extension)")
    parser.add_argument("--format", choices=["json", "xlsx", "md", "all"],
                        default="all", help="Output format(s)")

    args = parser.parse_args()

    xml_path = Path(args.xml)
    json_path = Path(args.json)

    if not xml_path.exists():
        print(f"rules.xml not found: {xml_path}")
        exit(1)
    if not json_path.exists():
        print(f"cas_schema.json not found: {json_path}")
        exit(1)

    print("Parsing rules.xml...")
    xml_rules = parse_rules_xml(xml_path)
    print(f"Found {len(xml_rules)} rules in XML")

    print("Parsing cas_schema.json...")
    json_rules = parse_cas_schema_json(json_path)
    print(f"Found {len(json_rules)} rules in JSON")

    print("Merging and comparing...")
    merged_data = merge_rules(xml_rules, json_rules)
    print(f"Total unique rules: {len(merged_data)}")

    base_name = args.output or "rules_comparison"

    formats = [args.format] if args.format != "all" else ["json", "xlsx", "md"]

    for fmt in formats:
        if fmt == "json":
            save_json(Path(f"{base_name}.json"), merged_data)
        elif fmt == "xlsx":
            save_xlsx(Path(f"{base_name}.xlsx"), merged_data)
        elif fmt == "md":
            save_markdown(Path(f"{base_name}.md"), merged_data)

    print("\nDone!")


if __name__ == "__main__":
    main()

