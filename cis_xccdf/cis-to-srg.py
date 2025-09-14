import pandas as pd

cis_df = pd.read_excel('cis_benchmark.xlsx')
srg_df = pd.DataFrame(columns=['SRGID', 'Requirement', 'Severity', 'Discussion', 'Check', 'Fix', 'CCI'])  # Add more as needed

srg_df['SRGID'] = 'CIS-' + cis_df['Section'].astype(str)
srg_df['Requirement'] = cis_df['Title']
srg_df['Severity'] = cis_df['Profile Applicability'].map({'Level 1': 'Medium', 'Level 2': 'Low'})
srg_df['Discussion'] = cis_df['Rationale'] + ' ' + cis_df['Impact']
srg_df['Check'] = cis_df['Audit']
srg_df['Fix'] = cis_df['Remediation']
srg_df['CCI'] = cis_df['References'].str.extract(r'(CCI-\d+)', expand=False)  # Extract if present

srg_df.to_excel('converted_srg.xlsx', index=False)

# option 2
import pandas as pd
from lxml import etree as ET
import datetime

# Read the CIS Benchmark XLSX
cis_file = 'cis_benchmark.xlsx'  # Replace with your CIS XLSX file path
cis_df = pd.read_excel(cis_file)

# Initialize XCCDF XML structure
xccdf_ns = 'http://checklists.nist.gov/xccdf/1.2'
nsmap = {
    'xccdf': xccdf_ns,
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'dc': 'http://purl.org/dc/elements/1.1/'
}
root = ET.Element('{' + xccdf_ns + '}Benchmark', id='CIS-Benchmark', nsmap=nsmap)
root.set('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', 
         'http://checklists.nist.gov/xccdf/1.2 xccdf_1.2.xsd')

# Add Benchmark metadata
ET.SubElement(root, 'status', date=str(datetime.date.today())).text = 'accepted'
ET.SubElement(root, 'title').text = 'CIS Benchmark XCCDF'
ET.SubElement(root, 'description').text = 'XCCDF generated from CIS Benchmark XLSX'
ET.SubElement(root, 'version').text = '1.0'

# Group controls by Section (e.g., 1.1, 1.2) for XCCDF <Group>
groups = cis_df.groupby('Section')

for section, group_data in groups:
    # Create a <Group> for each section
    group = ET.SubElement(root, 'Group', id=f'group-{section.replace(".", "-")}')
    ET.SubElement(group, 'title').text = f'Section {section}'

    for _, row in group_data.iterrows():
        # Create a <Rule> for each control
        rule_id = f'rule-{str(row["Section"]).replace(".", "-")}'
        severity_map = {'Level 1': 'medium', 'Level 2': 'low', 'Level 1 + BitLocker': 'medium'}
        rule = ET.SubElement(group, 'Rule', id=rule_id, severity=severity_map.get(row.get('Profile Applicability', 'Level 1'), 'medium'))
        
        # Add Rule details
        ET.SubElement(rule, 'title').text = str(row['Title'])
        
        # Combine Description, Rationale, Impact into <description>
        description = f"{row.get('Description', '')}\nRationale: {row.get('Rationale', '')}\nImpact: {row.get('Impact', '')}"
        ET.SubElement(rule, 'description').text = description.strip()
        
        # Add <check> for Audit
        check = ET.SubElement(rule, 'check', system='http://open-scap.org')
        ET.SubElement(check, 'check-content').text = str(row.get('Audit', ''))
        
        # Add <fix> for Remediation
        ET.SubElement(rule, 'fix').text = str(row.get('Remediation', ''))
        
        # Add <reference> for References (e.g., NIST CCI)
        references = str(row.get('References', ''))
        if 'CCI-' in references:
            for ref in references.split(','):
                if 'CCI-' in ref:
                    ET.SubElement(rule, 'reference').text = ref.strip()

# Write to XCCDF XML file
output_file = 'cis_benchmark.xccdf.xml'
tree = ET.ElementTree(root)
tree.write(output_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')
print(f"XCCDF file generated: {output_file}")