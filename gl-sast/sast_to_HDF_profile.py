import json
from datetime import datetime

# Load JSON files
def load_json_file(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Map GitLab SAST severity to HDF impact and severity
def map_severity_and_impact(sast_severity):
    severity_map = {
        'Critical': {'severity': 'critical', 'impact': 0.9, 'status': 'failed'},
        'High': {'severity': 'high', 'impact': 0.7, 'status': 'failed'},
        'Medium': {'severity': 'medium', 'impact': 0.5, 'status': 'failed'},
        'Low': {'severity': 'low', 'impact': 0.3, 'status': 'passed'},
        'Info': {'severity': 'info', 'impact': 0.1, 'status': 'passed'},
        'Unknown': {'severity': 'unknown', 'impact': 0.0, 'status': 'passed'}
    }
    return severity_map.get(sast_severity, {'severity': 'unknown', 'impact': 0.0, 'status': 'passed'})

# Normalize NIST control ID for matching
def normalize_nist_control(control_id):
    return control_id.replace('AC-', 'AC-0').replace('(A)', '(a)').replace('(B)', '(b)')

# Get NIST and GRC controls for a CWE using sast_cwe.json and catalog.json
def get_nist_and_grc_controls(cwe_id, cwe_data, catalog_data):
    nist_controls = set()
    grc_controls = set()
    cwe_id = cwe_id.replace('CWE-', '')  # Normalize (e.g., 'CWE-614' -> '614')
    
    # Find CWE entry in sast_cwe.json
    cwe_entry = next((entry for entry in cwe_data if entry['id'] == cwe_id), None)
    if not cwe_entry:
        return [], [], cwe_entry
    
    # Get rev4_controls and rev5_controls
    controls = cwe_entry.get('rev4_controls', []) + cwe_entry.get('rev5_controls', [])
    
    # Match controls against catalog.json
    for control in controls:
        normalized_control = normalize_nist_control(control)
        for catalog_entry in catalog_data:
            catalog_nist = normalize_nist_control(catalog_entry.get('nist_control', ''))
            catalog_tags_nist = [normalize_nist_control(n) for tag in catalog_entry.get('tags', []) for n in tag.get('nist', [])]
            if normalized_control == catalog_nist or normalized_control in catalog_tags_nist:
                nist_controls.add(normalized_control)
                # Add GRC from catalog
                for tag in catalog_entry.get('tags', []):
                    if tag.get('grc'):
                        grc_controls.add(tag['grc'])
    
    return sorted(list(nist_controls)), sorted(list(grc_controls)), cwe_entry

# Convert GitLab SAST report to HDF per the schema
def convert_to_hdf(sast_report, cwe_data, catalog_data):
    hdf_output = {
        "platform": {
            "name": "GitLab",
            "release": "1"
        },
        "profiles": [
            {
                "attributes": [],
                "controls": [],
                "copyright": "",
                "copyright_email": "",
                "groups": [],
                "license": "Apache-2.0",
                "maintainer": "",
                "name": "GitLab SAST Scanning Profile",
                "sha256": "placeholder_sha256",
                "status": "loaded",
                "summary": "GitLab enriched profile",
                "supports": [{
                    "platform-name": "multiple languages",
                    "release": "1.0"
                }],
                "statistics": {
                    "duration": 0.000139
                },
                "version": "",
                "passthrough": {
                    "auxiliary_data": [
                        {
                            "name": "GitLab SAST Data",
                            "data": {}
                        }
                    ]
                }
            }
        ]
    }

    controls = []
    for vuln in sast_report.get("vulnerabilities", []):
        severity_info = map_severity_and_impact(vuln.get("severity", "Unknown"))
        cwes = vuln.get("cwe", []) or [ident['value'] for ident in vuln.get("identifiers", []) if ident.get('type') == 'cwe']
        nist_controls = []
        grc_controls = []
        cwe_entry = None

        # Get NIST and GRC controls for each CWE
        for cwe in cwes:
            nist, grc, entry = get_nist_and_grc_controls(cwe, cwe_data, catalog_data)
            nist_controls.extend(nist)
            grc_controls.extend(grc)
            if entry and not cwe_entry:  # Use first matching CWE entry
                cwe_entry = entry

        # Map identifiers, extract OWASP
        identifiers = vuln.get("identifiers", [])
        mapped_identifiers = [
            {
                "url": ident.get("url", "")
            } for ident in identifiers
        ]
        owasp_ids = [ident['value'] for ident in identifiers if ident.get('type') == 'owasp']

        # Build code and descriptions from cwe_entry or fallback to vuln data
        rule_name = cwe_entry.get('rule_name', vuln.get('name', '')) if cwe_entry else vuln.get('name', '')
        description = cwe_entry.get('description', vuln.get('description', '')) if cwe_entry else vuln.get('description', '')
        extended_description = cwe_entry.get('extended_description', '') if cwe_entry else ''
        applicable_platforms = json.dumps(cwe_entry.get('applicable_platforms', [])) if cwe_entry else ''
        potential_mitigations = json.dumps(cwe_entry.get('potential_mitigations', [])) if cwe_entry else vuln.get('solution', '')

        control = {
            "code": f"{rule_name} {description} {applicable_platforms}",
            "desc": description,
            "descriptions": [
                {
                    "data": rule_name,
                    "label": "default"
                },
                {
                    "data": extended_description,
                    "label": "check"
                },
                {
                    "data": potential_mitigations,
                    "label": "fix"
                }
            ],
            "id": cwes[0] if cwes else vuln.get('id', ''),  # Use first CWE or fallback to vuln ID
            "impact": severity_info['impact'],
            "refs": mapped_identifiers,
            "results": [
                {
                    "code_desc": description,
                    "message": f"Vulnerability Found in source code: {vuln.get('description', '')}",
                    "run_time": 0.0,  # Placeholder; GitLab SAST doesn't provide start_time
                    "status": severity_info['status']
                }
            ],
            "source_location": {
                "line": f"{vuln.get('location', {}).get('start_line', '')}/{vuln.get('location', {}).get('end_line', '')}",
                "ref": vuln.get('location', {}).get('file', '')
            },
            "tags": {
                "severity": severity_info['severity'],
                "nist": sorted(list(set(nist_controls))),
                "grc": sorted(list(set(grc_controls))),
                "cwe": cwes[0] if cwes else '',
                "owasp": owasp_ids,
                "cci": [],  # Placeholder; requires external CCI-to-NIST mapping
                "category": vuln.get('category', '')
            },
            "title": rule_name,
            "waiver_data": {}
        }
        controls.append(control)

    hdf_output["profiles"][0]["controls"] = controls
    hdf_output["profiles"][0]["statistics"]["duration"] = 0.000139 * len(controls)  # Scale duration
    return hdf_output

# Save HDF output to a file
def save_hdf_output(hdf_data, output_path):
    with open(output_path, 'w') as f:
        json.dump(hdf_data, f, indent=2)

# Main function
def main(sast_file, cwe_file, catalog_file, output_file):
    try:
        sast_report = load_json_file(sast_file)
        cwe_data = load_json_file(cwe_file)['cwe_data']
        catalog_data = load_json_file(catalog_file)
        hdf_data = convert_to_hdf(sast_report, cwe_data, catalog_data)
        save_hdf_output(hdf_data, output_file)
        print(f"Conversion complete. HDF file saved to {output_file}")
    except Exception as e:
        print(f"Error during conversion: {str(e)}")

if __name__ == "__main__":
    sast_file = "gl-sast-report.json"  # Replace with your GitLab SAST report
    cwe_file = "sast_cwe.json"         # Provided CWE data
    catalog_file = "catalog.json"      # Provided NIST catalog
    output_file = "output_hdf.json"    # Desired output file
    main(sast_file, cwe_file, catalog_file, output_file)