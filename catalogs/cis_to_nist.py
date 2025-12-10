#!/usr/bin/env python3
import pandas as pd
import json
import argparse
from pathlib import Path

def parse_cis_excel(input_file: str, sheet_name: str = "All CIS Controls & Safeguards") -> dict:
    """
    Parse the CIS Controls Excel mapping file and return structured dict ready for JSON.
    # Basic usage
    python cis_to_nist_json.py -i "CIS_Controls_v8.1_Mapping_to_NIST_SP_800-53_Rev_5.xlsx" -o cis_to_nist.json

    # Custom sheet name (if different)
    python cis_to_nist_json.py -i file.xlsx -s "All CIS Controls & Safeguards" -o my_mapping.json
    """
    df = pd.read_excel(input_file, sheet_name=sheet_name, header=0)

    # Drop the very first column (Column A - usually "CIS Control" repeated or empty)
    df = df.iloc[:, 1:]

    # Expected column names based on official CIS mapping file
    expected_cols = [
        'CIS Sub-Control', 'Asset Type', 'Security Function', 'Title', 'Description',
        'IG1', 'IG2', 'IG3', 'Relationship', 'Control Identifier',
        'Control or Control Enhancement Name', 'Control Text', 'Moderate Baseline'
    ]

    # If columns don't match exactly, try to align by position
    if list(df.columns) != expected_cols:
        df.columns = expected_cols[:len(df.columns)]

    # Drop rows where Asset Type (now column B → index 1) is NaN/empty
    df = df[df['Asset Type'].notna() & (df['Asset Type'] != '')]

    # Fill forward the CIS Control number (it's only in some rows)
    df['CIS Control'] = df['CIS Sub-Control'].str.extract(r'^(\d+)').astype(float).fillna(method='ffill')

    # Extract safeguard (e.g., "1.1")
    df['Safeguard'] = df['CIS Sub-Control'].str.extract(r'(\d+\.\d+)')

    # Clean up IG1/IG2/IG3 → boolean
    for ig in ['IG1', 'IG2', 'IG3']:
        df[ig] = df[ig].astype(str).str.strip().str.lower().map({'x': True, 'nan': False, '': False})
        df[ig] = df[ig].fillna(False)

    # Group by CIS Control and then by Safeguard
    result = {
        "version": "CIS Controls v8.1",
        "date_created": pd.Timestamp('today').strftime('%m/%d/%Y'),
        "notes": "Generated from official CIS Controls v8.1 to NIST SP 800-53 Rev 5 mapping",
        "groups": []
    }

    for control_num in df['CIS Control'].dropna().unique():
        control_num = int(control_num)
        control_group = {
            "cis_control": control_num,
            "cis_sub_controls": []
        }

        control_df = df[df['CIS Control'] == control_num]

        for safeguard in control_df['Safeguard'].dropna().unique():
            safeguard_df = control_df[control_df['Safeguard'] == safeguard].copy()
            if safeguard_df.empty:
                continue

            # Take the first row for metadata (they should be identical per safeguard)
            row = safeguard_df.iloc[0]

            sub_control = {
                "safeguard": safeguard,
                "details": [{
                    "asset_type": str(row['Asset Type']).strip(),
                    "security_function": str(row['Security Function']).strip(),
                    "title": str(row['Title']).strip(),
                    "description": str(row['Description']).strip(),
                    "nist_controls": []
                }]
            }

            # Now collect all NIST mappings for this safeguard
            for _, mapping_row in safeguard_df.iterrows():
                nist_id = mapping_row['Control Identifier']
                if pd.isna(nist_id) or str(nist_id).strip() == '':
                    continue

                nist_control = {
                    "nist_control": str(nist_id).strip(),
                    "enhancement_name": str(mapping_row['Control or Control Enhancement Name']).strip(),
                    "relationship": str(mapping_row['Relationship']).strip(),
                    "ig1": bool(mapping_row['IG1']),
                    "ig2": bool(mapping_row['IG2']),
                    "ig3": bool(mapping_row['IG3']),
                    "control": str(mapping_row['Control Text']).strip()
                }
                sub_control["details"][0]["nist_controls"].append(nist_control)

            control_group["cis_sub_controls"].append(sub_control)

        result["groups"].append(control_group)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Convert CIS Controls v8.1 → NIST SP 800-53 Excel to structured JSON"
    )
    parser.add_argument("-i", "--input", required=True, help="Input Excel file (.xlsx)")
    parser.add_argument("-s", "--sheet", default="All CIS Controls & Safeguards",
                        help="Sheet name (default: 'All CIS Controls & Safeguards')")
    parser.add_argument("-o", "--output", default="cis_to_nist.json",
                        help="Output JSON file (default: cis_to_nist.json)")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}")
        exit(1)

    print(f"Reading {args.input} → sheet '{args.sheet}'...")
    data = parse_cis_excel(args.input, args.sheet)

    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Successfully written to {args.output}")
    print(f"   → {len(data['groups'])} CIS Controls")
    total_safeguards = sum(len(g['cis_sub_controls']) for g in data['groups'])
    print(f"   → {total_safeguards} Safeguards with NIST mappings")


if __name__ == "__main__":
    main()