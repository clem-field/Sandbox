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

def combine_json_files(file_a_path, file_b_path, output_file):
    # Load JSON files
    file_a_data = load_json_file(file_a_path)
    file_b_data = load_json_file(file_b_path)
    
    if file_a_data is None or file_b_data is None:
        return

    # Extract cwe_data from File B
    file_b_cwe_data = file_b_data.get("cwe_data", [])

    # Create a dictionary from File A indexed by cwe_id
    file_a_dict = {entry["cwe_id"]: entry["nist_id"] for entry in file_a_data}

    # Initialize the output cwe_data list
    combined_cwe_data = []

    # Template for new entries (for File A entries not in File B)
    default_entry = {
        "id": None,
        "rule_name": None,
        "description": None,
        "extended_description": None,
        "cwe_usage": None,
        "applicable_platforms": None,
        "common_consequences": None,
        "demonstrated_examples": None,
        "potential_mitigations": None,
        "likelihood": None,
        "related_weaknesses": None,
        "rev4_controls": [],
        "rev5_controls": [],
        "secondary_controls": []
    }

    # Process File B entries and add File A entries
    seen_cwe_ids = set()
    
    # First, process all File B entries
    for entry in file_b_cwe_data:
        try:
            cwe_id = int(entry["id"])
        except (ValueError, KeyError):
            print(f"Skipping invalid CWE ID: {entry.get('id', 'unknown')}")
            continue

        seen_cwe_ids.add(cwe_id)
        new_entry = entry.copy()  # Preserve all original fields
        # Update rev4_controls and rev5_controls from File A if available
        if cwe_id in file_a_dict:
            nist_id = file_a_dict[cwe_id]
            # Assume nist_id is a list with one dictionary containing rev4 and rev5
            if nist_id and isinstance(nist_id, list) and len(nist_id) > 0:
                new_entry["rev4_controls"] = nist_id[0].get("rev4", [])
                new_entry["rev5_controls"] = nist_id[0].get("rev5", [])
        
        combined_cwe_data.append(new_entry)

    # Add entries from File A that are not in File B
    for cwe_id, nist_id in file_a_dict.items():
        if cwe_id not in seen_cwe_ids:
            new_entry = default_entry.copy()
            new_entry["id"] = str(cwe_id)  # Convert to string to match File B's schema
            new_entry["rev4_controls"] = nist_id[0].get("rev4", []) if nist_id and isinstance(nist_id, list) else []
            new_entry["rev5_controls"] = nist_id[0].get("rev5", []) if nist_id and isinstance(nist_id, list) else []
            combined_cwe_data.append(new_entry)

    # Sort by cwe_id for consistent output
    combined_cwe_data.sort(key=lambda x: int(x["id"]) if x["id"].isdigit() else float('inf'))

    # Write the combined data to the output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"cwe_data": combined_cwe_data}, f, indent=2)
        print(f"Combined data written to '{output_file}'.")
    except Exception as e:
        print(f"Error writing to output file: {e}")

# Example usage
file_a_path = "file_a.json"
file_b_path = "file_b.json"
output_file = "combined_output.json"
combine_json_files(file_a_path, file_b_path, output_file)