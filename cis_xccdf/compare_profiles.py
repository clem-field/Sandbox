import json
import argparse
from difflib import SequenceMatcher
import pandas as pd
from typing import Dict, List, Any

def load_profile(file_path: str) -> Dict[str, Dict[str, Any]]:
    with open(file_path, 'r') as f:
        data = json.load(f)
    controls = {}
    for control in data.get('controls', []):
        control_id = control.get('id')
        tags = control.get('tags', {})
        check = tags.get('check', '')
        fix = tags.get('fix', '')
        nist = tags.get('nist', [])
        controls[control_id] = {
            'check': check.strip(),
            'fix': fix.strip(),
            'nist': nist
        }
    return controls

def is_similar(a: str, b: str, threshold: float = 0.9) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= threshold

def compare_profiles(base: Dict[str, Dict[str, Any]], target: Dict[str, Dict[str, Any]], fuzzy: bool) -> Dict[str, List[Dict[str, Any]]]:
    differences = {
        'removed': [],  # in base but not in target
        'added': [],    # in target but not in base
        'modified': []  # in both but different check/fix
    }
    
    # Removed
    for cid in set(base) - set(target):
        differences['removed'].append({
            'control_id': cid,
            'nist': base[cid]['nist'],
            'change': 'removed'
        })
    
    # Added
    for cid in set(target) - set(base):
        differences['added'].append({
            'control_id': cid,
            'nist': target[cid]['nist'],
            'change': 'added'
        })
    
    # Modified
    for cid in set(base) & set(target):
        base_check = base[cid]['check']
        base_fix = base[cid]['fix']
        target_check = target[cid]['check']
        target_fix = target[cid]['fix']
        
        check_diff = not (base_check == target_check or (fuzzy and is_similar(base_check, target_check)))
        fix_diff = not (base_fix == target_fix or (fuzzy and is_similar(base_fix, target_fix)))
        
        if check_diff or fix_diff:
            changes = []
            if check_diff:
                changes.append('check')
            if fix_diff:
                changes.append('fix')
            differences['modified'].append({
                'control_id': cid,
                'nist': target[cid]['nist'],  # or base, assuming same
                'change': 'modified',
                'details': ', '.join(changes)
            })
    
    return differences

def output_to_json(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    with open(output_file, 'w') as f:
        json.dump(diffs, f, indent=4)

def output_to_md(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    with open(output_file, 'w') as f:
        f.write('# InSpec Profile Differences\n\n')
        
        for category, items in diffs.items():
            if items:
                f.write(f'## {category.capitalize()}\n\n')
                f.write('| Control ID | NIST Controls | Details |\n')
                f.write('|------------|---------------|---------|\n')
                for item in items:
                    nist_str = ', '.join(item['nist'])
                    details = item.get('details', item['change'])
                    f.write(f'| {item["control_id"]} | {nist_str} | {details} |\n')
                f.write('\n')

def output_to_xlsx(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    data = []
    for category, items in diffs.items():
        for item in items:
            data.append({
                'Category': category,
                'Control ID': item['control_id'],
                'NIST Controls': ', '.join(item['nist']),
                'Details': item.get('details', item['change'])
            })
    df = pd.DataFrame(data)
    df.to_excel(output_file, index=False)

def main():
    parser = argparse.ArgumentParser(description='Compare two InSpec Profile JSON files.')
    parser.add_argument('-b', '--baseline', required=True, help='Path to baseline JSON file')
    parser.add_argument('-t', '--target', required=True, help='Path to target JSON file')
    parser.add_argument('-f', '--fuzzy', action='store_true', help='Enable fuzzy matching')
    parser.add_argument('-o', '--output', required=True, help='Output file path (.md, .xlsx, .json)')
    
    args = parser.parse_args()
    
    base_controls = load_profile(args.baseline)
    target_controls = load_profile(args.target)
    
    differences = compare_profiles(base_controls, target_controls, args.fuzzy)
    
    ext = args.output.split('.')[-1].lower()
    if ext == 'json':
        output_to_json(differences, args.output)
    elif ext == 'md':
        output_to_md(differences, args.output)
    elif ext == 'xlsx':
        output_to_xlsx(differences, args.output)
    else:
        raise ValueError('Unsupported output format. Use .md, .xlsx, or .json')

if __name__ == '__main__':
    main()