#!/usr/bin/env python3
"""
cis_to_xccdf.py - Convert CIS JSON Benchmark → DISA-style XCCDF Manual STIG

Usage:
    python cis_to_xccdf.py -i cis_benchmark.json -o U_CIS_Win2019_V3R1_Manual-xccdf.xml \
        -t "CIS Microsoft Windows Server 2019 Benchmark" \
        -b "CIS_Windows_Server_2019" -v 3 \
        -r "Release: 1 Benchmark Date: 22 Jul 2025" \
        -m mapping.yaml --start-vid 500000

Features:
  • Full XCCDF 1.1 compliance
  • Stable, sequential V-IDs and SV-IDs
  • Multiple Profile support (L1 DC, L1 MS, L2, etc.)
  • YAML mapper for severity, profile IDs, CCIs, skips, etc.
  • Manual check references (like DISA)
"""

import argparse
import json
import yaml
import hashlib
from lxml import etree
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# Configuration & Defaults
# ----------------------------------------------------------------------
NS = {
    None: "http://checklists.nist.gov/xccdf/1.1",
    "dc": "http://purl.org/dc/elements/1.1/",
    "xhtml": "http://www.w3.org/1999/xhtml"
}

XCCDF_HEADER = """<?xml version="1.0" encoding="utf-8"?>
<?xml-stylesheet type='text/xsl' href='STIG_unclass.xsl'?>
"""

def register_namespaces():
    for prefix, uri in NS.items():
        etree.register_namespace(prefix, uri)

register_namespaces()

# ----------------------------------------------------------------------
# Main Converter Class
# ----------------------------------------------------------------------
class CIStoXCCDF:
    def __init__(self, args, mapper):
        self.args = args
        self.mapper = mapper or {}
        self.vid_counter = args.start_vid
        self.svid_counter = args.start_vid
        self.rule_revision = 1
        self.profiles = {}

    def next_vid(self):
        vid = self.vid_counter
        self.vid_counter += 1
        return f"V-{vid}"

    def next_svid(self):
        svid = self.svid_counter
        self.svid_counter += 1
        return f"SV-{svid}r{self.rule_revision}_rule"

    def next_fix_id(self, vid):
        return f"F-{vid[2:]}r{self.rule_revision}_fix"

    def next_check_id(self, vid):
        return f"C-{vid[2:]}r{self.rule_revision}_chk"

    def create_benchmark(self):
        benchmark = etree.Element("Benchmark", 
            id=self.args.benchmark_id,
            xmlns="http://checklists.nist.gov/xccdf/1.1",
            **{"{http://www.w3.org/XML/1998/namespace}lang": "en"}
        )

        etree.SubElement(benchmark, "status").text = "accepted"
        etree.SubElement(benchmark, "title").text = self.args.title
        etree.SubElement(benchmark, "description").text = (
            "This is an automatically generated XCCDF representation of the CIS "
            f"{self.args.title} v{self.args.version}."
        )
        etree.SubElement(benchmark, "version").text = str(self.args.version)
        etree.SubElement(benchmark, "plain-text", id="release-info").text = self.args.release_info

        ref = etree.SubElement(benchmark, "reference")
        publisher = etree.SubElement(ref, "{http://purl.org/dc/elements/1.1/}publisher")
        publisher.text = self.mapper.get("metadata", {}).get("publisher", "Center for Internet Security")
        source = etree.SubElement(ref, "{http://purl.org/dc/elements/1.1/}source")
        source.text = "CIS"
        identifier = etree.SubElement(ref, "{http://purl.org/dc/elements/1.1/}identifier")
        identifier.text = str(self.mapper.get("metadata", {}).get("dc_identifier", "3000"))

        return benchmark

    def create_profile(self, profile_name):
        profile_id = self.mapper["profiles"].get(profile_name, profile_name.replace(" ", "_").replace("-", "_"))
        if profile_id in self.profiles:
            return self.profiles[profile_id]

        profile = etree.Element("Profile", id=profile_id)
        title = etree.SubElement(profile, "title")
        title.text = profile_name
        desc = etree.SubElement(profile, "description")
        desc.text = f"CIS Profile: {profile_name}"
        self.profiles[profile_id] = profile
        return profile

    def build_rule(self, rec, vid):
        rule = etree.Element("Rule", 
            id=self.next_svid(),
            severity=self.get_severity(rec),
            weight="10.0"
        )

        etree.SubElement(rule, "version").text = rec["recommendation"]
        title = etree.SubElement(rule, "title")
        title.text = rec["title"]

        # Description with proper XCCDF sections
        desc = etree.SubElement(rule, "description")
        vuln = etree.SubElement(desc, "VulnDiscussion")
        vuln.text = (rec.get("description", "") + "\n\n" + 
                    rec.get("rational_statement", "") + "\n\n" + 
                    rec.get("impact_statement", "")).strip()

        # CCI (optional)
        ccis = self.mapper.get("cci_mappings", {}).get(rec["recommendation"], [])
        for cci in ccis:
            ident = etree.SubElement(rule, "ident", system="http://cyber.mil/cci")
            ident.text = cci

        # Fixtext & Fix
        fixtext = etree.SubElement(rule, "fixtext", fixref=self.next_fix_id(vid))
        fixtext.text = rec.get("remediation_procedure", "No remediation procedure provided.").strip()

        fix = etree.SubElement(rule, "fix", id=self.next_fix_id(vid))

        # Check (manual)
        check = etree.SubElement(rule, "check", system=self.next_check_id(vid))
        check_content_ref = etree.SubElement(check, "check-content-ref",
            href=self.mapper.get("check_content_href", "CIS_Manual_Checks.xml"),
            name="M"
        )

        return rule

    def get_severity(self, rec):
        level = "Level 1" if "L1" in rec["title"] else "Level 2" if "L2" in rec["title"] else "Level 1"
        return self.mapper.get("severity", {}).get(level, "medium")

    def process_recommendation(self, rec, benchmark):
        rec_id = rec["recommendation"]
        if rec_id in self.mapper.get("skip", []):
            return None, None

        vid = self.next_vid()
        group = etree.Element("Group", id=vid)
        group_title = etree.SubElement(group, "title")
        group_title.text = rec_id

        rule = self.build_rule(rec, vid)
        group.append(rule)

        # Add to profiles
        profile_name = rec.get("profile", "Unknown")
        profile = self.create_profile(profile_name)
        select = etree.SubElement(profile, "select", idref=vid, selected="true")

        return group, profile

    def convert(self, cis_data):
        benchmark = self.create_benchmark()

        for section in cis_data.get("sections", []):
            for rec in section.get("recommendations", []):
                group, profile = self.process_recommendation(rec, benchmark)
                if group:
                    benchmark.append(group)
                if profile and profile not in benchmark:
                    benchmark.append(profile)

        return benchmark

# ----------------------------------------------------------------------
# Main CLI
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Convert CIS JSON → DISA XCCDF Manual STIG")
    parser.add_argument("-i", "--input", required=True, help="Input CIS JSON file")
    parser.add_argument("-o", "--output", required=True, help="Output XCCDF XML file")
    parser.add_argument("-t", "--title", required=True, help="Benchmark title")
    parser.add_argument("-b", "--benchmark-id", required=True, help="XCCDF Benchmark id")
    parser.add_argument("-v", "--version", type=int, required=True, help="Benchmark version")
    parser.add_argument("-r", "--release-info", required=True, help="Release info text")
    parser.add_argument("-m", "--mapper", help="YAML mapping config file")
    parser.add_argument("--start-vid", type=int, default=500000, help="Starting V-ID (default: 500000)")
    parser.add_argument("--start-svid", type=int, default=500000, help="Starting SV-ID base")

    args = parser.parse_args()

    # Load mapper
    mapper = {}
    if args.mapper and Path(args.mapper).exists():
        with open(args.mapper, "r", encoding="utf-8") as f:
            mapper = yaml.safe_load(f) or {}

    # Load CIS JSON
    with open(args.input, "r", encoding="utf-8") as f:
        cis_data = json.load(f)

    # Convert
    converter = CIStoXCCDF(args, mapper)
    converter.vid_counter = args.start_vid
    converter.svid_counter = args.start_svid

    benchmark = converter.convert(cis_data)

    # Write output
    tree = etree.ElementTree(benchmark)
    with open(args.output, "wb") as f:
        f.write(XCCDF_HEADER.encode("utf-8"))
        tree.write(f, pretty_print=True, encoding="utf-8", xml_declaration=False)

    print(f"Success: Converted {len(cis_data.get('sections', []))} sections → {args.output}")
    print(f"   V-IDs: V-{args.start_vid} → V-{converter.vid_counter-1}")
    print(f"   Profiles: {len(converter.profiles)} created")

if __name__ == "__main__":
    main()