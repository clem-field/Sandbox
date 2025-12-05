#!/usr/bin/env python3
"""
Merge cas_enriched.json with cas_schema.json to produce a final schema
matching the structure of cas_final_schema.json

Usage:
    python merge_cas_rules.py -i cas_enriched.json -m cas_schema.json -o cas_final_schema.json
"""

import json
import argparse
import sys
from typing import Dict, List, Any, Optional

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

def extract_rules_from_schema(schema_data: List[Dict]) -> Dict[str, Dict]:
    """
    Extract rules from cas_schema.json structure
    Expected format: [{"rules": [...]}]
    """
    rule_map = {}
    if isinstance(schema_data, list) and len(schema_data) > 0 and "rules" in schema_data[0]:
        for item in schema_data[0]["rules"]:
            rule_id = item.get("id")
            if rule_id:
                rule_map[rule_id] = item
    else:
        print("Warning: Unexpected schema format in -m file. Expected [{'rules': [...]}]")
    return rule_map

def extract_rules_from_enriched(enriched_data: Dict) -> List[Dict]:
    """
    Extract rules from cas_enriched.json
    Expected: {"rules": [{"rule_name": "...", ...}, ...]}
    """
    return enriched_data.get("rules", [])

def merge_rules(enriched_rules: List[Dict], schema_rule_map: Dict[str, Dict]) -> List[Dict]:
    merged_rules = []
    used_rule_names = set()
    new_incomplete_rules = []

    line_number = 1

    # First: process all rules from enriched file (preserve order)
    for enriched_rule in enriched_rules:
        rule_name = enriched_rule.get("rule_name")
        if not rule_name:
            print(f"Warning: Skipping enriched rule missing 'rule_name' at line {enriched_rule.get('line')}")
            continue

        used_rule_names.add(rule_name)

        merged_entry = {
            "line": line_number,
            "rule_name": rule_name,
            "nist_controls_r4": enriched_rule.get("nist_controls_r4", []),
            "nist_controls_r5": enriched_rule.get("nist_controls_r5", []),
            "secondary_controls": enriched_rule.get("secondary_controls", [])
        }

        # If this rule exists in schema, enrich it with full details
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
            # Rule not found in schema → incomplete
            new_incomplete_rules.append(rule_name)
            # Add minimal fields with defaults
            merged_entry.update({
                "severity": "UNKNOWN",
                "dpath": "",
                "description": f"[MISSING IN SCHEMA] Rule '{rule_name}' was found in enriched but not in schema",
                "checkov_rule": "",
                "resource": []
            })

        merged_rules.append(merged_entry)
        line_number += 1

    # Second: add any rules from schema that weren't in enriched (optional, but safe)
    # This ensures nothing is lost, though your example doesn't include them unless in enriched
    for rule_id, schema_rule in schema_rule_map.items():
        if rule_id not in used_rule_names:
            print(f"Note: Rule '{rule_id}' exists in schema but not in enriched data. Adding as incomplete.")
            new_incomplete_rules.append(rule_id)
            merged_rules.append({
                "line": line_number,
                "rule_name": rule_id,
                "severity": schema_rule.get("severity", "UNKNOWN"),
                "dpath": schema_rule.get("dpath", ""),
                "description": schema_rule.get("description", f"[ONLY IN SCHEMA] Rule '{rule_id}' not present in enriched data"),
                "checkov_rule": schema_rule.get("checkov_rule", ""),
                "resource": schema_rule.get("resource", []),
                "nist_controls_r4": [],
                "nist_controls_r5": [],
                "secondary_controls": []
            })
            line_number += 1

    return merged_rules, new_incomplete_rules

def main():
    parser = argparse.ArgumentParser(description="Merge CAS enriched and schema files")
    parser.add_argument("-i", "--input", required=True, help="Path to cas_enriched.json")
    parser.add_argument("-m", "--mapping", required=True, help="Path to cas_schema.json")
    parser.add_argument("-o", "--output", required=True, help="Output file path (e.g. cas_final_schema.json)")

    args = parser.parse_args()

    print("Loading files...")
    enriched_data = load_json_file(args.input)
    schema_data = load_json_file(args.mapping)

    print("Extracting rules...")
    schema_rule_map = extract_rules_from_schema(schema_data)
    enriched_rules = extract_rules_from_enriched(enriched_data)

    print(f"Found {len(schema_rule_map)} rules in schema file")
    print(f"Found {len(enriched_rules)} rules in enriched file")

    merged_rules, incomplete_rules = merge_rules(enriched_rules, schema_rule_map)

    # Build final output structure (matching cas_final_schema.json)
    output_data = {
        "metadata": {},
        "schema_info": {},
        "usage_guidelines": {},
        "change_log": [],
        "rules": merged_rules
    }

    # Write output
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nMerged {len(merged_rules)} rules into {args.output}")

    if incomplete_rules:
        print("\n" + "="*60)
        print("WARNING: The following rules lack complete information")
        print("(They exist in one source but not both, or missing NIST mappings)")
        print("="*60)
        for rule in incomplete_rules:
            print(f"   • {rule}")
        print(f"\nTotal incomplete/new rules: {len(incomplete_rules)}")
        print("These have been included with placeholder fields and empty control arrays.")
    else:
        print("\nAll rules are fully matched and enriched!")

if __name__ == "__main__":
    main()