#!/usr/bin/env python3
import json
import argparse
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(description="Generate NIST control coverage summary from CAS schema")
    parser.add_argument('-i', '--input', required=True, help='Input CAS schema JSON file')
    parser.add_argument('-o', '--output', required=True, help='Output summary JSON file')
    parser.add_argument('-p', '--profile', required=True, help='Some Profile', help='Profile name to include in output')
    parser.add_argument('-r', '--revision', choices=['r4', 'r5'], required=True,
                        help='NIST revision: r4 uses nist_controls_r4, r5 uses nist_controls_r5')

    args = parser.parse_args()

    # Determine which field to read based on revision
    control_field = 'nist_controls_r4' if args.revision == 'r4' else 'nist_controls_r5'

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rules = data.get('rules', [])

    all_nist_controls = set()
    missing_control_rules = []
    unique_rule_names = set()

    for rule in rules:
        rule_name = rule.get('rule_name')
        if not rule_name:
            continue

        unique_rule_names.add(rule_name)

        controls = rule.get(control_field, [])
        if not controls or len(controls) == 0:
            missing_control_rules.append(rule_name)
        else:
            all_nist_controls.update(controls)

    # Build output matching compare_file.json schema
    summary = [
        {
            "profile": args.profile,
            "unique_checks": len(unique_rule_names),
            "missing_nist_controls": len(missing_control_rules),
            "unique_nist_controls": len(all_nist_controls),
            "nist_controls": sorted(list(all_nist_controls)),
            "missing_nist": sorted(missing_control_rules)
        }
    ]

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)

    print(f"Summary written to {args.output}")
    print(f"  Profile: {args.profile}")
    print(f"  Unique checks (rule_names): {len(unique_rule_names)}")
    print(f"  Rules missing NIST controls: {len(missing_control_rules)}")
    print(f"  Unique NIST controls: {len(all_nist_controls)}")

if __name__ == '__main__':
    main()