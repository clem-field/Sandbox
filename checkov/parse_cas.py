#!/usr/bin/env python3
"""
Convert rules.xml → cas_schema.json format
Optionally export as JSON (exact schema), XLSX, and/or Markdown table
Supports local files and remote URLs

# All formats (recommended)
python xml_to_cas.py --xml rules.xml --output my_security_rules --format all

# Only the official cas_schema.json
python xml_to_cas.py --xml rules.xml --format json

# From a public GitHub URL
python xml_to_cas.py \
  --xml https://raw.githubusercontent.com/bridgecrewio/checkov/main/checkov/terraform/checks/resource/aws/RDSInstancePubliclyAccessible.xml \
  --output rds_rules \
  --format all
"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
import requests
from urllib.parse import urlparse


def load_xml_content(source: str) -> str:
    """Load XML from file or URL"""
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        print(f"Downloading XML from: {source}")
        resp = requests.get(source, timeout=30)
        resp.raise_for_status()
        return resp.text
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"XML file not found: {path}")
        print(f"Reading XML from: {path}")
        return path.read_text(encoding="utf-8")


def xml_to_cas_rules(xml_source: str) -> List[Dict[str, Any]]:
    """Convert rules.xml → list of rules in cas_schema format"""
    content = load_xml_content(xml_source)
    root = ET.fromstring(content)

    rules = []
    for rule_elem in root.findall(".//rule"):
        rule_id = rule_elem.get("id")
        if not rule_id:
            continue

        desc = rule_elem.findtext("description", "").strip()
        checkov = rule_elem.findtext("checkov_rule", "").strip()

        resources = [r.text.strip() for r in rule_elem.findall("resource") if r.text]

        rule = {
            "id": rule_id,
            "severity": rule_elem.get("severity"),
            "dpath": rule_elem.get("dpath", ""),
            "description": desc,
            "checkov_rule": checkov,
            "resource": resources or []
        }

        # Optional: clean empty strings → empty string (keeps schema consistent)
        for k, v in rule.items():
            if v == "":
                rule[k] = ""

        rules.append(rule)

    return rules


def save_cas_json(output_path: Path, rules: List[Dict]) -> None:
    data = [{"rules": rules}]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"CAS Schema JSON → {output_path}")


def save_xlsx(output_path: Path, rules: List[Dict]) -> None:
    df = pd.DataFrame(rules)
    # Reorder columns nicely
    cols = ["id", "severity", "description", "checkov_rule", "dpath", "resource"]
    df = df[[c for c in cols if c in df.columns]]
    df.to_excel(output_path, index=False)
    print(f"Excel (XLSX)     → {output_path}")


def save_markdown(output_path: Path, rules: List[Dict]) -> None:
    df = pd.DataFrame(rules)
    cols = ["id", "severity", "description", "checkov_rule", "resource"]
    df_display = df[[c for c in cols if c in df.columns]]
    md_table = df_display.to_markdown(index=False)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Security Rules (from rules.xml)\n\n")
        f.write(md_table + "\n")
    print(f"Markdown         → {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert rules.xml → cas_schema.json + optional XLSX/Markdown"
    )
    parser.add_argument("--xml", required=True, help="Path or URL to rules.xml")
    parser.add_argument(
        "--output", "-o",
        default="cas_schema",
        help="Base output name (e.g. 'myrules' → myrules.json, myrules.xlsx, etc.)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "xlsx", "md", "all"],
        default="all",
        help="Output format(s): json (cas_schema), xlsx, md, or all"
    )

    args = parser.parse_args()

    print("Converting rules.xml → CAS schema format...\n")
    rules = xml_to_cas_rules(args.xml)
    print(f"Extracted {len(rules)} rules\n")

    base = Path(args.output)
    formats = [args.format] if args.format != "all" else ["json", "xlsx", "md"]

    for fmt in formats:
        if fmt == "json":
            save_cas_json(base.with_suffix(".json"), rules)
        elif fmt == "xlsx":
            save_xlsx(base.with_suffix(".xlsx"), rules)
        elif fmt == "md":
            save_markdown(base.with_suffix(".md"), rules)

    print("\nAll done!")


if __name__ == "__main__":
    try:
        import pandas  # noqa: F401
    except ImportError:
        print("Please install requirements: pip install pandas openpyxl requests")
        exit(1)

    main()