#!/usr/bin/env python3
"""
Merge cas_enriched.json with cas_schema.json
Preserves all top-level metadata from enriched file, only merges 'rules'

Usage:
    python merge_cas_rules.py -i cas_enriched.json -m cas_schema.json -o cas_final_schema.json
"""

import json
import argparse
import sys
from typing import Dict, List, Any

def load_json_file(filepath: str) -> Any:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)

def extract_schema_rules(schema_data: Any) -> Dict[str, Dict]:
    """Extract mapping of rule 'id' → full rule object from cas_schema.json"""
    rule_map = {}
    # cas_schema.json structure: [ { "rules": [ {...}, {...} ] } ]
    if isinstance(schema_data, list) and len(schema_data) > 0 and "rules" in schema_data[0]:
        for rule in schema_data[0]["rules"]:
            rule_id = rule.get("id")
            if rule_id:
                rule_map[rule_id] = rule
    return rule_map

def merge_rules(enriched_data: Dict, schema_rule_map: Dict[str, Dict]) -> tuple[List[Dict], List[str]]:
    enriched_rules = enriched_data.get("rules", [])
    merged_rules = []
    incomplete_rules = []
    line_number = 1

    seen_rule_names = set()

    for enriched_rule in enriched_rules:
        rule_name = enriched_rule.get("rule_name")
        if not rule_name:
            print(f"Warning: Skipping enriched rule without 'rule_name': {enriched_rule}")
            continue

        seen_rule_names.add(rule_name)

        # Base from enriched (has NIST controls)
        merged_entry = {
            "line": line_number,
            "rule_name": rule_name,
            "nist_controls_r4": enriched_rule.get("nist_controls_r4", []),
            "nist_controls_r5": enriched_rule.get("nist_controls_r5", []),
            "secondary_controls": enriched_rule.get("secondary_controls", [])
        }

        # If rule exists in schema → enrich with full details
        if rule_name in schema_rule_map:
            schema_rule = schema_rule_map[rule_name]
            merged_entry.update({
                "severity": schema_rule.get("severity"),
                "dpath": schema_rule.get("dpath", ""),
                "description": schema_rule.get("description"),
                "checkov_rule": schema_rule.get("checkov_rule", ""),
                "resource": schema_rule.get("resource", [])
            })
        else:
            # Rule in enriched but NOT in schema → incomplete metadata
            incomplete_rules.append(rule_name)
            merged_entry.update({
                "severity": "UNKNOWN",
                "dpath": "",
                "description": f"[NOT IN SCHEMA] Rule '{rule_name}' found only in enriched data",
                "checkov_rule": "",
                "resource": []
            })

        merged_rules.append(merged_entry)
        line_number += 1

    # Optional: Add rules that exist in schema but not in enriched
    for rule_id, schema_rule in schema_rule_map.items():
        if rule_id not in seen_rule_names:
            print(f"Note: Rule '{rule_id}' exists in schema but missing from enriched → adding with empty controls")
            incomplete_rules.append(rule_id)
            merged_rules.append({
                "line": line_number,
                "rule_name": rule_id,
                "severity": schema_rule.get("severity", "UNKNOWN"),
                "dpath": schema_rule.get("dpath", ""),
                "description": schema_rule.get("description", f"[MISSING IN ENRICHED] {rule_id}"),
                "checkov_rule": schema_rule.get("checkov_rule", ""),
                "resource": schema_rule.get("resource", []),
                "nist_controls_r4": [],
                "nist_controls_r5": [],
                "secondary_controls": []
            })
            line_number += 1

    return merged_rules, incomplete_rules

def main():
    parser = argparse.ArgumentParser(description="Merge CAS enriched + schema → final schema (preserves metadata)")
    parser.add_argument("-i", "--input", required=True, help="cas_enriched.json (source of truth for metadata)")
    parser.add_argument("-m", "--mapping", required=True, help="cas_schema.json (source of rule metadata)")
    parser.add_argument("-o", "--output", required=True, help="Output file (e.g. cas_final_schema.json)")
    args = parser.parse_args()

    print("Loading input files...")
    enriched_data = load_json_file(args.input)
    schema_data = load_json_file(args.mapping)

    print(f"Loaded {len(enriched_data.get('rules', []))} rules from enriched file")
    schema_rule_map = extract_schema_rules(schema_data)
    print(f"Loaded {len(schema_rule_map)} rules from schema file")

    merged_rules, incomplete = merge_rules(enriched_data, schema_rule_map)

    # Preserve ALL top-level fields from enriched file, only replace 'rules'
    output_data = {
        k: v for k, v in enriched_data.items() if k != "rules"
    }
    output_data["rules"] = merged_rules

    # Write output
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully wrote {len(merged_rules)} rules to {args.output}")
    print(f"   Preserved metadata, schema_info, usage_guidelines, change_log from {args.input}")

    if incomplete:
        print("\n" + "═" * 70)
        print("WARNING: Incomplete rules detected (missing schema or NIST data)")
        print("═" * 70)
        for rule in incomplete:
            print(f"   • {rule}")
        print(f"\n   Total: {len(incomplete)} rule(s) with incomplete information")
        print("   These have been included with placeholders and empty control arrays.")
    else:
        print("\nAll rules fully matched and enriched!")

if __name__ == "__main__":
    main()