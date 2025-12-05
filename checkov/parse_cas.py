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
from typing import List, Dict
import pandas as pd
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re


def is_likely_html(content: str) -> bool:
    """Check if content is HTML (not raw XML)"""
    content = content.strip().lower()
    return content.startswith(("<!doctype", "<html", "<head", "<body"))


def extract_xml_from_html(html_content: str) -> str:
    """
    Extract XML content from HTML page.
    Looks for: <xml> tags, <pre> code blocks, downloadable links, or embedded data.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Method 1: Find <xml> or <pre> tags with XML-like content
    xml_candidates = []
    for tag in soup.find_all(['xml', 'pre', 'code']):
        text = tag.get_text().strip()
        if text.startswith('<?xml') or '<rules>' in text or '<rule' in text:
            xml_candidates.append(text)

    if xml_candidates:
        # Return the longest/most complete one
        return max(xml_candidates, key=len, default='')

    # Method 2: Look for links to XML files
    links = [a.get('href') for a in soup.find_all('a', href=True) if 'xml' in a.get('href', '').lower()]
    if links:
        print(f"Found potential XML download links: {links}")
        # Could auto-download first link; for now, suggest
        return f"XML_LINKS:{';'.join(links)}"  # Placeholder for manual handling

    # Method 3: Regex search for XML fragments (fallback)
    xml_match = re.search(r'(<\?xml[^<]*<rules[^<]*>.*?</rules>)', html_content, re.DOTALL | re.IGNORECASE)
    if xml_match:
        return xml_match.group(1)

    return ''  # No XML found


def load_xml_content(source: str) -> str:
    """Load XML from file, raw URL, or full web page (extracts from HTML)"""
    parsed = urlparse(source)

    if parsed.scheme in ("http", "https"):
        print(f"Fetching page: {source}")

        try:
            resp = requests.get(
                source,
                timeout=30,
                headers={"User-Agent": "xml-to-cas-extractor/1.0"}
            )
            resp.raise_for_status()
        except requests.exceptions.SSLError as e:
            print(f"SSL Error: {e}. Check if the site requires authentication or VPN.")
            raise
        except requests.exceptions.RequestException as e:
            print(f"Fetch failed: {e}")
            raise

        content = resp.text

        if is_likely_html(content):
            print("Detected HTML page. Attempting to extract embedded XML...")
            extracted = extract_xml_from_html(content)
            if extracted:
                if extracted.startswith('XML_LINKS:'):
                    raise ValueError(f"XML not embedded; download from links: {extracted}")
                print("XML extracted successfully from page!")
                return extracted
            else:
                # Save HTML for inspection
                html_path = Path("debug_page.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"No XML found on page. Saved raw HTML to '{html_path}' for manual review.")
                print("Inspect it for <pre>, <xml> tags, or download links to rules.xml.")
                raise ValueError("No extractable XML on the page.")
        else:
            # Assume it's raw XML
            return content

    else:
        # Local file
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        print(f"Reading local file: {path}")
        return path.read_text(encoding="utf-8")


def xml_to_cas_rules(xml_source: str) -> List[Dict]:
    """Convert XML content → list of rules in CAS schema format"""
    content = load_xml_content(xml_source)

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"XML parse error: {e}")
        print("Content preview:", content[:200])
        raise

    rules = []
    for rule_elem in root.findall(".//rule"):
        rule_id = rule_elem.get("id")
        if not rule_id:
            continue

        description = rule_elem.findtext("description", "").strip()
        checkov_rule = rule_elem.findtext("checkov_rule", "").strip()

        resources = [r.text.strip() for r in rule_elem.findall("resource") if r.text]

        rule = {
            "id": rule_id,
            "severity": rule_elem.get("severity"),
            "dpath": rule_elem.get("dpath", ""),
            "description": description,
            "checkov_rule": checkov_rule,
            "resource": resources or []
        }

        # Clean empty values
        for k, v in rule.items():
            if v == "":
                rule[k] = ""

        rules.append(rule)

    return rules


# Output functions (unchanged from previous)
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
        f.write("# Security Rules (Extracted from Report)\n\n")
        f.write(df.to_markdown(index=False))
    print(f"Markdown  → {path}")


def main():
    parser = argparse.ArgumentParser(description="Extract XML rules from web pages/files → CAS schema + formats")
    parser.add_argument("--source", required=True, help="URL to page (e.g., https://cas-report.aws.pvt) or path/URL to rules.xml")
    parser.add_argument("--output", "-o", default="cas_schema", help="Output base name")
    parser.add_argument("--format", choices=["json", "xlsx", "md", "all"], default="all")

    args = parser.parse_args()

    print("Starting extraction...\n")
    rules = xml_to_cas_rules(args.source)
    print(f"Successfully extracted {len(rules)} rules\n")

    base = Path(args.output)
    fmts = [args.format] if args.format != "all" else ["json", "xlsx", "md"]

    for fmt in fmts:
        if fmt == "json": save_cas_json(base.with_suffix(".json"), rules)
        if fmt == "xlsx": save_xlsx(base.with_suffix(".xlsx"), rules)
        if fmt == "md":    save_markdown(base.with_suffix(".md"), rules)

    print("\nExtraction complete!")


if __name__ == "__main__":
    try:
        import pandas, bs4  # noqa
    except ImportError:
        print("Run: pip install pandas openpyxl requests beautifulsoup4 lxml")
        exit(1)
    main()