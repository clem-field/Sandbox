import json
import argparse
import pandas as pd
from pathlib import Path

def validate_json_file(file_path):
    """Validate that the input file is a JSON file with valid content."""
    # Check file extension
    if not file_path.lower().endswith('.json'):
        raise ValueError("Input file must have a .json extension.")
    
    # Check if file contains valid JSON
    try:
        with open(file_path, 'r') as f:
            json.load(f)
    except json.JSONDecodeError:
        raise ValueError("Input file is not a valid JSON file.")
    except FileNotFoundError:
        raise ValueError(f"Input file '{file_path}' not found.")

def main():
    parser = argparse.ArgumentParser(description="Extract NIST controls matching a given overlay.")
    parser.add_argument('-i', '--input', required=True, help="Path to the input JSON file.")
    parser.add_argument('-o', '--output', required=True, help="Path to the output directory.")
    parser.add_argument('-f', '--filter', required=True, help="Overlay filter (e.g., 'Low', 'Mod', 'High').")
    args = parser.parse_args()

    # Validate input file
    try:
        validate_json_file(args.input)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Load JSON data
    with open(args.input, 'r') as f:
        data = json.load(f)

    # Filter controls where overlay includes the filter value
    matched = []
    for control in data:
        if args.filter in control.get('overlay', []):
            extracted = {
                'control_id': control.get('control_id', ''),
                'title': control.get('title', ''),
                'language': control.get('language', ''),
                'supplemental_guidance': control.get('supplemental_guidance', ''),
                'implementation_guidance': control.get('implementation_guidance', ''),
                'org_ref': ', '.join(control.get('org_ref', [])) if isinstance(control.get('org_ref'), list) else control.get('org_ref', '')
            }
            matched.append(extracted)

    if not matched:
        print(f"No controls matched the overlay '{args.filter}'.")
        return

    # Create DataFrame and save to XLSX
    df = pd.DataFrame(matched)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"matched_controls_{args.filter}.xlsx"
    df.to_excel(output_file, index=False)
    print(f"Output saved to {output_file}")

if __name__ == "__main__":
    main()