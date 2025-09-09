import libraries as lib
import locals as var

def normalize_nist(tag):
    tag = tag.upper().replace(' ', '').replace('.', '').replace('(', '').replace(')', '')
    # Remove leading zeros from all numeric sequences
    def remove_leading_zeros(m):
        return str(int(m.group(0)))
    tag = lib.re.sub(r'\d+', remove_leading_zeros, tag)
    return tag

def extract_nist_tags(rb_content):
    # Find the line with tag nist: [...] or tag 'nist': [...]
    match = lib.re.search(r'tag\s+[\'"]?nist[\'"]?:\s*\[([^\]]+)\]', rb_content)
    if not match:
        return []
    # Extract the content inside the array
    array_str = match.group(1)
    # Split by comma, strip quotes and spaces
    tags = [tag.strip().strip('"').strip("'") for tag in array_str.split(',')]
    return tags

def find_matching_tags(nist_tags, catalog):
    # Normalize the .rb NIST tags
    norm_nist_tags = {normalize_nist(t) for t in nist_tags}
    # Collect tag data from catalog.json that matches any of the normalized NIST tags
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
    # Format tag data as Ruby-compatible tag declarations, preserving exact values from catalog
    ruby_tags = []
    for tag_data in tags:
        # Handle each tag field exactly as it appears in catalog.json
        if 'grc' in tag_data:
            ruby_tags.append(f'tag grc: "{tag_data["grc"]}"')
        if 'baseline' in tag_data and tag_data['baseline']:
            # Convert list to Ruby array syntax, preserving exact values
            ruby_tags.append(f'tag baseline: {lib.json.dumps(tag_data["baseline"])}')
        if 'org_ref' in tag_data and tag_data['org_ref']:
            ruby_tags.append(f'tag org_ref: {lib.json.dumps(tag_data["org_ref"])}')
        if 'nist_references' in tag_data and tag_data['nist_references']:
            ruby_tags.append(f'tag nist_references: {lib.json.dumps(tag_data["nist_references"])}')
        if 'related_controls' in tag_data and tag_data['related_controls']:
            ruby_tags.append(f'tag related_controls: {lib.json.dumps(tag_data["related_controls"])}')
    return ruby_tags

def update_rb_file(file_path, catalog):
    with open(file_path, 'r', encoding='utf-8') as f:
        rb_content = f.read()
    
    # Extract NIST tags from the .rb file
    nist_tags = extract_nist_tags(rb_content)
    if not nist_tags:
        print(f"❌  No NIST tags found in {file_path}, skipping...")
        return
    
    # Find matching tag data from catalog
    matched_tags = find_matching_tags(nist_tags, catalog)
    if not matched_tags:
        print(f"❌  No matching catalog entries for NIST tags {nist_tags} in {file_path}, skipping...")
        return
    
    # Format the new tags for Ruby
    new_tags = format_tags_for_ruby(matched_tags)
    
    # Find the last 'tag' line to insert new tags after it
    lines = rb_content.splitlines()
    last_tag_line = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('tag '):
            last_tag_line = i
    
    # Insert new tags after the last tag line
    if last_tag_line >= 0:
        lines[last_tag_line + 1:last_tag_line + 1] = new_tags
    else:
        # If no tag lines exist, append at the top of the control block
        for i, line in enumerate(lines):
            if line.strip().startswith('control '):
                lines[i + 1:i + 1] = new_tags
                break
    
    # Write the updated content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"✅  Updated {file_path} with new tags: {new_tags}")

def main(directory_path, catalog_path):
    # Load catalog.json
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = lib.json.load(f)
    
    # Process each .rb file in the directory
    for filename in lib.os.listdir(directory_path):
        if filename.endswith('.rb'):
            print(f"📂  Processing: {filename}")
            file_path = lib.os.path.join(directory_path, filename)
            update_rb_file(file_path, catalog)

# Example usage:
# Replace with actual paths
# directory_path = 'path/to/rb/files/directory'
# catalog_path = 'path/to/catalog.json'
# update_rb_files_in_directory(directory_path, catalog_path)

if __name__ == "__main__":
    directory_path=var.RUBY_DIRECTORY
    catalog_path=var.CATALOG_DIRECTORY
    main(directory_path, catalog_path)