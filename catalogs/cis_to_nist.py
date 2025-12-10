import libraries as lib

def parse_cis_excel(input_file: str, sheet_name: str = "All CIS Controls & Safeguards") -> dict:
    df = pd.read_excel(input_file, sheet_name=sheet_name, header=0)

    # 1. Drop column A (the very first column that repeats the control number)
    df = df.iloc[:, 1:]

    # 2. Force column names – the official file sometimes has slightly different names
    expected = [
        'CIS Sub-Control', 'Asset Type', 'Security Function', 'Title', 'Description',
        'IG1', 'IG2', 'IG3', 'Relationship', 'Control Identifier',
        'Control or Control Enhancement Name', 'Control Text', 'Moderate Baseline'
    ]
    df.columns = expected[:len(df.columns)]

    # 3. Remove rows that are just the Control header rows (Asset Type is empty)
    df = df[df['Asset Type'].notna() & (df['Asset Type'].astype(str).str.strip() != '')]

    # 4. Extract the main Control number (1-18) and forward-fill it
    df['CIS_Control_Num'] = df['CIS Sub-Control'].astype(str).str.extract(r'^(\d+)')
    df['CIS_Control_Num'] = pd.to_numeric(df['CIS_Control_Num'], errors='coerce')
    df['CIS_Control_Num'] = df['CIS_Control_Num'].ffill()

    # 5. Extract the safeguard number (e.g. "1.1")
    df['Safeguard'] = df['CIS Sub-Control'].astype(str).str.extract(r'(\d+\.\d+)')

    # 6. Convert IG1/IG2/IG3 "x" → True, everything else → False
    for col in ['IG1', 'IG2', 'IG3']:
        df[col] = df[col].astype(str).str.strip().str.lower() == 'x'

    # ------------------------------------------------------------------
    result = {
        "version": "CIS Controls v8.1",
        "date_created": datetime.today().strftime('%m/%d/%Y'),
        "notes": "Generated from official CIS Controls v8.1 → NIST SP 800-53 Rev 5 mapping",
        "groups": []
    }

    for control_num in df['CIS_Control_Num'].dropna().unique():
        control_num = int(control_num)
        control_df = df[df['CIS_Control_Num'] == control_num]

        control_group = {
            "cis_control": control_num,
            "cis_sub_controls": []
        }

        for safeguard in control_df['Safeguard'].dropna().unique():
            sg_df = control_df[control_df['Safeguard'] == safeguard].copy()
            if sg_df.empty:
                continue

            # Metadata comes from the first row of this safeguard
            row = sg_df.iloc[0]

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

            # Collect every NIST mapping for this safeguard
            for _, r in sg_df.iterrows():
                nist_id = r['Control Identifier']
                if pd.isna(nist_id) or str(nist_id).strip() == '':
                    continue

                nist_entry = {
                    "nist_control": str(nist_id).strip(),
                    "enhancement_name": str(r['Control or Control Enhancement Name']).strip(),
                    "relationship": str(r['Relationship']).strip() or "",
                    "ig1": bool(r['IG1']),
                    "ig2": bool(r['IG2']),
                    "ig3": bool(r['IG3']),
                    "control": str(r['Control Text']).strip()
                }
                sub_control["details"][0]["nist_controls"].append(nist_entry)

            control_group["cis_sub_controls"].append(sub_control)

        result["groups"].append(control_group)

    return result


# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Convert CIS Controls v8.1 → NIST SP 800-53 Excel → structured JSON"
    )
    parser.add_argument("-i", "--input", required=True, help="Input .xlsx file")
    parser.add_argument("-s", "--sheet", default="All CIS Controls & Safeguards",
                        help="Sheet name (default: All CIS Controls & Safeguards)")
    parser.add_argument("-o", "--output", default="cis_to_nist.json",
                        help="Output JSON file")

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: File not found → {args.input}")
        return

    print(f"Parsing {args.input} (sheet: '{args.sheet}') ...")
    data = parse_cis_excel(args.input, args.sheet)

    Path(args.output).write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    
    total_safeguards = sum(len(g["cis_sub_controls"]) for g in data["groups"])
    print(f"Done! → {args.output}")
    print(f"   • {len(data['groups'])} CIS Controls")
    print(f"   • {total_safeguards} Safeguards with NIST mappings")


if __name__ == "__main__":
    main()