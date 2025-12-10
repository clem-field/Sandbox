#!/usr/bin/env python3

import json
import argparse
from pathlib import Path

def load_nist_controls(file_path):
    """Load a JSON file and extract the list from 'nist_controls' key (handles both list and single file)"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # If it's a list of profiles (like your example), take the first one
    if isinstance(data, list):
        if not data:
            raise ValueError(f"Empty list in {file_path}")
        profile_data = data[0]
    else:
        profile_data = data

    controls = profile_data.get("nist_controls", [])
    if not isinstance(controls, list):
        raise ValueError(f"'nist_controls' must be a list in {file_path}")
    
    return set(controls), profile_data.get("profile", "Unknown Profile")

def main():
    parser = argparse.ArgumentParser(
        description="Compare NIST controls between two JSON profile files"
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input JSON file (the one being tested)")
    parser.add_argument("-c", "--compare", required=True, help="Path to comparison JSON file (baseline/reference)")
    parser.add_argument("-o", "--output", default=None, help="Output JSON file (if not provided, prints to stdout)")

    args = parser.parse_args()

    # Load both files
    input_controls, input_profile = load_nist_controls(args.input)
    compare_controls, compare_profile = load_nist_controls(args.compare)

    # Compute sets
    unique_to_input = sorted(input_controls - compare_controls)
    unique_to_compare = sorted(compare_controls - input_controls)
    overlapping = sorted(input_controls & compare_controls)

    # Build result
    result = {
        "comparison_summary": {
            "input_profile": input_profile,
            "compare_profile": compare_profile,
            "total_in_input": len(input_controls),
            "total_in_compare": len(compare_controls),
            "unique_to_input_count": len(unique_to_input),
            "unique_to_compare_count": len(unique_to_compare),
            "overlapping_count": len(overlapping)
        },
        "unique_to_input": unique_to_input,
        "unique_to_compare": unique_to_compare,
        "overlapping_controls": overlapping
    }

    # Output
    output_json = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(output_json + "\n")
        print(f"Comparison written to {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    main()