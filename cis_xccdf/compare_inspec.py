import json
import argparse
from difflib import SequenceMatcher
import pandas as pd
from typing import Dict, List, Any

def load_profile(file_path: str) -> Dict[str, Dict[str, Any]]:
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load JSON file {file_path}: {str(e)}")
    
    controls = {}
    for control in data.get('controls', []):
        control_id = control.get('id')
        if not control_id:
            continue
        tags = control.get('tags', {})
        check = tags.get('check', '') or ''
        fix = tags.get('fix', '') or ''
        nist = tags.get('nist', [])
        nist = [str(n) for n in nist if n is not None] if isinstance(nist, list) else []
        controls[control_id] = {
            'check': check.strip(),
            'fix': fix.strip(),
            'nist': nist
        }
    return controls

def is_similar(a: str, b: str) -> float:
    if not a.strip() or not b.strip():
        return 0.0
    return SequenceMatcher(None, a, b).ratio()

def compare_profiles(base: Dict[str, Dict[str, Any]], target: Dict[str, Dict[str, Any]], fuzzy: bool, threshold: float) -> Dict[str, List[Dict[str, Any]]]:
    differences = {
        'removed': [],    # in base but not in target
        'added': [],      # in target but not in base
        'modified': [],   # in both but different check/fix
        'reassigned': []  # check/fix matches a different control_id (fuzzy only)
    }

    # Removed and Reassigned (baseline to target)
    for cid in set(base) - set(target):
        base_check = base[cid]['check']
        base_fix = base[cid]['fix']
        reassigned = False
        if fuzzy:
            best_check_match = None
            best_fix_match = None
            best_check_similarity = 0.0
            best_fix_similarity = 0.0
            for target_cid, target_data in target.items():
                check_similarity = is_similar(base_check, target_data['check'])
                fix_similarity = is_similar(base_fix, target_data['fix'])
                if check_similarity >= threshold and check_similarity > best_check_similarity:
                    best_check_similarity = check_similarity
                    best_check_match = (target_cid, target_data['check'])
                if fix_similarity >= threshold and fix_similarity > best_fix_similarity:
                    best_fix_similarity = fix_similarity
                    best_fix_match = (target_cid, target_data['fix'])
            if best_check_match or best_fix_match:
                details = []
                if best_check_match:
                    target_cid, target_check = best_check_match
                    details.append(f"Check matched in target {target_cid} (similarity: {best_check_similarity:.2f}); Baseline check: {base_check}; Target check: {target_check}")
                if best_fix_match:
                    target_cid, target_fix = best_fix_match
                    details.append(f"Fix matched in target {target_cid} (similarity: {best_fix_similarity:.2f}); Baseline fix: {base_fix}; Target fix: {target_fix}")
                differences['reassigned'].append({
                    'control_id': cid,
                    'check': base_check,
                    'fix': base_fix,
                    'nist': base[cid]['nist'],
                    'change': 'reassigned',
                    'details': '; '.join(details)
                })
                reassigned = True
        if not reassigned:
            differences['removed'].append({
                'control_id': cid,
                'check': base_check,
                'fix': base_fix,
                'nist': base[cid]['nist'],
                'change': 'removed'
            })

    # Added and Reassigned (target to baseline)
    for cid in set(target) - set(base):
        target_check = target[cid]['check']
        target_fix = target[cid]['fix']
        reassigned = False
        if fuzzy:
            best_check_match = None
            best_fix_match = None
            best_check_similarity = 0.0
            best_fix_similarity = 0.0
            for base_cid, base_data in base.items():
                check_similarity = is_similar(target_check, base_data['check'])
                fix_similarity = is_similar(target_fix, base_data['fix'])
                if check_similarity >= threshold and check_similarity > best_check_similarity:
                    best_check_similarity = check_similarity
                    best_check_match = (base_cid, base_data['check'])
                if fix_similarity >= threshold and fix_similarity > best_fix_similarity:
                    best_fix_similarity = fix_similarity
                    best_fix_match = (base_cid, base_data['fix'])
            if best_check_match or best_fix_match:
                details = []
                if best_check_match:
                    base_cid, base_check = best_check_match
                    details.append(f"Check matched in baseline {base_cid} (similarity: {best_check_similarity:.2f}); Target check: {target_check}; Baseline check: {base_check}")
                if best_fix_match:
                    base_cid, base_fix = best_fix_match
                    details.append(f"Fix matched in baseline {base_cid} (similarity: {best_fix_similarity:.2f}); Target fix: {target_fix}; Baseline fix: {base_fix}")
                differences['reassigned'].append({
                    'control_id': cid,
                    'check': target_check,
                    'fix': target_fix,
                    'nist': target[cid]['nist'],
                    'change': 'reassigned',
                    'details': '; '.join(details)
                })
                reassigned = True
        if not reassigned:
            differences['added'].append({
                'control_id': cid,
                'check': target_check,
                'fix': target_fix,
                'nist': target[cid]['nist'],
                'change': 'added'
            })
    
    # Modified
    for cid in set(base) & set(target):
        base_check = base[cid]['check']
        base_fix = base[cid]['fix']
        target_check = target[cid]['check']
        target_fix = target[cid]['fix']
        
        check_diff = base_check != target_check
        fix_diff = base_fix != target_fix
        
        if fuzzy:
            check_similarity = is_similar(base_check, target_check)
            fix_similarity = is_similar(base_fix, target_fix)
            check_diff = check_diff and check_similarity < threshold
            fix_diff = fix_diff and fix_similarity < threshold
        else:
            check_similarity = None
            fix_similarity = None
        
        if check_diff or fix_diff:
            details = []
            if check_diff:
                details.append(f"Check differs (similarity: {check_similarity:.2f})" if fuzzy else "Check differs")
                details.append(f"Baseline check: {base_check}")
                details.append(f"Target check: {target_check}")
            if fix_diff:
                details.append(f"Fix differs (similarity: {fix_similarity:.2f})" if fuzzy else "Fix differs")
                details.append(f"Baseline fix: {base_fix}")
                details.append(f"Target fix: {target_fix}")
            differences['modified'].append({
                'control_id': cid,
                'check': target_check,
                'fix': target_fix,
                'nist': target[cid]['nist'],
                'change': 'modified',
                'details': '; '.join(details)
            })
    
    return differences

def output_to_json(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    try:
        with open(output_file, 'w') as f:
            json.dump(diffs, f, indent=4)
    except Exception as e:
        raise ValueError(f"Failed to write JSON output to {output_file}: {str(e)}")

def output_to_md(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    try:
        with open(output_file, 'w') as f:
            f.write('# InSpec Profile Differences\n\n')
            
            for category, items in diffs.items():
                if items:
                    f.write(f'## {category.capitalize()}\n\n')
                    f.write('| Control ID | Check | Fix | NIST Controls | Details |\n')
                    f.write('|------------|-------|-----|---------------|---------|\n')
                    for item in items:
                        nist_str = ', '.join(item['nist']) if item['nist'] else 'None'
                        details = item.get('details', item['change'])
                        details = details.replace('|', '\\|')
                        check = item.get('check', '').replace('|', '\\|')
                        fix = item.get('fix', '').replace('|', '\\|')
                        f.write(f'| {item["control_id"]} | {check} | {fix} | {nist_str} | {details} |\n')
                    f.write('\n')
    except Exception as e:
        raise ValueError(f"Failed to write Markdown output to {output_file}: {str(e)}")

def output_to_xlsx(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    try:
        data = []
        for category, items in diffs.items():
            for item in items:
                data.append({
                    'Category': category,
                    'Control ID': item['control_id'],
                    'Check': item.get('check', ''),
                    'Fix': item.get('fix', ''),
                    'NIST Controls': ', '.join(item['nist']) if item['nist'] else 'None',
                    'Details': item.get('details', item['change'])
                })
        df = pd.DataFrame(data)
        df.to_excel(output_file, index=False)
    except Exception as e:
        raise ValueError(f"Failed to write Excel output to {output_file}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Compare two InSpec Profile JSON files.')
    parser.add_argument('-b', '--baseline', required=True, help='Path to baseline JSON file')
    parser.add_argument('-t', '--target', required=True, help='Path to target JSON file')
    parser.add_argument('-f', '--fuzzy', type=str, choices=['True', 'False'], default='False', 
                        help='Enable fuzzy matching (True/False, default: False)')
    parser.add_argument('-s', '--similarity', type=float, default=0.9, 
                        help='Fuzzy matching similarity threshold (0.0 to 1.0, default: 0.9)')
    parser.add_argument('-o', '--output', required=True, help='Output file path (.md, .xlsx, .json)')
    
    args = parser.parse_args()
    
    fuzzy = args.fuzzy == 'True'
    
    # Validate similarity threshold
    if not 0.0 <= args.similarity <= 1.0:
        raise ValueError("Similarity threshold must be between 0.0 and 1.0")
    
    base_controls = load_profile(args.baseline)
    target_controls = load_profile(args.target)
    
    differences = compare_profiles(base_controls, target_controls, fuzzy, args.similarity)
    
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
    try:
        main()
    except Exception as e:
        print(f"Error: {str(e)}")