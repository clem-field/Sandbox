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

def find_unmatched_tags(nist_tags, catalog):
    # Normalize the .rb NIST tags
    norm_nist_tags = {normalize_nist(t) for t in nist_tags}
    # Check if any catalog entry matches these normalized tags
    for entry in catalog:
        tags = entry.get('tags', [])
        if tags:
            tag_nist = tags[0].get('nist', [])
            norm_tag_nist = {normalize_nist(t) for t in tag_nist}
            if norm_nist_tags & norm_tag_nist:
                return []  # If any match is found, return empty list (no unmatched tags)
    # If no matches, return the original NIST tags
    return nist_tags

def generate_unmatched_tags_report(directory_path, catalog_path, output_path):
    # Load catalog.json
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = lib.json.load(f)
    
    # Collect unmatched tags for each .rb file
    unmatched_entries = []
    
    # Process each .rb file in the directory
    for filename in lib.os.listdir(directory_path):
        if filename.endswith('.rb'):
            print(f"📂 Processing: {filename}")
            file_path = lib.os.path.join(directory_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                rb_content = f.read()
            
            # Extract NIST tags
            nist_tags = extract_nist_tags(rb_content)
            if not nist_tags:
                print(f"❌ No NIST tags found in {filename}, skipping...")
                continue
            
            # Find unmatched NIST tags
            unmatched_tags = find_unmatched_tags(nist_tags, catalog)
            if unmatched_tags:
                unmatched_entries.append({
                    "file_name": filename,
                    "nist_tags": unmatched_tags
                })
                print(f"⚠️ Unmatched NIST tags in {filename}: {unmatched_tags}")
            else:
                print(f"✅ All NIST tags matched for {filename}")

    # Save results to validate_tagging_controls.json
    output_data = {"unmatched": unmatched_entries}
    with open(output_path, 'w', encoding='utf-8') as f:
        lib.json.dump(output_data, f, indent=4)
    print(f"📝 Saved report to {output_path}")

if __name__ == "__main__":
    directory_path = var.RUBY_DIRECTORY
    catalog_path = var.CATALOG_DIRECTORY
    output_path = lib.os.path.join(var.RUBY_DIRECTORY, "validate_tagging_controls.json")
    generate_unmatched_tags_report(directory_path, catalog_path, output_path)