import json
import hashlib
import datetime
from collections import Counter, defaultdict
try:
    import yaml
except ImportError:
    yaml = None

# Set up logging (assuming no logging module, use print for errors)
def print_error(msg):
    print(f"ERROR: {msg}")

# Load JSON files
def load_json_file(file_path, content=None):
    if content:
        return json.loads(content)
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print_error(f"Error loading JSON file {file_path}: {str(e)}")
        raise

def generate_sha(data):
    """Generate SHA256 hash for profile data"""
    print(f"📝 Signing gl-sast-report")
    serialized_data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(serialized_data.encode()).hexdigest()

def load_yaml_file(file_path, content=None):
    if not yaml:
        print("❌ PyYAML module not found. Using default thresholds.")
        return {
            'passed': {
                'info': True,
                'low': True,
                'medium': True,
                'high': False,
                'critical': False,
                'unknown': True
            },
            'failed': {
                'critical': {'max': 0},
                'high': {'max': 1},
                'medium': {'max': 10},
                'low': {'max': 25},
                'unknown': {'max': 15}
            }
        }
    try:
        if content:
            return yaml.safe_load(content) or {'passed': {}, 'failed': {}}
        with open(file_path, 'r') as f:
            print(f"📂 Loaded {file_path} for risk tolerance")
            return yaml.safe_load(f) or {'passed': {}, 'failed': {}}
    except Exception as e:
        print(f"❌ Error loading YAML file {file_path}: {str(e)}")
        return {
            'passed': {
                'info': True,
                'low': True,
                'medium': True,
                'high': False,
                'critical': False,
                'unknown': True
            },
            'failed': {
                'critical': {'max': 0},
                'high': {'max': 1},
                'medium': {'max': 10},
                'low': {'max': 25},
                'unknown': {'max': 15}
            }
        }

# Map GitLab SAST severity to HDF impact and severity
def map_severity_and_impact(sast_severity, thresholds):
    severity_map = {
        'Critical': {'severity': 'critical', 'impact': 0.9},
        'High': {'severity': 'high', 'impact': 0.7},
        'Medium': {'severity': 'medium', 'impact': 0.5},
        'Low': {'severity': 'low', 'impact': 0.3},
        'Info': {'severity': 'info', 'impact': 0.1},
        'Unknown': {'severity': 'unknown', 'impact': 0.5}
    }
    info = severity_map.get(sast_severity, {'severity': 'unknown', 'impact': 0.5})
    passed_rules = thresholds.get('passed', {})
    status = 'passed' if passed_rules.get(info['severity'], False) else 'failed'
    info['status'] = status
    return info

# Normalize NIST control ID for matching
def normalize_nist_control(control_id):
    return control_id.replace('AC-', 'AC-0').replace('(A)', '(a)').replace('(B)', '(b)')

# Get NIST and GRC controls for a CWE using sast_cwe.json and catalog.json
def get_nist_and_grc_controls(cwe_id, cwe_data, catalog_data):
    nist_controls = set()
    grc_controls = set()
    org_refs = set()
    nist_references = set()
    related_controls = set()
    cwe_id = cwe_id.replace('CWE-', '')
    
    cwe_entry = next((entry for entry in cwe_data if entry['id'] == cwe_id), None)
    if not cwe_entry:
        print(f"⚠️ CWE {cwe_id} not found in sast_cwe.json")
        return [], [], [], [], [], cwe_entry
    
    controls = cwe_entry.get('rev4_controls', []) + cwe_entry.get('rev5_controls', [])
    
    for control in controls:
        normalized_control = normalize_nist_control(control)
        for catalog_entry in catalog_data:
            catalog_nist = normalize_nist_control(catalog_entry.get('nist_control', ''))
            catalog_tags_nist = [normalize_nist_control(n) for tag in catalog_entry.get('tags', []) for n in tag.get('nist', [])]
            if normalized_control == catalog_nist or normalized_control in catalog_tags_nist:
                nist_controls.add(normalized_control)
                for tag in catalog_entry.get('tags', []):
                    if tag.get('grc'):
                        grc_controls.add(tag['grc'])
                    for nist_ref in tag.get('nist_references', []):
                        if nist_ref != "None":
                            nist_references.add(nist_ref)
                for org in catalog_entry.get('org_ref', []):
                    if org != "None":
                        org_refs.add(org)
                for rel_control in catalog_entry.get('related_controls', []):
                    if rel_control != "None":
                        related_controls.add(rel_control)
    
    return (
        sorted(list(nist_controls)),
        sorted(list(grc_controls)),
        sorted(list(org_refs)),
        sorted(list(nist_references)),
        sorted(list(related_controls)),
        cwe_entry
    )

# Check failure thresholds and return compliance status
def check_failure_thresholds(vuln_counts, thresholds):
    failed_limits = thresholds.get('failed', {})
    print(f"🛟 Checking thresholds {failed_limits}")
    compliance_issues = []
    for severity, count in vuln_counts.items():
        max_allowed = failed_limits.get(severity.lower(), {}).get('max', float('inf'))
        if count > max_allowed:
            compliance_issues.append(f"{severity} vulnerabilities ({count}) exceed max allowed ({max_allowed})")
    print(f"🆘 Compliance Issues detected {compliance_issues}")
    return compliance_issues

# Convert GitLab SAST report to HDF per the schema
def convert_to_hdf(sast_report, cwe_data, catalog_data, thresholds):
    try:
        duration = datetime.datetime.strptime(sast_report["scan"].get("end_time"), "%Y-%m-%dT%H:%M:%S") - \
                   datetime.datetime.strptime(sast_report["scan"].get("start_time", datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")), "%Y-%m-%dT%H:%M:%S")
        run_time = round(duration.total_seconds() / 86400, 6)
    except (KeyError, ValueError) as e:
        print(f"⚠️ Error calculating duration: {str(e)}. Using default run_time.")
        run_time = 0.000139

    print(f"⏱️ Duration calculated as {run_time}")
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
                "sha256": generate_sha(sast_report),
                "status": "loaded",
                "summary": "GitLab enriched profile",
                "supports": [
                    {
                        "platform-name": "multiple languages",
                        "release": "1.0"
                    }
                ],
                "title": "GitLab SAST Scan report through enrichment for visualization",
                "version": "1.1.1"
            }
        ],
        "statistics": {
            "duration": run_time
        },
        "version": "1.1",
        "passthrough": {
            "auxiliary_data": [
                {
                    "name": "block 0",
                    "data": {}
                },
                {
                    "name": "GitLab SAST Data",
                    "data": {
                        "compliance_issues": []
                    }
                }
            ]
        }
    }
    
    vuln_counts = Counter(vuln.get('severity', 'Unknown') for vuln in sast_report.get('vulnerabilities', []))
    compliance_issues = check_failure_thresholds(vuln_counts, thresholds)
    
    profile = hdf_output["profiles"][0]
    if compliance_issues:
        profile["status"] = "failed"
        hdf_output["passthrough"]["auxiliary_data"][1]["data"]["compliance_issues"] = compliance_issues

    controls = []
    print(f"🧭 Started mapping CWE's to Controls")
    
    # Collect unique CWEs and group vulns by primary CWE (first in list)
    cwe_to_vulns = defaultdict(list)
    for vuln in sast_report.get("vulnerabilities", []):
        cwes = vuln.get("cwe", []) or [ident['value'] for ident in vuln.get("identifiers", []) if ident.get('type') == 'cwe']
        if cwes:
            primary_cwe = cwes[0].replace('CWE-', '')  # Normalize to ID
            cwe_to_vulns[primary_cwe].append(vuln)
    
    for unique_cwe_id, matching_vulns in sorted(cwe_to_vulns.items()):
        cwe = 'CWE-' + unique_cwe_id
        
        # Get cwe_entry
        cwe_entry = next((entry for entry in cwe_data if entry['id'] == unique_cwe_id), None)
        
        # Get nist etc.
        nist, grc, org, nist_ref, rel_controls, _ = get_nist_and_grc_controls(unique_cwe_id, cwe_data, catalog_data)
        
        # Max severity from matching vulns
        severities = [v.get("severity", "Unknown") for v in matching_vulns]
        max_severity = max(severities, key=lambda s: map_severity_and_impact(s, thresholds)['impact'], default="Unknown")
        severity_info = map_severity_and_impact(max_severity, thresholds)
        
        # Aggregate locations
        aggregated_locations = ", ".join(
            f"{v.get('location', {}).get('file', 'unknown')}: {v.get('location', {}).get('start_line', '0')}/{v.get('location', {}).get('end_line', '')}"
            for v in matching_vulns
        )
        
        # Union identifiers and OWASP
        all_identifiers = [ident for v in matching_vulns for ident in v.get("identifiers", [])]
        mapped_identifiers = [{"url": ident.get("url", "")} for ident in all_identifiers if ident.get("url", "") != ""]
        owasp_ids = sorted(list(set(ident['value'] for ident in all_identifiers if ident.get('type') == 'owasp')))
        
        # Aggregated fields from cwe_entry or vulns
        rule_name = cwe_entry.get('rule_name', matching_vulns[0].get('name', '')) if cwe_entry else matching_vulns[0].get('name', '')
        description = cwe_entry.get('description', ', '.join(set(v.get('description', '') for v in matching_vulns))) if cwe_entry else ', '.join(set(v.get('description', '') for v in matching_vulns))
        extended_description = cwe_entry.get('extended_description', '') if cwe_entry else ''
        applicable_platforms = json.dumps(cwe_entry.get('applicable_platforms', []), indent=2) if cwe_entry else ''
        potential_mitigations = json.dumps(cwe_entry.get('potential_mitigations', []), indent=2) if cwe_entry else ', '.join(set(v.get('solution', '') for v in matching_vulns if v.get('solution', '')))
        
        # Aggregated message
        message = f"Vulnerability Found in multiple locations: {aggregated_locations}"
        
        control = {
            "code": f"{rule_name} {description} {applicable_platforms}",
            "desc": description,
            "descriptions": [
                {"data": rule_name, "label": "default"},
                {"data": extended_description, "label": "check"},
                {"data": potential_mitigations, "label": "fix"}
            ],
            "id": "CWE-" + unique_cwe_id,
            "impact": severity_info['impact'],
            "refs": mapped_identifiers,
            "results": [
                {
                    "code_desc": description,
                    "message": message,
                    "run_time": run_time,
                    "start_time": sast_report['scan'].get("start_time", datetime.datetime.utcnow().isoformat() + "Z"),
                    "status": severity_info['status']
                }
            ],
            "source_location": {
                "line": "aggregated",
                "ref": aggregated_locations
            },
            "tags": {
                "severity": severity_info['severity'],
                "nist": sorted(list(set(nist))),
                "grc": sorted(list(set(grc))),
                "cwe": "CWE-" + unique_cwe_id,
                "owasp": owasp_ids,
                "cci": [],
                "category": ', '.join(sorted(set(v.get('category', '') for v in matching_vulns))),
                "org_ref": sorted(list(set(org))),
                "nist_references": sorted(list(set(nist_ref))),
                "related_controls": sorted(list(set(rel_controls)))
            },
            "title": rule_name,
            "waiver_data": {}
        }
        controls.append(control)

    hdf_output["profiles"][0]["controls"] = controls
    hdf_output["statistics"]["duration"] = run_time * len(controls)
    return hdf_output

# Save HDF output to a file
def save_hdf_output(hdf_data, output_path):
    print(f"🗄️ Saving HDF Data to: {output_path}")
    with open(output_path, 'w') as f:
        json.dump(hdf_data, f, indent=2)

# Main function
def main(sast_file_content, cwe_file_content, catalog_file_content, thresholds_file_content, output_file):
    try:
        sast_report = load_json_file(None, sast_file_content)
        print(f"📁 Loaded gl-sast-report.json for gl-sast-report")
        cwe_data = load_json_file(None, cwe_file_content)['cwe_data']
        print(f"📁 Loaded sast_cwe.json for CWE Data")
        catalog_data = load_json_file(None, catalog_file_content)
        print(f"📂 Loaded catalog.json for SAFR data")
        thresholds = load_yaml_file(None, thresholds_file_content)
        hdf_data = convert_to_hdf(sast_report, cwe_data, catalog_data, thresholds)
        save_hdf_output(hdf_data, output_file)
        print(f"Conversion complete. HDF file saved to {output_file}")
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        raise


if __name__ == "__main__":
    # Update with file locations as needed
    INPUT_FOLDER = "./"
    OUTPUT_FOLDER = "./"
    THRESHOLDS = "thresholds.yaml"
    sast_file = INPUT_FOLDER + "gl-sast-report.json"
    cwe_file = INPUT_FOLDER + "sast_cwe.json"
    catalog_file = INPUT_FOLDER + "catalog.json"
    thresholds_file = THRESHOLDS
    output_file = OUTPUT_FOLDER + "output_hdf.json"
    main(sast_file, cwe_file, catalog_file, thresholds_file, output_file)
    output_file = "output_hdf.json"
