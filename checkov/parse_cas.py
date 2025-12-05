#!/usr/bin/env python3
"""
Convert rules.xml → cas_schema.json format
Supports: local file or remote URL for input XML
Output: perfectly formatted cas_schema.json structure

# From local file
python xml_to_cas.py --xml rules.xml --output cas_schema.json --pretty

# From GitHub or any public URL
python xml_to_cas.py \
  --xml https://raw.githubusercontent.com/bridgecrewio/checkov/main/checkov/terraform/checks/resource/aws/rules.xml \
  --output my_cas_schema.json

# Minimal output
python xml_to_cas.py --xml rules.xml
"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
from urllib.parse import urlparse
from typing import List, Dict, Any


def load_xml_content(source: str) -> str:
    """Load XML content from file path or URL"""
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


def convert_rules_xml_to_cas_schema(xml_source: str) -> List[Dict[str, Any]]:
    """
    Converts rules.xml into the exact structure expected by cas_schema.json
    Output matches:
    [
      {
        "rules": [
          { "id": "...", "severity": "...", "description": "...", ... }
        ]
      }
    ]
    """
    content = load_xml_content(xml_source)
    root = ET.fromstring(content)

    rules_list = []

    for rule_elem in root.findall(".//rule"):
        rule_id = rule_elem.get("id")
        if not rule_id:
            continue

        # Extract description text safely
        desc_elem = rule_elem.find("description")
        description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

        # Extract checkov_rule if present
        checkov_elem = rule_elem.find("checkov_rule")
        checkov_rule = checkov_elem.text.strip() if checkov_elem is not None and checkov_elem.text else ""

        # Collect all <resource> values as list
        resources = []
        for res in rule_elem.findall("resource"):
            if res.text:
                resources.append(res.text.strip())

        # Build rule dict in exact cas_schema.json format
        rule_dict = {
            "id": rule_id,
            "severity": rule_elem.get("severity"),
            "dpath": rule_elem.get("dpath", ""),  # may be missing or "True"
            "description": description,
            "checkov_rule": checkov_rule,
            "resource": resources  # always a list, even if single item
        }

        # Clean up empty strings → null-like (optional, matches your example)
        for k, v in list(rule_dict.items()):
            if v == "":
                rule_dict[k] = ""

        rules_list.append(rule_dict)

    # Return in the exact nested structure of cas_schema.json
    return [{"rules": rules_list}]


def main():
    parser = argparse.ArgumentParser(
        description="Convert rules.xml → cas_schema.json format (exact match)"
    )
    parser.add_argument(
        "--xml",
        required=True,
        help="Path or URL to rules.xml"
    )
    parser.add_argument(
        "--output", "-o",
        default="cas_schema.json",
        help="Output filename (default: cas_schema.json)"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON with indentation"
    )

    args = parser.parse_args()

    print("Converting rules.xml to cas_schema.json format...")
    result = convert_rules_xml_to_cas_schema(args.xml)

    indent = 2 if args.pretty else None
    output_path = Path(args.output)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=indent, ensure_ascii=False)

    print(f"Success! Converted {len(result[0]['rules'])} rules")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()