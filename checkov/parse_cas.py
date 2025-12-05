#!/usr/bin/env python3
"""
Convert rules.xml → cas_schema.json format
Optionally export as JSON (exact schema), XLSX, and/or Markdown table
Supports local files and remote URLs

# From local file
python xml_to_cas.py -i rules.xml -o myrules --format all

# From internal report portal
python xml_to_cas.py -u https://cas-report.aws.pvt -o aws_report --format all

# Raw XML from GitHub
python xml_to_cas.py -u https://raw.githubusercontent.com/.../rules.xml --format json
"""


#!/usr/bin/env python3
"""
FINAL VERSION – Works perfectly with your real cas-report.aws.pvt page
Handles XML wrapped in quotes inside <pre>, escaped entities, etc.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict
import pandas as pd
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import html


def extract_xml_from_cas_page(html_content: str) -> str:
    """
    Specifically handles the exact format from cas-report.aws.pvt:
    XML inside <pre> and wrapped in double quotes
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Find the <pre> tag
    pre_tag = soup.find("pre")
    if not pre_tag:
        raise ValueError("No <pre> tag found on the page")

    text = pre_tag.get_text(strip=True)

    # Remove surrounding quotes if present (very common)
    text = text.strip()
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]

    # Unescape HTML entities (&lt; → <, &quot; → ", etc.)
    text = html.unescape(text)

    # Basic validation
    if not text.strip().startswith("<?xml") and "<rules>" not in text:
        raise ValueError("Extracted text does not look like XML")

    return text


def load_xml_content(source: str) -> str:
    parsed = urlparse(source)

    if parsed.scheme in ("http", "https"):
        print(f"Fetching report page: {source}")
        resp = requests.get(source, timeout=30, headers={"User-Agent": "cas-converter/1.0"})
        resp.raise_for_status()

        return extract_xml_from_cas_page(resp.text)

    else:
        path = Path(source)
        if not Path(path).exists():
            raise FileNotFoundError(f"File not found: {path}")
        print(f"Reading local file: {path}")
        return Path(path).read_text(encoding="utf-8")


def xml_to_cas_rules(source: str) -> List[Dict]:
    xml_content = load_xml_content(source)

    # Debug: save extracted XML for inspection
    Path("debug_extracted.xml").write_text(xml_content, encoding="utf-8")

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse XML: {e}\nCheck debug_extracted.xml")

    rules = []
    for rule in root.findall(".//rule"):
        rule_id = rule.get("id")
        if not rule_id:
            continue

        resources = [r.text.strip() for r in rule.findall("resource") if r.text and r.text.strip()]

        rules.append({
            "id": rule_id,
            "severity": rule.get("severity", ""),
            "dpath": rule.get("dpath", ""),
            "description": (rule.findtext("description") or "").strip(),
            "checkov_rule": (rule.findtext("checkov_rule") or "").strip(),
            "resource": resources
        })

    return rules


# Output functions
def save_cas_json(path: Path, rules: List[Dict]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([{"rules": rules}], f, indent=2, ensure_ascii=False)
    print(f"CAS JSON  → {path}")

def save_xlsx(path: Path, rules: List[Dict]):
    df = pd.DataFrame(rules)
    cols = ["id", "severity", "description", "checkov_rule", "dpath", "resource"]
    df[cols].to_excel(path, index=False)
    print(f"Excel     → {path}")

def save_markdown(path: Path, rules: List[Dict]):
    df = pd.DataFrame(rules)[["id", "severity", "description", "checkov_rule", "resource"]]
    with open(path, "w", encoding="utf-8") as f:
        f.write("# CAS Security Rules\n\n")
        f.write(df.to_markdown(index=False))
    print(f"Markdown  → {path}")


def main():
    parser = argparse.ArgumentParser(description="Convert CAS report page → cas_schema.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--input-file", help="Local rules.xml or HTML file")
    group.add_argument("-u", "--url", help="URL to CAS report page (e.g. https://cas-report.aws.pvt)")

    parser.add_argument("-o", "--output", default="cas_schema", help="Output base name")
    parser.add_argument("--format", choices=["json", "xlsx", "md", "all"], default="all")

    args = parser.parse_args()

    source = args.input_file or args.url
    print(f"Source: {source}\n")

    rules = xml_to_cas_rules(source)
    print(f"Successfully extracted {len(rules)} rules\n")

    base = Path(args.output)
    formats = [args.format] if args.format != "all" else ["json", "xlsx", "md"]

    for fmt in formats:
        if fmt == "json": save_cas_json(base.with_suffix(".json"), rules)
        if fmt == "xlsx": save_xlsx(base.with_suffix(".xlsx"), rules)
        if fmt == "md":   save_markdown(base.with_suffix(".md"), rules)

    print("Done!")


if __name__ == "__main__":
    try:
        import pandas as pd
        from bs4 import BeautifulSoup
    except ImportError:
        print("Run: pip install pandas openpyxl requests beautifulsoup4 lxml")
        exit(1)
    main()