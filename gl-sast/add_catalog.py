import json

def load_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{file_path}'.")
        return None

def join_cwe_nist(file_b_path, file_c_path, output_file):
    # Load JSON files
    file_b_data = load_json_file(file_b_path)
    file_c_data = load_json_file(file_c_path)
    
    if file_b_data is None or file_c_data is None:
        return

    # Extract cwe_data from File B
    cwe_data = file_b_data.get("cwe_data", [])

    # Initialize the output list
    combined_data = []

    # Process each CWE entry
    for cwe_entry in cwe_data:
        cwe_controls = set(cwe_entry.get("rev4_controls", []) + cwe_entry.get("rev5_controls", []))
        if not cwe_controls:
            continue  # Skip CWE entries with no controls

        # Process each NIST control entry
        for nist_entry in file_c_data:
            # Extract nist tags
            nist_tags = set()
            for tag in nist_entry.get("tags", []):
                nist_tags.update(tag.get("nist", []))

            # Check for intersection between cwe_controls and nist_tags
            if cwe_controls & nist_tags:  # Non-empty intersection means a match
                combined_entry = {
                    "cwe": cwe_entry,
                    "nist_control": nist_entry
                }
                combined_data.append(combined_entry)

    # Write the combined data to the output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2)
        print(f"Combined data written to '{output_file}'.")
    except Exception as e:
        print(f"Error writing to output file: {e}")

# Example usage
file_b_path = "combined_output.json"
file_c_path = "nist_controls.json"
output_file = "cwe_nist_joined.json"
join_cwe_nist(file_b_path, file_c_path, output_file)