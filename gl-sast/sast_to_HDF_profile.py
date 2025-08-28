import json
from datetime import datetime

# Load JSON files
def load_json_file(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Map GitLab SAST severity to HDF impact and severity
def map_severity_and_impact(sast_severity):
    severity_map = {
        'Critical': {'severity': 'critical', 'impact': 0.9},
        'High': {'severity': 'high', 'impact': 0.7},
        'Medium': {'severity': 'medium', 'impact': 0.5},
        'Low': {'severity': 'low', 'impact': 0.3},
        'Info': {'severity': 'info', 'impact': 0.1},
        'Unknown': {'severity': 'unknown', 'impact': 0.0}
    }
    return severity_map.get(sast_severity, {'severity': 'unknown', 'impact': 0.0})

# Normalize NIST control ID for matching (e.g., 'AC-1(a)' -> 'AC-01(a)')
def normalize_nist_control(control_id):
    return control_id.replace('AC-', 'AC-0').replace('(A)', '(a)').replace('(B)', '(b)')

# Get NIST controls for a CWE using sast_cwe.json and catalog.json
def get_nist_controls(cwe_id, cwe_data, catalog_data):
    nist_controls = set()
    cwe_id = cwe_id.replace('CWE-', '')  # Normalize (e.g., 'CWE-614' -> '614')
    
    # Find CWE entry in sast_cwe.json
    cwe_entry = next((entry for entry in cwe_data if entry['id'] == cwe_id), None)
    if not cwe_entry:
        return []
    
    # Get rev4_controls and rev5_controls
    controls = cwe_entry.get('rev4_controls', []) + cwe_entry.get('rev5_controls', [])
    if not controls:
        return []
    
    # Match controls against catalog.json
    for control in controls:
        normalized_control = normalize_nist_control(control)
        # Check catalog for matching nist_control or tags['nist']
        for catalog_entry in catalog_data:
            catalog_nist = normalize_nist_control(catalog_entry.get('nist_control', ''))
            catalog_tags_nist = [normalize_nist_control(n) for tag in catalog_entry.get('tags', []) for n in tag.get('nist', [])]
            if normalized_control == catalog_nist or normalized_control in catalog_tags_nist:
                nist_controls.add(normalized_control)
    
    return sorted(list(nist_controls))  # Return sorted for consistency

# Convert GitLab SAST report to profile-like HDF
def convert_to_hdf(sast_report, cwe_data, catalog_data):
    hdf_output = {
        "version": "1.0",
        "profile_name": "GitLab SAST Profile",
        "sha256": "placeholder_sha256",
        "metadata": {
            "tool": "GitLab SAST",
            "version": sast_report.get("version", "unknown"),
            "generated": datetime.utcnow().isoformat() + "Z"
        },
        "controls": [],
        "statistics": {
            "duration": "unknown",
            "total_controls": 0
        }
    }

    controls = []
    for vuln in sast_report.get("vulnerabilities", []):
        severity_info = map_severity_and_impact(vuln.get("severity", "Unknown"))
        cwes = vuln.get("cwe", [])  # List of CWEs (e.g., ['CWE-614'])
        nist_controls = []
        for cwe in cwes:
            nist_controls.extend(get_nist_controls(cwe, cwe_data, catalog_data))

        # Map identifiers
        identifiers = vuln.get("identifiers", [])
        mapped_identifiers = [
            {
                "type": ident.get("type", ""),
                "name": ident.get("name", ""),
                "value": ident.get("value", ""),
                "url": ident.get("url", "")
            } for ident in identifiers
        ]

        control = {
            "id": vuln.get("id", ""),
            "title": vuln.get("name", ""),
            "desc": vuln.get("description", ""),
            "impact": severity_info['impact'],
            "tags": {
                "cwe": cwes,
                "nist": nist_controls,  # Populated from sast_cwe.json and catalog.json
                "severity": severity_info['severity']
            },
            "refs": mapped_identifiers,
            "source_location": {
                "file": vuln.get("location", {}).get("file", ""),
                "line": vuln.get("location", {}).get("start_line", 0)
            },
            "results": [
                {
                    "status": "failed",
                    "code_desc": f"Vulnerability detected in {vuln.get('location', {}).get('file', '')}",
                    "run_time": 0.0,
                    "start_time": datetime.utcnow().isoformat() + "Z",
                    "message": vuln.get("solution", "") or vuln.get("description", "")
                }
            ]
        }
        controls.append(control)

    hdf_output["controls"] = controls
    hdf_output["statistics"]["total_controls"] = len(controls)
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