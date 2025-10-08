"""
Below is a Python script to convert a CIS Benchmark in Excel (XLSX) format to an XCCDF (Extensible Configuration Checklist Description Format) file compliant with the Security Requirements Guide (SRG) or Security Technical Implementation Guide (STIG) format, suitable for import into MITRE’s Vulcan (part of the Security Automation Framework, SAF). The script assumes the XLSX file follows a typical CIS Benchmark structure (e.g., columns for Rule ID, Title, Description, Rationale, Check Procedure, Remediation, Level, and References) and maps the controls to SRG/STIG identifiers, producing an XCCDF file with NIST SP 800-53 Rev. 4/Rev. 5 references where applicable. The script uses pandas for reading Excel, lxml for generating XCCDF XML, and includes basic validation for Vulcan compatibility.

Assumptions

Input XLSX: The CIS Benchmark Excel file has columns like Rule ID, Title, Description, Rationale, Check Procedure, Remediation, Level, and References (e.g., mapping to NIST 800-53 or SRG IDs).
Output XCCDF: The output is an SCAP-compliant XCCDF file with elements for each control, including SRG/STIG mappings in tags.
Vulcan Compatibility: The XCCDF file includes a profile for CIS Level 3 (STIG-specific) and references SRG/STIG IDs where available.
Dependencies: Requires Python libraries pandas and lxml.
Limitations: Automated check content (e.g., OVAL or SCE scripts) is not generated, as CIS Excel files typically lack executable check logic. Placeholder elements are included, which can be extended manually.
Python Script: `cis_xlsx_to_xccdf.py`
"""
"""#!/usr/bin/env python3"""

import pandas as pd
from lxml import etree
import argparse
import os

def create_xccdf_from_xlsx(xlsx_file, output_file, benchmark_title, benchmark_version, benchmark_id):
    """
    Convert a CIS Benchmark XLSX file to an XCCDF file for SRG/STIG compliance.

    Args:
        xlsx_file (str): Path to the input CIS Benchmark XLSX file.
        output_file (str): Path to the output XCCDF file.
        benchmark_title (str): Title of the CIS Benchmark (e.g., "CIS Docker Benchmark").
        benchmark_version (str): Version of the CIS Benchmark (e.g., "1.6.0").
        benchmark_id (str): Unique ID for the benchmark (e.g., "xccdf_org.cisecurity.benchmarks_benchmark_1.6.0_CIS_Docker_Benchmark").
    """
    # Read Excel file
    try:
        df = pd.read_excel(xlsx_file, engine='openpyxl')
    except Exception as e:
        print(f"Error reading XLSX file: {e}")
        return

    # Validate required columns
    required_columns = ['Rule ID', 'Title', 'Description', 'Rationale', 'Check Procedure', 'Remediation', 'Level', 'References']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        print(f"Missing required columns: {missing}")
        return

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
        rule_id = f"xccdf_org.cisecurity.benchmarks_rule_{row['Rule ID'].replace('.', '_')}"
        rule = etree.SubElement(benchmark, '{http://checklists.nist.gov/xccdf/1.2}Rule',
                                id=rule_id,
                                severity='medium' if row['Level'] == 'Level 3' else 'low')
        
        # Add rule metadata
        etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}title').text = str(row['Title'])
        etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}description').text = str(row['Description'])
        etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}rationale').text = str(row['Rationale'])
        
        # Add check procedure and remediation (in check-content for manual checks)
        check = etree.SubElement(rule, '{http://checklists.nist.gov/xccdf/1.2}check',
                                 system='http://checklists.nist.gov/xccdf/1.2')
        check_content = etree.SubElement(check, '{http://checklists.nist.gov/xccdf/1.2}check-content')
        check_content.text = f"Check Procedure: {row['Check Procedure']}\nRemediation: {row['Remediation']}"
        
        # Add references (e.g., SRG/STIG, NIST 800-53)
        references = str(row['References']).split(',')
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
    
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Input file {args.input} does not exist")
        return

    create_xccdf_from_xlsx(args.input, args.output, args.title, args.version, args.benchmark_id)

if __name__ == '__main__':
    main()

"""Prerequisites

Install Dependencies:
pip install pandas openpyxl lxml

pandas: Reads the XLSX file.
openpyxl: Engine for Excel file parsing.
lxml: Generates and manipulates XML for XCCDF.
Optional: OpenSCAP: Install OpenSCAP for XCCDF validation:
On Ubuntu:
sudo apt-get install libopenscap8

On RedHat/CentOS:
sudo yum install openscap-scanner

Input XLSX File: Ensure the CIS Benchmark XLSX file has the following columns:
Rule ID (e.g., 5.7)
Title (e.g., “Ensure containers run as non-root user”)
Description (e.g., “Containers should not run as root…”)
Rationale (e.g., “Minimizes privilege escalation risks…”)
Check Procedure (e.g., “Check container user in task definition…”)
Remediation (e.g., “Set user to non-root (e.g., nobody)…”)
Level (e.g., “Level 3”)
References (e.g., “SRG-APP-000141, CM-7”)
Example XLSX content (saved as cis_docker_benchmark.xlsx):
Rule ID,Title,Description,Rationale,Check Procedure,Remediation,Level,References
5.7,Ensure containers run as non-root user,"Containers should not run as root...","Minimizes privilege escalation risks...","Check container user in task definition...","Set user to non-root (e.g., nobody)...","Level 3","SRG-APP-000141, CM-7"
5.21,Ensure read-only root filesystem,"Root filesystem should be read-only...","Prevents unauthorized changes...","Verify readOnlyRootFilesystem in task definition...","Set readOnlyRootFilesystem to true...","Level 3","SRG-APP-000133, SC-2"

Vulcan Context:
The script generates an XCCDF file compatible with Vulcan, which expects SCAP 1.2-compliant XML with elements and SRG/STIG references.
The output includes a Level 3 - STIG profile, aligning with STIG-specific controls as per CIS Benchmark recommendations.
How to Use the Script

Save the Script: Save the script as cis_xlsx_to_xccdf.py.
Run the Script: Execute the script with command-line arguments:
python cis_xlsx_to_xccdf.py \
    -i cis_docker_benchmark.xlsx \
    -o cis_docker_xccdf.xml \
    -t "CIS Docker Benchmark" \
    -v "1.6.0" \
    -id "xccdf_org.cisecurity.benchmarks_benchmark_1.6.0_CIS_Docker_Benchmark"

-i: Path to the input XLSX file.
-o: Path to the output XCCDF file (default: cis_benchmark_xccdf.xml).
-t: Benchmark title (default: “CIS Benchmark”).
-v: Benchmark version (default: “1.0.0”).
-id: Unique XCCDF benchmark ID (default: generic ID).
Output: The script generates an XCCDF file (e.g., cis_docker_xccdf.xml) with:
A element containing metadata (title, version, description).
A for Level 3 (STIG-specific) controls.
elements for each CIS control, including title, description, rationale, check procedure, remediation, and references (SRG/STIG IDs, NIST 800-53 controls).
Placeholder elements for manual verification (can be extended with OVAL or SCE scripts).
Example output snippet:
  CIS Docker Benchmark
  1.6.0
  CIS Docker Benchmark for compliance with SRG/STIG requirements, mapped to NIST 800-53 controls.
  
    Level 3 - STIG
    STIG-specific controls for compliance with CIS Benchmark requirements.
    
  
  
    Ensure containers run as non-root user
    Containers should not run as root...
    Minimizes privilege escalation risks...
    
      Check Procedure: Check container user in task definition...

Remediation: Set user to non-root (e.g., nobody)… SRG-APP-000141 CM-7

4. **Validate the XCCDF**:

If OpenSCAP is installed, the script automatically validates the output:

```bash

oscap xccdf validate cis_docker_xccdf.xml

If validation fails, check the XML structure or missing attributes.

Import into Vulcan:
Upload the cis_docker_xccdf.xml file to Vulcan via its interface or API.
Select the xccdf_org.cisecurity.benchmarks_profile_Level_3 profile for STIG-specific assessments.
Run an assessment to verify that controls are correctly interpreted and reported.
Additional Features

Severity Mapping: The script maps CIS Level 3 controls to severity="medium" in XCCDF (per STIG alignment) and other levels to severity="low". Customize this in the script if needed.
References Parsing: The script parses the References column for SRG/STIG IDs (e.g., SRG-APP-000141, V-123456) and NIST 800-53 controls (e.g., CM-7, SC-2), adding them as elements with appropriate href attributes.
Error Handling: Checks for missing columns and file errors, providing clear error messages.
Extensibility: The elements are placeholders for manual checks. To add automated checks (e.g., OVAL), extend the script to generate elements linking to OVAL files.
Limitations

Manual Checks: The script includes check procedures and remediation steps as text in , as CIS Excel files typically lack executable check logic. To add automated checks, pair with tools like inspec_tools to generate InSpec profiles, then convert to XCCDF with OVAL/SCE references.
References Column: Assumes the References column contains comma-separated SRG/STIG IDs and NIST controls. If the format differs (e.g., free text), modify the script’s parsing logic.
Fargate Context: For CIS Docker Benchmarks applied to ECS Fargate, host-level controls (e.g., CIS 1.x, 2.x) may need to be excluded. Create a tailoring file to disable these:
  
    
      Level 3 - STIG for Fargate
      
      
    
  


Dependencies: Requires openpyxl for XLSX files. If using CSV, modify the script to use pd.read_csv() instead.
Customization

Column Names: If your XLSX has different column names, update the required_columns list in the script.
Severity Levels: Adjust the severity mapping (e.g., Level 1 to low, Level 2 to medium, Level 3 to high) based on your requirements.
Automated Checks: To include OVAL or SCE scripts, extend the script to generate elements pointing to external files (e.g., cis_docker_oval.xml).
Benchmark Metadata: Customize benchmark_title, benchmark_version, and benchmark_id via command-line arguments to match your CIS Benchmark (e.g., Docker, Ubuntu).
Testing

Prepare an XLSX File: Create or obtain a CIS Benchmark XLSX file (e.g., cis_docker_benchmark.xlsx) with the required columns. If starting from a PDF, use tools like tabula to extract tables to CSV, then convert to XLSX.
Run the Script:
python cis_xlsx_to_xccdf.py -i cis_docker_benchmark.xlsx -o cis_docker_xccdf.xml -t "CIS Docker Benchmark" -v "1.6.0" -id "xccdf_org.cisecurity.benchmarks_benchmark_1.6.0_CIS_Docker_Benchmark"

Validate Output: Check the generated cis_docker_xccdf.xml for correctness. Use OpenSCAP to validate:
oscap xccdf validate cis_docker_xccdf.xml

Test in Vulcan:
Import the XCCDF file into Vulcan via its interface or API.
Run a test assessment to ensure controls are correctly displayed and mapped to SRG/STIG and NIST 800-53 controls.
Verify that the Level 3 - STIG profile includes the expected rules.
Integration with MITRE Vulcan

Upload to Vulcan: Use Vulcan’s interface to import the XCCDF file. Ensure the ID (xccdf_org.cisecurity.benchmarks_profile_Level_3) is selected for STIG-specific assessments.
Run Assessments: Vulcan will process the XCCDF file and generate compliance reports (e.g., ARF, HTML) based on the rules and profile.
Manual Checks: Since the script includes manual check content, document any manual verification steps in Vulcan for non-automated controls.
Additional Notes

inspec_tools Alternative: If you prefer to generate an InSpec profile first, use inspec_tools to convert the XLSX to InSpec, then to XCCDF:
inspec_tools xls2inspec -x cis_docker_benchmark.xlsx -o inspec_profile
inspec_tools inspec2xccdf -i inspec_profile -o cis_docker_xccdf.xml

This requires inspec_tools (available via MITRE SAF or GitHub: mitre/inspec_tools).
Tailoring for Fargate: For ECS Fargate, exclude host-level controls using a tailoring file or modify the script to filter rules based on the Level or References column.
SRG/STIG Mappings: Ensure the References column includes accurate SRG/STIG IDs (e.g., SRG-APP-000141) or NIST 800-53 controls (e.g., CM-7). If mappings are missing, consult DISA STIGs or NIST 800-53 documentation to add them manually.
This script provides a robust starting point for converting CIS Benchmark XLSX files to XCCDF for Vulcan. If your XLSX file has a non-standard structure or you need specific SRG/STIG mappings, provide details for further customization.
"""