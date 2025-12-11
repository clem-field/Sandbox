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


import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict
import pandas as pd
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re


def is_likely_html(content: str) -> bool:
    return content.strip().lower().startswith(("<!doctype", "<html", "<html", "<head", "<body"))


def extract_xml_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # 1. Look for <pre>, <code>, or <xml> blocks containing XML
    for tag in soup.find_all(["pre", "code", "xml", "script"]):
        text = tag.get_text()
        if re.search(r'<rule\s', text) or "<rules>" in text:
            return text.strip()

    # 2. Look for any large text block that starts with <?xml or <rules
    text_blocks = soup.find_all(string=re.compile(r'<\?xml|<rules|<rule'))
    if text_blocks:
        return max(text_blocks, key=len).strip()

    return ""


def load_xml_content(source: str) -> str:
    parsed = urlparse(source)

    if parsed.scheme in ("http", "https"):
        print(f"Fetching from URL: {source}")
        try:
            resp = requests.get(source, timeout=40, headers={"User-Agent": "cas-converter/1.0"})
            resp.raise_for_status()
        except Exception as e:
            raise ValueError(f"Failed to download from URL: {e}")

        content = resp.text

        if is_likely_html(content):
            print("HTML page detected → attempting to extract embedded XML...")
            xml = extract_xml_from_html(content)
            if not xml:
                Path("debug_report_page.html").write_text(content, encoding="utf-8")
                raise ValueError(
                    "No XML found in the HTML page. "
                    "Saved page as 'debug_report_page.html' for inspection."
                )
            print("Successfully extracted XML from HTML page!")
            return xml
        else:
            return content  # raw XML

    else:
        # Local file
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        print(f"Reading local file: {path}")
        return path.read_text(encoding="utf-8")


def xml_to_cas_rules(source: str) -> List[Dict]:
    content = load_xml_content(source)

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML content: {e}\nFirst 200 chars: {content[:200]}")

    rules = []
    for rule in root.findall(".//rule"):
        rule_id = rule.get("id")
        if not rule_id:
            continue

        resources = [r.text.strip() for r in rule.findall("resource") if r.text and r.text.strip()]

        rules.append({
            "id": rule_id,
            "severity": rule.get("severity") or "",
            "dpath": rule.get("dpath") or "",
            "description": (rule.findtext("description") or "").strip(),
            "checkov_rule": (rule.findtext("checkov_rule") or "").strip(),
            "resource": resources
        })

    return rules


# Output functions
def save_cas_json(path: Path, rules: List[Dict]):
    json.dump([{"rules": rules}], path.open("w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"CAS Schema JSON → {path}")

def save_xlsx(path: Path, rules: List[Dict]):
    pd.DataFrame(rules)[["id", "severity", "description", "checkov_rule", "dpath", "resource"]].to_excel(path, index=False)
    print(f"Excel (XLSX)    → {path}")

def save_markdown(path: Path, rules: List[Dict]):
    df = pd.DataFrame(rules)[["id", "severity", "description", "checkov_rule", "resource"]]
    path.write_text("# CAS Security Rules\n\n" + df.to_markdown(index=False), encoding="utf-8")
    print(f"Markdown        → {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert rules.xml → cas_schema.json (from file or web report)"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--input-file", help="Path to local rules.xml file")
    group.add_argument("-u", "--url", help="URL to report page (e.g. https://cas-report.aws.pvt) or raw XML")

    parser.add_argument("-o", "--output", default="cas_schema", help="Output base name (default: cas_schema)")
    parser.add_argument("--format", choices=["json", "xlsx", "md", "all"], default="all",
                        help="Output format(s)")

    args = parser.parse_args()

    source = args.input_file or args.url

    print(f"Source: {source}\n")
    rules = xml_to_cas_rules(source)
    print(f"Extracted {len(rules)} rules\n")

    base = Path(args.output)
    formats = [args.format] if args.format != "all" else ["json", "xlsx", "md"]

    for fmt in formats:
        if fmt == "json": save_cas_json(base.with_suffix(".json"), rules)
        if fmt == "xlsx": save_xlsx(base.with_suffix(".xlsx"), rules)
        if fmt == "md":   save_markdown(base.with_suffix(".md"), rules)

    print("\nConversion complete!")


if __name__ == "__main__":
    try:
        import pandas as pd
        from bs4 import BeautifulSoup
    except ImportError:
        print("Install dependencies:")
        print("pip install pandas openpyxl requests beautifulsoup4 lxml")
        exit(1)
    main()