#!/usr/bin/env python3
"""
cis_to_nist.py
→ Generates cis_to_nist.json + cis-sg_no_nist.md (now with Description column)
Fully compatible with: import libraries as lib (uv/Docker)
"""

import libraries as lib


def parse_cis_excel(
    input_file: str,
    sheet_name: str = "All CIS Controls & Safeguards",
    version: str = "CIS Controls v8.1",
    notes: str = None
) -> tuple[dict, list]:
    df = lib.pd.read_excel(input_file, sheet_name=sheet_name, header=0)

    # Drop first column (repeated CIS Control number)
    df = df.iloc[:, 1:]

    # Force column names
    expected = [
        'CIS Sub-Control', 'Asset Type', 'Security Function', 'Title', 'Description',
        'IG1', 'IG2', 'IG3', 'Relationship', 'Control Identifier',
        'Control or Control Enhancement Name', 'Control Text', 'Moderate Baseline'
    ]
    df.columns = expected[:len(df.columns)]

    # Remove header rows
    df = df[df['Asset Type'].notna() & (df['Asset Type'].astype(str).str.strip() != '')]

    # Extract control & safeguard
    df['CIS_Control_Num'] = df['CIS Sub-Control'].astype(str).str.extract(r'^(\d+)')
    df['CIS_Control_Num'] = lib.pd.to_numeric(df['CIS_Control_Num'], errors='coerce').ffill()
    df['Safeguard'] = df['CIS Sub-Control'].astype(str).str.extract(r'(\d+\.\d+)')

    # IG flags
    for col in ['IG1', 'IG2', 'IG3']:
        df[col] = df[col].astype(str).str.strip().str.lower() == 'x'

    # Split mapped / unmapped
    has_nist = df['Control Identifier'].notna() & (df['Control Identifier'].astype(str).str.strip() != '')
    mapped_df = df[has_nist].copy()
    unmapped_df = df[~has_nist].copy()

    if notes is None:
        notes = "Generated from official CIS Controls to NIST SP 800-53 Rev 5 mapping"

    # Build JSON (only mapped)
    result = {
        "version": version,
        "date_created": lib.datetime.today().strftime('%m/%d/%Y'),
        "notes": notes,
        "groups": []
    }

    for control_num in mapped_df['CIS_Control_Num'].dropna().unique():
        control_num = int(control_num)
        control_df = mapped_df[mapped_df['CIS_Control_Num'] == control_num]

        control_group = {"cis_control": control_num, "cis_sub_controls": []}

        for safeguard in control_df['Safeguard'].dropna().unique():
            sg_df = control_df[control_df['Safeguard'] == safeguard]
            if sg_df.empty:
                continue

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

            for _, r in sg_df.iterrows():
                if lib.pd.isna(r['Control Identifier']) or str(r['Control Identifier']).strip() == '':
                    continue
                sub_control["details"][0]["nist_controls"].append({
                    "nist_control": str(r['Control Identifier']).strip(),
                    "enhancement_name": str(r['Control or Control Enhancement Name']).strip(),
                    "relationship": str(r['Relationship'] or "").strip(),
                    "ig1": bool(r['IG1']),
                    "ig2": bool(r['IG2']),
                    "ig3": bool(r['IG3']),
                    "control": str(r['Control Text']).strip()
                })

            control_group["cis_sub_controls"].append(sub_control)

        result["groups"].append(control_group)

    # Build unmapped list (with Description)
    unmapped_list = []
    for _, row in unmapped_df.iterrows():
        if lib.pd.isna(row.get('Safeguard')) or not row['Safeguard']:
            continue
        unmapped_list.append({
            "control": int(row['CIS_Control_Num']),
            "safeguard": row['Safeguard'],
            "asset_type": str(row['Asset Type']).strip(),
            "security_function": str(row['Security Function']).strip(),
            "title": str(row['Title']).strip(),
            "description": str(row['Description']).strip(),
            "ig1": bool(row['IG1']),
            "ig2": bool(row['IG2']),
            "ig3": bool(row['IG3']),
        })

    return result, unmapped_list


def write_unmapped_markdown(unmapped: list, output_path: lib.Path):
    if not unmapped:
        content = "# CIS Safeguards Without NIST Mapping\n\nNo unmapped safeguards found.\n"
        output_path.write_text(content, encoding="utf-8")
        return

    lines = [
        "# CIS Safeguards Without NIST Mapping\n",
        f"**Generated on:** {lib.datetime.today().strftime('%B %d, %Y')}\n",
        f"**Total unmapped safeguards:** {len(unmapped)}\n",
        "## Checklist\n",
    ]

    for sg in sorted(unmapped, key=lambda x: x['safeguard']):
        lines.append(f"- [ ] {sg['safeguard']} – {sg['title']}\n")

    lines.append("\n## Detailed Table\n")
    header = "| Control | Safeguard | Asset Type      | Security Function | Title                                      | Description                                      | IG1 | IG2 | IG3 |"
    separator = "|---------|----------|----------------|------------------|--------------------------------------------|--------------------------------------------------|-----|-----|-----|"
    lines.extend([header, separator])

    for sg in sorted(unmapped, key=lambda x: (x['control'], x['safeguard'])):
        ig1 = "Yes" if sg['ig1'] else ""
        ig2 = "Yes" if sg['ig2'] else ""
        ig3 = "Yes" if sg['ig3'] else ""
        # Escape pipe characters in description to avoid breaking table
        desc = sg['description'].replace("|", "\\|")
        lines.append(
            f"| {sg['control']} | {sg['safeguard']} | {sg['asset_type']} | {sg['security_function']} | "
            f"{sg['title']} | {desc} | {ig1} | {ig2} | {ig3} |"
        )

    lines.append("")  # final newline
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = lib.argparse.ArgumentParser(
        description="CIS to NIST mapping + unmapped safeguards report (uv/Docker ready)"
    )
    parser.add_argument("-i", "--input", required=True, help="Input .xlsx file")
    parser.add_argument("-s", "--sheet", default="All CIS Controls & Safeguards")
    parser.add_argument("-o", "--output", default="data/output_files/cis_to_nist.json")
    parser.add_argument("-v", "--version", default="CIS Controls v8.1")
    parser.add_argument("-n", "--notes", default=None)

    args = parser.parse_args()

    input_path = lib.Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {args.input}")
        return

    print(f"Processing {args.input} ...")
    json_data, unmapped = parse_cis_excel(
        input_file=str(input_path),
        sheet_name=args.sheet,
        version=args.version,
        notes=args.notes
    )

    # Ensure directories
    out_json = lib.Path(args.output)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md = lib.Path("data/output_files/cis-sg_no_nist.md")
    out_md.parent.mkdir(parents=True, exist_ok=True)

    # Write files
    out_json.write_text(lib.json.dumps(json_data, indent=4, ensure_ascii=False), encoding="utf-8")
    write_unmapped_markdown(unmapped, out_md)

    total_mapped = sum(len(g["cis_sub_controls"]) for g in json_data["groups"])
    print("Success!")
    print(f"   • JSON → {out_json}")
    print(f"   • Unmapped report → {out_md} ({len(unmapped)} items)")
    print(f"   • {len(json_data['groups'])} Controls | {total_mapped} mapped safeguards")


if __name__ == "__main__":
    main()