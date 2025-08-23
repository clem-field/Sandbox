import pandas as pd
import requests
import json

# Load the community mapping CSV (assume it's in the current directory)
def load_mappings(csv_file='/Users/brandonfield/GitHub/Sandbox/nist_to_cwe_exercise.csv'):
    df = pd.read_csv(csv_file)
    # Assume columns like 'CWE' and 'NIST_Controls' (adjust based on actual CSV structure)
    # Create a dict for quick lookup: CWE -> list of controls
    mapping = {}
    for _, row in df.iterrows():
        cwe = row['CWE']  # e.g., 'CWE-20'
        controls = row['NIST SP800-53 Controls (Columbus Collaboratory)'].split(', ') if pd.notna(row['NIST SP800-53 Controls (Columbus Collaboratory)']) else []  # e.g., ['AT-3(3)', 'SI-2']
        mapping[cwe] = controls
    return mapping

# Fetch CVEs associated with a CWE from NVD API
def get_cves_for_cwe(cwe_id, num_results=20):
    url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cweId={cwe_id}&resultsPerPage={num_results}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        cves = [vuln['cve']['id'] for vuln in data.get('vulnerabilities', [])]
        return cves
    else:
        print(f"API error: {response.status_code}")
        return []

# Main function to map CWE to 800-53 controls and enrich with CVEs
def map_cwe_to_controls(cwe_id, mappings):
    controls = mappings.get(cwe_id, [])
    if controls:
        print(f"CWE-{cwe_id} maps to NIST 800-53 controls: {', '.join(controls)}")
    else:
        print(f"No mapping found for CWE-{cwe_id} in the community data.")
    
    # Enrich with NVD data
    cves = get_cves_for_cwe(f"CWE-{cwe_id}")
    if cves:
        print(f"Example CVEs associated with CWE-{cwe_id}: {', '.join(cves)}")
    else:
        print(f"No recent CVEs found for CWE-{cwe_id}.")

# Example usage
if __name__ == "__main__":
    mappings = load_mappings()
    # Replace with your CWE ID, e.g., '20' for CWE-20
    map_cwe_to_controls('20', mappings) 