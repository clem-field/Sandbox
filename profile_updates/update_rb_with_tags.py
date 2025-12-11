#!/usr/bin/env python3
import libraries as lib
import argparse
import os

def normalize_nist(tag):
    tag = tag.upper().replace(' ', '').replace('.', '').replace('(', '').replace(')', '')
    def remove_leading_zeros(m):
        return str(int(m.group(0)))
    tag = lib.re.sub(r'\d+', remove_leading_zeros, tag)
    return tag

def extract_nist_tags(rb_content):
    match = lib.re.search(r'tag\s+[\'"]?nist[\'"]?:\s*\[([^\]]+)\]', rb_content)
    if not match:
        return []
    array_str = match.group(1)
    tags = [tag.strip().strip('"').strip("'") for tag in array_str.split(',')]
    return tags

def find_matching_tags(nist_tags, catalog):
    norm_nist_tags = {normalize_nist(t) for t in nist_tags}
    matched_tags = []
    for entry in catalog:
        tags = entry.get('tags', [])
        if tags:
            tag_nist = tags[0].get('nist', [])
            norm_tag_nist = {normalize_nist(t) for t in tag_nist}
            if norm_nist_tags & norm_tag_nist:
                matched_tags.append(tags[0])
    return matched_tags

def format_tags_for_ruby(tags):
    aggregated_grc = set()
    aggregated_baseline = set()
    aggregated_org_ref = set()
    aggregated_nist_references = set()
    aggregated_related_controls = set()

    for tag_data in tags:
        if 'grc' in tag_data:
            aggregated_grc.add(tag_data['grc'])
        if 'baseline' in tag_data and tag_data['baseline']:
            aggregated_baseline.update(tag_data['baseline'])
        if 'org_ref' in tag_data and tag_data['org_ref']:
            aggregated_org_ref.update(tag_data['org_ref'])
        if 'nist_references' in tag_data and tag_data['nist_references']:
            aggregated_nist_references.update(tag_data['nist_references'])
        if 'related_controls' in tag_data and tag_data['related_controls']:
            aggregated_related_controls.update(tag_data['related_controls'])

    ruby_tags = []
    if aggregated_grc:
        ruby_tags.append(f'tag grc: {lib.json.dumps(sorted(aggregated_grc))}')
    if aggregated_baseline:
        ruby_tags.append(f'tag baseline: {lib.json.dumps(sorted(aggregated_baseline))}')
    if aggregated_org_ref:
        ruby_tags.append(f'tag org_ref: {lib.json.dumps(sorted(aggregated_org_ref))}')
    if aggregated_nist_references:
        ruby_tags.append(f'tag nist_references: {lib.json.dumps(sorted(aggregated_nist_references))}')
    if aggregated_related_controls:
        ruby_tags.append(f'tag related_controls: {lib.json.dumps(sorted(aggregated_related_controls))}')

    return ruby_tags

def update_rb_file(file_path, catalog):
    with open(file_path, 'r', encoding='utf-8') as f:
        rb_content = f.read()
    
    nist_tags = extract_nist_tags(rb_content)
    if not nist_tags:
        print(f"❌  No NIST tags found in {file_path}, skipping...")
        return
    
    matched_tags = find_matching_tags(nist_tags, catalog)
    if not matched_tags:
        print(f"❌  No matching catalog entries for NIST tags {nist_tags} in {file_path}, skipping...")
        return
    
    new_tags = format_tags_for_ruby(matched_tags)
    
    lines = rb_content.splitlines()
    last_tag_line = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('tag '):
            last_tag_line = i
    
    if last_tag_line >= 0:
        lines[last_tag_line + 1:last_tag_line + 1] = new_tags
    else:
        for i, line in enumerate(lines):
            if line.strip().startswith('control '):
                lines[i + 1:i + 1] = new_tags
                break
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')  # Ensure newline at EOF
    print(f"✅  Updated {os.path.basename(file_path)} with {len(new_tags)} new tag(s)")

def main(directory_path, catalog_path):
    if not os.path.isdir(directory_path):
        lib.argparse.ArgumentParser.exit(1, f"Error: Ruby directory not found: {directory_path}\n")
    if not os.path.isfile(catalog_path):
        lib.argparse.ArgumentParser.exit(1, f"Error: Catalog file not found: {catalog_path}\n")

    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = lib.json.load(f)
    
    updated_count = 0
    for filename in sorted(lib.os.listdir(directory_path)):
        if filename.endswith('.rb'):
            file_path = lib.os.path.join(directory_path, filename)
            print(f"Processing: {filename}")
            update_rb_file(file_path, catalog)
            updated_count += 1
    
    print(f"\nDone! Processed {updated_count} .rb files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update InSpec profiles (.rb files) with enriched tags from a catalog using existing NIST tags."
    )
    parser.add_argument(
        "-r", "--ruby-dir",
        required=True,
        help="Path to directory containing .rb control files"
    )
    parser.add_argument(
        "-c", "--catalog",
        required=True,
        help="Path to catalog.json file with enriched tag data"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Increase output verbosity"
    )

    args = parser.parse_args()

    main(args.ruby_dir, args.catalog)