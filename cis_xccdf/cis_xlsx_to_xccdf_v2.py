#!/usr/bin/env python3

import pandas as pd
from lxml import etree
import argparse
import os
import yaml

def create_xccdf_from_xlsx(xlsx_file, output_file, benchmark_title, benchmark_version, benchmark_id, mapping_file=None):
    """
    Convert a CIS Benchmark XLSX file to an XCCDF file for SRG/STIG compliance.

    Args:
        xlsx_file (str): Path to the input CIS Benchmark XLSX file.
        output_file (str): Path to the output XCCDF file.
        benchmark_title (str): Title of the CIS Benchmark (e.g., "CIS Docker Benchmark").
        benchmark_version (str): Version of the CIS Benchmark (e.g., "1.6.0").
        benchmark_id (str): Unique ID for the benchmark (e.g., "xccdf_org.cisecurity.benchmarks_benchmark_1.6.0_CIS_Docker_Benchmark").
        mapping_file (str, optional): Path to the YAML mapping file for column names.
    """
    # Read Excel file
    try:
        df = pd.read_excel(xlsx_file, engine='openpyxl')
    except Exception as e:
        print(f"Error reading XLSX file: {e}")
        return

    # Load mapping if provided, else use defaults
    if mapping_file:
        try:
            with open(mapping_file, 'r') as f:
                mapping = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading YAML mapping file: {e}")
            return
    else:
        mapping = {
            'id': ['Rule ID'],
            'title': ['Title'],
            'desc': ['Description'],
            'desc.rationale': ['Rationale'],
            'desc.check': ['Check Procedure'],
            'desc.fix': ['Remediation'],
            'level': ['Level'],
            'ref': ['References']
        }

    # Function to get the actual column name from possible names
    def get_column_name(possible_names, required=True):
        if isinstance(possible_names, str):  # Handle fixed values if needed
            possible_names = [possible_names]
        for name in possible_names:
            if name in df.columns:
                return name
        if required:
            print(f"Missing required column for {possible_names}")
            raise ValueError(f"No matching column found for {possible_names}")
        return None

    # Resolve column names using the mapping
    try:
        id_col = get_column_name(mapping.get('id', ['Rule ID']))
        title_col = get_column_name(mapping.get('title', ['Title']))
        desc_col = get_column_name(mapping.get('desc', ['Description']))
        rationale_col = get_column_name(mapping.get('desc.rationale', ['Rationale']))
        check_col = get_column_name(mapping.get('desc.check', ['Check Procedure']))
        fix_col = get_column_name(mapping.get('desc.fix', ['Remediation']))
        level_col = get_column_name(mapping.get('level', ['Level']))
        ref_col = get_column_name(mapping.get('ref', ['References']))
    except ValueError as e:
        print(e)
        return

    # Handle optional fixed values from mapping (e.g., impact for severity adjustment)
    default_impact = mapping.get('impact', None)  # If provided, can use for severity

    # Create XCCDF root
    nsmap = {
        'xccdf': 'http://checklists.nist.gov/xccdf/1.2',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }
    benchmark = etree.Element('{http://checklists.nist.gov/xccdf/1.2}Benchmark',
                             id=benchmark_id,
                             nsmap=nsmap,
                             attrib={'{http://www.w3.org/2001/XMLSchema-instance}schemaLocation':
                                    'http://checklists.nist.gov/xccdf/1.2 xccdf-1.2.xsd'})
    
    # Add metadata
    etree.SubElement(benchmark, '{http://checklists.nist.gov/xccdf/1.2}title').text = benchmark_title
    etree.SubElement(benchmark, '{http://checklists.nist.gov/xccdf/1.2}version').text = benchmark_version
    etree.SubElement(benchmark, '{http://checklists.nist.gov/xccdf/1.2}description').text = (
        f"{benchmark_title} for compliance with SRG/STIG requirements, mapped to NIST 800-53 controls."
    )

    # Create STIG-specific profile
    profile = etree.SubElement(benchmark, '{http://checklists.nist.gov/xccdf/1.2}Profile',
                              id='xccdf_org.cisecurity.benchmarks_profile_Level_3')
    etree.SubElement(profile, '{http://checklists.nist.gov/xccdf/1.2}title').text = 'Level 3 - STIG'
    etree.SubElement(profile, '{http://checklists.nist.gov/xccdf/1.2}description').text = (
        'STIG-specific controls for compliance with CIS Benchmark requirements.'
    )

    # Process each rule
    for index, row in df.iterrows():
        # Skip rows with missing title or description
        if pd.isna(row[title_col]) or pd.isna(row[desc_col]):
            continue

        rule_id_value = str(row[id_col]).strip().replace('.', '_') or f"rule_{index}"
        rule_id = f"xccdf_org.cisecurity.benchmarks_rule_{rule_id_value}"
        
        # Determine severity: Use level if available, else fallback to default impact if provided
        if level_col:
            level_value = str(row[level_col])
            severity = 'medium' if level_value == 'Level 3' else 'low'
        elif default_impact is not None:
            severity = 'high' if default_impact >= 0.7 else 'medium' if default_impact >= 0.4 else 'low'
        else:
            severity = 'low'  # Default if neither is available
        
        rule = etree.SubElement(benchmark, '{http://checklists.nist.gov/xccdf/1.2}Rule',
                                id=rule_id,
                                severity=severity)
        
        # Safe text population
        def safe_text(val, fallback="N/A"):
            return etree.CDATA(str(val).strip() or fallback)
        
        # Add rule metadata
        title_elem = etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}title')
        title_elem.text = safe_text(row[title_col], "Untitled Rule")
        
        desc_elem = etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}description')
        desc_elem.text = safe_text(row[desc_col], "No description available.")
        
        rationale_elem = etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}rationale')
        rationale_elem.text = safe_text(row[rationale_col], "No rationale provided.")
        
        # Add check procedure and remediation (in check-content for manual checks)
        check = etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}check',
                                 system='http://checklists.nist.gov/xccdf/1.2')
        check_content = etree.SubElement(check, '{http://checklists.nist.gov/xccdf/1.2}check-content')
        check_content.text = safe_text(
            f"Check Procedure: {row[check_col]}\nRemediation: {row[fix_col]}",
            "Check Procedure: Manual check required.\nRemediation: Apply remediation as per description."
        )
        
        # Add references (e.g., SRG/STIG, NIST 800-53)
        references = str(row[ref_col]).split(',') if not pd.isna(row[ref_col]) else []
        for ref in references:
            ref = ref.strip()
            if ref.startswith('SRG-') or ref.startswith('V-'):
                etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}reference',
                                href=f"https://www.stigviewer.com/stig/{ref}").text = ref
            elif ref.startswith('CM-') or ref.startswith('AC-'):  # NIST 800-53 controls
                etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}reference',
                                href="http://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf").text = ref
        
        # Add rule to profile
        etree.SubElement(profile, '{http://checklists.nist.gov/xccdf/1.2}select',
                         idref=rule_id, selected='true')
        
        # Add status for completeness
        etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}status').text = 'draft'

    # Save XCCDF file
    try:
        tree = etree.ElementTree(benchmark)
        tree.write(output_file)
        print(f"XCCDF file written to {output_file}")
        
        # Validate XCCDF
        try:
            import subprocess
            result = subprocess.run(['oscap', 'xccdf', 'validate', output_file], capture_output=True, text=True)
            if result.returncode == 0:
                print("XCCDF validation successful")
            else:
                print(f"XCCDF validation failed: {result.stderr}")
        except FileNotFoundError:
            print("OpenSCAP not installed; skipping validation")
    except Exception as e:
        print(f"Error writing XCCDF file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Convert CIS Benchmark XLSX to SRG/STIG-compliant XCCDF for MITRE Vulcan")
    parser.add_argument('-i', '--input', required=True, help='Path to CIS Benchmark XLSX file')
    parser.add_argument('-o', '--output', default='cis_benchmark_xccdf.xml', help='Path to output XCCDF file')
    parser.add_argument('-t', '--title', default='CIS Benchmark', help='Title of the CIS Benchmark')
    parser.add_argument('-v', '--version', default='1.0.0', help='Version of the CIS Benchmark')
    parser.add_argument('-id', '--benchmark-id', default='xccdf_org.cisecurity.benchmarks_benchmark_1.0.0',
                        help='Unique ID for the XCCDF Benchmark')
    parser.add_argument('-m', '--mapping', default=None, help='Path to YAML mapping file for column names')
    
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file {args.input} does not exist")
        return

    if args.mapping and not os.path.exists(args.mapping):
        print(f"Mapping file {args.mapping} does not exist")
        return

    create_xccdf_from_xlsx(args.input, args.output, args.title, args.version, args.benchmark_id, args.mapping)

if __name__ == '__main__':
    main()