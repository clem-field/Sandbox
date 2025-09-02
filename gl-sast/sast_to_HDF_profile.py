import locals as var
import libraries as lib


# Load JSON files
def load_json_file(file_path):
    with open(file_path, 'r') as f:
        return lib.json.load(f)

def generate_sha(data: str) -> str:
    """Generate SHA256 hash for profile data"""
    print(f"📝 Signing gl-sast-report")
    return lib.hashlib.sha256(data.encode()).hexdigest() 

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
    duration = lib.datetime.strptime(sast_file["scan"].get("end_time"), "%Y-%m-%dT%H:%M:%S") - lib.datetime.strptime(sast_file["scan"].get("start_time", "%Y-%m-%dT%H:%M:%S"))
    run_time = round((duration.total_seconds() / 86400), 6)
    print(f"⏱️  Duration calculated as {run_time}")
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
                "sha256": str(generate_sha(sast_file)),
                "status": "loaded",
                "summary": "GitLab enriched profile",
                "supports": [
                    {
                        "platform-name": "multiple languages",
                        "release": "1.0"
                    }
                ],
                "title":"GitLab SAST Scan report through enrichment for visualization",
                "version": ""
            }
        ],
        "statistics": {
                    "duration": run_time
                },
        "version": "1.1",
        "passthrough": {
            "auxiliary_data": [
                    {
                        "name": "GitLab SAST Data",
                        "data": {}
                    }
                ]
            }
    }

    controls = []
    print(f"🧭  Started mapping CWE's to Controls")
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
        applicable_platforms = lib.json.dumps(cwe_entry.get('applicable_platforms', [])) if cwe_entry else ''
        potential_mitigations = lib.json.dumps(cwe_entry.get('potential_mitigations', [])) if cwe_entry else vuln.get('solution', '')

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
            "id": cwes[0] if cwes else vuln.get('id', ''),  
            "impact": severity_info['impact'],
            "refs": mapped_identifiers,
            "results": [
                {
                    "code_desc": description,
                    "message": f"Vulnerability Found in source code: {vuln.get('description', '')}",
                    "run_time": runt_time,
                    "start_time": sast_report['scan'].get("start_time", lib.datetime.utcnow().isoformat()+"Z"),
                    "status": severity_info['status']
                }
            ],
            "source_location": {
                "line": {vuln.get('location', {}).get('start_line', 0)},
                "ref": vuln.get('location', {}).get('file', '')
            },
            "tags": {
                "severity": severity_info['severity'],
                "nist": sorted(list(set(nist_controls))),
                "grc": sorted(list(set(grc_controls))),
                "cwe": "CWE-" + cwes[0] if cwes else '',
                "owasp": owasp_ids,
                "cci": [], 
                "category": vuln.get('category', '')
            },
            "title": rule_name,
            "waiver_data": {}
        }
        controls.append(control)

    hdf_output["profiles"][0]["controls"] = controls
    hdf_output["statistics"]["duration"] = run_time * len(controls)  # Scale duration
    return hdf_output

# Save HDF output to a file
def save_hdf_output(hdf_data, output_path):
    print(f"🗄️  Saving HDF Data to {output_path}")
    with open(output_path, 'w') as f:
        lib.json.dump(hdf_data, f, indent=2)

# Main function
def main(sast_file, cwe_file, catalog_file, output_file):
    try:
        sast_report = load_json_file(sast_file)
        print(f"📁  Loaded {sast_file} for gl-sast-report")
        cwe_data = load_json_file(cwe_file)['cwe_data']
        print(f"📁  Loaded {cwe_file} for CWE Data")
        catalog_data = load_json_file(catalog_file)
        print(f"📁  Loaded {catalog_file} for catalog data")
        hdf_data = convert_to_hdf(sast_report, cwe_data, catalog_data)
        save_hdf_output(hdf_data, output_file)
        print(f"Conversion complete. HDF file saved to {output_file}")
    except Exception as e:
        print(f"Error during conversion: {str(e)}")

if __name__ == "__main__":
    sast_file = var.INPUT_FOLDER + "gl-sast-report.json"  # Replace with your GitLab SAST report
    cwe_file = var.INPUT_FOLDER + "sast_cwe.json"         # Provided CWE data
    catalog_file = var.INPUT_FOLDER + "catalog.json"      # Provided NIST catalog
    output_file = var.OUTPUT_FOLDER + "output_hdf.json"    # Desired output file
    main(sast_file, cwe_file, catalog_file, output_file)