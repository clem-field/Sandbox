import json
import argparse
import pandas as pd
from pathlib import Path

def validate_json_file(file_path):
    """Validate that the input file is a JSON file with valid content."""
    if not file_path.lower().endswith('.json'):
        raise ValueError(f"Input file '{file_path}' must have a .json extension.")
    try:
        with open(file_path, 'r') as f:
            json.load(f)
    except json.JSONDecodeError:
        raise ValueError(f"Input file '{file_path}' is not a valid JSON file.")
    except FileNotFoundError:
        raise ValueError(f"Input file '{file_path}' not found.")

def extract_control_data(control):
    """Extract relevant fields from a control."""
    return {
        'control_id': control.get('control_id', ''),
        'title': control.get('title', ''),
        'language': control.get('language', ''),
        'supplemental_guidance': control.get('supplemental_guidance', ''),
        'implementation_guidance': control.get('implementation_guidance', ''),
        'org_ref': ', '.join(control.get('org_ref', [])) if isinstance(control.get('org_ref'), list) else control.get('org_ref', '')
    }

def main():
    parser = argparse.ArgumentParser(description="Extract NIST controls matching a given overlay or compare two overlays from one or two JSON files.")
    parser.add_argument('-i', '--input', required=True, help="Path to the first JSON file (used with --filter).")
    parser.add_argument('-t', '--target', help="Path to the second JSON file (used with --delta).")
    parser.add_argument('-o', '--output', required=True, help="Path to the output directory.")
    parser.add_argument('-f', '--filter', required=True, help="Overlay filter for the first file (e.g., 'Low', 'Mod', 'High').")
    parser.add_argument('-d', '--delta', help="Overlay filter for the second file (e.g., 'Low', 'Mod', 'High'). Required if --target is specified.")
    parser.add_argument('-u', '--unidirectional', action='store_true', help="When used with --delta, only include controls in --delta not in --filter.")
    args = parser.parse_args()

    # Print selected options
    print(f"Selected options:")
    print(f"  Input file: {args.input}")
    print(f"  Filter overlay: {args.filter}")
    print(f"  Output directory: {args.output}")
    if args.target:
        print(f"  Target file: {args.target}")
        print(f"  Delta overlay: {args.delta}")
    if args.unidirectional:
        print(f"  Unidirectional comparison: Enabled")
    print()

    # Validate input file
    try:
        validate_json_file(args.input)
    except ValueError as e:
        print(f"Error: {e}")
        return
    print(f"Input file '{args.input}' validated successfully.")

    # Validate that --target requires --delta
    if args.target and not args.delta:
        print("Error: --target requires --delta to be specified.")
        return

    # Validate that --unidirectional requires --delta
    if args.unidirectional and not args.delta:
        print("Error: --unidirectional requires --delta to be specified.")
        return

    # Validate target file if provided
    if args.target:
        try:
            validate_json_file(args.target)
        except ValueError as e:
            print(f"Error: {e}")
            return
        print(f"Target file '{args.target}' validated successfully.")

    # Load JSON data from input file
    with open(args.input, 'r') as f:
        input_data = json.load(f)
    print(f"Loaded input file '{args.input}' successfully.")

    # Filter controls
    print("Starting analysis...")
    matched = []
    if args.target and args.delta:
        # Load JSON data from target file
        with open(args.target, 'r') as f:
            target_data = json.load(f)
        print(f"Loaded target file '{args.target}' successfully.")

        # Get control IDs for each overlay
        filter_controls = {control['control_id'] for control in input_data if args.filter in control.get('overlay', [])}
        delta_controls = {control['control_id'] for control in target_data if args.delta in control.get('overlay', [])}

        if args.unidirectional:
            # Unidirectional: only controls in delta (target file) but not in filter (input file)
            diff_controls = delta_controls - filter_controls
            for control in target_data:
                if control['control_id'] in diff_controls and args.delta in control.get('overlay', []):
                    extracted = extract_control_data(control)
                    extracted['overlay'] = ', '.join(control.get('overlay', []))  # Add overlay for clarity
                    matched.append(extracted)
        else:
            # Bidirectional: controls in either filter or delta, but not both
            diff_controls = filter_controls.symmetric_difference(delta_controls)
            # Check input file for filter overlay
            for control in input_data:
                if control['control_id'] in diff_controls and args.filter in control.get('overlay', []):
                    extracted = extract_control_data(control)
                    extracted['overlay'] = ', '.join(control.get('overlay', []))  # Add overlay for clarity
                    matched.append(extracted)
            # Check target file for delta overlay
            for control in target_data:
                if control['control_id'] in diff_controls and args.delta in control.get('overlay', []) and control['control_id'] not in {m['control_id'] for m in matched}:
                    extracted = extract_control_data(control)
                    extracted['overlay'] = ', '.join(control.get('overlay', []))  # Add overlay for clarity
                    matched.append(extracted)
        output_filename = f"delta_{args.filter}_to_{args.delta}.xlsx"
    else:
        # Normal mode: find all controls matching the filter overlay from input file
        for control in input_data:
            if args.filter in control.get('overlay', []):
                matched.append(extract_control_data(control))
        output_filename = f"matched_controls_{args.filter}.xlsx"

    if not matched:
        print(f"No controls matched the criteria (overlay: '{args.filter}'{', delta: ' + args.delta if args.delta else ''}{', unidirectional' if args.unidirectional else ''}).")
        return

    # Create DataFrame and save to XLSX
    df = pd.DataFrame(matched)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / output_filename
    df.to_excel(output_file, index=False)
    print(f"Output file written to '{output_file}'.")

if __name__ == "__main__":
    main()