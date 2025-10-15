import json
import argparse
from difflib import SequenceMatcher
import pandas as pd
import re
import logging
from typing import Dict, List, Any
from collections import Counter

# Set up logging
logging.basicConfig(level=logging.WARNING)

def normalize_text(text: str) -> str:
    """Normalize text for comparison, preserving path separators and key terms."""
    if not text:
        return ""
    # Remove extra spaces, standardize quotes
    text = re.sub(r'\s+', ' ', text.strip())
    text = text.replace('\"', '"').replace("'", '"').replace('\\', '')
    # Preserve path separators and specific punctuation (e.g., /)
    # Remove other punctuation except for slashes in paths
    text = re.sub(r'[^\w\s/]', '', text)
    return text.lower()

def is_similar(a: str, b: str, field: str = 'unknown') -> float:
    """Compute token-based similarity between two strings."""
    if not a.strip() or not b.strip():
        return 0.0
    
    # Normalize and split into tokens
    a_tokens = normalize_text(a).split()
    b_tokens = normalize_text(b).split()
    
    # If either is empty after normalization
    if not a_tokens or not b_tokens:
        return 0.0
    
    # Compute token overlap using Counter
    a_counter = Counter(a_tokens)
    b_counter = Counter(b_tokens)
    common_tokens = sum((a_counter & b_counter).values())
    total_tokens = sum(a_counter.values()) + sum(b_counter.values())
    token_similarity = (2.0 * common_tokens) / total_tokens if total_tokens > 0 else 0.0
    
    # Adjust threshold for titles to be more lenient
    threshold_adjust = 0.6 if field == 'title' else 0.7
    
    # Log similarity for debugging
    logging.debug(f"Comparing {field}: '{a}' vs '{b}' -> token similarity={token_similarity:.2f}")
    
    return token_similarity

def load_profile(file_path: str) -> Dict[str, Dict[str, Any]]:
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load JSON file {file_path}: {str(e)}")
    
    print(f"📁 Loading {file_path}...")
    controls = {}
    for control in data.get('controls', []):
        control_id = control.get('id')
        if not control_id:
            logging.warning(f"Control with missing ID in {file_path}")
            continue
        descriptions = control.get('descriptions', {})
        check = descriptions.get('check', '') or control.get('desc', '') or control.get('description', '') or ''
        fix = descriptions.get('fix', '') or control.get('fix', '') or descriptions.get('remediation', '') or ''
        title = control.get('title', '') or ''
        tags = control.get('tags', {})
        nist = tags.get('nist', [])
        nist = [str(n) for n in nist if n is not None] if isinstance(nist, list) else []
        if not check:
            logging.warning(f"No check found for control {control_id} in {file_path}")
        if not fix:
            logging.warning(f"No fix found for control {control_id} in {file_path}")
        if not title:
            logging.warning(f"No title found for control {control_id} in {file_path}")
        controls[control_id] = {
            'check': check.strip(),
            'fix': fix.strip(),
            'title': title.strip(),
            'nist': nist
        }
    print(f"✅ Loaded {len(controls)} controls from {file_path}")
    return controls

def compare_profiles(base: Dict[str, Dict[str, Any]], target: Dict[str, Dict[str, Any]], fuzzy: bool, threshold: float) -> Dict[str, List[Dict[str, Any]]]:
    differences = {
        'removed': [],    # in base but not in target
        'added': [],      # in target but not in base
        'modified': [],   # in both but different title/check/fix
        'reassigned': []  # title/check/fix matches a different control_id (fuzzy only)
    }

    print("🔍 Checking for Removed and Reassigned controls...")
    for cid in set(base) - set(target):
        base_check = base[cid]['check'] or ''
        base_fix = base[cid]['fix'] or ''
        base_title = base[cid]['title'] or ''
        reassigned = False
        if fuzzy:
            matches = []
            for target_cid, target_data in target.items():
                target_check = target_data['check'] or ''
                target_fix = target_data['fix'] or ''
                target_title = target_data['title'] or ''
                title_similarity = is_similar(base_title, target_title, 'title')
                check_similarity = is_similar(base_check, target_check, 'check')
                fix_similarity = is_similar(base_fix, target_fix, 'fix')
                adjusted_threshold = 0.6 if 'title' in [base_title, target_title] else threshold
                if title_similarity >= adjusted_threshold or check_similarity >= threshold or fix_similarity >= threshold:
                    details = []
                    if title_similarity >= adjusted_threshold:
                        details.append(f"Title matched in target {target_cid} (similarity: {title_similarity:.2f}); Baseline title: {base_title}; Target title: {target_title}")
                    if check_similarity >= threshold:
                        details.append(f"Check matched in target {target_cid} (similarity: {check_similarity:.2f}); Baseline check: {base_check}; Target check: {target_check}")
                    if fix_similarity >= threshold:
                        details.append(f"Fix matched in target {target_cid} (similarity: {fix_similarity:.2f}); Baseline fix: {base_fix}; Target fix: {target_fix}")
                    matches.append('; '.join(details))
                else:
                    if base_fix and target_fix:
                        logging.debug(f"No match for {cid} -> {target_cid}: title similarity={title_similarity:.2f}, check similarity={check_similarity:.2f}, fix similarity={fix_similarity:.2f}, threshold={threshold}")
            if matches:
                differences['reassigned'].append({
                    'control_id': cid,
                    'title': base_title,
                    'check': base_check,
                    'fix': base_fix,
                    'nist': base[cid]['nist'],
                    'change': 'reassigned',
                    'details': '; '.join(matches)
                })
                reassigned = True
        if not reassigned:
            differences['removed'].append({
                'control_id': cid,
                'title': base_title,
                'check': base_check,
                'fix': base_fix,
                'nist': base[cid]['nist'],
                'change': 'removed',
                'details': 'No matching control found in target'
            })
    print(f"✅ Found {len(differences['removed'])} removed and {len(differences['reassigned'])} reassigned controls")

    print("🔍 Checking for Added and Reassigned controls...")
    for cid in set(target) - set(base):
        target_check = target[cid]['check'] or ''
        target_fix = target[cid]['fix'] or ''
        target_title = target[cid]['title'] or ''
        reassigned = False
        if fuzzy:
            matches = []
            for base_cid, base_data in base.items():
                base_check = base_data['check'] or ''
                base_fix = base_data['fix'] or ''
                base_title = base_data['title'] or ''
                title_similarity = is_similar(target_title, base_title, 'title')
                check_similarity = is_similar(target_check, base_check, 'check')
                fix_similarity = is_similar(target_fix, base_fix, 'fix')
                adjusted_threshold = 0.6 if 'title' in [target_title, base_title] else threshold
                if title_similarity >= adjusted_threshold or check_similarity >= threshold or fix_similarity >= threshold:
                    details = []
                    if title_similarity >= adjusted_threshold:
                        details.append(f"Title matched in baseline {base_cid} (similarity: {title_similarity:.2f}); Target title: {target_title}; Baseline title: {base_title}")
                    if check_similarity >= threshold:
                        details.append(f"Check matched in baseline {base_cid} (similarity: {check_similarity:.2f}); Target check: {target_check}; Baseline check: {base_check}")
                    if fix_similarity >= threshold:
                        details.append(f"Fix matched in baseline {base_cid} (similarity: {fix_similarity:.2f}); Target fix: {target_fix}; Baseline fix: {base_fix}")
                    matches.append('; '.join(details))
                else:
                    if target_fix and base_fix:
                        logging.debug(f"No match for {cid} -> {base_cid}: title similarity={title_similarity:.2f}, check similarity={check_similarity:.2f}, fix similarity={fix_similarity:.2f}, threshold={threshold}")
            if matches:
                differences['reassigned'].append({
                    'control_id': cid,
                    'title': target_title,
                    'check': target_check,
                    'fix': target_fix,
                    'nist': target[cid]['nist'],
                    'change': 'reassigned',
                    'details': '; '.join(matches)
                })
                reassigned = True
        if not reassigned:
            differences['added'].append({
                'control_id': cid,
                'title': target_title,
                'check': target_check,
                'fix': target_fix,
                'nist': target[cid]['nist'],
                'change': 'added',
                'details': 'No matching control found in baseline'
            })
    print(f"✅ Found {len(differences['added'])} added and {len(differences['reassigned'])} reassigned controls")

    print("🔍 Checking for Modified controls...")
    for cid in set(base) & set(target):
        base_check = base[cid]['check'] or ''
        base_fix = base[cid]['fix'] or ''
        base_title = base[cid]['title'] or ''
        target_check = target[cid]['check'] or ''
        target_fix = target[cid]['fix'] or ''
        target_title = target[cid]['title'] or ''
        
        title_diff = normalize_text(base_title) != normalize_text(target_title)
        check_diff = normalize_text(base_check) != normalize_text(target_check)
        fix_diff = normalize_text(base_fix) != normalize_text(target_fix)
        
        if fuzzy:
            title_similarity = is_similar(base_title, target_title, 'title')
            check_similarity = is_similar(base_check, target_check, 'check')
            fix_similarity = is_similar(base_fix, target_fix, 'fix')
            title_diff = title_diff and title_similarity < 0.6  # Lower threshold for titles
            check_diff = check_diff and check_similarity < threshold
            fix_diff = fix_diff and fix_similarity < threshold
        else:
            title_similarity = None
            check_similarity = None
            fix_similarity = None
        
        if title_diff or check_diff or fix_diff:
            details = []
            if title_diff:
                details.append(f"Title differs (similarity: {title_similarity:.2f})" if fuzzy else "Title differs")
                details.append(f"Baseline title: {base_title}")
                details.append(f"Target title: {target_title}")
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
                'title': target_title,
                'check': target_check,
                'fix': target_fix,
                'nist': target[cid]['nist'],
                'change': 'modified',
                'details': '; '.join(details)
            })
    print(f"✅ Found {len(differences['modified'])} modified controls")

    return differences

def output_to_json(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    try:
        print(f"💾 Writing output to {output_file} (JSON)...")
        with open(output_file, 'w') as f:
            json.dump(diffs, f, indent=4)
        print(f"✅ JSON output written to {output_file}")
    except Exception as e:
        raise ValueError(f"Failed to write JSON output to {output_file}: {str(e)}")

def output_to_md(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    try:
        print(f"💾 Writing output to {output_file} (Markdown)...")
        with open(output_file, 'w') as f:
            f.write('# InSpec Profile Differences\n\n')
            
            for category, items in diffs.items():
                if items:
                    f.write(f'## {category.capitalize()}\n\n')
                    f.write('| Category | Control ID | Title | Check | Fix | NIST Controls | Details |\n')
                    f.write('|----------|------------|-------|-------|-----|---------------|---------|\n')
                    for item in items:
                        nist_str = ', '.join(item['nist']) if item['nist'] else 'None'
                        details = item.get('details', item['change']).replace('|', '\\|')
                        title = (item.get('title', '') or '').replace('|', '\\|')
                        check = (item.get('check', '') or '').replace('|', '\\|')
                        fix = (item.get('fix', '') or '').replace('|', '\\|')
                        f.write(f'| {item["change"]} | {item["control_id"]} | {title} | {check} | {fix} | {nist_str} | {details} |\n')
                    f.write('\n')
        print(f"✅ Markdown output written to {output_file}")
    except Exception as e:
        raise ValueError(f"Failed to write Markdown output to {output_file}: {str(e)}")

def output_to_xlsx(diffs: Dict[str, List[Dict[str, Any]]], output_file: str):
    try:
        print(f"💾 Writing output to {output_file} (Excel)...")
        data = []
        for category, items in diffs.items():
            for item in items:
                data.append({
                    'Category': item['change'],
                    'Control ID': item['control_id'],
                    'Title': item.get('title', '') or '',
                    'Check': item.get('check', '') or '',
                    'Fix': item.get('fix', '') or '',
                    'NIST Controls': ', '.join(item['nist']) if item['nist'] else 'None',
                    'Details': item.get('details', item['change'])
                })
        df = pd.DataFrame(data)
        df.to_excel(output_file, index=False)
        print(f"✅ Excel output written to {output_file}")
    except Exception as e:
        raise ValueError(f"Failed to write Excel output to {output_file}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Compare two InSpec Profile JSON files.')
    parser.add_argument('-b', '--baseline', required=True, help='Path to baseline JSON file')
    parser.add_argument('-t', '--target', required=True, help='Path to target JSON file')
    parser.add_argument('-f', '--fuzzy', type=str, choices=['True', 'False'], default='False', 
                        help='Enable fuzzy matching (True/False, default: False)')
    parser.add_argument('-s', '--similarity', type=float, default=0.7, 
                        help='Fuzzy matching similarity threshold (0.0 to 1.0, default: 0.7)')
    parser.add_argument('-o', '--output', required=True, help='Output file path (.md, .xlsx, .json)')
    
    args = parser.parse_args()
    
    fuzzy = args.fuzzy == 'True'
    
    # Validate similarity threshold
    if not 0.0 <= args.similarity <= 1.0:
        raise ValueError("Similarity threshold must be between 0.0 and 1.0")
    
    print("🚀 Starting InSpec profile comparison...")
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
    print("🎉 Comparison completed!")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {str(e)}")