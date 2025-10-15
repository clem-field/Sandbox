import argparse
import re
import pdfplumber
from openpyxl import Workbook

def parse_pdf(input_file, output_file):
    with pdfplumber.open(input_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    lines = full_text.splitlines()

    controls = []
    current_control = None
    current_section = None
    sections = {
        'Profile Applicability:': 'profile',
        'Description:': 'description',
        'Rationale:': 'rationale',
        'Audit:': 'audit',
        'Remediation:': 'remediation',
        'References:': 'references'
    }

    control_pattern = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+?)\s+\((Automated|Manual)\)$')

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = control_pattern.match(line)
        if match:
            if current_control:
                controls.append(current_control)
            control_id, title, _ = match.groups()  # We don't use the assessment status, but it's there
            current_control = {
                'id': control_id,
                'title': title,
                'profile': [],
                'description': [],
                'rationale': [],
                'audit': [],
                'remediation': [],
                'references': []
            }
            current_section = None
        elif current_control:
            if line in sections:
                current_section = sections[line]
                i += 1
                continue
            elif current_section == 'profile':
                if line.startswith('• '):
                    current_control['profile'].append(line[2:].strip())
            elif current_section:
                current_control[current_section].append(line)
        i += 1

    if current_control:
        controls.append(current_control)

    # Process each control
    wb = Workbook()
    ws = wb.active
    headers = ['Control ID', 'Title', 'Profile Applicability', 'Description', 'Rationale', 'Audit', 'Remediation', 'Rev.', 'NIST Controls', 'STIG Finding ID']
    ws.append(headers)

    for control in controls:
        profile_str = ', '.join(control['profile'])
        desc_str = ' '.join(control['description']).strip()
        rat_str = ' '.join(control['rationale']).strip()
        audit_str = ' '.join(control['audit']).strip()
        rem_str = ' '.join(control['remediation']).strip()

        refs = control['references']
        rev = ''
        nist_controls = ''
        stig = ''

        nist_pattern = re.compile(r'NIST SP 800-53 Rev\. (\d+):\s*([\w\- ,()]+)')
        stig_pattern = re.compile(r'STIG Finding ID:\s*(V-\d+)')

        ref_text = ' '.join(refs)
        nist_matches = nist_pattern.findall(ref_text)
        stig_matches = stig_pattern.findall(ref_text)

        if nist_matches:
            rev = nist_matches[0][0]  # Assuming one rev
            nist_controls = ', '.join([m[1].strip() for m in nist_matches])

        if stig_matches:
            stig = ', '.join(stig_matches)

        ws.append([control['id'], control['title'], profile_str, desc_str, rat_str, audit_str, rem_str, rev, nist_controls, stig])

    wb.save(output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse CIS Benchmark PDF to XLSX')
    parser.add_argument('-i', required=True, help='Input PDF file')
    parser.add_argument('-o', required=True, help='Output XLSX file')
    args = parser.parse_args()

    if not args.i.lower().endswith('.pdf'):
        raise ValueError("Input file must be a .pdf file")

    parse_pdf(args.i, args.o)