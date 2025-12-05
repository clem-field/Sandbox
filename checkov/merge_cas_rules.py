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
from pathlib import Path

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
    rule_map = {}
    if isinstance(schema_data, list) and len(schema_data) > 0 and "rules" in schema_data[0]:
        for rule in schema_data[0]["rules"]:
            rule_id = rule.get("id")
            if rule_id:
                rule_map[rule_id] = rule
    return rule_map

def merge_rules(enriched_data: Dict, schema_rule_map: Dict[str, Dict]) -> tuple[List[Dict], List[str]]:
    enriched_rules = enriched_data.get("rules", [])
    merged_rules = []
    needs_mapping = []  # Rules that are incomplete
    line_number = 1
    seen_rule_names = set()

    for enriched_rule in enriched_rules:
        rule_name = enriched_rule.get("rule_name")
        if not rule_name:
            print(f"Warning: Skipping enriched rule without 'rule_name': {enriched_rule}")
            continue

        seen_rule_names.add(rule_name)

        base_entry = {
            "line": line_number,
            "rule_name": rule_name,
            "nist_controls_r4": enriched_rule.get("nist_controls_r4", []),
            "nist_controls_r5": enriched_rule.get("nist_controls_r5", []),
            "secondary_controls": enriched_rule.get("secondary_controls", [])
        }

        if rule_name in schema_rule_map:
            schema_rule = schema_rule_map[rule_name]
            base_entry.update({
                "severity": schema_rule.get("severity"),
                "dpath": schema_rule.get("dpath", ""),
                "description": schema_rule.get("description"),
                "checkov_rule": schema_rule.get("checkov_rule", ""),
                "resource": schema_rule.get("resource", [])
            })
            # Only consider fully complete if NIST controls exist and schema metadata is present
            has_nist = (
                len(base_entry["nist_controls_r4"]) > 0 or
                len(base_entry["nist_controls_r5"]) > 0 or
                len(base_entry["secondary_controls"]) > 0
            )
            if not has_nist:
                needs_mapping.append(rule_name)
        else:
            # Rule in enriched but missing schema → definitely needs work
            needs_mapping.append(rule_name)
            base_entry.update({
                "severity": "UNKNOWN",
                "dpath": "",
                "description": f"[NOT IN SCHEMA] Rule '{rule_name}' found only in enriched data",
                "checkov_rule": "",
                "resource": []
            })

        merged_rules.append(base_entry)
        line_number += 1

    # Add rules that exist only in schema (not in enriched)
    for rule_id, schema_rule in schema_rule_map.items():
        if rule_id not in seen_rule_names:
            needs_mapping.append(rule_id)
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

    return merged_rules, needs_mapping

def write_todo_markdown(needs_mapping: List[str], output_path: Path):
    if not needs_mapping:
        return

    md_content = "# Rules Requiring NIST / Control Mapping\n\n"
    md_content += "These rules are either:\n"
    md_content += "- Missing from the schema (no severity, description, etc.)\n"
    md_content += "- Present but have no NIST or secondary control mappings\n\n"
    md_content += "Please enrich them in the source data.\n\n"

    # Sort for consistency
    for rule in sorted(needs_mapping):
        md_content += f"- [ ] `{rule}`\n"

    md_content += f"\n**Total pending**: {len(needs_mapping)} rule(s)\n"

    todo_file = output_path.parent / "TODO_MAPPING.md"
    with open(todo_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"   → Generated {todo_file.name} with {len(needs_mapping)} items to map")

def main():
    parser = argparse.ArgumentParser(
        description="Merge CAS enriched + schema → final schema + generate TODO list"
    )
    parser.add_argument("-i", "--input", required=True, help="Path to cas_enriched.json")
    parser.add_argument("-m", "--mapping", required=True, help="Path to cas_schema.json")
    parser.add_argument("-o", "--output", required=True, help="Output cas_final_schema.json path")
    args = parser.parse_args()

    print("Loading files...")
    enriched_data = load_json_file(args.input)
    schema_data = load_json_file(args.mapping)

    schema_rule_map = extract_schema_rules(schema_data)
    print(f"   • {len(enriched_data.get('rules', []))} rules in enriched file")
    print(f"   • {len(schema_rule_map)} rules in schema file")

    merged_rules, needs_mapping = merge_rules(enriched_data, schema_rule_map)

    # Preserve all top-level fields from enriched file
    output_data = {k: v for k, v in enriched_data.items() if k != "rules"}
    output_data["rules"] = merged_rules

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nSuccess: Merged {len(merged_rules)} rules → {output_path.name}")

    if needs_mapping:
        write_todo_markdown(needs_mapping, output_path)
        print(f"\nWarning: {len(needs_mapping)} rule(s) need mapping/review!")
    else:
        print("\nAll rules are fully mapped and complete!")

if __name__ == "__main__":
    main()