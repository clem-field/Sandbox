import json
from datetime import datetime
'''
Explanation of the Script

Loading the Report: The load_sast_report function reads the GitLab SAST JSON file.
Mapping Fields: The convert_to_hdf function maps key fields from the GitLab SAST report to a simplified HDF structure. The map_severity function normalizes severity levels.
Output Generation: The save_hdf_output function writes the HDF JSON to a file.
Error Handling: Basic error handling ensures robustness against malformed input.

'''
# Load GitLab SAST report
def load_sast_report(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Map GitLab SAST severity to HDF severity (customize as needed)
def map_severity(sast_severity):
    severity_map = {
        'Critical': 'critical',
        'High': 'high',
        'Medium': 'medium',
        'Low': 'low',
        'Info': 'info',
        'Unknown': 'unknown'
    }
    return severity_map.get(sast_severity, 'unknown')

# Convert GitLab SAST report to HDF
def convert_to_hdf(sast_report):
    hdf_output = {
        "version": "1.0",
        "metadata": {
            "tool": "GitLab SAST",
            "version": sast_report.get("version", "unknown"),
            "generated": datetime.utcnow().isoformat() + "Z"
        },
        "findings": []
    }

    for vuln in sast_report.get("vulnerabilities", []):
        finding = {
            "id": vuln.get("id", ""),
            "title": vuln.get("name", ""),
            "description": vuln.get("description", ""),
            "severity": map_severity(vuln.get("severity", "Unknown")),
            "location": {
                "file": vuln.get("location", {}).get("file", ""),
                "line": vuln.get("location", {}).get("start_line", 0)
            },
            "cwe": vuln.get("cwe", []),
            "remediation": vuln.get("solution", "")
        }
        hdf_output["findings"].append(finding)

    return hdf_output

# Save HDF output to a file
def save_hdf_output(hdf_data, output_path):
    with open(output_path, 'w') as f:
        json.dump(hdf_data, f, indent=2)

# Main function
def main(input_file, output_file):
    try:
        sast_report = load_sast_report(input_file)
        hdf_data = convert_to_hdf(sast_report)
        save_hdf_output(hdf_data, output_file)
        print(f"Conversion complete. HDF file saved to {output_file}")
    except Exception as e:
        print(f"Error during conversion: {str(e)}")

if __name__ == "__main__":
    input_file = "gl-sast-report.json"  # Replace with your input file path
    output_file = "output_hdf.json"     # Replace with your desired output file path
    main(input_file, output_file)